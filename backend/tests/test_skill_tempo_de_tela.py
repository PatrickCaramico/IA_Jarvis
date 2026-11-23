"""V9.0: tempo de tela por programa (só o nome do programa) e resumo da semana. O Windows é falso."""
import asyncio
from datetime import date, timedelta

import pytest

import skills.tempo_de_tela as tt
from core import safe_io
from core.skills import registry, router
from modules import prefs, tasks, water
from modules.quick_replies import _norm

TODAY = date.today()


def match(phrase):
    return registry.match(_norm(phrase), phrase)


def ask(phrase):
    return asyncio.run(router.try_fast_path(phrase))


def test_phrases(real_skills):
    cases = {
        "quanto tempo eu fiquei no chrome hoje?": {"acao": "programa", "programa": "chrome", "periodo": "hoje"},
        "quanto tempo passei no discord ontem": {"acao": "programa", "programa": "discord", "periodo": "ontem"},
        "quanto tempo eu fiquei no vs code essa semana": {"acao": "programa", "programa": "vs code", "periodo": "semana"},
        "meu tempo de tela hoje": {"acao": "total", "periodo": "hoje"},
        "quais programas eu mais usei essa semana?": {"acao": "total", "periodo": "semana"},
        "quanto tempo eu fiquei no computador hoje": {"acao": "total", "periodo": "hoje"},
        "para de medir meu tempo de tela": {"acao": "desligar"},
    }
    for phrase, args in cases.items():
        hit = match(phrase)
        assert hit and hit[0].name == "tempo_de_tela" and hit[1] == args, phrase
    assert match("resumo da semana")[0].name == "resumo_da_semana"
    assert match("como foi minha semana?")[0].name == "resumo_da_semana"
    for phrase in ("quanto tempo falta para o natal", "quanto tempo demora para chegar no rio", "timer de 5 minutos"):
        hit = match(phrase)
        assert hit is None or hit[0].name not in ("tempo_de_tela", "resumo_da_semana"), phrase


def test_counts_and_answers(real_skills):
    tt.add_seconds({"Chrome": 3725, "Discord": 1800, "Explorador de Arquivos": 30})
    tt.add_seconds({"Chrome": 600}, (TODAY - timedelta(days=1)).isoformat())
    assert ask("quanto tempo eu fiquei no chrome hoje?").speech == "Hoje, o senhor passou 1 hora e 2 minutos no Chrome."
    assert ask("quanto tempo passei no chrome ontem?").speech == "Ontem, o senhor passou 10 minutos no Chrome."
    week = ask("quanto tempo eu fiquei no chrome essa semana")
    assert week.data["segundos"] == 4325
    total = ask("meu tempo de tela hoje")
    assert total.speech.startswith("Hoje, o senhor usou o PC por 1 hora e 32 minutos.") and "Chrome" in total.speech
    assert [r["label"] for r in total.cards[0]["data"]["rows"]] == ["Chrome", "Discord"]  # menos de 1 min não aparece
    assert "Não vi o photoshop" in ask("quanto tempo eu fiquei no photoshop hoje").speech


def test_only_names_and_old_days_are_dropped():
    old = (TODAY - timedelta(days=tt.KEEP_DAYS + 5)).isoformat()
    safe_io.write_json(tt._PATH, {"dias": {old: {"Chrome": 100}}, "xp": {}})
    tt.add_seconds({"Chrome": 60})
    data = safe_io.read_json(tt._PATH)
    assert old not in data["dias"] and list(data["dias"]) == [TODAY.isoformat()]
    assert tt.friendly("chrome.exe") == "Chrome" and tt.friendly("Code.exe") == "VS Code" and tt.friendly("meuapp.exe") == "Meuapp"


def test_switch(real_skills):
    assert "parei de medir" in ask("para de medir meu tempo de tela").speech
    assert prefs.get_all()["screen_time_enabled"] is False
    ask("volta a medir meu tempo de tela")
    assert prefs.get_all()["screen_time_enabled"] is True


def test_service_counts_foreground_and_skips_idle(monkeypatch):
    monkeypatch.setattr(tt, "on_windows", lambda: True)
    seq = [("chrome.exe", 5), ("chrome.exe", 5), ("discord.exe", 999), ("LockApp.exe", 1)]
    monkeypatch.setattr(tt, "foreground_exe", lambda: seq[0][0])
    monkeypatch.setattr(tt, "idle_seconds", lambda: seq.pop(0)[1])
    monkeypatch.setattr(tt, "FLUSH_S", 0)
    monkeypatch.setattr(tt, "snapshot_xp", lambda day=None: None)
    calls = {"n": 0}

    async def fake_sleep(_s):
        calls["n"] += 1
        if calls["n"] >= 4:
            raise asyncio.CancelledError

    monkeypatch.setattr(tt.asyncio, "sleep", fake_sleep)
    tt._pending.clear()
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(tt.tempo_de_tela_loop())
    assert tt.day_apps(TODAY.isoformat()) == {"Chrome": 20}  # discord parado (ausente) e a tela de bloqueio não contam


def test_week_summary(real_skills, monkeypatch):
    t = tasks.add_task("Pagar a conta")
    tasks.complete_task(t["texto"])
    data = water._load_data()
    data["days"] = {TODAY.isoformat(): {"total_ml": 2500, "logs": []}, (TODAY - timedelta(days=2)).isoformat(): {"total_ml": 2100, "logs": []}}
    data["goal_ml"] = 2000
    water._save_data(data)
    safe_io.write_json(tt._PATH, {"dias": {TODAY.isoformat(): {"Chrome": 7200}},
                                  "xp": {(TODAY - timedelta(days=8)).isoformat(): 100, TODAY.isoformat(): 340}})
    s = tt.week_summary()
    assert s["tarefas"] == 1 and s["agua_dias"] == 2 and s["xp"] == 240 and s["apps"][0][0] == "Chrome"
    res = ask("resumo da semana")
    assert res.speech.startswith("Na semana, o senhor concluiu 1 tarefa, bateu a meta de água em 2 de 7 dias e ganhou 240 de XP.")
    assert "Tempo de tela: 2 horas, mais no Chrome." in res.speech
    assert res.cards[0]["data"]["tag"] == "SUA SEMANA"

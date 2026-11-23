"""V8.11: Skill System Guard (programas pesados, fechar programa com "sim" e o vigia)."""
import asyncio

import pytest

from core import confirm, session
from core.skills import executor, registry, router
from core.skills.base import SkillContext
from modules import access
from skills import system_guard as sg

RUNNING = ["chrome.exe", "Discord.exe", "Code.exe", "explorer.exe", "python.exe"]
PROCS = [
    {"name": "chrome.exe", "label": "Google Chrome", "count": 14, "mem_mb": 2150, "mem_percent": 13.0, "cpu_percent": 22.0, "protected": False},
    {"name": "Discord.exe", "label": "Discord", "count": 5, "mem_mb": 420, "mem_percent": 2.6, "cpu_percent": 1.0, "protected": False},
    {"name": "Code.exe", "label": "VS Code", "count": 8, "mem_mb": 900, "mem_percent": 5.5, "cpu_percent": 3.0, "protected": False},
    {"name": "explorer.exe", "label": "explorer", "count": 1, "mem_mb": 150, "mem_percent": 1.0, "cpu_percent": 0.5, "protected": True},
]


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def guard(real_skills, monkeypatch):
    monkeypatch.setattr(sg, "running_names", lambda: list(RUNNING))
    monkeypatch.setattr(sg, "processes", lambda: [dict(p) for p in PROCS])
    closed = []

    def fake_close(names):
        closed.append(list(names))
        return {"closed": [{"name": n, "label": n.replace(".exe", ""), "count": 5} for n in names], "blocked": []}

    from modules import pc_scan

    monkeypatch.setattr(pc_scan, "close_programs", fake_close)
    return closed


def test_match_process_names():
    assert sg.match_process("chrome", RUNNING) == ["chrome.exe"]
    assert sg.match_process("vs code", RUNNING) == ["Code.exe"]
    assert sg.match_process("discord", RUNNING) == ["Discord.exe"]
    assert sg.match_process("photoshop", RUNNING) == []


def test_heavy_programs_answer(guard):
    result = run(router.try_fast_path("o que está pesando no PC?"))
    assert result.speech.startswith("O que mais pesa agora: Google Chrome (2,1 GB de memória, 22% do processador)")
    assert "explorer" not in result.speech  # programas do Windows ficam fora
    assert result.cards[0]["data"]["tag"] == "O QUE ESTÁ PESANDO"


def test_close_program_asks_then_closes(guard):
    result = run(router.try_fast_path("fecha o discord"))
    assert result.pending and result.speech.startswith("Fecho o Discord, senhor?")
    assert guard == []
    assert run(confirm.answer("sim")).startswith("Fechei o Discord (5 processos)")
    assert guard == [["Discord.exe"]]


def test_close_program_no_answer_closes_nothing(guard):
    run(router.try_fast_path("encerra o chrome"))
    assert run(confirm.answer("nao")) == "Certo, senhor. Não mexi em nada."
    assert guard == []


def test_never_closes_windows_programs(guard):
    assert run(router.try_fast_path("fecha o explorer")).speech.startswith("Por segurança, não fecho o explorer")
    reply = run(confirm.answer("sim"))
    assert "Por segurança" in reply and guard == []


def test_close_phrase_only_when_the_program_is_open(guard):
    assert registry.match("fecha o photoshop", "fecha o photoshop") is None  # não está aberto: segue o fluxo
    assert registry.match("fecha a aba", "fecha a aba") is None
    assert registry.match("fechar o timer", "fechar o timer") is None


def test_close_refused_from_another_device(guard):
    result = run(executor.execute("fechar_programa", {"programa": "chrome"}, SkillContext(remote=True)))
    assert result.ok is False and session.pending_action is None


def test_resources_work_with_the_central_locked(guard, credentials):
    access.reset_for_tests(access.LOCKED)
    result = run(router.try_fast_path("como está o uso do processador?", public_only=True))
    assert result.ok and result.speech.startswith("Agora: processador em")
    assert run(router.try_fast_path("o que está pesando no pc", public_only=True)) is None  # nomes = pessoal


def test_watch_needs_sustained_load_and_respects_cooldown():
    w = sg.Watch()
    t0 = 1_000_000.0
    for i in range(9):  # 2 min a 95%
        w.add(t0 + i * sg.SAMPLE_S, 95, 50)
    now = t0 + 8 * sg.SAMPLE_S
    assert w.check(now) == ["cpu"]
    assert w.check(now + sg.SAMPLE_S) == []  # intervalo mínimo entre avisos
    w2 = sg.Watch()
    for i in range(9):
        w2.add(t0 + i * sg.SAMPLE_S, 95 if i != 4 else 40, 50)  # uma queda no meio: não é sustentado
    assert w2.check(now) == []
    w3 = sg.Watch()
    for i in range(3):  # só 30 s: cedo demais
        w3.add(t0 + i * sg.SAMPLE_S, 99, 99)
    assert w3.check(t0 + 2 * sg.SAMPLE_S) == []


def test_alert_text_names_the_hog():
    top = [p for p in PROCS if not p["protected"]]
    text, victim = sg.alert_text("cpu", top, 96, 60)
    assert "acima de 90%" in text and "Google Chrome, com 22%" in text and victim == "chrome.exe"
    text, victim = sg.alert_text("ram", top, 30, 95)
    assert "memória está quase cheia: 95%" in text and victim == "chrome.exe"
    calm = [{**p, "cpu_percent": 2.0} for p in top]
    assert sg.alert_text("cpu", calm, 92, 50)[1] is None


def test_alert_offers_to_close(guard, monkeypatch):
    from core import runtime, speech

    notified, said = [], []
    monkeypatch.setattr(runtime, "notify", lambda kind, title, body: notified.append(body))
    monkeypatch.setattr(speech, "say_quietly", lambda text: _record(said, text))
    run(_alert_then_settle())
    assert notified and "Quer que eu feche?" in notified[0]
    assert session.pending_action["data"]["name"] == "fechar_programa"
    assert session.pending_action["data"]["args"] == {"programa": "chrome"}
    assert run(confirm.answer("sim")).startswith("Fechei o chrome")


async def _record(store, text):
    store.append(text)


async def _alert_then_settle():
    await sg._alert("cpu", 96, 60)
    await asyncio.sleep(0)


def test_watch_toggle(guard):
    assert sg.watch_enabled() is True
    assert "desligado" in run(router.try_fast_path("desliga o vigia do sistema")).speech
    assert sg.watch_enabled() is False
    assert "ligado" in run(router.try_fast_path("liga os alertas do sistema")).speech
    assert sg.watch_enabled() is True

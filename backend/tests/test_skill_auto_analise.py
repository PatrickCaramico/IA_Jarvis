"""V9.2: auto-análise do PC (diagnóstico com sugestões, oferta de fechar com "sim" e o aviso calmo do vigia)."""
import asyncio

import pytest

from core import confirm, session
from core.skills import registry, router
from modules.quick_replies import _norm
from skills import auto_analise as aa
from skills import system_guard as sg

PROCS = [
    {"name": "chrome.exe", "label": "Google Chrome", "count": 38, "mem_mb": 3400, "cpu_percent": 9.0, "protected": False},
    {"name": "Teams.exe", "label": "Teams", "count": 6, "mem_mb": 820, "cpu_percent": 1.0, "protected": False},
    {"name": "Discord.exe", "label": "Discord", "count": 5, "mem_mb": 410, "cpu_percent": 0.5, "protected": False},
    {"name": "Code.exe", "label": "VS Code", "count": 8, "mem_mb": 300, "cpu_percent": 2.0, "protected": False},
    {"name": "explorer.exe", "label": "explorer", "count": 1, "mem_mb": 150, "cpu_percent": 0.2, "protected": True},
]


def snap(**over):
    base = {"cpu": 35.0, "ram": 86.0, "ram_total_gb": 16.0, "swap": 20.0, "procs": [dict(p) for p in PROCS],
            "jarvis_mb": 420.0, "uptime_days": 1.2, "disk_free_gb": 189.0, "disk_free_pct": 40.0, "tabs": None}
    return {**base, **over}


def match(phrase):
    return registry.match(_norm(phrase), phrase)


def test_phrases(real_skills):
    for phrase in ("faz uma auto análise", "jarvis, faz uma autoanalise", "analisa o meu PC", "faz um diagnóstico do sistema",
                   "por que a memória está alta?", "por que o processador tá no talo", "como liberar memória?",
                   "como posso melhorar o desempenho"):
        hit = match(phrase)
        assert hit and hit[0].name == "auto_analise", phrase
    for phrase in ("meu PC está lento", "o que está pesando no PC?", "como está a memória?", "lembre que eu analiso dados"):
        hit = match(phrase)
        assert hit is None or hit[0].name != "auto_analise", phrase


def test_diagnose_high_memory():
    r = aa.diagnose(snap(tabs=24))
    assert r["speech"].startswith("Memória em 86%, alta, e processador em 35%.")
    assert "O Google Chrome é o que mais pesa: 3,3 GB (o navegador do JARVIS está com 24 abas)" in r["speech"]
    assert r["offer"]["label"] == "Teams"  # o maior que não é navegador e é seguro fechar
    assert r["speech"].endswith("Quer que eu feche o Teams, que está com 820 MB? Diga sim.")
    assert any("segundo plano" in t and "Teams (820 MB)" in t and "Discord (410 MB)" in t for t in r["tips"])


def test_diagnose_other_tips_and_calm():
    r = aa.diagnose(snap(ram=91, jarvis_mb=1300, uptime_days=9, swap=70, ram_total_gb=8, disk_free_pct=6, disk_free_gb=14))
    joined = " ".join(r["tips"])
    for part in ("Eu mesmo estou usando 1,3 GB", "ligado há 9 dias", "usando o disco como memória", "Com 8 GB",
                 "disco está quase cheio (14 GB livres)"):
        assert part in joined, part
    calm = aa.diagnose(snap(ram=48, cpu=12, procs=[PROCS[3], PROCS[4]]))
    assert calm["speech"] == "Está tudo tranquilo, senhor: memória em 48% e processador em 12%."
    assert calm["offer"] is None and calm["tips"] == []


def test_runs_offers_and_closes_with_yes(real_skills, monkeypatch):
    monkeypatch.setattr(aa, "snapshot", lambda: snap())
    closed = []
    monkeypatch.setattr(sg, "running_names", lambda: ["Teams.exe", "chrome.exe"])

    def fake_close(names):
        closed.append(list(names))
        return {"closed": [{"name": n, "label": n.replace(".exe", ""), "count": 1} for n in names], "blocked": []}

    from modules import pc_scan

    monkeypatch.setattr(pc_scan, "close_programs", fake_close)
    res = asyncio.run(router.try_fast_path("faz uma auto análise"))
    assert "Quer que eu feche o Teams" in res.speech
    assert res.cards[0]["data"]["tag"] == "AUTO-ANÁLISE"
    assert session.pending_action["data"]["name"] == "fechar_programa"
    assert asyncio.run(confirm.answer("sim")).startswith("Fechei o Teams")
    assert closed == [["Teams.exe"]]


def test_watch_soft_memory_alert():
    w = sg.Watch()
    t0 = 1_000_000.0
    steps = int(sg.RAM_SOFT_WINDOW_S // sg.SAMPLE_S) + 1
    for i in range(steps):  # 3 min a 87%: aviso calmo, não o crítico
        w.add(t0 + i * sg.SAMPLE_S, 30, 87)
    now = t0 + (steps - 1) * sg.SAMPLE_S
    assert w.check(now) == ["ram_suave"]
    assert w.check(now + 40 * 60) == []  # no máximo 1 vez por hora


@pytest.mark.parametrize("ram", [87.0])
def test_soft_alert_is_screen_only(real_skills, monkeypatch, ram):
    from core import runtime, speech

    monkeypatch.setattr(aa, "snapshot", lambda: snap(ram=ram))
    sent, notified, said = [], [], []

    async def fake_broadcast(e):
        sent.append(e)

    async def fake_say(text):
        said.append(text)

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    monkeypatch.setattr(runtime, "notify", lambda kind, title, body: notified.append(body))
    monkeypatch.setattr(speech, "say_quietly", fake_say)
    asyncio.run(sg._alert("ram_suave", 30, ram))
    assert notified and notified[0].startswith("Senhor, a memória está em 87% há alguns minutos. O Google Chrome")
    assert sent and sent[0]["type"] == "alert" and said == []  # só tela e celular, sem voz
    assert session.pending_action is None or session.pending_action.get("data", {}).get("name") != "fechar_programa"

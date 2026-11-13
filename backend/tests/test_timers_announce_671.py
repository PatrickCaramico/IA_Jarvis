"""V6.7.1: timers com nome (cancelar um, aumentar, quanto falta, sobrevivem ao reinício) e aviso geral."""
import asyncio
import json
import time

import pytest

from modules import announce, tools
from modules.quick_replies import _norm


@pytest.fixture(autouse=True)
def _isolate_timers(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "_TIMERS_PATH", tmp_path / "timers.json")
    tools._timers.clear()
    yield
    for job in tools._timers.values():
        job["task"].cancel()
    tools._timers.clear()


def timer(text):
    return tools._h_timer(text, _norm(text), len(text.split()), "")


def test_named_timers():
    async def run():
        assert "arroz" in await timer("timer de 15 minutos para o arroz")
        assert "ovo" in await timer("timer de 8 minutos para o ovo")
        asked = await timer("cancela o timer")
        assert "Qual deles" in asked and "arroz" in asked and "ovo" in asked
        left = await timer("quanto falta pro arroz?")
        assert left.startswith("Faltam") and "arroz" in left
        more = await timer("aumenta 5 minutos no timer do arroz")
        assert "mais 5 minutos" in more and "arroz" in more
        arroz = next(j for j in tools._timers.values() if j["label"].endswith("arroz"))
        assert 19 * 60 < arroz["ends"] - time.monotonic() <= 20 * 60
        assert "arroz" in await timer("cancela o timer do arroz")
        assert [j["label"] for j in tools._timers.values()] == ["o ovo"] or [j["label"] for j in tools._timers.values()] == ["ovo"]
        saved = json.loads(tools._TIMERS_PATH.read_text(encoding="utf-8"))
        assert len(saved) == 1
        assert "Cancelei 1 timer" in await timer("cancela todos os timers")
    asyncio.run(run())


def test_timers_survive_restart():
    said = []

    async def fake_announce(text):
        said.append(text)

    async def run():
        now = time.time()
        tools._TIMERS_PATH.write_text(json.dumps([
            {"id": 7, "label": "bolo", "ends_at": now + 300, "total_seconds": 600},
            {"id": 8, "label": "chá", "ends_at": now - 60, "total_seconds": 300},
            {"id": 9, "label": "antigo", "ends_at": now - 3600, "total_seconds": 300},
        ]), encoding="utf-8")
        old = tools._announce
        tools.set_announcer(fake_announce)
        try:
            await tools.restore_timers()
        finally:
            tools.set_announcer(old)
        assert [j["label"] for j in tools._timers.values()] == ["bolo"]
        assert said == ["Enquanto eu reiniciava, terminou: chá."]
    asyncio.run(run())


@pytest.mark.parametrize("text,expected", [
    ("Jarvis, avisa em todos os aparelhos que o almoço está pronto", "O almoço está pronto"),
    ("avisa todo mundo que o filme vai começar", "O filme vai começar"),
    ("Jarvis, faz um anúncio: reunião em 5 minutos.", "Reunião em 5 minutos"),
    ("anuncia que estou saindo", "Estou saindo"),
])
def test_announce_parse(text, expected):
    assert announce.parse(text) == expected


def test_announce_not_triggered_by_other_phrases():
    for text in ("me avisa em 10 minutos", "avisa a Ana no WhatsApp que eu chego às 8", "o que é um anúncio"):
        assert announce.parse(text) is None


def test_announce_reaches_everyone(monkeypatch):
    from core import runtime, speech

    events, spoken = [], []

    async def fake_broadcast(ev):
        events.append(ev)

    async def fake_say(text):
        spoken.append(text)

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    monkeypatch.setattr(speech, "say_quietly", fake_say)
    reply = asyncio.run(announce.handle_voice("avisa em todos os aparelhos que o almoço está pronto"))
    assert reply == "Avisado em todos os aparelhos, senhor."
    assert {"type": "speak_everywhere", "text": "O almoço está pronto."} in events
    assert spoken == ["O almoço está pronto."]
    assert any(n["kind"] == "announce" for n in runtime.NOTIFY_FEED)

"""V8.12.4: resposta local do chat sai na hora; os cartões da internet chegam depois (não seguram a resposta)."""
import asyncio
import time

from core import reactive_cards, runtime, session, speech, turns


def _setup(monkeypatch, cards_delay):
    sent = []

    async def fake_broadcast(event):
        sent.append((time.perf_counter(), event))

    async def fake_speak(text, *a, **k):
        session.busy = False

    async def slow_cards(message, reply):
        await asyncio.sleep(cards_delay)
        return [{"type": "weather", "data": {"temperature": 25}}]

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    monkeypatch.setattr(speech, "speak", fake_speak)
    monkeypatch.setattr(reactive_cards, "detect_reactive_cards", slow_cards)
    monkeypatch.setattr(turns, "CARDS_WAIT_SECONDS", 0.05)
    monkeypatch.setattr(session, "busy", False)
    return sent


def test_local_reply_does_not_wait_for_slow_cards(monkeypatch, real_skills):
    sent = _setup(monkeypatch, cards_delay=0.4)

    async def scenario():
        start = time.perf_counter()
        out = await turns.handle_turn("olá", routine=False)
        took = time.perf_counter() - start
        await asyncio.sleep(0.6)  # deixa os cartões atrasados chegarem
        return out, took, start

    out, took, start = asyncio.run(scenario())
    assert out["source"] == "local" and out["response"].startswith("Olá")
    assert took < 0.3  # antes esperava os 0,4 s dos cartões
    responses = [e for _, e in sent if e.get("type") == "response"]
    assert responses and responses[0]["cards"] == []
    late = [e for _, e in sent if e.get("type") == "response_cards"]
    assert late and late[0]["text"] == out["response"] and late[0]["cards"][0]["type"] == "weather"


def test_fast_cards_still_come_with_the_reply(monkeypatch, real_skills):
    sent = _setup(monkeypatch, cards_delay=0)
    monkeypatch.setattr(turns, "CARDS_WAIT_SECONDS", 1)
    out = asyncio.run(turns.handle_turn("oi jarvis", routine=False))
    assert out["cards"] and out["cards"][0]["type"] == "weather"
    assert not [e for _, e in sent if e.get("type") == "response_cards"]

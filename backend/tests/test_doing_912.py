"""V9.1.2: a central mostra com o que o JARVIS está ocupado (fila, habilidade, IA)."""
import asyncio

from fastapi.testclient import TestClient

import main
from core import runtime, session, speech, turn_queue, turns
from modules import access, tools


def test_doing_is_stored_and_broadcast(monkeypatch):
    sent = []

    async def fake_broadcast(event):
        sent.append(event)

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    asyncio.run(runtime.doing("pensando com a inteligência artificial"))
    assert session.doing == "pensando com a inteligência artificial"
    assert sent == [{"type": "doing", "text": "pensando com a inteligência artificial"}]


def test_queue_says_it_is_waiting(monkeypatch):
    sent = []

    async def fake_broadcast(event):
        sent.append(event)

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    monkeypatch.setattr(turn_queue, "WAIT_LIMIT_S", 0.05)
    monkeypatch.setattr(turn_queue, "POLL_S", 0.01)
    turn_queue.cancel_all()
    session.busy = True
    try:
        assert asyncio.run(turn_queue.wait_turn("que horas são")) == "timeout"
    finally:
        session.busy = False
        turn_queue.cancel_all()
    assert {"type": "doing", "text": "esperando o pedido anterior terminar"} in sent


def test_ai_turn_announces_thinking(monkeypatch):
    seen = []

    async def fake_doing(text):
        seen.append(text)

    async def fake_generate(message, on_step=None, **kwargs):
        return "Claro, senhor."

    async def quiet(*_a, **_k):
        return None

    monkeypatch.setattr(runtime, "doing", fake_doing)
    monkeypatch.setattr(turns, "generate_jarvis_response", fake_generate)
    monkeypatch.setattr(speech, "speak", quiet)
    monkeypatch.setattr(speech, "filler_loop", quiet)
    monkeypatch.setattr(tools, "run", quiet)
    access.unlock("test")
    session.busy = False
    with TestClient(main.app) as client:
        assert client.post("/api/chat", json={"message": "me conta uma curiosidade sobre o mar"}).status_code == 200
    assert "cuidando do pedido" in seen and seen[-1] == "pensando com a inteligência artificial"

# V8.11.1: pedido cancelado no meio devolve a central para "em espera" (antes ela ficava presa em PROCESSANDO).
import asyncio

from core import runtime, session, turns


def _run(monkeypatch, result, busy):
    sent = []

    async def fake_turn(message, routine, force_deep=False):
        # o "processando" do turno sai depois do "em espera" do /api/cancel
        await runtime.manager.broadcast({"type": "state", "state": "processing"})
        session.busy = busy
        return result

    async def fake_broadcast(event):
        sent.append(event)

    monkeypatch.setattr(turns, "_handle_turn", fake_turn)
    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    monkeypatch.setattr(session, "busy", False)
    out = asyncio.run(turns.handle_turn("quais as notícias", routine=False))
    return out, [e.get("state") for e in sent if e.get("type") == "state"]


def test_canceled_turn_returns_the_screen_to_idle(monkeypatch):
    out, states = _run(monkeypatch, {"status": "canceled"}, busy=False)
    assert out == {"status": "canceled"}
    assert states == ["processing", "idle"]  # o último estado é "em espera"


def test_does_not_step_on_a_newer_request(monkeypatch):
    # cancelou e já pediu outra coisa: quem manda na tela é o pedido novo
    _out, states = _run(monkeypatch, {"status": "canceled"}, busy=True)
    assert states == ["processing"]


def test_normal_answer_is_untouched(monkeypatch):
    out, states = _run(monkeypatch, {"status": "ok", "response": "Pronto, senhor."}, busy=False)
    assert out["response"] == "Pronto, senhor."
    assert states == ["processing"]

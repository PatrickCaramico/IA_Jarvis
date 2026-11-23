"""V9.0: voz que começa antes (primeiras frases do streaming) e fila de pedidos (no lugar do "ocupado")."""
import asyncio

import pytest
from fastapi.testclient import TestClient

import main
from core import early_voice, session, speech, turn_queue, turns
from modules import access, tools


# ------------------------------------------------------------------ primeiras frases
def test_first_sentences():
    fs = early_voice.first_sentences
    assert fs("Claro, senhor. A capital da Austrália é Camberra, não Sydney. Ela fica") == \
        "Claro, senhor. A capital da Austrália é Camberra, não Sydney."
    assert fs("Sim, senhor. Ok") == ""  # curto demais: espera
    assert fs("A previsão para Maceió hoje é de sol") == ""  # frase ainda sem fim
    assert fs("O Sr. Silva ligou. Ele pediu retorno amanhã cedo, senhor. E") == "O Sr. Silva ligou. Ele pediu retorno amanhã cedo, senhor."
    assert fs("1. Primeiro passo é abrir o painel de controle do Windows. 2.") == "1. Primeiro passo é abrir o painel de controle do Windows."
    assert fs("- item um da lista grande. - item dois") == ""  # lista: resposta inteira
    long = ("Frase número um bem comprida para passar do limite de caracteres. " * 6)
    head = fs(long + "fim")
    assert head and len(head) <= early_voice.MAX_HEAD and head.endswith(".")


def test_rest_without_repeating():
    ev = early_voice.EarlyVoice()
    assert ev.rest("Tudo.") == "Tudo."  # não começou: fala tudo
    ev.head, ev.task = "Claro, senhor. A capital é **Camberra**.", object()
    assert ev.rest("Claro, senhor. A capital é **Camberra**. Ela foi planejada.") == "Ela foi planejada."
    assert ev.rest("Outra resposta completamente diferente.") == "Outra resposta completamente diferente."
    ev.restarted = True
    assert ev.rest("Claro, senhor. A capital é Camberra. Mais.").startswith("Claro")


@pytest.fixture
def chat(monkeypatch):
    spoken, after = [], []

    async def fake_speak(text, release_busy=True, idle_after=True):
        spoken.append(text)
        if release_busy:
            session.busy = False

    async def fake_after(first, rest):
        await first
        after.append(rest)
        session.busy = False

    async def quiet(*_a, **_k):
        return None

    async def no_tool(*_a, **_k):
        return None

    monkeypatch.setattr(speech, "speak", fake_speak)
    monkeypatch.setattr(speech, "speak_after", fake_after)
    monkeypatch.setattr(speech, "filler_loop", quiet)
    monkeypatch.setattr(tools, "run", no_tool)
    access.unlock("test")
    session.busy = False
    return spoken, after


def test_turn_speaks_head_while_streaming_and_then_rest(chat, monkeypatch):
    spoken, after = chat
    final = "Claro, senhor. A capital da Austrália é Camberra, não Sydney. Ela foi planejada para ser a capital."

    async def fake_generate(message, on_step=None, on_stream=None, **kwargs):
        for cut in (20, 70, len(final)):
            on_stream({"type": "response_stream", "seq": cut, "text": final[:cut]})
            await asyncio.sleep(0)
        return final

    monkeypatch.setattr(turns, "generate_jarvis_response", fake_generate)
    with TestClient(main.app) as client:
        r = client.post("/api/chat", json={"message": "qual a capital da australia e por que nao sydney?"}).json()
    assert r["response"] == final
    assert spoken == ["Claro, senhor. A capital da Austrália é Camberra, não Sydney."]
    assert after == ["Ela foi planejada para ser a capital."]


def test_short_answer_still_speaks_whole(chat, monkeypatch):
    spoken, after = chat

    async def fake_generate(message, on_step=None, on_stream=None, **kwargs):
        on_stream({"type": "response_stream", "seq": 1, "text": "São 3 horas, senhor."})
        return "São 3 horas, senhor."

    monkeypatch.setattr(turns, "generate_jarvis_response", fake_generate)
    with TestClient(main.app) as client:
        client.post("/api/chat", json={"message": "me explica uma coisa qualquer de teste"})
    assert spoken == ["São 3 horas, senhor."] and after == []


# ------------------------------------------------------------------ fila
@pytest.fixture
def clean_queue():
    turn_queue.cancel_all()
    session.busy = False
    yield
    turn_queue.cancel_all()
    session.busy = False


def test_queue_serves_in_order(clean_queue, monkeypatch):
    monkeypatch.setattr(turn_queue, "POLL_S", 0.01)

    async def scenario():
        session.busy = True
        order = []

        async def req(name):
            outcome = await turn_queue.wait_turn(name)
            order.append((name, outcome))
            if outcome == "ok":
                session.busy = True
                await asyncio.sleep(0.03)
                session.busy = False

        tasks = [asyncio.create_task(req(n)) for n in ("a", "b", "c")]
        await asyncio.sleep(0.03)
        assert turn_queue.waiting() == 3
        assert await turn_queue.wait_turn("d") == "full"
        session.busy = False
        await asyncio.gather(*tasks)
        return order

    assert asyncio.run(scenario()) == [("a", "ok"), ("b", "ok"), ("c", "ok")]


def test_queue_cancel_and_timeout(clean_queue, monkeypatch):
    monkeypatch.setattr(turn_queue, "POLL_S", 0.01)

    async def scenario():
        session.busy = True
        waiter = asyncio.create_task(turn_queue.wait_turn("x"))
        await asyncio.sleep(0.02)
        turn_queue.cancel_all()
        first = await waiter
        monkeypatch.setattr(turn_queue, "WAIT_LIMIT_S", 0.05)
        second = await turn_queue.wait_turn("y")
        return first, second, turn_queue.waiting()

    assert asyncio.run(scenario()) == ("canceled", "timeout", 0)


def test_cancel_route_empties_queue(clean_queue):
    turn_queue._waiting.extend([101, 102])
    with TestClient(main.app) as client:
        access.unlock("test")
        assert client.post("/api/cancel").status_code == 200
    assert turn_queue.waiting() == 0

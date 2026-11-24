"""V9.5.1: comandos no bloqueio. "Abre o clima" abre a janela do cartão (além de falar) e um pedido feito
enquanto o JARVIS ainda fala a resposta anterior é atendido (antes voltava 409 e sumia em silêncio)."""
import asyncio

from core import runtime, session, speech, turns
from modules import access, sentinel, tools

FAKE = {"data": {"daily": {"temperature_2m_max": [30, 28], "temperature_2m_min": [20, 19], "weather_code": [61, 3],
                           "precipitation_probability_max": [90, 20]},
                 "current": {"weather_code": 61, "temperature_2m": 25}}, "place": "São Paulo"}


def ask(text, state="locked"):
    return asyncio.run(sentinel.classify_and_answer(text, state))


def test_frases_que_abrem_cartoes():
    assert sentinel.open_card_intent("abrir clima") == "weather"
    assert sentinel.open_card_intent("abre o clima") == "weather"
    assert sentinel.open_card_intent("mostra a previsao do tempo") == "weather"
    assert sentinel.open_card_intent("abre o mercado") == "rates"
    assert sentinel.open_card_intent("mostra o dolar") == "rates"
    assert sentinel.open_card_intent("abre a agua") == "water"
    assert sentinel.open_card_intent("abre as manchetes") == "headline"
    assert sentinel.open_card_intent("mostra os sistemas") == "status"


def test_frases_que_nao_abrem():
    assert sentinel.open_card_intent("como esta o clima") is None  # pergunta: só responde
    assert sentinel.open_card_intent("abre o spotify") is None  # é o programa do PC (protegido)
    assert sentinel.open_card_intent("abre as minhas tarefas") is None
    assert sentinel.open_card_intent("abre o clima de amanha em sao paulo e me fala tudo com detalhes") is None


def test_abrir_clima_fala_e_abre(monkeypatch):
    monkeypatch.setattr(tools, "_fetch_weather", lambda city: FAKE)
    r = ask("jarvis, abrir clima")
    assert r["public"] and not r["requires_unlock"]
    assert r["open"] == "weather" and r["card"] is None  # a janela do cartão, sem a mini janela junto
    assert "25 graus" in r["reply"]


def test_abrir_mercado_confirma_e_abre():
    r = ask("abre o mercado")
    assert r["open"] == "rates" and r["public"]
    assert r["reply"] == "Aqui está o mercado, senhor."


def test_pergunta_normal_nao_abre(monkeypatch):
    monkeypatch.setattr(tools, "_fetch_weather", lambda city: FAKE)
    r = ask("como está o clima?")
    assert r.get("open") is None and r["card"] is not None


def test_spotify_continua_protegido():
    assert ask("jarvis abre o spotify")["requires_unlock"]


def test_pedido_enquanto_fala_e_atendido(monkeypatch):
    sent = []

    async def fake_broadcast(msg):
        sent.append(msg)

    interrupted = []

    async def fake_interrupt():
        interrupted.append(True)
        session.busy = False

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    monkeypatch.setattr(speech, "only_speaking", lambda: True)
    monkeypatch.setattr(speech, "interrupt", fake_interrupt)
    monkeypatch.setattr(speech, "speak", lambda text, **kw: asyncio.sleep(0))
    monkeypatch.setattr(access, "effective_state", lambda: "locked")
    session.busy = True
    try:
        r = asyncio.run(turns.handle_restricted_turn("abre o mercado"))
    finally:
        session.busy = False
    assert interrupted == [True]
    assert r["open"] == "rates"
    assert any(m.get("type") == "sentinel_reply" and m.get("open") == "rates" for m in sent)


def test_ocupado_de_verdade_responde_com_calma(monkeypatch):
    sent = []

    async def fake_broadcast(msg):
        sent.append(msg)

    async def no_sleep(_s):
        return None

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    monkeypatch.setattr(speech, "only_speaking", lambda: False)
    monkeypatch.setattr(turns.asyncio, "sleep", no_sleep)
    monkeypatch.setattr(access, "effective_state", lambda: "locked")
    session.busy = True
    try:
        r = asyncio.run(turns.handle_restricted_turn("abre o clima"))
    finally:
        session.busy = False
    assert r["status"] == "busy"
    assert r["response"].startswith("Um instante, senhor")
    assert sent and sent[0]["type"] == "sentinel_reply"

"""V6.8: sub-agentes (rotas no Google Maps e pesquisa no YouTube), abrindo no aparelho que pediu."""
import asyncio

import pytest

from core import runtime, voice_route
from modules import agents, cloud_sync, tools


@pytest.fixture
def capture(monkeypatch):
    events, opened = [], []

    async def fake_broadcast(ev):
        events.append(ev)

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    monkeypatch.setattr(tools, "_open_in_default_browser", lambda url: opened.append(url))
    return events, opened


def ask(text):
    return asyncio.run(agents.handle(text))


def test_route_save_then_go_opens_maps_on_pc(capture):
    events, opened = capture
    assert "trabalho fica em Av. Paulista, 1000 - São Paulo" in ask("Meu trabalho fica na Av. Paulista, 1000 - São Paulo")
    reply = ask("Jarvis, quero ir para o trabalho de ônibus")
    assert reply == "Abrindo a rota para trabalho de transporte público no Google Maps, senhor."
    assert opened == ["https://www.google.com/maps/dir/?api=1&destination=Av.%20Paulista%2C%201000%20-%20S%C3%A3o%20Paulo&travelmode=transit"]
    statuses = [e["status"] for e in events if e["type"] == "agent"]
    assert statuses[-2:] == ["working", "done"]


def test_opens_on_the_phone_that_asked(capture):
    events, opened = capture
    token = voice_route.set_target("celular123")
    try:
        assert "aeroporto de Guarulhos" in ask("rota para o aeroporto de Guarulhos")
    finally:
        voice_route.reset(token)
    assert opened == []
    ev = next(e for e in events if e["type"] == "open_url")
    assert ev["client_id"] == "celular123" and "destination=aeroporto%20de%20Guarulhos" in ev["url"]


def test_asks_for_unknown_personal_place_and_ignores_non_places(capture):
    _, opened = capture
    assert "Ainda não sei onde fica academia" in ask("me leva pra academia")
    for text in ("quero ir dormir", "vou ir para a cama", "meu time é o Palmeiras", "que horas são"):
        assert ask(text) is None
    assert opened == []


def test_list_and_forget_places(capture):
    ask("o endereço da academia é Rua Augusta 500")
    assert "academia, Rua Augusta 500" in ask("quais são meus lugares?")
    assert "esqueci" in ask("esquece o endereço da academia")
    assert agents.load_places() == {}


def test_youtube_agent(capture):
    _, opened = capture
    assert ask("abre o YouTube e pesquisa receita de bolo de cenoura") == "Pesquisando receita de bolo de cenoura no YouTube, senhor."
    assert ask("procura lofi hip hop no youtube") == "Pesquisando lofi hip hop no YouTube, senhor."
    assert opened[-1] == "https://www.youtube.com/results?search_query=lofi+hip+hop"
    assert ask("toca Coldplay no Spotify") is None


def test_places_go_to_cloud_and_come_back():
    agents.save_place("trabalho", "Av. Paulista, 1000")
    assert cloud_sync.snapshot()["perfil"]["lugares"] == {"trabalho": "Av. Paulista, 1000"}
    assert cloud_sync.apply_op({"op": "place_set", "nome": "academia", "endereco": "Rua Augusta 500"})
    assert agents.load_places()["academia"] == "Rua Augusta 500"

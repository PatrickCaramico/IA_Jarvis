"""Modo automático (como a Alexa): pergunta factual vai para a IA com busca no Google, sem perguntar."""
import pytest
from fastapi.testclient import TestClient

import main
from core import session, speech, turns
from modules import access, prefs, tools
from services import llm_orchestrator


@pytest.fixture
def chat(monkeypatch):
    calls = []

    async def fake_generate(message, on_step=None, **kwargs):
        calls.append({"message": message, **kwargs})
        return "Segundo o ge, o Palmeiras venceu por 2 a 0, senhor."

    async def quiet(*_a, **_k):
        return None

    async def no_tool(*_a, **_k):
        return None

    monkeypatch.setattr(turns, "generate_jarvis_response", fake_generate)
    monkeypatch.setattr(speech, "speak", quiet)
    monkeypatch.setattr(speech, "filler_loop", quiet)
    monkeypatch.setattr(tools, "run", no_tool)
    access.unlock("test")
    session.busy = False
    client = TestClient(main.app)

    def ask(text):
        session.busy = False
        return client.post("/api/chat", json={"message": text}).json()

    return ask, calls


def test_auto_e_o_padrao_e_pesquisa_sem_perguntar(chat):
    ask, calls = chat
    assert prefs.get_search_mode() == "auto"
    r = ask("quem ganhou o jogo do Palmeiras ontem?")
    assert r.get("action") != "ask_search_mode"
    assert calls and calls[-1]["web"] is True and calls[-1]["deep"] is False
    assert "ge" in r["response"]


def test_conversa_comum_nao_pesquisa(chat):
    ask, calls = chat
    ask("me conta uma curiosidade sobre o espaço")
    assert calls[-1]["web"] is False


def test_modo_perguntar_continua_disponivel(chat):
    ask, calls = chat
    prefs.set_search_mode("ask")
    r = ask("quem ganhou o jogo do Palmeiras ontem?")
    assert r["action"] == "ask_search_mode" and not calls


def test_outro_provedor_pesquisa_pelo_gemini(monkeypatch):
    used = {}
    monkeypatch.setattr(prefs, "get_llm_config", lambda: ("anthropic", "direto"))
    monkeypatch.setattr(llm_orchestrator.settings, "GEMINI_API_KEY", "x")
    monkeypatch.setattr(llm_orchestrator, "_call_gemini", lambda *a, **k: used.setdefault("gemini", k) or "ok")
    monkeypatch.setattr(llm_orchestrator, "_call_anthropic", lambda *a, **k: used.setdefault("anthropic", True) or "ok")
    llm_orchestrator._call_llm("pergunta", None, [], deep=True)
    assert used == {"gemini": {"deep": True}}
    llm_orchestrator._call_llm("pergunta", None, [], deep=False)
    assert used.get("anthropic") is True

"""V8.2: Cérebro automático grátis (Groq + Gemini) e a chave colada no app (salva só no .env do PC)."""
import pytest
from fastapi.testclient import TestClient

from config import settings
from modules import access, brain_keys, prefs
from services import llm_orchestrator as llm

GROQ = "gsk_" + "a" * 40
GEMINI = "AIza" + "b" * 35


@pytest.fixture
def keys(monkeypatch, tmp_path):
    env = tmp_path / ".env"
    env.write_text("LLM_PROVIDER=gemini\nGEMINI_API_KEY=antiga\n", encoding="utf-8")
    monkeypatch.setattr(settings, "ENV_FILE", env)
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")
    llm._provider_rest.clear()
    return env


def test_save_key_validates_and_writes_env_only(keys):
    with pytest.raises(ValueError, match="gsk_"):
        brain_keys.save_key("groq", "123")
    st = brain_keys.save_key("groq", f'  "{GROQ}" ')
    assert settings.GROQ_API_KEY == GROQ
    assert f"GROQ_API_KEY={GROQ}" in keys.read_text()
    assert GROQ not in str(st)  # a chave nunca volta para a tela
    brain_keys.save_key("gemini", GEMINI)
    text = keys.read_text()
    assert text.count("GEMINI_API_KEY=") == 1 and "antiga" not in text and "LLM_PROVIDER=gemini" in text
    brain_keys.remove_key("groq")
    assert "GROQ_API_KEY" not in keys.read_text() and settings.GROQ_API_KEY == ""


def test_auto_falls_back_when_groq_hits_limit(keys, monkeypatch):
    monkeypatch.setattr(settings, "GROQ_API_KEY", GROQ)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", GEMINI)
    calls = []

    def groq(prompt, frame, history):
        calls.append("groq")
        raise RuntimeError("429 rate_limit_exceeded: tokens per day")

    def gemini(prompt, frame, history, deep=False):
        calls.append("gemini")
        return "Oi do Gemini"

    monkeypatch.setattr(llm, "_call_groq", groq)
    monkeypatch.setattr(llm, "_call_gemini", gemini)
    monkeypatch.setattr(prefs, "get_llm_config", lambda: ("auto", "direto"))
    assert llm._call_llm("oi", None, []) == "Oi do Gemini"
    assert calls == ["groq", "gemini"] and llm.last_provider() == "gemini"
    assert llm.provider_rest("groq") > 1000  # limite do dia: fica de lado
    calls.clear()
    llm._call_llm("de novo", None, [])
    assert calls == ["gemini"]  # nem tenta a Groq enquanto descansa


def test_auto_prefers_gemini_for_web_search_and_images(keys, monkeypatch):
    monkeypatch.setattr(settings, "GROQ_API_KEY", GROQ)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", GEMINI)
    assert llm._auto_order(deep=True, frame=False)[0] == "gemini"
    assert llm._auto_order(deep=False, frame=True)[0] == "gemini"
    assert llm._auto_order(deep=False, frame=False)[0] == "groq"
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")
    assert llm._auto_order(False, False) == ["gemini"]


def test_routes_status_key_and_test(keys, monkeypatch):
    import main

    access.reset_for_tests(access.UNLOCKED)
    monkeypatch.setattr(prefs, "update", lambda patch=None, **kw: None)
    c = TestClient(main.app)
    st = c.get("/api/brain").json()
    assert [p["id"] for p in st["provedores"]] == ["groq", "gemini"] and not st["provedores"][0]["conectada"]
    assert c.post("/api/brain/key", json={"provedor": "groq", "chave": "x"}).status_code == 400
    assert c.post("/api/brain/key", json={"provedor": "zzz", "chave": GROQ}).status_code == 404
    r = c.post("/api/brain/key", json={"provedor": "groq", "chave": GROQ})
    assert r.status_code == 200 and r.json()["provedores"][0]["conectada"] is True and GROQ not in r.text
    monkeypatch.setattr(llm, "ask_with_provider", lambda p, prov: f"teste {prov}")
    t = c.post("/api/desk/test-ai", json={"provedor": "groq"}).json()
    assert t["resposta"] == "teste groq"
    assert c.post("/api/desk/test-ai", json={"provedor": "xyz"}).status_code == 400
    assert c.delete("/api/brain/key/groq").json()["provedores"][0]["conectada"] is False

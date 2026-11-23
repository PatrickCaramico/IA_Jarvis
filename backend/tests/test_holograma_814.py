"""V8.14: holograma pesquisado na internet (fontes), cenas que chegam aos poucos e velocidade da narração."""
import json

import pytest

from modules import holo, tts
from services import llm_stream

SCENE = {"icone": "🌌", "titulo": "Horizonte", "fala": "Nada escapa daqui, senhor.", "pontos": ["luz presa"],
         "numero": None, "foto": None, "visual": None}
FULL = {"tipo": "apresentacao", "titulo": "Buracos negros", "wiki": "Buraco negro",
        "cenas": [SCENE, {**SCENE, "titulo": "Origem", "fala": "Nascem de estrelas {gigantes} [sim]."},
                  {**SCENE, "titulo": "Fim", "fala": "E evaporam devagar."}]}


def test_partial_scenes_only_returns_complete_ones():
    raw = json.dumps(FULL, ensure_ascii=False)
    cut = raw[: raw.index("E evaporam")]  # a IA ainda está escrevendo a 3ª cena
    assert [c["titulo"] for c in holo.partial_scenes("```json\n" + cut)] == ["Horizonte", "Origem"]
    assert holo.partial_title(cut) == "Buracos negros"
    assert [c["titulo"] for c in holo.partial_scenes(raw)] == ["Horizonte", "Origem", "Fim"]
    assert holo.partial_scenes('{"titulo": "x"') == []


def test_sources_are_cleaned():
    src = [{"name": "NASA", "url": "https://nasa.gov/a"}, {"name": "dup", "url": "https://nasa.gov/a"},
           {"headline": "Sem https", "url": "http://x.com"}, {"titulo": "", "url": "https://wiki.org"}, "lixo"]
    assert holo.clean_sources(src) == [{"titulo": "NASA", "url": "https://nasa.gov/a"},
                                       {"titulo": "Fonte", "url": "https://wiki.org"}]
    many = [{"name": f"F{i}", "url": f"https://f{i}.com"} for i in range(10)]
    assert len(holo.clean_sources(many)) == holo.MAX_SOURCES


def test_saved_presentation_keeps_sources():
    data = holo.parse(json.dumps({**FULL, "fontes": [{"titulo": "NASA", "url": "https://nasa.gov"}]}), "apresentacao")
    assert data["fontes"] == [{"titulo": "NASA", "url": "https://nasa.gov"}]
    assert "fontes" not in holo.parse(json.dumps(FULL), "apresentacao")


@pytest.fixture
def client(monkeypatch, isolated_data):
    from fastapi.testclient import TestClient

    import main
    from core import runtime
    from modules import access

    sent = []

    async def fake_broadcast(event):
        sent.append(event)

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    access.reset_for_tests(access.UNLOCKED)
    yield TestClient(main.app), sent
    access.reset_for_tests(access.LOCKED)


def test_presentation_is_researched_and_streams_scenes(client, monkeypatch):
    http, sent = client
    from services import llm_orchestrator

    asked = []

    def fake_web(prompt, max_tokens=None):
        asked.append(prompt)
        sink = llm_stream.current()
        raw = json.dumps(FULL, ensure_ascii=False)
        for i in range(0, len(raw), 40):  # a IA escrevendo aos poucos
            sink.delta(raw[i:i + 40])
            sink._last = 0  # sem o limite de envio no teste
        return raw, [{"name": "NASA", "url": "https://nasa.gov/bn"}]

    monkeypatch.setattr(llm_orchestrator, "ask_web", fake_web)
    res = http.post("/api/holo", json={"query": "buracos negros", "req_id": "abc"}).json()
    assert res["pesquisado"] is True and res["fontes"] == [{"titulo": "NASA", "url": "https://nasa.gov/bn"}]
    assert "pesquisa no Google" in asked[0]
    partial = [e for e in sent if e.get("type") == "holo_partial"]
    assert partial and partial[0]["req_id"] == "abc" and len(partial[0]["cenas"]) == 1
    assert [len(e["cenas"]) for e in partial] == sorted(len(e["cenas"]) for e in partial)  # só cresce


def test_recipe_does_not_search(client, monkeypatch):
    http, _ = client
    from services import llm_orchestrator

    monkeypatch.setattr(llm_orchestrator, "ask_web", lambda *a, **k: pytest.fail("receita não pesquisa"))
    recipe = {"tipo": "receita", "titulo": "Bolo", "ingredientes": ["farinha"], "passos": [{"texto": "Misture"}]}
    monkeypatch.setattr(llm_orchestrator, "ask_text", lambda *a, **k: json.dumps(recipe))
    res = http.post("/api/holo", json={"query": "receita de bolo"}).json()
    assert res["tipo"] == "receita" and "fontes" not in res


def test_without_gemini_the_presentation_still_comes(client, monkeypatch):
    http, _ = client
    from services import llm_orchestrator

    monkeypatch.setattr(llm_orchestrator, "ask_web", lambda *a, **k: (json.dumps(FULL), []))
    res = http.post("/api/holo", json={"query": "buracos negros"}).json()
    assert res["pesquisado"] is False and res["fontes"] == [] and len(res["cenas"]) == 3


def test_narration_speed():
    assert tts.combine_rate("-4%", 1.25) == "+21%"
    assert tts.combine_rate("+0%", 1.5) == "+50%"
    token = tts.use_speed(1.5)
    try:
        assert tts.voice_params()[1] == tts.combine_rate(tts.VOICE_STYLES["natural"]["rate"], 1.5)
    finally:
        tts.reset_speed(token)
    token = tts.use_speed(7)  # fora da lista: velocidade normal
    try:
        assert tts.voice_params()[1] == tts.VOICE_STYLES["natural"]["rate"]
    finally:
        tts.reset_speed(token)

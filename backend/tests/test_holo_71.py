"""V7.1: HOLOGRAMA (pesquisa vira apresentação narrada ou receita viva)."""
import json

import pytest
from fastapi.testclient import TestClient

import main
from modules import access, holo
from services import llm_orchestrator

SHOW = {"tipo": "apresentacao", "titulo": "Buracos negros", "wiki": "Buraco negro", "cenas": [
    {"icone": "🌌", "titulo": "Nem a luz escapa", "fala": "Senhor, imagine um lugar de onde nem a luz consegue sair.", "pontos": ["Gravidade extrema", ""], "numero": None},
    {"icone": "⭐", "titulo": "Nascem de estrelas", "fala": "Eles surgem quando estrelas gigantes colapsam.", "pontos": [],
     "numero": {"valor": "6,5", "unidade": "bilhões de sóis", "rotulo": "massa do M87*"}},
    {"fala": ""},
]}
RECIPE = {"tipo": "receita", "titulo": "Bolo de cenoura", "wiki": "Bolo de cenoura", "fala": "Um clássico, senhor.",
          "ingredientes": ["3 cenouras", "4 ovos", 7], "passos": [{"texto": "Bata tudo.", "minutos": 0}, {"texto": "Asse.", "minutos": "40"}, "Faça a cobertura."],
          "dica": "Forno pré-aquecido."}


def test_parse_presentation_cleans_scenes():
    out = holo.parse("```json\n" + json.dumps(SHOW) + "\n```", "apresentacao")
    assert out["tipo"] == "apresentacao" and len(out["cenas"]) == 2
    assert out["cenas"][0]["pontos"] == ["Gravidade extrema"] and out["cenas"][0]["numero"] is None
    assert out["cenas"][1]["numero"] == {"valor": 6.5, "unidade": "bilhões de sóis", "rotulo": "massa do M87*"}
    assert holo._number("384.400") == 384400 and holo._number("4.6") == 4.6 and holo._number(True) is None


def test_parse_recipe_and_failures():
    out = holo.parse(json.dumps(RECIPE), "receita")
    assert out["ingredientes"] == ["3 cenouras", "4 ovos"]
    assert [p["minutos"] for p in out["passos"]] == [0, 40, 0]
    for bad in ("sem json", "{quebrado", json.dumps({"tipo": "apresentacao", "titulo": "x", "cenas": []})):
        with pytest.raises(ValueError):
            holo.parse(bad, "apresentacao")
    assert holo.guess_kind("receita de pão") == "receita" and holo.guess_kind("como fazer backup") == "apresentacao"
    assert "RECEITA" in holo.build_prompt("bolo", "receita") and "APRESENTAÇÃO" in holo.build_prompt("x", "apresentacao")


def test_route(monkeypatch):
    access.reset_for_tests(access.UNLOCKED)
    seen = {}

    def fake(prompt, web=False, max_tokens=None):
        seen["prompt"] = prompt
        seen["max_tokens"] = max_tokens  # V7.13: o holograma pede mais espaço para as animações
        return json.dumps(RECIPE)

    monkeypatch.setattr(llm_orchestrator, "ask_text", fake)
    r = TestClient(main.app).post("/api/holo", json={"query": "receita de bolo de cenoura"})
    assert r.status_code == 200 and r.json()["tipo"] == "receita" and "bolo de cenoura" in seen["prompt"]
    assert seen["max_tokens"] >= 2000
    monkeypatch.setattr(llm_orchestrator, "ask_text", lambda prompt, *a, **k: "não sei")
    assert TestClient(main.app).post("/api/holo", json={"query": "me explica a lua"}).status_code == 502
    assert TestClient(main.app).post("/api/holo", json={"query": "  "}).status_code == 400


def test_personal_route_needs_unlock(credentials):
    access.reset_for_tests(access.LOCKED)
    assert TestClient(main.app).post("/api/holo", json={"query": "receita de bolo"}).status_code == 403


def test_prefetch_route_starts_voice(monkeypatch):
    from modules import tts

    access.reset_for_tests(access.UNLOCKED)
    seen = {}

    def fake(texts, whole=False):
        seen.update(texts=list(texts), whole=whole)
        return len(texts)

    monkeypatch.setattr(tts, "prefetch", fake)
    r = TestClient(main.app).post("/api/tts/prefetch", json={"texts": ["Cena um.", "  ", "Cena dois."]})
    assert r.status_code == 200 and r.json()["started"] == 2 and seen["texts"] == ["Cena um.", "Cena dois."]


def test_scene_visuals_713():
    """V7.13: cada cena pode ter uma animação (gráfico, linha do tempo, mapa, ciência) e uma foto."""
    from modules import holo

    raw = json.dumps({"tipo": "apresentacao", "titulo": "Lua", "cenas": [
        {"fala": "Cena 1.", "visual": {"tipo": "grafico", "estilo": "linha", "dados": [{"rotulo": "1969", "valor": "2"}, {"rotulo": "1972", "valor": 12}]}, "foto": "Apollo 11"},
        {"fala": "Cena 2.", "visual": {"tipo": "linha_do_tempo", "marcos": [{"data": "1969", "texto": "Pouso"}, {"data": "1972", "texto": "Último"}]}},
        {"fala": "Cena 3.", "visual": {"tipo": "mapa", "lugares": [{"nome": "Cabo Canaveral", "lat": 28.4, "lon": -80.6}, {"nome": "Lua?", "lat": 999, "lon": 0}], "rota": True}},
        {"fala": "Cena 4.", "visual": {"tipo": "ciencia", "modelo": "sistema_solar"}, "foto": None},
        {"fala": "Cena 5.", "visual": {"tipo": "grafico", "dados": [{"rotulo": "só um", "valor": 1}]}},
        {"fala": "Cena 6.", "visual": {"tipo": "ciencia", "modelo": "dragao"}},
    ]})
    cenas = holo.parse(raw, "apresentacao")["cenas"]
    assert cenas[0]["visual"]["estilo"] == "linha" and cenas[0]["visual"]["dados"][0]["valor"] == 2.0 and cenas[0]["foto"] == "Apollo 11"
    assert len(cenas[1]["visual"]["marcos"]) == 2
    assert cenas[2]["visual"]["lugares"] == [{"nome": "Cabo Canaveral", "lat": 28.4, "lon": -80.6}] and cenas[2]["visual"]["rota"] is False
    assert cenas[3]["visual"] == {"tipo": "ciencia", "modelo": "sistema_solar"} and cenas[3]["foto"] == ""
    assert cenas[4]["visual"] is None and cenas[5]["visual"] is None
    assert "linha_do_tempo" in holo.build_prompt("a lua", "apresentacao")

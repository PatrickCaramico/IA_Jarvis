"""V7.14: Holograma parte 2: perguntar no meio, quiz, salvar e rever, cartão rápido."""
import json

from fastapi.testclient import TestClient

from modules import access, cloud_sync, holo_extra
from services import llm_orchestrator

PRES = {"tipo": "apresentacao", "titulo": "A Lua", "wiki": "Lua", "cenas": [{"fala": "A Lua é o satélite da Terra."}, {"fala": "Ela tem fases."}]}


def _client():
    import main

    access.reset_for_tests(access.UNLOCKED)
    return TestClient(main.app)


def test_quiz_parser_keeps_only_valid_questions():
    raw = json.dumps({"perguntas": [
        {"pergunta": "O que é a Lua?", "opcoes": ["Estrela", "Satélite", "Planeta", "Cometa"], "certa": 1, "explicacao": "Ela orbita a Terra."},
        {"pergunta": "Errada", "opcoes": ["a", "b"], "certa": 0},
        {"pergunta": "Índice ruim", "opcoes": ["a", "b", "c", "d"], "certa": 7},
    ]})
    q = holo_extra.parse_quiz(raw)
    assert len(q) == 1 and q[0]["certa"] == 1 and q[0]["opcoes"][1] == "Satélite"


def test_save_list_get_delete_and_cloud(monkeypatch):
    item = holo_extra.save(PRES, "me explica a lua")
    assert item["titulo"] == "A Lua" and "data" not in item
    assert holo_extra.get(item["id"])["data"]["cenas"][0]["fala"].startswith("A Lua")
    holo_extra.save(PRES)  # mesmo título não duplica
    assert len(holo_extra.listing()) == 1
    assert cloud_sync.snapshot()["holo_salvos"][0]["titulo"] == "A Lua"
    assert holo_extra.delete(item["id"]) and holo_extra.listing() == []
    assert cloud_sync.apply_op({"op": "holo_save", "id": 7, "item": "abc123", "data": PRES, "query": "lua"})
    assert holo_extra.get("abc123")["pergunta"] == "lua"
    assert cloud_sync.apply_op({"op": "holo_delete", "id": 8, "item": "abc123"}) and holo_extra.listing() == []
    assert cloud_sync.apply_op({"op": "holo_save", "data": {"tipo": "virus"}}) is False


def test_quick_card_detection_and_parse(monkeypatch):
    assert holo_extra.is_quick("quanto está o dólar hoje?") and holo_extra.currency_of("quanto está o dólar hoje?") == "USD"
    assert holo_extra.is_quick("quem ganhou o jogo do Palmeiras?")
    assert not holo_extra.is_quick("me conta uma piada")
    assert holo_extra.parse_card('{"tipo": "placar", "time1": "Palmeiras", "gols1": 2, "time2": "Santos", "gols2": "1"}')["gols2"] == 1
    assert holo_extra.parse_card('{"tipo": "numero", "valor": "8.848", "unidade": "m"}')["valor"] == 8848
    assert holo_extra.parse_card('{"tipo": null}') is None and holo_extra.parse_card("lixo") is None
    from services import http_client

    monkeypatch.setattr(http_client, "get_json", lambda *a, **k: [{"bid": "5.40", "timestamp": "1763200000"}, {"bid": "5.20", "timestamp": "1762700000"}])
    c = holo_extra.currency_card("USD")
    assert c["valor"] == 5.4 and c["serie"][0]["valor"] == 5.2 and "subiu" in c["rotulo"]


def test_routes(monkeypatch):
    c = _client()
    calls = []

    def fake(prompt, web=False, max_tokens=None):
        calls.append(prompt)
        if "QUIZ" in prompt:
            return json.dumps({"perguntas": [{"pergunta": "?", "opcoes": ["a", "b", "c", "d"], "certa": 2, "explicacao": "x"}]})
        if "CARTÃO" in prompt:
            return json.dumps({"tipo": "placar", "titulo": "Brasileirão", "time1": "Palmeiras", "gols1": 2, "time2": "Santos", "gols2": 0})
        return "É a região de onde nem a luz escapa, senhor."

    monkeypatch.setattr(llm_orchestrator, "ask_text", fake)
    r = c.post("/api/holo/ask", json={"titulo": "Buraco negro", "cena": "...", "pergunta": "o que é horizonte de eventos?"})
    assert r.status_code == 200 and "luz" in r.json()["resposta"] and "horizonte de eventos" in calls[-1]
    assert c.post("/api/holo/quiz", json={"titulo": "x", "falas": ["a"]}).json()["perguntas"][0]["certa"] == 2
    assert c.post("/api/holo/quiz", json={"titulo": "x", "falas": []}).status_code == 400
    saved = c.post("/api/holo/saved", json={"data": PRES, "query": "lua"}).json()
    sid = saved["item"]["id"]
    assert c.get("/api/holo/saved").json()["itens"][0]["id"] == sid
    assert c.get(f"/api/holo/saved/{sid}").json()["data"]["titulo"] == "A Lua"
    assert c.delete(f"/api/holo/saved/{sid}").json()["itens"] == []
    assert c.post("/api/holo/saved", json={"data": {"tipo": "x"}}).status_code == 400
    card = c.post("/api/quickcard", json={"pergunta": "quem ganhou o jogo do Palmeiras?", "resposta": "O Palmeiras ganhou de 2 a 0."}).json()["card"]
    assert card["tipo"] == "placar" and card["gols1"] == 2
    assert c.post("/api/quickcard", json={"pergunta": "me conta uma piada", "resposta": "..."}).json() == {"card": None}

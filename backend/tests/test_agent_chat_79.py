"""V7.9: conversa direta com os agentes (@nome, abas, voz)."""
import json

from fastapi.testclient import TestClient

import main
from modules import access, agent_chat, finances, reminders, shopping, tasks
from services import llm_orchestrator


def _c():
    access.reset_for_tests(access.UNLOCKED)
    return TestClient(main.app)


def _say(monkeypatch, payload, seen=None):
    def fake(prompt, web=False):
        if seen is not None:
            seen.append(prompt)
        return json.dumps(payload) if isinstance(payload, dict) else payload
    monkeypatch.setattr(llm_orchestrator, "ask_text", fake)


def test_resolve_names():
    assert agent_chat.resolve("@mercado") == "mercado"
    assert agent_chat.resolve("Finanças") == "financas"
    assert agent_chat.resolve("agenda") == "secretario"
    assert agent_chat.resolve("xyz") is None
    assert {a["id"] for a in agent_chat.catalog()} == {"rotas", "pesquisa", "mercado", "financas", "secretario", "professor"}


def test_mercado_adds_items_and_remembers(monkeypatch):
    seen = []
    _say(monkeypatch, {"resposta": "Coloquei na lista, senhor.", "acoes": [{"tipo": "compras_add", "itens": ["Carvão", "Picanha 2 kg"]},
                                                                             {"tipo": "gasto", "valor": 10, "descricao": "x"}]}, seen)
    r = _c().post("/api/agents/chat", json={"agent": "@mercado", "message": "monta a lista do churrasco", "speak": False}).json()
    assert r["reply"].startswith("Coloquei") and r["done"] == ["✓ 2 item(ns) na lista de compras"]
    assert {i["texto"] for i in shopping.list_items()} == {"Carvão", "Picanha 2 kg"}
    assert finances.summary()["spent"] == 0  # ação de outra área (gasto) foi ignorada
    hist = _c().get("/api/agents/chat/mercado").json()["messages"]
    assert [m["role"] for m in hist] == ["user", "agent"]
    _c().post("/api/agents/chat", json={"agent": "mercado", "message": "e o que falta?", "speak": False})
    assert "monta a lista do churrasco" in seen[-1] and "Carvão" in seen[-1]  # lembra a conversa e vê a lista


def test_each_agent_has_own_memory_and_clear(monkeypatch):
    _say(monkeypatch, {"resposta": "ok", "acoes": []})
    c = _c()
    c.post("/api/agents/chat", json={"agent": "professor", "message": "me explica frações", "speak": False})
    assert c.get("/api/agents/chat/financas").json()["messages"] == []
    for i in range(20):
        c.post("/api/agents/chat", json={"agent": "professor", "message": f"pergunta {i}", "speak": False})
    assert len(c.get("/api/agents/chat/professor").json()["messages"]) == agent_chat.HISTORY
    c.delete("/api/agents/chat/professor")
    assert c.get("/api/agents/chat/professor").json()["messages"] == []


def test_finance_and_secretary_actions(monkeypatch):
    _say(monkeypatch, {"resposta": "Anotado.", "acoes": [{"tipo": "gasto", "valor": "54,90", "descricao": "mercado"}]})
    _c().post("/api/agents/chat", json={"agent": "financas", "message": "gastei 54,90 no mercado", "speak": False})
    assert finances.summary()["spent"] == 54.9
    _say(monkeypatch, {"resposta": "Marcado.", "acoes": [{"tipo": "lembrete", "texto": "Dentista", "data_hora": "2026-11-20 10:00"},
                                                        {"tipo": "tarefa", "texto": "Levar exames"}]})
    _c().post("/api/agents/chat", json={"agent": "secretario", "message": "marca dentista sexta às 10", "speak": False})
    assert reminders.get_reminders()[0]["texto"] == "Dentista"
    assert tasks.get_tasks()[0]["texto"].lower().startswith("levar exames")


def test_big_actions_wait_for_confirm(monkeypatch):
    shopping.add(["Leite"])
    shopping.set_bought(shopping.list_items()[0]["id"])
    _say(monkeypatch, {"resposta": "Posso limpar?", "acoes": [{"tipo": "compras_limpar_comprados"},
                                                             {"tipo": "compras_add", "itens": [f"item {i}" for i in range(12)]}]})
    r = _c().post("/api/agents/chat", json={"agent": "mercado", "message": "limpa os comprados e põe 12 coisas", "speak": False}).json()
    assert [p["tipo"] for p in r["pending"]] == ["compras_limpar_comprados", "compras_add"] and r["done"] == []
    assert len(shopping.list_items()) == 1  # nada mudou ainda
    ok = _c().post("/api/agents/chat/confirm", json={"agent": "mercado", "acao": r["pending"][0]})
    assert ok.status_code == 200 and shopping.list_items() == []
    bad = _c().post("/api/agents/chat/confirm", json={"agent": "mercado", "acao": {"tipo": "gasto", "valor": 5}})
    assert bad.status_code == 400  # ação de outra área não roda pelo confirmar


def test_holo_and_unknown_agent(monkeypatch):
    _say(monkeypatch, {"resposta": "Vou mostrar.", "acoes": [{"tipo": "holograma", "tema": "frações"}]})
    r = _c().post("/api/agents/chat", json={"agent": "professor", "message": "me explica frações", "speak": False}).json()
    assert r["holo"] == "frações"
    assert _c().post("/api/agents/chat", json={"agent": "xyz", "message": "oi"}).status_code == 404
    _say(monkeypatch, "resposta solta sem json")
    r = _c().post("/api/agents/chat", json={"agent": "pesquisa", "message": "oi", "speak": False}).json()
    assert r["reply"] == "resposta solta sem json" and r["done"] == []


def test_brazilian_money():
    assert agent_chat.money(54.9) == "R$ 54,90"
    assert agent_chat.money(1234.5) == "R$ 1.234,50"

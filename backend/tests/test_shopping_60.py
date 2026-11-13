"""V6.0: lista de compras por voz e pela tela."""
import asyncio

from fastapi.testclient import TestClient

import main
from modules import access, shopping, tasks


def say(text):
    return asyncio.run(shopping.handle_voice(text))


def test_voice_flow():
    assert say("Jarvis, coloca leite, pão e ovos na lista") == "Coloquei leite, pão e ovos na lista de compras."
    assert [i["texto"] for i in shopping.list_items()] == ["Leite", "Pão", "Ovos"]
    assert say("coloca leite na lista de compras") == "Leite já está na lista."
    assert say("comprei o leite") == "Marquei leite como comprado."
    assert say("o que tem na lista de compras?") == "Na lista de compras: pão e ovos."
    assert say("tira os ovos da lista") == "Tirei ovos da lista."
    assert say("limpa a lista de compras") == "Pronto: tirei 1 item da lista."
    assert [i["texto"] for i in shopping.list_items()] == ["Pão"]


def test_does_not_steal_tasks_or_other_phrases():
    assert say("coloca na lista de tarefas pagar a luz") is None
    assert say("qual a previsão do tempo") is None
    assert say("comprei") is None


def test_routes(credentials):
    access.reset_for_tests(access.UNLOCKED)
    c = TestClient(main.app)
    r = c.post("/api/shopping", json={"texto": "café e açúcar"}).json()
    ids = [i["id"] for i in r["items"]]
    assert [i["texto"] for i in r["items"]] == ["Café", "Açúcar"]
    r = c.patch(f"/api/shopping/{ids[0]}", json={"comprado": True}).json()
    assert r["items"][-1]["comprado"] is True and r["items"][0]["texto"] == "Açúcar"
    assert c.post("/api/shopping/clear").json()["removed"] == 1
    assert c.delete(f"/api/shopping/{ids[1]}").json()["items"] == []
    access.reset_for_tests(access.LOCKED)
    assert c.get("/api/shopping").status_code == 403  # pessoal: só com a central liberada
    assert tasks.get_tasks() == []

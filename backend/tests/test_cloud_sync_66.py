"""V6.6: sincronização do PC com o modo nuvem (Netlify)."""
from modules import alarms, cloud_sync, reminders, shopping, tasks, water


class FakeResp:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def test_apply_ops_from_phone():
    shopping.add(["leite"])
    tasks.add_task("pagar a luz")
    ops = [
        {"op": "shopping_add", "itens": ["pão", "café"]},
        {"op": "shopping_set", "texto": "leite", "comprado": True},
        {"op": "shopping_remove", "texto": "café"},
        {"op": "task_add", "texto": "levar o carro"},
        {"op": "task_done", "texto": "pagar a luz"},
        {"op": "reminder_add", "texto": "Remédio", "data_hora": "2099-01-01 20:00"},
        {"op": "alarm_add", "hora": "06:30", "dias": [0, 1, 2, 3, 4], "rotulo": "academia"},
        {"op": "water_add", "ml": 300},
        {"op": "water_goal", "goal_ml": 2500},
    ]
    assert all(cloud_sync.apply_op(op) for op in ops)
    assert [(i["texto"], i["comprado"]) for i in shopping.list_items()] == [("Pão", False), ("Leite", True)]
    assert [t["texto"] for t in tasks.get_tasks()] == ["levar o carro"]
    assert reminders.get_reminders()[0]["data_hora"] == "2099-01-01 20:00"
    assert alarms.list_alarms()[0]["hora"] == "06:30" and alarms.list_alarms()[0]["dias"] == [0, 1, 2, 3, 4]
    st = water.get_status()
    assert st["total_ml"] == 300 and st["goal_ml"] == 2500
    # o que não cabe mais é ignorado, sem erro
    assert cloud_sync.apply_op({"op": "shopping_remove", "texto": "nada disso"}) is False
    assert cloud_sync.apply_op({"op": "water_add", "ml": 200, "date": "2000-01-01"}) is False
    assert cloud_sync.apply_op({"op": "desconhecida"}) is False


def test_sync_once_pulls_and_pushes(monkeypatch):
    monkeypatch.setenv("JARVIS_NUVEM_CHAVE", "chave")
    sent = {}

    def fake_get(url, headers, timeout):
        assert url.endswith("/api/cloud/sync") and headers["X-Jarvis-Nuvem"] == "chave"
        return FakeResp({"ops": [{"id": 4, "op": "shopping_add", "itens": ["ovos"]}], "last_id": 4})

    def fake_post(url, headers, json, timeout):
        sent.update(json)
        return FakeResp({"pending": 0})

    monkeypatch.setattr(cloud_sync.requests, "get", fake_get)
    monkeypatch.setattr(cloud_sync.requests, "post", fake_post)
    assert cloud_sync.sync_once() == {"applied": 1, "ops": 1}
    assert sent["ack"] == 4
    assert [i["texto"] for i in sent["snapshot"]["compras"]] == ["Ovos"]
    assert "agua" in sent["snapshot"] and "perfil" in sent["snapshot"]


def test_disabled_without_key(monkeypatch):
    monkeypatch.delenv("JARVIS_NUVEM_CHAVE", raising=False)
    assert cloud_sync.enabled() is False

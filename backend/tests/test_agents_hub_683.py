"""V6.8.3: Central de Agentes (catálogo + lugares pela tela)."""
import pytest

from modules import access, agents

pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402


@pytest.fixture
def client(isolated_data, monkeypatch, tmp_path):
    monkeypatch.setattr(agents, "_PATH", tmp_path / "places.json")
    access.unlock("test")
    return TestClient(main.app)


def test_catalog_has_desc_and_examples():
    cat = agents.catalog()
    assert {a["name"] for a in cat} >= {"rotas"}
    for a in cat:
        assert a["label"] and a["icon"] and a["desc"] and a["examples"]


def test_places_routes(client):
    r = client.get("/api/agents")
    assert r.status_code == 200 and r.json()["agents"]
    r = client.post("/api/agents/places", json={"name": "Trabalho", "address": "Av. Paulista, 1000"})
    assert r.status_code == 200
    places = r.json()["places"]
    key = agents._key("Trabalho")
    assert places[key] == "Av. Paulista, 1000"
    r = client.delete(f"/api/agents/places/{key}")
    assert key not in r.json()["places"]

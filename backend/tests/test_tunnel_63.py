"""V6.3: pedidos que chegam por túnel (Cloudflare etc.) não contam como "este PC"."""
from fastapi.testclient import TestClient

import main
from core import runtime
from modules import access

CF = {"cf-connecting-ip": "203.0.113.9", "cf-ray": "abc"}


def test_tunnel_needs_the_key_and_never_gets_it(monkeypatch):
    monkeypatch.setattr(main.settings, "NETWORK_MODE", True)
    access.reset_for_tests(access.UNLOCKED)
    c = TestClient(main.app)
    assert c.get("/api/auth/token").status_code == 200                      # no próprio PC: ok
    assert c.get("/api/auth/token", headers=CF).status_code in (401, 403)  # pelo túnel: nunca
    assert c.get("/api/tasks", headers=CF).status_code == 401              # sem a chave: fora
    ok = c.get("/api/tasks", headers={**CF, "X-Jarvis-Token": runtime.ACCESS_TOKEN})
    assert ok.status_code == 200                                            # com a chave: entra
    assert c.post("/api/system/update", json={"confirm": True},
                  headers={**CF, "X-Jarvis-Token": runtime.ACCESS_TOKEN}).status_code == 403
    access.reset_for_tests(access.LOCKED)


def test_tunnel_websocket_needs_the_key(monkeypatch):
    monkeypatch.setattr(main.settings, "NETWORK_MODE", True)
    c = TestClient(main.app)
    import pytest
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with c.websocket_connect("/ws", headers=CF) as ws:
            ws.receive_json()
    with c.websocket_connect(f"/ws?token={runtime.ACCESS_TOKEN}", headers=CF) as ws:
        assert ws.receive_json()["type"] == "state"

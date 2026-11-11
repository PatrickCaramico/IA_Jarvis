"""V5.1 "Esqueci o PIN": PIN novo sem o atual, só logo depois de confirmar o rosto."""
import time

from fastapi.testclient import TestClient

import main
from core import session
from modules import access, lock_log, lock_pin
from routes import access as access_routes


def test_sem_rosto_confirmado_recusa():
    lock_pin.set_pin("4821")
    session.face_ok_at = 0.0
    r = TestClient(main.app).post("/api/auth/pin/reset", json={"new_pin": "9753"})
    assert r.status_code == 403
    assert lock_pin.verify("4821")["verified"] is True


def test_rosto_confirmado_libera_uma_vez():
    lock_pin.set_pin("4821")
    access.unlock("face")  # o rosto confirmado na entrada libera a central
    session.face_ok_at = time.monotonic()
    client = TestClient(main.app)
    r = client.post("/api/auth/pin/reset", json={"new_pin": "9753"})
    assert r.status_code == 200 and r.json()["has_pin"] is True
    assert lock_pin.verify("9753")["verified"] is True
    assert lock_pin.verify("4821")["verified"] is False
    # a confirmação vale para uma redefinição só
    assert client.post("/api/auth/pin/reset", json={"new_pin": "8642"}).status_code == 403
    assert lock_log.list_entries()[0]["result"] == "pin_reset"


def test_confirmacao_expira(monkeypatch):
    lock_pin.set_pin("4821")
    access.unlock("face")
    session.face_ok_at = time.monotonic() - access_routes.PIN_RESET_WINDOW_S - 1
    assert TestClient(main.app).post("/api/auth/pin/reset", json={"new_pin": "9753"}).status_code == 403


def test_pin_novo_invalido():
    lock_pin.set_pin("4821")
    access.unlock("face")
    session.face_ok_at = time.monotonic()
    assert TestClient(main.app).post("/api/auth/pin/reset", json={"new_pin": "12"}).status_code == 400

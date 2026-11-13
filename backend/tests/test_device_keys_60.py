"""V6.0: entrar com a digital no app (chave do aparelho)."""
from fastapi.testclient import TestClient

import main
from modules import access, device_keys


def test_enroll_requires_unlocked_and_unlock_works(credentials):
    c = TestClient(main.app)
    access.reset_for_tests(access.LOCKED)
    assert c.post("/api/auth/device/enroll", json={"name": "Galaxy"}).status_code == 403
    access.reset_for_tests(access.UNLOCKED)
    key = c.post("/api/auth/device/enroll", json={"name": "Galaxy"}).json()
    assert len(key["secret"]) >= 40
    assert key["secret"] not in device_keys._PATH.read_text(encoding="utf-8")  # só o hash fica salvo
    access.reset_for_tests(access.LOCKED)
    assert c.post("/api/auth/device/unlock", json={"secret": "chute"}).json()["verified"] is False
    assert access.get_state() == access.LOCKED
    ok = c.post("/api/auth/device/unlock", json={"secret": key["secret"]}).json()
    assert ok["verified"] is True and access.get_state() == access.UNLOCKED
    assert c.delete("/api/auth/device").json()["removed"] == 1
    access.reset_for_tests(access.LOCKED)
    assert c.post("/api/auth/device/unlock", json={"secret": key["secret"]}).json()["verified"] is False
    access.reset_for_tests(access.LOCKED)


def test_same_device_replaces_its_key():
    a = device_keys.enroll("Galaxy")
    b = device_keys.enroll("Galaxy")
    assert device_keys.verify(a["secret"]) is None and device_keys.verify(b["secret"]) is not None
    assert len(device_keys.list_keys()) == 1

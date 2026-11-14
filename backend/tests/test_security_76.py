"""V7.6: chave por aparelho, aprovação no PC, remoção e bloqueio de tentativas suspeitas."""
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

import main
from core import runtime
from modules import access, device_access, health_check

PHONE = "192.168.0.50"


def _phone(token=None, host=PHONE):
    c = TestClient(main.app, client=(host, 50000))
    if token:
        c.headers["X-Jarvis-Token"] = token
    return c


def _pc():
    return TestClient(main.app)


def _setup(monkeypatch, migration=False):
    monkeypatch.setattr(main.settings, "NETWORK_MODE", True)
    access.reset_for_tests(access.UNLOCKED)
    device_access._load()  # noqa: SLF001
    if not migration:
        device_access.end_migration()


def test_migration_gives_own_key_without_approval(monkeypatch):
    _setup(monkeypatch, migration=True)
    r = _phone(runtime.ACCESS_TOKEN).post("/api/security/claim", json={"name": "Galaxy", "kind": "celular"})
    assert r.json()["status"] == "approved"
    token = r.json()["token"]
    assert token != runtime.ACCESS_TOKEN
    assert _phone(token).get("/api/tasks").status_code == 200
    assert [d["name"] for d in device_access.list_devices()] == ["Galaxy"]
    assert token not in device_access._PATH.read_text(encoding="utf-8")  # noqa: SLF001 (só o hash)


def test_new_device_waits_for_pc_approval(monkeypatch):
    _setup(monkeypatch)
    pairing = _phone(runtime.ACCESS_TOKEN)
    # depois da migração, a chave do QR não abre a central: só pede acesso
    assert pairing.get("/api/tasks").json()["code"] == "device_required"
    assert pairing.get("/api/health").status_code == 200  # o app ainda vê se o PC está no ar
    r = pairing.post("/api/security/claim", json={"name": "Tablet", "kind": "tablet"}).json()
    assert r["status"] == "pending"
    status = lambda: _phone(runtime.ACCESS_TOKEN).get("/api/security/claim", params={"id": r["request_id"], "secret": r["secret"]}).json()  # noqa: E731
    assert status()["status"] == "pending"
    # o celular não pode aprovar a si mesmo; só a tela do PC
    assert _phone(runtime.ACCESS_TOKEN).post(f"/api/security/pending/{r['request_id']}", json={"approve": True}).status_code in (401, 403)
    assert [p["name"] for p in _pc().get("/api/security/pending").json()["items"]] == ["Tablet"]
    assert _pc().post(f"/api/security/pending/{r['request_id']}", json={"approve": True}).status_code == 200
    got = status()
    assert got["status"] == "approved"
    assert status()["status"] == "delivered"  # a chave é entregue uma vez só
    assert _phone(got["token"]).get("/api/tasks").status_code == 200


def test_refused_and_expired(monkeypatch):
    _setup(monkeypatch)
    r = _phone(runtime.ACCESS_TOKEN).post("/api/security/claim", json={"name": "Estranho"}).json()
    _pc().post(f"/api/security/pending/{r['request_id']}", json={"approve": False})
    assert device_access.claim_status(r["request_id"], r["secret"])["status"] == "refused"
    r2 = device_access.claim("Lento", "celular", PHONE)
    device_access._load()["pending"][r2["request_id"]]["at"] -= device_access.PENDING_TTL + 1  # noqa: SLF001
    assert device_access.claim_status(r2["request_id"], r2["secret"])["status"] == "expired"
    assert device_access.claim_status(r2["request_id"], "errado")["status"] == "unknown"


def test_removed_device_is_locked_out(monkeypatch):
    _setup(monkeypatch, migration=True)
    token = _phone(runtime.ACCESS_TOKEN).post("/api/security/claim", json={"name": "Velho"}).json()["token"]
    dev_id = device_access.list_devices()[0]["id"]
    assert _pc().delete(f"/api/security/devices/{dev_id}").status_code == 200
    r = _phone(token).get("/api/tasks")
    assert r.status_code == 401 and r.json()["code"] == "device_revoked"


def test_disconnect_all_rotates_qr_key(monkeypatch):
    _setup(monkeypatch, migration=True)
    old = runtime.ACCESS_TOKEN
    token = _phone(old).post("/api/security/claim", json={"name": "A"}).json()["token"]
    assert _phone().post("/api/security/disconnect-all").status_code in (401, 403)  # só o PC
    assert _pc().post("/api/security/disconnect-all").json()["removed"] == 1
    assert runtime.ACCESS_TOKEN != old
    assert _phone(token).get("/api/tasks").status_code == 401
    assert _phone(old).get("/api/health").status_code == 401  # QR antigo não vale mais


def test_wrong_keys_block_the_address(monkeypatch):
    _setup(monkeypatch)
    said = []
    monkeypatch.setattr(device_access, "alert", lambda msg, ip="": said.append(msg) or device_access.add_event("alert", msg, ip))
    bad = _phone("chave-errada", host="192.168.0.66")
    for _ in range(device_access.FAIL_LIMIT):
        bad.get("/api/tasks")
    r = bad.get("/api/tasks")
    assert r.status_code == 429 and r.json()["code"] == "blocked"
    # mesmo com a chave certa, o endereço bloqueado espera
    assert _phone(runtime.ACCESS_TOKEN, host="192.168.0.66").get("/api/health").status_code == 429
    assert said and "192.168.0.66" in said[0]
    assert health_check.check_security()["status"] == "fail"
    # outro aparelho segue normal
    assert _phone(runtime.ACCESS_TOKEN).get("/api/health").status_code == 200


def test_block_time_doubles(monkeypatch):
    monkeypatch.setattr(device_access, "alert", lambda *a, **k: None)
    first = [device_access.record_failure("10.0.0.9", "x") for _ in range(device_access.FAIL_LIMIT)][-1]
    device_access._blocks["10.0.0.9"]["until"] = 0  # noqa: SLF001 (bloqueio acabou)
    second = [device_access.record_failure("10.0.0.9", "x") for _ in range(device_access.FAIL_LIMIT)][-1]
    assert first == device_access.BLOCK_BASE and second == 2 * device_access.BLOCK_BASE


def test_security_check_idle_devices(monkeypatch):
    _setup(monkeypatch, migration=True)
    device_access.claim("Antigo", "celular", PHONE)
    dev = next(iter(device_access._load()["devices"].values()))  # noqa: SLF001
    dev["last_seen"] = (datetime.now() - timedelta(days=40)).isoformat(timespec="seconds")
    item = health_check.check_security()
    assert item["status"] == "warn" and "Antigo" in item["detail"]


def test_locked_screen_diagnostic_rate_limit(monkeypatch, credentials):
    from modules import health_check as hc

    async def fake():
        return {"items": [], "version": "x", "took_ms": 0, "at": ""}

    monkeypatch.setattr(hc, "run", fake)
    access.reset_for_tests(access.LOCKED)
    assert _pc().get("/api/system/health-check").status_code == 200
    assert _pc().get("/api/system/health-check").status_code == 429

"""V9.4: tecla de acesso (a câmera só começa depois da tecla certa) e o rosto de quem tenta entrar sem ser pelo rosto
(PIN errado, teclas erradas)."""
import asyncio

import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from core import runtime, session, speech  # noqa: E402
from modules import access, face, lock_key, lock_log, lock_pin, prefs  # noqa: E402
from modules import tts as tts_module  # noqa: E402
from routes import access as access_routes  # noqa: E402
from skills import seguranca  # noqa: E402

STRANGER = {"faces": 1, "known": 0, "unknown": 1, "jpeg": b"\xff\xd8rosto"}
OWNER = {"faces": 1, "known": 1, "unknown": 0}


@pytest.fixture
def client(isolated_data, monkeypatch):
    async def fake_speak(text, release_busy=True, idle_after=True):
        session.busy = False if release_busy else session.busy

    async def quiet(*_a, **_k):
        return 1

    monkeypatch.setattr(speech, "speak", fake_speak)
    monkeypatch.setattr(speech, "say_quietly", quiet)
    monkeypatch.setattr(main.manager, "send_local", quiet)
    monkeypatch.setattr(runtime.manager, "broadcast", quiet)
    monkeypatch.setattr(tts_module, "stop_playback", lambda: None)
    monkeypatch.setattr(face, "has_profile", lambda: True)
    monkeypatch.setattr(face, "get_name", lambda: "Patrick")
    monkeypatch.setattr(access_routes, "_last_snap", 0.0)
    session.busy = False
    return TestClient(main.app)


# ------------------------------------------------------------------ o módulo
def test_valid_keys_and_labels():
    for code in ("F8", "KeyJ", "Digit7", "Numpad0", "Insert", "F12"):
        assert lock_key.valid(code), code
    for code in ("Space", "Enter", "Escape", "", "Tab", "ShiftLeft", "KeyJJ", "F25", "rm -rf", "KeyP"):
        assert not lock_key.valid(code), code
    assert lock_key.label("KeyJ") == "J" and lock_key.label("Digit7") == "7" and lock_key.label("F8") == "F8"
    with pytest.raises(lock_key.LockKeyError):
        lock_key.set_key("Space")


def test_status_never_reveals_the_key_when_locked():
    assert lock_key.status() == {"enabled": False} and lock_key.matches("KeyA")  # sem tecla: tudo vale
    lock_key.set_key("F8")
    assert lock_key.status() == {"enabled": True}
    assert lock_key.status(full=True) == {"enabled": True, "code": "F8", "label": "F8"}
    assert lock_key.matches("F8") and not lock_key.matches("F9") and not lock_key.matches("")
    lock_key.clear()
    assert not lock_key.enabled()


def test_wrong_keys_become_one_attempt_with_cooldown():
    t = 1000.0
    assert not any(lock_key.wrong_key(t + i) for i in range(lock_key.WRONG_LIMIT - 1))
    assert lock_key.wrong_key(t + 10) is True  # a 6ª tecla errada em menos de 1 min
    assert not any(lock_key.wrong_key(t + 20 + i) for i in range(lock_key.WRONG_LIMIT))  # 1 tentativa a cada 2 min
    lock_key.reset_for_tests()
    assert not any(lock_key.wrong_key(t + i * 30) for i in range(lock_key.WRONG_LIMIT))  # espalhadas: não conta


# ------------------------------------------------------------------ as rotas
def test_routes_policy():
    assert access.is_allowed("GET", "/api/auth/lock-key", access.LOCKED)
    assert access.is_allowed("POST", "/api/auth/lock-key/check", access.LOCKED)
    assert not access.is_allowed("POST", "/api/auth/lock-key", access.LOCKED)
    assert not access.is_allowed("DELETE", "/api/auth/lock-key", access.LOCKED)


def test_set_key_route_and_locked_status(client):
    access.reset_for_tests(access.UNLOCKED)
    assert client.post("/api/auth/lock-key", json={"code": "Space"}).status_code == 400
    assert client.post("/api/auth/lock-key", json={"code": "KeyJ"}).json() == {"enabled": True, "code": "KeyJ", "label": "J"}
    access.reset_for_tests(access.LOCKED)
    assert client.get("/api/auth/lock-key").json() == {"enabled": True}  # bloqueada: não diz qual
    access.reset_for_tests(access.UNLOCKED)
    assert client.delete("/api/auth/lock-key").json() == {"enabled": False}


def test_verify_needs_the_key(client, monkeypatch):
    lock_key.set_key("F8")
    calls = []

    def fake_verify(timeout=None, on_frame=None):
        calls.append(1)
        return {"verified": True, "saw_face": True, "score": 0.6}

    monkeypatch.setattr(face, "verify_against_profile", fake_verify)
    for body in ({"trigger": "clap"}, {"trigger": "wake"}, {"trigger": "button"}, {"trigger": "key", "key": "F9"}):
        r = client.post("/api/auth/verify", json=body)
        assert r.status_code == 403 and "tecla de acesso" in r.json()["detail"], body
    assert not calls and access.get_state() == access.LOCKED  # a câmera nem ligou
    r = client.post("/api/auth/verify", json={"trigger": "key", "key": "F8"}).json()
    assert r["verified"] is True and access.get_state() == access.UNLOCKED and calls == [1]
    # a reverificação por palma (já dentro) não pede tecla
    r = client.post("/api/auth/verify", json={"mode": "recheck"}).json()
    assert r["verified"] is True


def test_check_route_counts_wrong_keys_and_blocks(client, monkeypatch):
    snaps = []

    async def fake_snap(text):
        snaps.append(text)

    monkeypatch.setattr(access_routes, "snap_attempt", fake_snap)
    monkeypatch.setattr(runtime, "is_local_conn", lambda conn: True)
    assert client.post("/api/auth/lock-key/check", json={"code": "KeyA"}).json()["ok"] is True  # sem tecla: tudo vale
    lock_key.set_key("F8")
    assert client.post("/api/auth/lock-key/check", json={"code": "F8"}).json() == {"ok": True, "attempt": False, "blocked": 0}
    got = [client.post("/api/auth/lock-key/check", json={"code": "KeyA"}).json() for _ in range(lock_key.WRONG_LIMIT)]
    assert got[-1]["attempt"] is True and got[-1]["blocked"] > 0 and not any(g["attempt"] for g in got[:-1])
    assert snaps and "teclas erradas" in snaps[0]
    # bloqueada por 2 min: nem a tecla certa vale (o PIN continua)
    assert client.post("/api/auth/lock-key/check", json={"code": "F8"}).json()["ok"] is False
    r = client.post("/api/auth/verify", json={"trigger": "key", "key": "F8"})
    assert r.status_code == 429 and "PIN" in r.json()["detail"]


# ------------------------------------------------------------------ o rosto de quem tenta
def _events():
    return seguranca._load()["events"]  # noqa: SLF001


def test_snap_attempt_saves_stranger_photo(isolated_data, monkeypatch):
    notified = []
    monkeypatch.setattr(face, "has_profile", lambda: True)
    monkeypatch.setattr(face, "look_once", lambda refs=None: STRANGER)
    monkeypatch.setattr(runtime, "notify", lambda kind, title, body: notified.append(title))
    monkeypatch.setattr(access_routes, "_last_snap", 0.0)
    assert prefs.get_all()["lock_save_failed_photo"] is True  # V9.4: vem ligado
    asyncio.run(access_routes.snap_attempt("PIN errado digitado no PC às 10:00."))
    ev = _events()[-1]
    assert ev["kind"] == "tentativa" and ev["photo"].startswith("tentativa_") and notified == ["🚨 Tentativa de entrar"]
    assert (lock_log.INTRUDERS_DIR / ev["photo"]).read_bytes() == STRANGER["jpeg"]
    asyncio.run(access_routes.snap_attempt("de novo"))  # 1 por minuto
    assert len(_events()) == 1


def test_snap_attempt_ignores_owner_and_works_without_camera(isolated_data, monkeypatch):
    monkeypatch.setattr(face, "has_profile", lambda: True)
    monkeypatch.setattr(face, "look_once", lambda refs=None: OWNER)
    monkeypatch.setattr(access_routes, "_last_snap", 0.0)
    asyncio.run(access_routes.snap_attempt("PIN errado"))
    assert _events() == []  # o próprio dono errou o PIN

    def broken(refs=None):
        raise RuntimeError("sem câmera")

    monkeypatch.setattr(face, "look_once", broken)
    monkeypatch.setattr(access_routes, "_last_snap", 0.0)
    asyncio.run(access_routes.snap_attempt("PIN errado"))
    assert _events()[-1]["kind"] == "tentativa" and "photo" not in _events()[-1]
    prefs.update(lock_save_failed_photo=False)
    monkeypatch.setattr(face, "look_once", lambda refs=None: pytest.fail("não devia olhar"))
    monkeypatch.setattr(access_routes, "_last_snap", 0.0)
    asyncio.run(access_routes.snap_attempt("PIN errado"))  # foto desligada: registra sem olhar
    assert len(_events()) == 2


def test_wrong_pin_on_the_pc_takes_a_look(client, monkeypatch):
    snaps = []

    async def fake_snap(text):
        snaps.append(text)

    monkeypatch.setattr(access_routes, "snap_attempt", fake_snap)
    lock_pin.set_pin("4821")
    access.lock("test")
    monkeypatch.setattr(runtime, "is_local_conn", lambda conn: False)
    client.post("/api/auth/pin", json={"pin": "1111"})
    assert snaps == []  # do celular: a câmera do PC não ajuda
    monkeypatch.setattr(runtime, "is_local_conn", lambda conn: True)
    client.post("/api/auth/pin", json={"pin": "1111"})
    assert snaps and snaps[0].startswith("PIN errado digitado no PC")

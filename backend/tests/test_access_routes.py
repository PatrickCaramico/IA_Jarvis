"""Testes de rotas: bloqueio real, modo visitante, Sentinela, PIN e envio local da câmera.

Requer httpx (TestClient). Instale com: pip install -r backend/requirements-dev.txt
"""
import asyncio
import re
from types import SimpleNamespace

import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from core import session, speech, turns  # noqa: E402
from modules import access, face, lock_log, lock_pin  # noqa: E402
from modules import tts as tts_module  # noqa: E402


@pytest.fixture
def client(isolated_data, monkeypatch):
    async def fake_speak(text, release_busy=True, idle_after=True):
        session.busy = False if release_busy else session.busy

    async def fake_quiet(text):
        return None

    monkeypatch.setattr(speech, "speak", fake_speak)
    monkeypatch.setattr(speech, "say_quietly", fake_quiet)
    monkeypatch.setattr(tts_module, "stop_playback", lambda: None)
    session.busy = False
    return TestClient(main.app)


def _with_pin_locked():
    lock_pin.set_pin("4821")
    access.lock("test")


def test_personal_routes_blocked_when_locked(client):
    _with_pin_locked()
    r = client.get("/api/tasks")
    assert r.status_code == 403 and r.json()["code"] == "locked"
    assert client.get("/api/memory").status_code == 403
    assert client.patch("/api/prefs", json={"silent_mode": True}).status_code == 403
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/presence").json() == {"clients": 0}


def test_prefs_and_profile_are_filtered_when_locked(client):
    _with_pin_locked()
    data = client.get("/api/prefs").json()
    assert data["restricted"] is True
    assert "custom_shortcuts" not in data and "clap_wake_enabled" in data
    assert client.get("/api/profile").json()["name"] == ""


def test_pin_unlocks(client):
    _with_pin_locked()
    bad = client.post("/api/auth/pin", json={"pin": "1111"}).json()
    assert bad["verified"] is False and bad["remaining_attempts"] == 4
    ok = client.post("/api/auth/pin", json={"pin": "4821"}).json()
    assert ok["verified"] is True
    assert "Houve 1 tentativa" in ok["message"]
    assert client.get("/api/tasks").status_code == 200
    entries = lock_log.list_entries()
    assert [e["result"] for e in entries[:2]] == ["ok", "fail"]


def test_pin_set_requires_unlock(client):
    _with_pin_locked()
    assert client.post("/api/auth/pin/set", json={"new_pin": "9999", "current_pin": "4821"}).status_code == 403
    access.unlock("test")
    r = client.post("/api/auth/pin/set", json={"new_pin": "1234", "current_pin": "4821"})
    assert r.status_code == 200 and r.json()["weak"] is True
    assert client.post("/api/auth/pin/set", json={"new_pin": "5678", "current_pin": "0000"}).status_code == 400


def test_sentinel_public_and_protected(client):
    _with_pin_locked()
    r = client.post("/api/chat", json={"message": "Jarvis, que horas são?"}).json()
    assert r["source"] == "sentinel" and r["public"] is True and r["requires_unlock"] is False
    assert re.search(r"hora|meia-noite|meio-dia", r["response"])
    session.busy = False
    r = client.post("/api/chat", json={"message": "tá acordado?"}).json()
    assert r["public"] is True and r["action"] == "awake"
    session.busy = False
    r = client.post("/api/chat", json={"message": "quais são minhas tarefas"}).json()
    assert r["public"] is False and r["requires_unlock"] is True
    session.busy = False
    r = client.post("/api/chat", json={"message": "qual é o meu nome"}).json()
    assert r["public"] is False


def _all_routes(routes):
    """Rotas finais do app. Do FastAPI 0.162 em diante, cada include_router vira um item que guarda
    o roteador original (original_router) em vez de copiar as rotas para app.routes."""
    for route in routes:
        inner = getattr(route, "original_router", None)
        if inner is not None:
            yield from _all_routes(inner.routes)
        else:
            yield route


def test_guest_mode_blocks_every_personal_route(client):
    """Todas as rotas /api fora da lista pública respondem 403 no modo visitante."""
    lock_pin.set_pin("4821")
    assert client.post("/api/guest/enter").status_code == 403  # desligado por padrão
    access.unlock("test")
    client.patch("/api/prefs", json={"lock_guest_enabled": True})
    assert client.post("/api/guest/enter").status_code == 200
    blocked, allowed = [], []
    for route in _all_routes(main.app.routes):
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", None) or set()
        if not path.startswith("/api"):
            continue
        concrete = re.sub(r"\{[^}]+\}", "1", path)
        for method in sorted(methods - {"HEAD", "OPTIONS"}):
            if access.is_allowed(method, concrete, access.GUEST):
                allowed.append((method, path))
                continue
            r = client.request(method, concrete, json={})
            assert r.status_code == 403, (method, path, r.status_code)
            assert r.json()["code"] == "guest"
            blocked.append((method, path))
    assert ("GET", "/api/tasks") in blocked and ("POST", "/api/integrations/spotify/control") in allowed
    assert len(blocked) > 40
    # Sair do visitante volta ao bloqueio (exige rosto ou PIN)
    assert client.post("/api/guest/exit").json()["state"] == "locked"
    assert client.get("/api/tasks").status_code == 403


def test_guest_voice_refuses_personal(client):
    lock_pin.set_pin("4821")
    access.unlock("test")
    client.patch("/api/prefs", json={"lock_guest_enabled": True})
    client.post("/api/guest/enter")
    session.busy = False
    r = client.post("/api/chat", json={"message": "minhas anotações"}).json()
    assert r["public"] is False and r["requires_unlock"] is False
    assert "visitante" in r["response"]


def test_verify_streams_frames_and_unlocks(client, monkeypatch):
    lock_pin.set_pin("4821")
    access.lock("test")
    monkeypatch.setattr(face, "has_profile", lambda: True)
    monkeypatch.setattr(face, "get_name", lambda: "Patrick")
    sent = []

    async def fake_send_local(event):
        sent.append(event)
        return 1

    monkeypatch.setattr(main.manager, "send_local", fake_send_local)

    def fake_verify(timeout=None, on_frame=None):
        on_frame({"jpeg": b"\xff\xd8x", "box": [0.1, 0.1, 0.3, 0.4], "saw_face": True, "score": 0.2, "phase": "comparing"})
        on_frame({"jpeg": b"\xff\xd8y", "box": [0.1, 0.1, 0.3, 0.4], "saw_face": True, "score": 0.5, "phase": "verified"})
        return {"verified": True, "saw_face": True, "score": 0.5}

    monkeypatch.setattr(face, "verify_against_profile", fake_verify)
    r = client.post("/api/auth/verify", json={"mode": "login", "trigger": "clap"}).json()
    assert r["verified"] is True and r["name"] == "Patrick"
    assert access.get_state() == access.UNLOCKED
    types = [e["type"] for e in sent]
    assert types[0] == "face_scan_start" and types[-1] == "face_scan_end"
    assert any(e["type"] == "face_frame" and e["phase"] == "verified" for e in sent)
    assert lock_log.list_entries()[0]["method"] == "clap"


def test_verify_without_body_keeps_old_contract(client, monkeypatch):
    monkeypatch.setattr(face, "has_profile", lambda: True)
    monkeypatch.setattr(face, "get_name", lambda: "")
    monkeypatch.setattr(face, "verify_against_profile",
                        lambda timeout=None, on_frame=None: {"verified": False, "saw_face": False, "score": -1.0})
    r = client.post("/api/auth/verify").json()
    assert set(["verified", "name", "message"]) <= set(r)
    assert r["verified"] is False and "rosto" in r["message"]


def test_recheck_does_not_unlock_and_can_relock(client, monkeypatch):
    lock_pin.set_pin("4821")
    access.unlock("pin")
    client.patch("/api/prefs", json={"clap_relock_on_fail": True})
    monkeypatch.setattr(face, "has_profile", lambda: True)
    monkeypatch.setattr(face, "verify_against_profile",
                        lambda timeout=None, on_frame=None: {"verified": False, "saw_face": True, "score": 0.1})
    r = client.post("/api/auth/verify", json={"mode": "recheck"}).json()
    assert r["verified"] is False and r["message"] == "Rosto não reconhecido."
    assert access.get_state() == access.LOCKED


def test_send_local_only_reaches_local_sockets():
    class FakeWS:
        def __init__(self, host):
            self.client = SimpleNamespace(host=host)
            self.got = []

        async def send_json(self, event):
            self.got.append(event)

    mgr = main.ConnectionManager()
    local, local6, remote = FakeWS("127.0.0.1"), FakeWS("::1"), FakeWS("192.168.0.20")
    mgr.connections = {local, local6, remote}
    n = asyncio.run(mgr.send_local({"type": "face_frame"}))
    assert n == 2 and local.got and local6.got and remote.got == []


def test_prefs_patch_validation(client):
    assert client.patch("/api/prefs", json={"clap_sensitivity": 42}).status_code == 400
    r = client.patch("/api/prefs", json={"clap_wake_enabled": True, "clap_sensitivity": 8, "water_vessel": "bottle"})
    assert r.status_code == 200 and r.json()["clap_sensitivity"] == 8 and r.json()["water_vessel"] == "bottle"


def test_water_undo_and_sentence(client):
    client.post("/api/water/add", json={"ml": 300})
    client.post("/api/water/add", json={"ml": 200})
    st = client.post("/api/water/undo").json()
    assert st["total_ml"] == 300 and st["last"]["ml"] == 300
    r = client.post("/api/chat", json={"message": "como está minha hidratação"}).json()
    assert "300 ml" in r["response"]
    card = next(c for c in r["cards"] if c["type"] == "water")
    assert card["open_panel"] is True and card["data"]["total_ml"] == 300


def test_voice_lock_command(client):
    lock_pin.set_pin("4821")
    access.unlock("pin")
    r = client.post("/api/chat", json={"message": "Jarvis, bloquear"}).json()
    assert "Bloqueando" in r["response"]
    assert access.get_state() == access.LOCKED


def test_windows_lock_phrase_is_not_jarvis_lock():
    assert turns.JARVIS_LOCK_CMD.fullmatch("jarvis bloquear")
    assert turns.JARVIS_LOCK_CMD.fullmatch("modo sentinela")
    assert turns.JARVIS_LOCK_CMD.fullmatch("bloquear a central")
    assert not turns.JARVIS_LOCK_CMD.fullmatch("bloquear a tela")
    assert not turns.JARVIS_LOCK_CMD.fullmatch("bloquear o computador")


def test_403_from_lock_keeps_cors_headers(client):
    """O frontend (porta 5173) precisa ler o 403 do bloqueio: a resposta leva cabeçalhos CORS."""
    _with_pin_locked()
    r = client.get("/api/tasks", headers={"Origin": "http://127.0.0.1:5173"})
    assert r.status_code == 403
    assert r.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"

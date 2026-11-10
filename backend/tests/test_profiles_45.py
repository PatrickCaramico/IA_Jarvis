"""V4.5: perfis por pessoa — dados separados, PIN, criação pelo bloqueio e volta ao dono."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import main
from modules import access, face, lock_pin, memory, prefs, profiles, tasks


@pytest.fixture
def home(tmp_path, monkeypatch):
    """data/ temporário: o dono usa a raiz, as pessoas novas data/perfis/<id>."""
    import importlib

    for module_name, attr, _ in profiles.PERSONAL_FILES:  # o monkeypatch devolve tudo no fim
        module = importlib.import_module(f"modules.{module_name}")
        if hasattr(module, attr):
            monkeypatch.setattr(module, attr, getattr(module, attr))
    monkeypatch.setattr(main.settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr(profiles, "REGISTRY_PATH", tmp_path / "perfis.json")
    monkeypatch.setattr(profiles, "PROFILES_DIR", tmp_path / "perfis")
    monkeypatch.setattr(profiles, "_active", "__nenhum__")
    profiles._point_modules_to(profiles.OWNER_ID)
    monkeypatch.setattr(profiles, "_active", profiles.OWNER_ID)
    # O rosto não é testado aqui (precisa de câmera e modelos): a foto é salva sem validar
    monkeypatch.setattr(face, "save_profile", lambda image, name: (
        face.PHOTO_PATH.parent.mkdir(parents=True, exist_ok=True),
        face.PHOTO_PATH.write_bytes(image),
        face.META_PATH.write_text('{"name": "%s"}' % name, encoding="utf-8"),
    ))
    access.reset_for_tests(access.LOCKED)
    yield tmp_path
    access.reset_for_tests(access.LOCKED)


def test_new_person_has_separate_files(home):
    prefs.update({"fan_mode_enabled": True})
    tasks_path_owner = Path(tasks._TASKS_PATH)
    pid = profiles.create("Maria Clara")
    assert pid == "maria-clara"
    profiles.activate(pid)
    assert Path(prefs._SETTINGS_PATH) == home / "perfis" / pid / "jarvis_settings.json"
    assert Path(memory._PATH).parent == home / "perfis" / pid
    assert prefs.get_all()["fan_mode_enabled"] is False  # começa com os padrões, não com os do dono
    assert Path(tasks._TASKS_PATH) != tasks_path_owner
    profiles.activate_owner()
    assert prefs.get_all()["fan_mode_enabled"] is True


def test_lock_returns_to_owner(home):
    pid = profiles.create("Ana")
    profiles.activate(pid)
    access.unlock("pin")
    assert profiles.active_id() == pid
    access.lock("manual")
    assert profiles.active_id() == profiles.OWNER_ID
    assert Path(prefs._SETTINGS_PATH) == home / "jarvis_settings.json"


def test_create_from_lock_requires_owner_pin(home):
    lock_pin.set_pin("4826")  # PIN do dono
    client = TestClient(main.app)
    body = {"name": "João", "photo": "data:image/jpeg;base64,AAAA", "pin": "7391"}
    assert client.get("/api/profiles/lock-info").json()["owner_pin_required"] is True
    assert client.post("/api/profiles", json={**body, "owner_pin": "0000"}).status_code == 403
    res = client.post("/api/profiles", json={**body, "owner_pin": "4826"})
    assert res.status_code == 200, res.text
    assert res.json()["profile"] == "joao" and res.json()["name"] == "João"
    assert access.get_state() == access.UNLOCKED and profiles.active_id() == "joao"
    assert client.get("/api/profiles").status_code == 200  # dentro: a lista abre


def test_pin_picks_the_right_person_and_counts_on_owner(home):
    lock_pin.set_pin("4826")
    pid = profiles.create("Ana")
    profiles.activate(pid)
    lock_pin.set_pin("7391")
    profiles.activate_owner()
    client = TestClient(main.app)

    res = client.post("/api/auth/pin", json={"pin": "7391"}).json()
    assert res["verified"] is True and profiles.active_id() == pid
    access.lock("manual")

    res = client.post("/api/auth/pin", json={"pin": "1111"}).json()
    assert res["verified"] is False and res["remaining_attempts"] == lock_pin.MAX_ATTEMPTS - 1  # contou no dono
    res = client.post("/api/auth/pin", json={"pin": "4826"}).json()
    assert res["verified"] is True and profiles.active_id() == profiles.OWNER_ID


def test_only_owner_deletes_and_owner_cannot_be_deleted(home):
    pid = profiles.create("Ana")
    access.unlock("pin")
    client = TestClient(main.app)
    assert client.delete(f"/api/profiles/{profiles.OWNER_ID}").status_code == 400
    profiles.activate(pid)
    assert client.delete(f"/api/profiles/{pid}").status_code == 403
    profiles.activate_owner()
    assert client.delete(f"/api/profiles/{pid}").status_code == 200
    assert not (home / "perfis" / pid).exists()

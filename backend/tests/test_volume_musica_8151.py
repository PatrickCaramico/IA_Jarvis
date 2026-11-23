"""V8.15.1: volume da música (barra do painel VOZ), guardado e usado no fim do briefing da manhã."""
from types import SimpleNamespace as NS

import pytest

from modules import morning_music as mm
from modules import prefs, spotify


@pytest.fixture
def client(monkeypatch, isolated_data):
    from fastapi.testclient import TestClient

    import main
    from modules import access

    access.reset_for_tests(access.UNLOCKED)
    yield TestClient(main.app)
    access.reset_for_tests(access.LOCKED)


def test_set_volume_saves_and_applies(client, monkeypatch):
    applied = []
    monkeypatch.setattr(spotify, "set_volume", lambda v, device_id=None: applied.append(v))
    assert client.post("/api/integrations/spotify/volume", json={"percent": 85}).json() == {"percent": 85}
    assert applied == [85] and prefs.get_all()["music_volume"] == 85
    assert client.post("/api/integrations/spotify/volume", json={"percent": 140}).json() == {"percent": 100}


def test_volume_saved_even_without_spotify(client, monkeypatch):
    def boom(v, device_id=None):
        raise RuntimeError("Spotify ainda não está conectado.")

    monkeypatch.setattr(spotify, "set_volume", boom)
    res = client.post("/api/integrations/spotify/volume", json={"percent": 40})
    assert res.status_code == 409 and prefs.get_all()["music_volume"] == 40


def test_get_volume_live_or_saved(client, monkeypatch):
    monkeypatch.setattr(spotify, "current_volume", lambda: 33)
    assert client.get("/api/integrations/spotify/volume").json() == {"percent": 33, "saved": 60, "live": True}
    monkeypatch.setattr(spotify, "current_volume", lambda: (_ for _ in ()).throw(RuntimeError("x")))
    assert client.get("/api/integrations/spotify/volume").json()["percent"] == 60


def test_current_volume_reads_the_device(monkeypatch):
    monkeypatch.setattr(spotify, "_request", lambda m, p, **k: NS(status_code=200, json=lambda: {"device": {"volume_percent": 47}}))
    assert spotify.current_volume() == 47
    monkeypatch.setattr(spotify, "_request", lambda m, p, **k: NS(status_code=204, json=lambda: None))
    assert spotify.current_volume() is None


def test_morning_music_rises_to_your_volume(monkeypatch):
    vols = []
    monkeypatch.setattr(spotify, "set_volume", lambda v, device_id=None: vols.append(v))
    prefs.update(music_volume=90)
    mm.finish(mm.Plan("Back in Black", "pc1", "uri", playing=True), sleep=lambda s: None)
    assert vols[-1] == 90 and vols == sorted(vols)
    assert prefs.validate_patch({"music_volume": 101}) is not None
    assert prefs.validate_patch({"music_volume": True}) is not None

"""V8.13.2: o JARVIS toca num aparelho de verdade (antes mandava tocar sem aparelho e o Spotify recusava com 404)."""
from types import SimpleNamespace as NS

import pytest
import requests

from modules import spotify

PC = {"id": "pc1", "type": "Computer", "is_active": False, "is_restricted": False}
PHONE = {"id": "cel1", "type": "Smartphone", "is_active": True, "is_restricted": False}
TV = {"id": "tv1", "type": "TV", "is_active": False, "is_restricted": True}


def test_pick_device_prefers_active_then_computer():
    assert spotify.pick_device([PC, PHONE])["id"] == "cel1"
    assert spotify.pick_device([TV, {**PHONE, "is_active": False}, PC])["id"] == "pc1"
    assert spotify.pick_device([TV]) is None  # restrito não aceita controle
    assert spotify.pick_device([]) is None


@pytest.fixture
def api(monkeypatch):
    calls, state = [], {"devices": [[PC]], "play_status": 204}

    def fake_request(method, path, **kw):
        calls.append((method, path, kw))
        if path == "/me/player/devices":
            devs = state["devices"].pop(0) if len(state["devices"]) > 1 else state["devices"][0]
            return NS(json=lambda: {"devices": devs})
        if path == "/me/player/play" and state["play_status"] >= 400:
            raise requests.HTTPError(response=NS(status_code=state["play_status"]))
        return NS(status_code=204, json=lambda: {})

    monkeypatch.setattr(spotify, "_request", fake_request)
    return calls, state


def test_plays_on_the_chosen_device(api):
    calls, _ = api
    spotify._play({"uris": ["spotify:track:x"]})
    method, path, kw = calls[-1]
    assert (method, path) == ("PUT", "/me/player/play")
    assert kw["params"] == {"device_id": "pc1"} and kw["json"] == {"uris": ["spotify:track:x"]}


def test_opens_the_app_and_waits_when_no_device(api, monkeypatch):
    calls, state = api
    state["devices"] = [[], [], [PC]]
    opened = []
    monkeypatch.setattr(spotify, "_launch_app", lambda: opened.append(1) or True)
    assert spotify.ensure_device(wait_s=10, sleep=lambda s: None) == "pc1"
    assert opened == [1]


def test_no_device_even_after_opening(api, monkeypatch):
    _, state = api
    state["devices"] = [[]]
    monkeypatch.setattr(spotify, "_launch_app", lambda: True)
    with pytest.raises(spotify.SpotifyError) as err:
        spotify.ensure_device(wait_s=0.01, sleep=lambda s: None)
    assert err.value.code == "no_device" and "Abra o Spotify" in str(err.value)


def test_premium_and_404_become_clear_errors(api):
    _, state = api
    state["play_status"] = 403
    with pytest.raises(spotify.SpotifyError) as err:
        spotify._play({"uris": ["x"]})
    assert err.value.code == "premium"
    state["play_status"] = 404
    with pytest.raises(spotify.SpotifyError) as err:
        spotify._play({"uris": ["x"]})
    assert err.value.code == "no_device"


def test_route_returns_the_reason(monkeypatch, isolated_data):
    from fastapi.testclient import TestClient

    import main
    from modules import access

    def boom(query, playlist=False):
        raise spotify.SpotifyError("premium", spotify.PREMIUM_MSG)

    monkeypatch.setattr(spotify, "search_and_play", boom)
    access.reset_for_tests(access.UNLOCKED)
    try:
        res = TestClient(main.app).post("/api/integrations/spotify/play", json={"query": "Back in Black AC/DC"})
        assert res.status_code == 409 and "Premium" in res.json()["detail"]
    finally:
        access.reset_for_tests(access.LOCKED)

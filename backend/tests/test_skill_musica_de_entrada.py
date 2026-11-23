"""V8.13: música de entrada (Back in Black) pela voz e ao entrar na central. O Spotify é falso."""
import asyncio

import pytest

from core.skills import registry, router
from modules import prefs, spotify


@pytest.fixture
def fake_spotify(monkeypatch):
    played = []
    state = {"connected": True, "error": None, "reply": None}
    monkeypatch.setattr(spotify, "connected", lambda: state["connected"])

    def play(query, playlist=False):
        if state["error"]:
            raise state["error"]
        played.append((query, playlist))
        return state["reply"] or f"Tocando {query}, senhor."

    monkeypatch.setattr(spotify, "search_and_play", play)
    return played, state


def test_phrases_reach_the_skill(real_skills):
    for phrase in ("toca a musica do homem de ferro", "toca back in black", "coloca back in black no spotify",
                   "jarvis toca a musica de entrada", "modo homem de ferro"):
        hit = registry.match(phrase, phrase)
        assert hit and hit[0].name == "musica_de_entrada", phrase
    for phrase in ("toca coldplay", "quem e o homem de ferro", "assiste homem de ferro 2", "abre o spotify"):
        hit = registry.match(phrase, phrase)
        assert hit is None or hit[0].name != "musica_de_entrada", phrase


def test_plays_back_in_black_by_default(real_skills, fake_spotify):
    played, _ = fake_spotify
    res = asyncio.run(router.try_fast_path("toca a música do Homem de Ferro"))
    assert played == [("Back in Black AC/DC", False)]
    assert res.speech.startswith("Back in Black, senhor")


def test_uses_the_chosen_song(real_skills, fake_spotify):
    played, _ = fake_spotify
    prefs.update(intro_song="Thunderstruck AC/DC")
    asyncio.run(router.try_fast_path("toca a musica de entrada"))
    assert played == [("Thunderstruck AC/DC", False)]


def test_without_spotify_or_with_errors(real_skills, fake_spotify):
    played, state = fake_spotify
    state["connected"] = False
    assert "conecte o Spotify" in asyncio.run(router.try_fast_path("toca back in black")).speech
    state["connected"] = True
    state["error"] = spotify.SpotifyError("no_device", spotify.NO_DEVICE_MSG)
    assert "Abra o Spotify" in asyncio.run(router.try_fast_path("toca back in black")).speech
    state["error"] = spotify.SpotifyError("premium", spotify.PREMIUM_MSG)
    assert "Premium" in asyncio.run(router.try_fast_path("toca back in black")).speech
    state["error"] = RuntimeError("A autorização do Spotify expirou.")
    assert "Conecte de novo" in asyncio.run(router.try_fast_path("toca back in black")).speech
    state["error"] = None
    state["reply"] = "Não encontrei track com o nome 'x'."
    assert asyncio.run(router.try_fast_path("toca back in black")).ok is False
    assert played == [("Back in Black AC/DC", False)]


def test_prefs_validation():
    assert prefs.validate_patch({"intro_song": "x" * 200}) is not None
    patch = {"intro_song": "  Back in Black  ", "intro_song_on_entry": False}
    assert prefs.validate_patch(patch) is None and patch["intro_song"] == "Back in Black"
    assert prefs.validate_patch({"intro_song_on_entry": "sim"}) is not None


def test_entry_music_route(monkeypatch, isolated_data):
    from fastapi.testclient import TestClient

    import main
    from modules import access
    from routes import access as access_routes

    scheduled = []
    monkeypatch.setattr(spotify, "connected", lambda: True)
    monkeypatch.setattr(access_routes.runtime, "track_service", lambda coro: (scheduled.append(coro), coro.close()))
    access.reset_for_tests(access.UNLOCKED)
    try:
        client = TestClient(main.app)
        out = client.post("/api/lock/intro-music").json()
        assert out == {"status": "scheduled", "song": "Back in Black AC/DC"} and len(scheduled) == 1
        prefs.update(intro_song_on_entry=False)
        assert client.post("/api/lock/intro-music").json()["reason"] == "no_playlist"
        prefs.update(intro_song_on_entry=True, silent_mode=True)
        assert client.post("/api/lock/intro-music").json()["reason"] == "silent_mode"
    finally:
        access.reset_for_tests(access.LOCKED)

"""V8.14.1: Back in Black na inicialização do dia (briefing de "bom dia"), baixinho e subindo no fim. Spotify falso."""
import asyncio
from datetime import date

import pytest

from modules import morning_music as mm
from modules import prefs, spotify

TODAY = date(2026, 11, 24)


@pytest.fixture
def fake(monkeypatch):
    log = []
    state = {"playing": False, "volume_ok": True, "track": {"uri": "spotify:track:bib"}}
    monkeypatch.setattr(spotify, "connected", lambda: True)
    monkeypatch.setattr(spotify, "now_playing", lambda: {"state": "playing" if state["playing"] else "idle"})
    monkeypatch.setattr(spotify, "find_track", lambda q: log.append(("find", q)) or state["track"])
    monkeypatch.setattr(spotify, "ensure_device", lambda launch=True: "pc1")

    def set_volume(v, device_id=None):
        if not state["volume_ok"]:
            raise RuntimeError("sem volume")
        log.append(("vol", v, device_id))

    monkeypatch.setattr(spotify, "set_volume", set_volume)
    monkeypatch.setattr(spotify, "_play", lambda body=None, launch=True, device_id=None: log.append(("play", body["uris"][0], device_id)))
    return log, state


def test_starts_quiet_and_raises_at_the_end(fake):
    log, _ = fake
    plan = mm.start(TODAY)
    assert log == [("find", "Back in Black AC/DC"), ("vol", mm.BACKGROUND_VOLUME, "pc1"), ("play", "spotify:track:bib", "pc1")]
    assert prefs.get_all()["intro_song_morning_day"] == "2026-11-24"
    log.clear()
    mm.finish(plan, sleep=lambda s: None)
    vols = [v for kind, v, *_ in log if kind == "vol"]
    assert vols[0] > mm.BACKGROUND_VOLUME and vols[-1] == mm.NORMAL_VOLUME and vols == sorted(vols)


def test_only_once_a_day(fake):
    log, _ = fake
    assert mm.start(TODAY) is not None
    log.clear()
    assert mm.start(TODAY) is None and log == []
    assert mm.start(date(2026, 11, 25)) is not None


def test_without_volume_control_it_waits_for_the_briefing(fake):
    log, state = fake
    state["volume_ok"] = False
    plan = mm.start(TODAY)
    assert plan.deferred and not [e for e in log if e[0] == "play"]  # nada por cima da fala
    mm.finish(plan, sleep=lambda s: None)
    assert log[-1] == ("play", "spotify:track:bib", "pc1")


def test_canceled_briefing_does_not_start_the_waiting_song(fake):
    log, state = fake
    state["volume_ok"] = False
    plan = mm.start(TODAY)
    mm.finish(plan, canceled=True, sleep=lambda s: None)
    assert not [e for e in log if e[0] == "play"]


def test_respects_music_already_playing_silent_mode_and_the_switch(fake):
    log, state = fake
    state["playing"] = True
    assert mm.start(TODAY) is None
    state["playing"] = False
    prefs.update(silent_mode=True)
    assert mm.start(TODAY) is None
    prefs.update(silent_mode=False, intro_song_morning=False)
    assert mm.start(TODAY) is None
    assert not [e for e in log if e[0] == "play"]


def test_spotify_errors_never_break_the_briefing(fake, monkeypatch):
    def no_device(launch=True):
        raise spotify.SpotifyError("no_device", spotify.NO_DEVICE_MSG)

    monkeypatch.setattr(spotify, "ensure_device", no_device)
    assert mm.start(TODAY) is None
    mm.finish(None)  # nada a fazer


def test_briefing_flow_plays_only_in_the_morning(monkeypatch):
    from core import briefing_flow, runtime, session

    calls = []
    monkeypatch.setattr(mm, "start", lambda: calls.append("start") or "plano")
    monkeypatch.setattr(mm, "finish", lambda plan, canceled=False: calls.append(("finish", plan, canceled)))

    async def quiet(*a, **k):
        return None

    monkeypatch.setattr(runtime.manager, "broadcast", quiet)
    monkeypatch.setattr(briefing_flow.speech, "speak", quiet)
    monkeypatch.setattr(briefing_flow, "_say_or_skip", quiet)
    monkeypatch.setattr(briefing_flow.prefs, "is_silent_mode", lambda: True)
    data = {"mode": "morning", "segments": [], "greeting": "Bom dia", "opening_speech": "", "title": "t", "tabs": [],
            "opening": "o", "opening_sub": "", "readiness": 0, "closing": "", "speech": "x"}

    async def run(mode):
        calls.clear()
        await briefing_flow.run_sequence("bom dia", session.turn_id, {**data, "mode": mode}, 10)
        # espera de verdade as tarefas de fundo (pausar/retomar/música rodam em threads), sem tempo fixo
        for _ in range(100):
            pending = [t for t in runtime.background_tasks if not t.done()]
            if not pending:
                break
            await asyncio.wait(pending, timeout=1)

    asyncio.run(run("morning"))
    assert calls[0] == "start" and calls[-1] == ("finish", "plano", False)
    asyncio.run(run("evening"))
    assert calls == []

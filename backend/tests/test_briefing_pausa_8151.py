"""V8.15.1: o Spotify pausa enquanto o JARVIS lê o briefing e volta no fim. Spotify falso."""
import asyncio

import pytest

from modules import briefing_music as bm
from modules import morning_music, prefs, spotify


@pytest.fixture
def fake(monkeypatch):
    log = []
    state = {"state": "playing", "title": "Thunderstruck"}
    monkeypatch.setattr(spotify, "connected", lambda: True)
    monkeypatch.setattr(spotify, "now_playing", lambda: dict(state))

    def pause():
        log.append("pause")
        state["state"] = "paused"

    def play():
        log.append("play")
        state["state"] = "playing"

    monkeypatch.setattr(spotify, "pause", pause)
    monkeypatch.setattr(spotify, "play", play)
    return log, state


def test_pauses_and_resumes(fake):
    log, _ = fake
    paused = bm.pause_if_playing()
    assert paused == {"title": "Thunderstruck"} and log == ["pause"]
    assert bm.resume(paused) is True and log == ["pause", "play"]


def test_nothing_playing_nothing_to_do(fake):
    log, state = fake
    state["state"] = "paused"
    assert bm.pause_if_playing() is None and log == []
    assert bm.resume(None) is False


def test_does_not_resume_over_what_you_changed(fake):
    log, state = fake
    paused = bm.pause_if_playing()
    state.update(state="playing", title="Outra")  # você deu play em outra coisa no meio
    assert bm.resume(paused) is False
    state.update(state="paused", title="Outra")  # trocou de música e pausou
    assert bm.resume(paused) is False
    assert log == ["pause"]


def test_switch_and_silent_mode(fake):
    log, _ = fake
    prefs.update(briefing_pause_music=False)
    assert bm.pause_if_playing() is None
    prefs.update(briefing_pause_music=True, silent_mode=True)  # silencioso: o briefing não é falado
    assert bm.pause_if_playing() is None
    assert log == []


def test_spotify_errors_never_break_the_briefing(fake, monkeypatch):
    def boom():
        raise RuntimeError("sem rede")

    monkeypatch.setattr(spotify, "now_playing", boom)
    assert bm.pause_if_playing() is None
    assert bm.resume({"title": "x"}) is False


def _briefing(monkeypatch, mode):
    from core import briefing_flow, runtime, session

    async def quiet(*a, **k):
        return None

    monkeypatch.setattr(runtime.manager, "broadcast", quiet)
    monkeypatch.setattr(briefing_flow.speech, "speak", quiet)
    monkeypatch.setattr(briefing_flow, "_say_or_skip", quiet)
    monkeypatch.setattr(briefing_flow.prefs, "is_silent_mode", lambda: False)
    data = {"mode": mode, "segments": [], "greeting": "Bom dia", "opening_speech": "", "title": "t", "tabs": [],
            "opening": "o", "opening_sub": "", "readiness": 0, "closing": "", "speech": "x"}

    async def run():
        await briefing_flow.run_sequence("bom dia", session.turn_id, data, 10)
        # espera de verdade as tarefas de fundo (pausar/retomar/música rodam em threads), sem tempo fixo
        for _ in range(100):
            pending = [t for t in runtime.background_tasks if not t.done()]
            if not pending:
                break
            await asyncio.wait(pending, timeout=1)

    asyncio.run(run())


def test_briefing_pauses_your_music_and_skips_back_in_black(fake, monkeypatch):
    log, _ = fake
    started = []
    monkeypatch.setattr(morning_music, "start", lambda: started.append(1))
    _briefing(monkeypatch, "morning")
    assert log == ["pause", "play"]  # pausou para ler e voltou no fim
    assert started == []  # a música da manhã não entra no lugar da sua


def test_every_briefing_pauses(fake, monkeypatch):
    log, _ = fake
    _briefing(monkeypatch, "evening")
    assert log == ["pause", "play"]

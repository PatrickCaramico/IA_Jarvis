"""V9.4: a música do briefing começa enquanto o briefing ainda é montado, e no fim sobe ainda mais de volume."""
import asyncio

from core import briefing_flow, runtime, session
from modules import briefing, morning_music as mm, prefs


def test_end_volume_goes_higher_than_the_panel():
    assert prefs.get_all()["briefing_end_volume"] == 80
    prefs.update(music_volume=60)
    assert mm.target_volume() == 80  # sobe além dos 60 do painel
    prefs.update(music_volume=95)
    assert mm.target_volume() == 95  # se o painel já está mais alto, vale o painel
    prefs.update(music_volume=60, briefing_end_volume=70)
    assert mm.target_volume() == 70
    assert prefs.validate_patch({"briefing_end_volume": 120}) is not None
    assert prefs.validate_patch({"briefing_end_volume": 85}) is None


def test_music_starts_while_the_briefing_is_being_built(monkeypatch):
    order = []

    def fake_start():
        order.append("musica")
        return "plano"

    monkeypatch.setattr(mm, "start", fake_start)
    monkeypatch.setattr(mm, "finish", lambda plan, canceled=False: order.append(("fim", plan, canceled)))
    monkeypatch.setattr(briefing_flow, "_pause_music", _none)
    monkeypatch.setattr(mm, "wanted", lambda today=None: "Back in Black")  # V9.5.5: Spotify conectado

    async def slow_build():
        await asyncio.sleep(0.3)  # notícias, clima, e-mails...
        order.append("montado")
        return {"mode": "morning"}

    monkeypatch.setattr(briefing, "build_for", lambda mode: slow_build)
    seen = {}

    async def fake_sequence(message, turn, data, max_history, music=None):
        seen["music"] = music
        await music.finish(False)

    monkeypatch.setattr(briefing_flow, "run_sequence", fake_sequence)

    async def scenario():
        out = await briefing_flow.start("bom dia", session.turn_id, 10, "morning")
        for _ in range(50):
            pending = [t for t in runtime.background_tasks if not t.done()]
            if not pending:
                break
            await asyncio.wait(pending, timeout=1)
        return out

    assert asyncio.run(scenario())["status"] == "ok"
    assert order.index("musica") < order.index("montado")  # antes, só depois de montar tudo
    assert order[-1] == ("fim", "plano", False) and seen["music"].plan == "plano"


async def _none():
    return None


def test_your_music_is_paused_and_no_morning_song(monkeypatch):
    calls = []

    async def paused():
        return {"title": "Minha música"}

    async def resumed(p):
        calls.append(("volta", p["title"]))

    monkeypatch.setattr(briefing_flow, "_pause_music", paused)
    monkeypatch.setattr(briefing_flow, "_resume_music", resumed)
    monkeypatch.setattr(mm, "start", lambda: calls.append("musica_da_manha"))

    async def scenario():
        music = briefing_flow.start_music("morning")
        await music.wait_pause()
        await music.finish(False)
        return music

    music = asyncio.run(scenario())
    assert music.paused == {"title": "Minha música"} and music.plan is None
    assert calls == [("volta", "Minha música")]  # a da manhã não entra no lugar da sua

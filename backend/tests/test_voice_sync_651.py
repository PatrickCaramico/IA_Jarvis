"""V6.5.1: briefing com a voz adiantada e o celular confirmando o fim de cada fala."""
import asyncio
from pathlib import Path

from core import voice_route
from modules import tts


def test_prefetched_voice_is_reused(monkeypatch, tmp_path):
    calls = []

    async def fake_remote(text, path, volume):
        calls.append(text)
        await asyncio.sleep(0.01)
        Path(path).write_bytes(b"MP3:" + text.encode())

    monkeypatch.setattr(tts, "_synthesize_remote", fake_remote)
    monkeypatch.setattr(tts, "_current_volume", lambda: "+0%")

    async def run():
        tts.clear_prefetch()
        started = tts.prefetch(["Em Marvel, as três principais. Primeira: filme novo."], whole=True)
        assert started == 1
        out = tmp_path / "a.mp3"
        await tts._synthesize("Em Marvel, as três principais. Primeira: filme novo.", str(out))  # noqa: SLF001
        return out.read_bytes()

    data = asyncio.run(run())
    assert data.startswith(b"MP3:Em Marvel")
    assert len(calls) == 1  # gerou uma vez só (adiantada), não de novo na hora de falar


def test_prefetch_skips_empty_and_duplicates(monkeypatch):
    async def fake_remote(text, path, volume):
        Path(path).write_bytes(b"x")

    monkeypatch.setattr(tts, "_synthesize_remote", fake_remote)

    async def run():
        tts.clear_prefetch()
        n = tts.prefetch(["Olá, senhor.", "", "Olá, senhor."], whole=True)
        tts.clear_prefetch()
        return n

    assert asyncio.run(run()) == 1


def test_device_ack_releases_the_wait():
    async def run():
        say_id = voice_route.new_say_id()
        ev = voice_route.expect(say_id)
        assert not ev.is_set()
        assert voice_route.mark_played(say_id) is True
        assert ev.is_set()
        assert voice_route.mark_played(say_id) is False  # só vale uma vez
        assert voice_route.mark_played("desconhecido") is False

    asyncio.run(run())


def test_speak_on_device_waits_for_the_phone(monkeypatch):
    from core import runtime, session, speech
    from modules import prefs

    sent = []

    async def fake_broadcast(msg):
        sent.append(msg)
        if msg.get("type") == "speak_on_device":
            asyncio.get_running_loop().call_later(0.05, voice_route.mark_played, msg["say_id"])

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    monkeypatch.setattr(prefs, "is_silent_mode", lambda: False)
    monkeypatch.setattr(voice_route, "estimate_seconds", lambda text: 30.0)  # sem o aviso, esperaria 51 s

    async def run():
        token = voice_route.set_target("celular-abc123")
        try:
            loop = asyncio.get_running_loop()
            t0 = loop.time()
            await speech.speak("Primeira manchete do dia.", release_busy=False, idle_after=False)
            return loop.time() - t0
        finally:
            voice_route.reset(token)

    elapsed = asyncio.run(run())
    assert elapsed < 2
    msg = next(m for m in sent if m.get("type") == "speak_on_device")
    assert msg["say_id"] and msg["client_id"] == "celular-abc123"
    assert session.speaking == 0

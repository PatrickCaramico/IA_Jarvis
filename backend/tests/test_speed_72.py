"""V7.2: JARVIS mais rápido (o aviso "só um minutinho" é cortado; cartões não atrasam a resposta)."""
import asyncio

from config import settings
from core import speech
from modules import tts


def test_filler_is_cut_when_answer_arrives(monkeypatch):
    stopped = []
    cut = {}

    async def long_filler(text):  # "toca" por 5 s, a não ser que o áudio seja cortado
        cut["event"] = asyncio.Event()
        try:
            await asyncio.wait_for(cut["event"].wait(), timeout=5)
        except asyncio.TimeoutError:
            pass

    def stop_playback():
        stopped.append(True)
        cut["event"].set()

    monkeypatch.setattr(settings, "FILLER_FIRST_DELAY", 0.05)
    monkeypatch.setattr(speech, "say_quietly", long_filler)
    monkeypatch.setattr(tts, "stop_playback", stop_playback)

    async def run():
        stop = asyncio.Event()
        loop_task = asyncio.create_task(speech.filler_loop(stop))
        await asyncio.sleep(0.15)  # o aviso já começou
        stop.set()
        await asyncio.wait_for(loop_task, timeout=1)  # antes: esperava os 5 s do aviso

    asyncio.run(run())
    assert stopped == [True]


def test_no_filler_when_answer_is_fast(monkeypatch):
    said = []

    async def filler(text):
        said.append(text)

    monkeypatch.setattr(settings, "FILLER_FIRST_DELAY", 0.3)
    monkeypatch.setattr(speech, "say_quietly", filler)

    async def run():
        stop = asyncio.Event()
        task = asyncio.create_task(speech.filler_loop(stop))
        await asyncio.sleep(0.05)
        stop.set()
        await asyncio.wait_for(task, timeout=1)

    asyncio.run(run())
    assert said == []

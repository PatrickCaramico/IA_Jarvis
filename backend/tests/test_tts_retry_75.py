"""V7.4.2: a voz tenta de novo quando a Microsoft responde "No audio was received"."""
import asyncio

from modules import tts


class FakeCommunicate:
    calls = 0

    def __init__(self, *a, **k):
        pass

    async def save(self, path):
        FakeCommunicate.calls += 1
        if FakeCommunicate.calls < 3:
            raise RuntimeError("No audio was received. Please verify that your parameters are correct.")
        with open(path, "wb") as f:
            f.write(b"ID3audio")


class FakeEdge:
    Communicate = FakeCommunicate


def test_retries_then_succeeds(tmp_path, monkeypatch):
    monkeypatch.setattr(tts, "_get_edge_tts", lambda: FakeEdge)
    monkeypatch.setattr(tts, "_edge_tts", FakeEdge, raising=False)
    monkeypatch.setattr(tts, "RETRY_DELAYS", (0.01, 0.01))
    FakeCommunicate.calls = 0
    out = tmp_path / "a.mp3"
    asyncio.run(tts._synthesize_remote("Olá, senhor.", str(out), "+0%"))
    assert FakeCommunicate.calls == 3 and out.read_bytes() == b"ID3audio"


def test_gives_up_after_retries(tmp_path, monkeypatch):
    monkeypatch.setattr(tts, "_get_edge_tts", lambda: FakeEdge)
    monkeypatch.setattr(tts, "_edge_tts", FakeEdge, raising=False)
    monkeypatch.setattr(tts, "RETRY_DELAYS", (0.01,))
    FakeCommunicate.calls = -10
    try:
        asyncio.run(tts._synthesize_remote("Olá.", str(tmp_path / "b.mp3"), "+0%"))
        raise AssertionError("deveria desistir")
    except RuntimeError:
        assert FakeCommunicate.calls == -8


def test_nothing_to_say():
    assert tts.speakable("Olá") and tts.speakable("42")
    assert not tts.speakable("✦ 🌌 …") and not tts.speakable("")

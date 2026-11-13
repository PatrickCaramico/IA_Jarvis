"""V7.2: ⚡ OTIMIZAR no PC."""
import os
import time

from modules import optimizer


def test_removes_only_old_leftovers_and_trims_cache(tmp_path):
    now = time.time()
    old = tmp_path / "jarvis_abc.mp3"
    old.write_bytes(b"x" * 2048)
    os.utime(old, (now - 3600, now - 3600))
    fresh = tmp_path / "jarvis_now.mp3"  # fala tocando agora: fica
    fresh.write_bytes(b"x")
    other = tmp_path / "foto.jpg"
    other.write_bytes(b"x")
    os.utime(other, (now - 3600, now - 3600))
    cache = tmp_path / "jarvis_tts_cache"
    cache.mkdir()
    for i in range(optimizer.VOICE_CACHE_KEEP + 3):
        f = cache / f"{i}.mp3"
        f.write_bytes(b"y")
        os.utime(f, (now - 10_000 + i, now - 10_000 + i))

    out = optimizer.run(tmp_path, now)
    assert out["audio_leftovers"] == 1 and out["voice_cache_trimmed"] == 3
    assert not old.exists() and fresh.exists() and other.exists()
    assert not (cache / "0.mp3").exists() and (cache / f"{optimizer.VOICE_CACHE_KEEP + 2}.mp3").exists()

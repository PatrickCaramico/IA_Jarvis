"""V7.2: ⚡ OTIMIZAR (botão no perfil, em CONTROLES e na tela de bloqueio).

No PC: apaga as sobras de áudio de falas interrompidas (jarvis_*.mp3 na pasta temporária), enxuga o
cache de voz em disco (mantém as frases mais recentes, que tocam na hora) e libera memória.
Nada de dados do usuário é apagado. A parte do aparelho (cache do navegador, modo leve) fica no frontend.
"""
from __future__ import annotations

import gc
import tempfile
import time
from pathlib import Path

ORPHAN_AGE_SECONDS = 10 * 60  # áudio de fala que ficou para trás (a fala atual nunca tem tanto tempo)
VOICE_CACHE_KEEP = 400  # frases no cache de voz em disco


def _remove(path: Path) -> int:
    try:
        size = path.stat().st_size
        path.unlink()
        return size
    except OSError:
        return 0


def run(tmp_dir: Path | None = None, now: float | None = None) -> dict:
    tmp = Path(tmp_dir or tempfile.gettempdir())
    now = now or time.time()
    freed = removed = 0
    for f in tmp.glob("jarvis_*.mp3"):
        try:
            old = now - f.stat().st_mtime > ORPHAN_AGE_SECONDS
        except OSError:
            continue
        if old:
            size = _remove(f)
            freed += size
            removed += 1 if size or not f.exists() else 0

    cache = tmp / "jarvis_tts_cache"
    trimmed = 0
    if cache.is_dir():
        files = sorted((f for f in cache.iterdir() if f.is_file()), key=lambda f: f.stat().st_mtime, reverse=True)
        for f in files[VOICE_CACHE_KEEP:]:
            freed += _remove(f)
            trimmed += 1

    collected = gc.collect()
    return {
        "status": "ok",
        "freed_mb": round(freed / 1_048_576, 2),
        "audio_leftovers": removed,
        "voice_cache_trimmed": trimmed,
        "objects_freed": collected,
    }

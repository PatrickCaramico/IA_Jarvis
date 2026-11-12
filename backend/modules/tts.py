"""Módulo de voz: sintetiza fala em português com edge-tts e reproduz com pygame.

Para a resposta começar a tocar mais cedo, o texto é dividido em frases: todas são
sintetizadas em paralelo e tocadas em ordem, assim que cada uma fica pronta.
Um lock garante que duas falas nunca toquem ao mesmo tempo.

Otimizações 4.2 (latência):
- a primeira parte é curta (corta numa vírgula se a primeira frase for longa), então o primeiro
  som sai antes enquanto o resto ainda é sintetizado;
- frases fixas (avisos, "só um minutinho") ficam num cache em disco e frases curtas repetidas num
  cache em memória, tocando sem nova síntese;
- a pausa entre partes caiu de 0,35 s para 0,2 s.
"""
import hashlib
import asyncio
import logging
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Awaitable, Callable, Optional

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402

# V4.4: o edge_tts (com o aiohttp) levava ~4 s só para importar e segurava a subida do servidor.
# Agora ele é carregado na primeira fala ou por preload() em segundo plano logo após o servidor subir.
_edge_tts = None


def _get_edge_tts():
    global _edge_tts
    if _edge_tts is None:
        import edge_tts

        _edge_tts = edge_tts
    return _edge_tts


async def preload() -> None:
    """Carrega o edge_tts numa thread, sem atrasar a subida do servidor."""
    try:
        await asyncio.to_thread(_get_edge_tts)
    except Exception:  # noqa: BLE001
        log.warning("Não foi possível pré-carregar o edge-tts.", exc_info=True)

from config import settings  # noqa: E402

log = logging.getLogger("jarvis.tts")

_playback_lock = asyncio.Lock()


def _clean_for_speech(text: str) -> str:
    """Remove marcações Markdown que a voz leria em voz alta (asteriscos, #, crases...)."""
    text = re.sub(r"[*_`#>]+", "", text)
    text = re.sub(r"\.{3,}|…", ",", text)  # V6.1: "Olá... tudo bem" soava arrastado; vira uma pausa curta
    text = re.sub(r",\s*,", ",", text)
    return re.sub(r"\s+", " ", text).strip()


FIRST_CHUNK_MAX = 90  # caracteres: acima disso a primeira frase é cortada numa vírgula
PAUSE_BETWEEN_CHUNKS = 0.2


def _split_first(sentence: str) -> list[str]:
    """Corta uma primeira frase longa na primeira vírgula/ponto e vírgula depois de ~25 caracteres."""
    if len(sentence) <= FIRST_CHUNK_MAX:
        return [sentence]
    m = re.search(r"^(.{25,%d}?[,;:])\s+(.+)$" % FIRST_CHUNK_MAX, sentence)
    return [m.group(1), m.group(2)] if m else [sentence]


ONE_PIECE_MAX = 280  # V6.1: até aqui a fala vai inteira (entonação contínua, sem "recomeçar" a cada frase)


def _split_chunks(text: str, max_chunks: int = 4) -> list[str]:
    """V6.1: fala curta vai inteira; fala longa vai em blocos de frases inteiras (~240 caracteres).

    Antes a primeira frase saía sozinha (para começar mais rápido) e cada pedaço recomeçava a entonação,
    o que deixava a voz picotada e robótica.
    """
    if len(text) <= ONE_PIECE_MAX:
        return [text] if text else []
    parts = [p.strip() for p in re.split(r"(?<=[.!?…])\s+", text) if p.strip()]
    chunks: list[str] = []
    for p in parts:
        if chunks and len(chunks[-1]) + 1 + len(p) <= 240:
            chunks[-1] = f"{chunks[-1]} {p}"
        else:
            chunks.append(p)
    if len(chunks) <= max_chunks:
        return chunks
    return chunks[: max_chunks - 1] + [" ".join(chunks[max_chunks - 1:])]


# ---- cache de frases fixas e repetidas --------------------------------------------------------
# Frases fixas do sistema (avisos, "só um minutinho") podem ser registradas com register_phrases():
# ficam em disco e tocam na hora até depois de reiniciar. Outras frases curtas só entram num cache
# em memória quando se repetem na mesma sessão, e nunca vão para o disco (podem ser pessoais).
CACHE_DIR = Path(tempfile.gettempdir()) / "jarvis_tts_cache"
CACHE_MAX_CHARS = 160
CACHE_MAX_FILES = 40
MEMORY_CACHE_MAX = 20
_preset_phrases: set[str] = set()
_seen_counts: dict[str, int] = {}
_memory_cache: dict[str, bytes] = {}


def register_phrases(phrases) -> None:
    """Marca frases fixas para o cache em disco (texto exatamente como será falado)."""
    for phrase in phrases:
        cleaned = _clean_for_speech(phrase)
        for chunk in _split_chunks(cleaned):
            _preset_phrases.add(chunk)


# V6.1: estilos de voz (Configurações › Voz). "natural" é o padrão: o mesmo Antonio, um pouco mais grave e
# mais calmo, como um mordomo. Quem definiu TTS_VOICE/TTS_RATE no .env continua com eles em "classica".
VOICE_STYLES = {
    "natural": {"label": "Natural (padrão)", "voice": None, "rate": "-4%", "pitch": "-3Hz"},
    "grave": {"label": "Grave", "voice": None, "rate": "-7%", "pitch": "-9Hz"},
    "classica": {"label": "Clássica (como antes)", "voice": None, "rate": None, "pitch": "+0Hz"},
    "thalita": {"label": "Thalita (feminina)", "voice": "pt-BR-ThalitaMultilingualNeural", "rate": "-2%", "pitch": "+0Hz"},
    "andrew": {"label": "Andrew (multilíngue)", "voice": "en-US-AndrewMultilingualNeural", "rate": "-3%", "pitch": "+0Hz"},
}


def voice_params() -> tuple[str, str, str]:
    """(voz, velocidade, tom) do estilo escolhido nas preferências."""
    try:
        from modules import prefs

        style = VOICE_STYLES.get(prefs._load().get("voice_style") or "natural") or VOICE_STYLES["natural"]
    except Exception:  # noqa: BLE001
        style = VOICE_STYLES["natural"]
    return (style["voice"] or settings.TTS_VOICE, style["rate"] or settings.TTS_RATE, style["pitch"])


def _cache_key(text: str, volume: str) -> str:
    voice, rate, pitch = voice_params()
    return hashlib.sha1(f"{voice}|{rate}|{pitch}|{volume}|{text}".encode("utf-8")).hexdigest()


def _trim_disk_cache() -> None:
    try:
        files = sorted(CACHE_DIR.glob("*.mp3"), key=lambda p: p.stat().st_mtime)
        for old in files[:-CACHE_MAX_FILES]:
            old.unlink(missing_ok=True)
    except OSError:
        log.debug("Não foi possível limpar o cache de voz.")


def _from_cache(text: str, volume: str, path: str) -> bool:
    key = _cache_key(text, volume)
    if key in _memory_cache:
        Path(path).write_bytes(_memory_cache[key])
        return True
    disk = CACHE_DIR / f"{key}.mp3"
    if text in _preset_phrases and disk.exists() and disk.stat().st_size > 0:
        shutil.copyfile(disk, path)
        return True
    return False


def _to_cache(text: str, volume: str, path: str) -> None:
    if len(text) > CACHE_MAX_CHARS:
        return
    try:
        data = Path(path).read_bytes()
    except OSError:
        return
    if not data:
        return
    key = _cache_key(text, volume)
    if text in _preset_phrases:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            (CACHE_DIR / f"{key}.mp3").write_bytes(data)
            _trim_disk_cache()
        except OSError:
            log.debug("Não foi possível guardar a frase no cache de voz.")
        return
    _seen_counts[key] = _seen_counts.get(key, 0) + 1
    if _seen_counts[key] >= 2:
        if len(_memory_cache) >= MEMORY_CACHE_MAX:
            _memory_cache.pop(next(iter(_memory_cache)))
        _memory_cache[key] = data
    if len(_seen_counts) > 500:
        _seen_counts.clear()


_mixer_device: Optional[str] = None  # V6.5.8: aparelho em que o mixer foi aberto ("" = padrão)


def _ensure_mixer() -> None:
    """Abre (ou reabre) o som na caixa escolhida no botão de áudio do bloqueio."""
    global _mixer_device
    try:
        from modules import prefs

        wanted = prefs.get_all().get("audio_output_device") or ""
    except Exception:  # noqa: BLE001
        wanted = ""
    if pygame.mixer.get_init() and wanted == (_mixer_device or ""):
        return
    if pygame.mixer.get_init():
        pygame.mixer.quit()
    try:
        pygame.mixer.init(devicename=wanted) if wanted else pygame.mixer.init()
        _mixer_device = wanted
    except pygame.error:
        log.warning("Saída de áudio %r indisponível; usando a padrão.", wanted)
        pygame.mixer.init()
        _mixer_device = ""


def _play_audio_blocking(path: str) -> None:
    """Toca o arquivo de áudio e só retorna quando terminar (rodar em thread)."""
    _ensure_mixer()
    pygame.mixer.music.load(path)
    pygame.mixer.music.play()
    clock = pygame.time.Clock()
    while pygame.mixer.music.get_busy():
        clock.tick(15)
    pygame.mixer.music.unload()  # libera o arquivo (necessário para apagá-lo no Windows)


def stop_playback() -> None:
    """Corta na hora o áudio que estiver tocando (usado pelo botão Cancelar)."""
    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
    except pygame.error:
        log.debug("Não foi possível parar o áudio.")


# Permite ao main baixar o volume da voz (ex.: modo noturno da tela de bloqueio). Formato edge-tts: "+0%", "-35%".
volume_provider = None


def _current_volume() -> str:
    try:
        return volume_provider() if volume_provider else "+0%"
    except Exception:  # noqa: BLE001
        return "+0%"


async def _synthesize(text: str, path: str) -> None:
    volume = _current_volume()
    if _from_cache(text, volume, path):
        return
    task = _prefetched.pop(_cache_key(text, volume), None)
    if task is not None:  # V6.5.1: já estava sendo gerada antes (briefing): só espera terminar
        try:
            data = await task
            if data:
                Path(path).write_bytes(data)
                return
        except Exception:  # noqa: BLE001 - a geração adiantada falhou: gera agora, como antes
            log.debug("Voz adiantada falhou; gerando de novo.")
    await _synthesize_remote(text, path, volume)
    _to_cache(text, volume, path)


# ---- V6.5.1: voz adiantada ------------------------------------------------------------------
# No briefing, cada parte só começava a ser gerada quando chegava a vez dela: o card entrava e a voz
# demorava (pior nas notícias, as falas mais longas). Agora todas as partes começam a ser geradas no
# início (no máximo 3 de cada vez) e cada fala só espera o que faltar.
_prefetched: dict[str, "asyncio.Task[bytes]"] = {}
_PREFETCH_MAX = 24
_prefetch_slots: Optional[asyncio.Semaphore] = None


async def _render_bytes(text: str, volume: str) -> bytes:
    global _prefetch_slots
    if _prefetch_slots is None:
        _prefetch_slots = asyncio.Semaphore(3)
    async with _prefetch_slots:
        fd, path = tempfile.mkstemp(suffix=".mp3", prefix="jarvis_pre_")
        os.close(fd)
        try:
            await _synthesize_remote(text, path, volume)
            return Path(path).read_bytes()
        finally:
            try:
                os.remove(path)
            except OSError:
                pass


def prefetch(texts, whole: bool = False) -> int:
    """Começa a gerar a voz destes textos já. whole=False: nos mesmos pedaços que a caixa do PC toca;
    whole=True: o texto inteiro, como o celular pede em /api/tts. Devolve quantos pedidos começaram."""
    volume = _current_volume()
    started = 0
    for text in texts:
        speech = _clean_for_speech(text or "")
        if not speech:
            continue
        for piece in ([speech[:1500]] if whole else _split_chunks(speech)):
            key = _cache_key(piece, volume)
            if key in _prefetched or key in _memory_cache:
                continue
            while len(_prefetched) >= _PREFETCH_MAX:
                old = _prefetched.pop(next(iter(_prefetched)))
                old.cancel()
            _prefetched[key] = asyncio.create_task(_render_bytes(piece, volume))
            started += 1
    return started


def clear_prefetch() -> None:
    for task in _prefetched.values():
        task.cancel()
    _prefetched.clear()


async def _synthesize_remote(text: str, path: str, volume: str) -> None:
    edge_tts = _get_edge_tts() if _edge_tts is not None else await asyncio.to_thread(_get_edge_tts)
    voice, rate, pitch = voice_params()
    await edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch).save(path)


async def generate_and_play_speech(
    text: str,
    on_playback_start: Optional[Callable[[], Awaitable[None]]] = None,
) -> None:
    """Gera e toca a voz. on_playback_start é chamado logo antes do primeiro som."""
    speech = _clean_for_speech(text)
    if not speech:
        return

    chunks = _split_chunks(speech)
    paths: list[str] = []
    for _ in chunks:
        fd, p = tempfile.mkstemp(suffix=".mp3", prefix="jarvis_")
        os.close(fd)
        paths.append(p)

    # Começa a sintetizar tudo já (inclusive enquanto outra fala ainda toca).
    tasks = [asyncio.create_task(_synthesize(c, p)) for c, p in zip(chunks, paths)]
    try:
        async with _playback_lock:
            started = False
            for task, path in zip(tasks, paths):
                await task
                if not started:
                    started = True
                    if on_playback_start:
                        await on_playback_start()
                await asyncio.to_thread(_play_audio_blocking, path)
                if path != paths[-1]:
                    await asyncio.sleep(PAUSE_BETWEEN_CHUNKS)
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        for p in paths:
            try:
                os.remove(p)
            except OSError:
                log.debug("Não foi possível apagar %s", p)

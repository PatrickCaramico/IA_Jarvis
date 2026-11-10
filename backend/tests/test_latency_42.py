"""Otimizações de latência da 4.2: fala por partes, cache de voz e nada bloqueando o servidor."""
import ast
import asyncio
from pathlib import Path

import pytest

from modules import tts

BACKEND = Path(__file__).resolve().parent.parent


def test_long_first_sentence_is_split_at_comma():
    text = ("Senhor, analisei os dados de clima, agenda e mercado e preparei um resumo completo para hoje. "
            "Segunda frase. Terceira.")
    chunks = tts._split_chunks(text)
    assert len(chunks[0]) <= tts.FIRST_CHUNK_MAX
    assert chunks[0].endswith(",")
    assert " ".join(chunks) == text


def test_short_text_is_unchanged():
    assert tts._split_chunks("Bom dia, senhor. Tudo pronto.") == ["Bom dia, senhor.", "Tudo pronto."]


def test_never_more_than_four_chunks():
    text = " ".join(f"Frase número {i}." for i in range(10))
    assert len(tts._split_chunks(text)) == 4


@pytest.fixture
def tts_sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(tts, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(tts, "_preset_phrases", set())
    monkeypatch.setattr(tts, "_seen_counts", {})
    monkeypatch.setattr(tts, "_memory_cache", {})
    monkeypatch.setattr(tts, "volume_provider", None)
    calls = []

    async def fake_remote(text, path, volume):
        calls.append(text)
        Path(path).write_bytes(b"mp3:" + text.encode())

    monkeypatch.setattr(tts, "_synthesize_remote", fake_remote)
    monkeypatch.setattr(tts, "_play_audio_blocking", lambda path: None)
    monkeypatch.setattr(tts, "PAUSE_BETWEEN_CHUNKS", 0)
    return calls


def test_preset_phrase_is_synthesized_once_and_kept_on_disk(tts_sandbox):
    tts.register_phrases(["Um instante, senhor."])
    asyncio.run(tts.generate_and_play_speech("Um instante, senhor."))
    asyncio.run(tts.generate_and_play_speech("Um instante, senhor."))
    assert tts_sandbox == ["Um instante, senhor."]
    assert len(list(tts.CACHE_DIR.glob("*.mp3"))) == 1


def test_personal_phrase_never_goes_to_disk(tts_sandbox):
    for _ in range(3):
        asyncio.run(tts.generate_and_play_speech("Sua consulta é às 15h."))
    assert tts_sandbox == ["Sua consulta é às 15h."] * 2  # 3ª vez sai do cache em memória
    assert not tts.CACHE_DIR.exists() or not list(tts.CACHE_DIR.glob("*.mp3"))


def test_playback_starts_after_first_chunk(tts_sandbox):
    events = []

    async def on_start():
        events.append(("start", list(tts_sandbox)))

    asyncio.run(tts.generate_and_play_speech("Primeira. Segunda. Terceira.", on_playback_start=on_start))
    assert events and events[0][0] == "start"
    assert events[0][1][0] == "Primeira."


# Funções que fazem rede ou medem a CPU e não podem ser chamadas direto dentro de "async def":
# travariam o servidor inteiro (inclusive o WebSocket) enquanto esperam.
_BLOCKING = {
    ("fan_mode", "fetch_fan_news"), ("system_monitor", "snapshot"), ("tools", "_fetch_weather"),
    ("quotes", "fetch_rates"), ("quotes", "get_rate"), ("news", "fetch_top_news"),
    ("news_radar", "fetch_news"), ("http_client", "get_json"), ("http_client", "get_bytes"),
    ("requests", "get"), ("requests", "post"), ("requests", "request"),
}


def test_no_blocking_network_calls_inside_async_functions():
    offenders = []
    for path in [*BACKEND.glob("core/*.py"), *BACKEND.glob("routes/*.py"), *BACKEND.glob("modules/*.py")]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for fn in ast.walk(tree):
            if not isinstance(fn, ast.AsyncFunctionDef):
                continue
            for node in ast.walk(fn):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                        and isinstance(node.func.value, ast.Name) \
                        and (node.func.value.id, node.func.attr) in _BLOCKING:
                    offenders.append(f"{path.name}:{node.lineno} {node.func.value.id}.{node.func.attr}")
    assert offenders == [], offenders


def test_backend_starts_without_tzdata():
    """No Windows sem o pacote tzdata, ZoneInfo("America/Sao_Paulo") falha: nenhum módulo pode depender dele."""
    offenders = []
    for path in BACKEND.rglob("*.py"):
        if "venv" in path.parts or "tests" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if "import ZoneInfo" in text or "zoneinfo.ZoneInfo" in text:
            offenders.append(path.name)
    assert offenders == [], offenders

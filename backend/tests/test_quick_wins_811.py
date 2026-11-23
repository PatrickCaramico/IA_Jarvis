"""V8.11 (quick wins Q1-Q3): prazo da IA, JSON com cache/gravação atômica e avisos em paralelo."""
import asyncio
import json
import time

import pytest

from core import runtime, safe_io
from services import llm_orchestrator as llm


@pytest.fixture(autouse=True)
def _fresh_cache():
    safe_io.forget_json_cache()
    yield
    safe_io.forget_json_cache()


# ------------------------------------------------------------------ Q1: prazo da IA
def test_turn_budget_frees_the_turn(monkeypatch):
    monkeypatch.setattr(llm.settings, "LLM_TURN_BUDGET_S", 1)
    monkeypatch.setattr(llm, "_call_llm", lambda *a, **k: time.sleep(2) or "tarde demais")

    async def scenario():
        started = time.monotonic()
        with pytest.raises(llm.LLMTimeout):
            await llm.generate_jarvis_response("explique a teoria da relatividade")
        return time.monotonic() - started

    assert asyncio.run(scenario()) < 1.8  # o turno é liberado antes da IA travada terminar


class _FakeModels:
    def __init__(self, exc):
        self.exc, self.calls = exc, []

    def generate_content(self, model, contents, config):
        self.calls.append((model, bool(config.tools)))
        raise self.exc


def _fake_gemini(monkeypatch, exc):
    models = _FakeModels(exc)
    fake = type("C", (), {"models": models})()
    monkeypatch.setattr(llm.settings, "GEMINI_API_KEY", "chave-teste")
    monkeypatch.setattr(llm, "_client", lambda *a, **k: fake)
    return models


def test_gemini_without_tools_does_not_repeat_the_same_call(monkeypatch):
    models = _fake_gemini(monkeypatch, RuntimeError("500 internal"))
    with pytest.raises(RuntimeError):
        llm._call_gemini("oi", None, [], deep=False)
    names = [m for m, _ in models.calls]
    assert len(names) == len(set(names))  # antes: cada modelo 2 vezes (até 6 chamadas)


def test_gemini_timeout_gives_up_at_once(monkeypatch):
    models = _fake_gemini(monkeypatch, TimeoutError("timed out"))
    with pytest.raises(TimeoutError):
        llm._call_gemini("oi", None, [], deep=True)
    assert len(models.calls) == 1  # o modo automático segue para outra IA


def test_gemini_with_search_still_retries_without_tools(monkeypatch):
    models = _fake_gemini(monkeypatch, RuntimeError("tool not supported"))
    with pytest.raises(RuntimeError):
        llm._call_gemini("oi", None, [], deep=True)
    assert models.calls[:2] == [(models.calls[0][0], True), (models.calls[0][0], False)]


def test_timeout_detection():
    assert llm._is_timeout(TimeoutError())
    assert llm._is_timeout(RuntimeError("Request timed out."))
    assert not llm._is_timeout(RuntimeError("429 quota"))


# ------------------------------------------------------------------ Q2: JSON com cache e gravação atômica
def test_read_json_reuses_until_the_file_changes(tmp_path, monkeypatch):
    path = tmp_path / "x.json"
    safe_io.write_json(path, {"a": 1})
    reads = []
    real = type(path).read_text

    def counting(self, *a, **k):
        reads.append(self.name)
        return real(self, *a, **k)

    monkeypatch.setattr(type(path), "read_text", counting)
    first = safe_io.read_json(path)
    first["a"] = 99  # quem chama pode alterar a cópia
    assert safe_io.read_json(path) == {"a": 1}
    assert reads == []  # a gravação já deixou no cache
    path.write_text(json.dumps({"a": 2, "b": 3}), encoding="utf-8")
    assert safe_io.read_json(path) == {"a": 2, "b": 3}
    assert reads == ["x.json"]


def test_corrupt_file_is_kept_and_last_good_version_used(tmp_path):
    path = tmp_path / "jarvis_settings.json"
    safe_io.write_json(path, {"nome": "Patrick"})
    assert safe_io.read_json(path) == {"nome": "Patrick"}
    path.write_text('{"nome": "Pat', encoding="utf-8")  # gravação pela metade
    assert safe_io.read_json(path) == {"nome": "Patrick"}
    assert list(tmp_path.glob("jarvis_settings.corrompido-*.json"))


def test_corrupt_file_without_good_copy_raises_and_is_kept(tmp_path):
    path = tmp_path / "memoria.json"
    path.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError):
        safe_io.read_json(path)
    assert list(tmp_path.glob("memoria.corrompido-*.json"))


def test_prefs_survive_a_corrupt_file(tmp_path, monkeypatch):
    from modules import prefs

    path = tmp_path / "jarvis_settings.json"
    monkeypatch.setattr(prefs, "_SETTINGS_PATH", path)
    data = prefs._load()
    data["fan_team"] = "time-teste"
    prefs._save(data)
    path.write_text("{quebrado", encoding="utf-8")
    assert prefs._load()["fan_team"] == "time-teste"
    assert list(tmp_path.glob("jarvis_settings.corrompido-*.json"))


def test_event_log_still_works(tmp_path, monkeypatch):
    from modules import event_log

    monkeypatch.setattr(event_log, "_PATH", tmp_path / "eventos.json")
    for i in range(3):
        event_log.add("command", f"pedido {i}")
    assert [e["message"] for e in event_log.list_events()] == ["pedido 2", "pedido 1", "pedido 0"]


# ------------------------------------------------------------------ Q3: avisos em paralelo com prazo
class _WS:
    def __init__(self, delay=0.0):
        self.delay, self.got, self.closed = delay, [], False
        self.client = None
        self.headers = {}

    async def send_json(self, event):
        await asyncio.sleep(self.delay)
        self.got.append(event)

    async def close(self, code=1000):
        self.closed = True


def test_slow_device_does_not_hold_the_others(monkeypatch):
    monkeypatch.setattr(runtime, "SEND_TIMEOUT_S", 0.3)

    async def scenario():
        mgr = runtime.ConnectionManager()
        fast, stuck = _WS(), _WS(delay=10)
        mgr.connections |= {fast, stuck}
        started = time.monotonic()
        await mgr.broadcast({"type": "state", "state": "idle"})
        took = time.monotonic() - started
        await asyncio.sleep(0.05)
        return mgr, fast, stuck, took

    mgr, fast, stuck, took = asyncio.run(scenario())
    assert took < 1.0
    assert fast.got == [{"type": "state", "state": "idle"}]
    assert stuck not in mgr.connections and fast in mgr.connections

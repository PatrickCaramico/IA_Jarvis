"""V8.12.3: sempre ligado — atalho da Inicialização sozinho, PC acordado na tomada e guardião religado."""
import asyncio
import os
import time
from pathlib import Path

import pytest

from modules import always_on, autostart, prefs


@pytest.fixture
def windows(monkeypatch, tmp_path):
    appdata = tmp_path / "AppData"
    pyw = tmp_path / "pythonw.exe"
    pyw.write_text("", encoding="utf-8")
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setattr(autostart, "_is_windows", lambda: True)
    monkeypatch.setattr(always_on, "_is_windows", lambda: True)
    monkeypatch.setattr(autostart, "pythonw", lambda: pyw)

    def fake_run(args, env=None, **kw):
        Path(env["JARVIS_LNK"]).write_text("lnk", encoding="utf-8")  # o PowerShell criaria o atalho

    monkeypatch.setattr(autostart.subprocess, "run", fake_run)
    logs = tmp_path / "logs"
    logs.mkdir()
    monkeypatch.setattr(always_on, "BEAT_PATH", logs / "guardiao.beat")
    monkeypatch.setattr(always_on, "STARTING_FLAG", logs / "iniciando.flag")
    started = []
    monkeypatch.setattr(always_on.subprocess, "Popen", lambda args, **kw: started.append(args))
    return started


# ------------------------------------------------------------------ atalho da Inicialização
def test_always_on_is_the_default_and_creates_the_startup_shortcut(windows):
    assert prefs.get_all()["always_on"] is True and prefs.get_all()["keep_awake"] is True
    assert autostart.status()["enabled"] is False
    assert always_on.ensure_autostart()["changed"] is True
    assert autostart.status()["enabled"] is True
    assert always_on.ensure_autostart()["changed"] is False  # já existe: não mexe


def test_turning_off_is_respected_on_the_next_start(windows):
    always_on.ensure_autostart()
    assert always_on.set_autostart(False)["ok"] is True
    assert prefs.get_all()["always_on"] is False
    assert always_on.ensure_autostart()["changed"] is False  # o usuário pediu: não recria
    assert autostart.status()["enabled"] is False
    always_on.set_autostart(True)
    assert prefs.get_all()["always_on"] is True and autostart.status()["enabled"] is True


def test_nothing_happens_outside_windows(monkeypatch):
    monkeypatch.setattr(autostart, "_is_windows", lambda: False)
    monkeypatch.setattr(always_on, "_is_windows", lambda: False)
    assert always_on.ensure_autostart()["changed"] is False
    assert always_on.keep_awake_tick() is False
    assert always_on.ensure_guardian() is False


# ------------------------------------------------------------------ PC acordado na tomada
class _Battery:
    def __init__(self, plugged):
        self.power_plugged = plugged


def test_keep_awake_only_on_ac_power(windows, monkeypatch):
    import psutil

    calls = []

    class _K32:
        def SetThreadExecutionState(self, flags):  # noqa: N802 - nome da API do Windows
            calls.append(flags)
            return 1

    class _Windll:
        kernel32 = _K32()

    import ctypes

    monkeypatch.setattr(ctypes, "windll", _Windll(), raising=False)
    monkeypatch.setattr(psutil, "sensors_battery", lambda: _Battery(True))
    assert always_on.keep_awake_tick() is True
    assert calls == [always_on.ES_SYSTEM_REQUIRED]  # só a suspensão; a tela apaga normalmente
    monkeypatch.setattr(psutil, "sensors_battery", lambda: _Battery(False))
    assert always_on.keep_awake_tick() is False  # na bateria não segura
    monkeypatch.setattr(psutil, "sensors_battery", lambda: None)  # PC de mesa
    assert always_on.keep_awake_tick() is True
    prefs.update(keep_awake=False)
    assert always_on.keep_awake_tick() is False
    prefs.update(keep_awake=True, always_on=False)
    assert always_on.keep_awake_tick() is False
    assert len(calls) == 2


def test_battery_sensor_error_does_not_hold_the_pc(monkeypatch):
    import psutil

    def boom():
        raise RuntimeError("sem sensor")

    monkeypatch.setattr(psutil, "sensors_battery", boom)
    assert always_on.on_ac_power() is False


# ------------------------------------------------------------------ guardião
def test_guardian_is_started_only_when_it_is_really_gone(windows):
    started = windows
    now = time.time()
    always_on.BEAT_PATH.write_text("1", encoding="ascii")
    assert always_on.ensure_guardian(now) is False  # sinal de vida recente
    old = now - 600
    os.utime(always_on.BEAT_PATH, (old, old))
    always_on.STARTING_FLAG.write_text("1", encoding="ascii")
    assert always_on.ensure_guardian(now) is False  # o Iniciar está ligando: ele liga o guardião no fim
    always_on.STARTING_FLAG.unlink()
    assert always_on.ensure_guardian(now) is True
    assert started and started[0][1].endswith("guardiao.py")
    prefs.update(always_on=False)
    assert always_on.ensure_guardian(now) is False


def test_loop_survives_errors(monkeypatch):
    monkeypatch.setattr(always_on, "ensure_autostart", lambda: (_ for _ in ()).throw(RuntimeError("x")))
    ticks = []

    def tick():
        ticks.append(1)
        raise RuntimeError("y")

    monkeypatch.setattr(always_on, "keep_awake_tick", tick)

    async def fast_sleep(_s):
        raise asyncio.CancelledError

    monkeypatch.setattr(always_on.asyncio, "sleep", fast_sleep)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(always_on.always_on_loop())
    assert ticks == [1]


# ------------------------------------------------------------------ rotas e voz
def test_routes(windows, isolated_data):
    from fastapi.testclient import TestClient

    import main
    from modules import access

    access.reset_for_tests(access.UNLOCKED)
    try:
        client = TestClient(main.app)
        assert client.get("/api/health").json()["always_on"] is True
        st = client.get("/api/system/always-on").json()
        assert st["always_on"] is True and st["keep_awake"] is True and "on_ac" in st
        assert client.post("/api/system/always-on", json={"keep_awake": False}).json()["keep_awake"] is False
        assert client.post("/api/system/autostart", json={"enabled": False}).json()["enabled"] is False
        assert client.get("/api/health").json()["always_on"] is False
    finally:
        access.reset_for_tests(access.LOCKED)


def test_voice_skill_turns_always_on_off_and_on(real_skills, windows):
    from core.skills import router

    asyncio.run(router.try_fast_path("não liga mais com o Windows"))
    assert prefs.get_all()["always_on"] is False
    asyncio.run(router.try_fast_path("liga o JARVIS junto com o Windows"))
    assert prefs.get_all()["always_on"] is True and autostart.status()["enabled"] is True

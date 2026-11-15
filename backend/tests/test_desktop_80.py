"""V8.0: JARVIS.exe (ilha no topo) e as rotas de download e da ilha."""
import importlib.util
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from core import runtime
from modules import access

ROOT = Path(__file__).resolve().parents[2]


def _desktop():
    spec = importlib.util.spec_from_file_location("jarvis_desktop", ROOT / "desktop" / "jarvis_desktop.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["jarvis_desktop"] = mod
    spec.loader.exec_module(mod)
    return mod


def _client():
    import main

    access.reset_for_tests(access.UNLOCKED)
    return TestClient(main.app)


def test_island_geometry_and_hotkeys():
    d = _desktop()
    x, y, w, h = d.island_position(1920, "media")
    assert (w, h) == d.ISLAND_SIZES["media"] and x == (1920 - w) // 2 and y < 20
    assert d.island_position(1920, "xyz")[2:] == d.ISLAND_SIZES["media"]
    assert d.hotkey_spec("PageDown") == (d.MOD_NOREPEAT, 0x22)
    assert d.hotkey_spec("Ctrl+Space") == (d.MOD_NOREPEAT | d.MOD_CONTROL, 0x20)
    assert "JarvisDesktop/" in d.USER_AGENT


def test_desktop_client_does_not_silence_pc_ear():
    dev = runtime.describe_device("127.0.0.1", "Mozilla/5.0 Edg/130 JarvisDesktop/8.0.0", True)
    assert dev["kind"] == "desktop"
    assert runtime.describe_device("127.0.0.1", "Mozilla/5.0 Chrome/130", True)["kind"] == "pc"


def test_island_state_and_routes(tmp_path, monkeypatch):
    runtime.note_island({"type": "state", "state": "speaking"})
    runtime.note_island({"type": "response", "text": "  Claro,\n senhor.  "})
    c = _client()
    il = c.get("/api/desk/island").json()
    assert il["estado"] == "speaking" and il["resposta"] == "Claro, senhor." and il["hora"]
    from routes import desktop

    monkeypatch.setattr(desktop, "EXE", tmp_path / "JARVIS.exe")
    info = c.get("/api/desktop/info").json()
    assert info["gerado"] is False and info["local"] is True and "Gerar-App-Windows.bat" in info["como_gerar"]
    assert c.get("/api/desktop/app").status_code == 404
    (tmp_path / "JARVIS.exe").write_bytes(b"MZ" + b"0" * 2048)
    assert c.get("/api/desktop/info").json()["disponivel"] is True
    r = c.get("/api/desktop/app")
    assert r.status_code == 200 and r.content.startswith(b"MZ")

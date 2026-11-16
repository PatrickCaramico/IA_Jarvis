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
    # V8.1.2: ao clicar a ilha vira cartão, continua centralizada e o recorte arredonda os cantos
    cx, _, cw, ch = d.island_position(1920, "media", "cartao")
    assert cw > w and ch >= 200 and cx + cw // 2 in (960, 959)
    assert d.island_radius("mini", h) == h and d.island_radius("cartao", ch) < ch
    d.shape_window(None, 10)  # sem janela (ou fora do Windows) não quebra
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

    monkeypatch.setattr(desktop, "MARK", tmp_path / "app.json")
    monkeypatch.setattr(desktop, "OLD_EXE", tmp_path / "JARVIS.exe")
    info = c.get("/api/desktop/info").json()
    assert info["instalado"] is False and info["local"] is True and "Gerar-App-Windows.bat" in info["como_instalar"]
    assert c.get("/api/desktop/app").status_code == 410  # V8.1.1: sem exe para baixar (antivírus)
    assert c.post("/api/desktop/open").status_code == 404
    (tmp_path / "app.json").write_text('\ufeff{"versao": "8.1.1", "instalado_em": "15/11/2026 20:00", "atalho": ""}', encoding="utf-8")
    info = c.get("/api/desktop/info").json()
    assert info["instalado"] is True and info["versao"] == "8.1.1"


def test_installer_has_no_pyinstaller_exe():
    """V8.1.1: o McAfee acusava o exe "onefile" do PyInstaller; o instalador agora só cria o atalho com o pythonw.exe."""
    ps = (ROOT / "scripts" / "desktop" / "build_exe.ps1").read_text(encoding="utf-8-sig")
    assert "PyInstaller" not in ps.split("\n", 6)[-1].split("$ErrorActionPreference", 1)[-1]
    assert "pythonw.exe" in ps and "CreateShortcut" in ps and "app.json" in ps
    src = (ROOT / "desktop" / "jarvis_desktop.py").read_text(encoding="utf-8")
    assert "CREATE_NO_WINDOW" not in src


def test_island_click_fallback_and_hidden_main():
    """V8.1.3: o toque na ilha é convertido para a página; o X da janela só esconde (a ilha continua)."""
    d = _desktop()
    assert d.island_hit((1000, 20), (770, 6, 1150, 98), 2.0) == (115, 7)
    assert d.island_hit((10, 20), (770, 6, 1150, 98), 2.0) is None

    class W:
        hidden = destroyed = False

        def hide(self):
            self.hidden = True

        def destroy(self):
            self.destroyed = True

    b = d.Bridge()
    b.main, b.island = W(), W()
    assert b.on_main_closing() is False  # cancela o fechamento e esconde
    import time as _t

    _t.sleep(0.05)
    assert b.main.hidden is True
    b.quit()
    assert b.quitting and b.main.destroyed and b.island.destroyed
    assert b.on_main_closing() is True
    src = (ROOT / "desktop" / "jarvis_desktop.py").read_text(encoding="utf-8")
    assert "hidden=island_on" in src and "min_size=(120, 30)" in src

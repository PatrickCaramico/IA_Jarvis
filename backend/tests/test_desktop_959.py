"""V9.5.9: app do Windows (desktop/jarvis_desktop.py).

- a ilha às vezes não aparecia (2 de cada 5 aberturas): island_hwnd() lia window.native.Handle de uma thread de fundo,
  o que obriga o .NET a criar a janela fora da thread da interface e travava o app inteiro. Agora é só Win32;
- o app aparece na barra de tarefas como JARVIS (AppUserModelID próprio e o ícone do JARVIS), não como "Python".
"""
import importlib.util
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _desktop():
    spec = importlib.util.spec_from_file_location("jarvis_desktop", ROOT / "desktop" / "jarvis_desktop.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["jarvis_desktop"] = mod
    spec.loader.exec_module(mod)
    return mod


class _NoTouch:
    """Janela falsa que acusa se alguém ler o .native (era o que travava o app)."""

    @property
    def native(self):
        raise AssertionError("island_hwnd não pode ler window.native (trava o app fora da thread da interface)")


class _FakeUser32:
    def __init__(self, hwnd):
        self.hwnd = hwnd

    def FindWindowW(self, cls, title):  # noqa: N802 - nome da função do Windows
        return self.hwnd


def test_ilha_ainda_nao_criada_devolve_zero_sem_tocar_no_dotnet(monkeypatch):
    d = _desktop()
    monkeypatch.setattr(d, "_user32", lambda: _FakeUser32(0))
    assert d.island_hwnd(_NoTouch()) == 0


def test_ilha_achada_pelo_titulo(monkeypatch):
    d = _desktop()
    monkeypatch.setattr(d, "_user32", lambda: _FakeUser32(4242))
    assert d.island_hwnd(_NoTouch()) == 4242


def test_falha_no_win32_devolve_zero(monkeypatch):
    d = _desktop()

    def boom():
        raise OSError("sem user32")

    monkeypatch.setattr(d, "_user32", boom)
    assert d.island_hwnd(_NoTouch()) == 0
    assert d.island_hwnd(None) == 0


def test_codigo_do_app_nao_le_o_handle_do_dotnet():
    src = (ROOT / "desktop" / "jarvis_desktop.py").read_text(encoding="utf-8")
    assert ".native.Handle" not in src


def test_icone_sem_arquivo_ou_sem_janela_nao_quebra(monkeypatch, tmp_path):
    d = _desktop()
    assert d.set_window_icon("JARVIS", tmp_path / "nao_existe.ico") is False
    ico = tmp_path / "jarvis.ico"
    ico.write_bytes(b"\x00")
    monkeypatch.setattr(d, "own_window", lambda title: 0)
    assert d.set_window_icon("JARVIS", ico) is False


def test_fora_do_windows_nada_acontece(monkeypatch):
    d = _desktop()
    monkeypatch.setattr(d.sys, "platform", "linux")
    assert d.set_app_id() is False
    assert d.own_window("JARVIS") == 0
    assert d.set_window_icon("JARVIS") is False


def test_own_window_so_acha_janela_deste_processo():
    d = _desktop()
    assert d.own_window("titulo que nenhuma janela tem 9f3c2b") == 0


def test_abertura_define_o_id_antes_das_janelas_e_poe_o_icone():
    d = _desktop()
    src = inspect.getsource(d.main)
    assert src.index("set_app_id()") < src.index("import webview")
    assert src.index("set_app_id()") < src.index("create_window(")
    assert 'events.shown += lambda: set_window_icon("JARVIS")' in src
    assert "events.shown += lambda: set_window_icon(ISLAND_TITLE)" in src
    assert d.ICON_PATH.name == "jarvis.ico" and d.ICON_PATH.parent.name == "desktop"

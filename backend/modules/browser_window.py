"""V6.5.8: "abra o YouTube" abre uma JANELA própria do navegador, menor e no canto da tela.

Antes o site entrava como aba nova do navegador (em tela cheia, por cima de tudo). Agora:
  1. abre uma janela nova do navegador padrão (Chrome, Edge ou Firefox);
  2. acha essa janela nova e a deixa em tamanho médio (~60% da tela), no canto inferior direito;
  3. ela é uma janela normal do Windows: dá para arrastar, redimensionar, maximizar.
Preferência "site_window_mode": "compact" (padrão) ou "tab" (o jeito antigo, aba no navegador).
Fora do Windows, ou sem achar o navegador, cai no jeito antigo.
"""
from __future__ import annotations

import logging
import os
import subprocess
import time
import webbrowser

log = logging.getLogger("jarvis.browser_window")

_CANDIDATES = {
    "chrome": [r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
               r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
               r"%LocalAppData%\Google\Chrome\Application\chrome.exe"],
    "edge": [r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
             r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"],
    "firefox": [r"%ProgramFiles%\Mozilla Firefox\firefox.exe",
                r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe"],
    "brave": [r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe",
              r"%LocalAppData%\BraveSoftware\Brave-Browser\Application\brave.exe"],
}
_WINDOW_CLASS = {"chrome": "Chrome_WidgetWin_1", "edge": "Chrome_WidgetWin_1", "brave": "Chrome_WidgetWin_1",
                 "firefox": "MozillaWindowClass"}


def compact_rect(work: tuple[int, int, int, int], scale: float = 0.6, margin: int = 24) -> tuple[int, int, int, int]:
    """(x, y, largura, altura) da janela média no canto inferior direito da área de trabalho."""
    left, top, right, bottom = work
    w = max(640, int((right - left) * scale))
    h = max(420, int((bottom - top) * scale))
    w = min(w, right - left - 2 * margin)
    h = min(h, bottom - top - 2 * margin)
    return right - margin - w, bottom - margin - h, w, h


def _default_browser() -> str:
    try:
        import winreg

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice")
        prog = str(winreg.QueryValueEx(key, "ProgId")[0]).lower()
    except OSError:
        return "edge"
    if "chrome" in prog:
        return "chrome"
    if "firefox" in prog:
        return "firefox"
    if "brave" in prog:
        return "brave"
    return "edge"


def _exe(kind: str) -> str | None:
    for raw in _CANDIDATES.get(kind, []):
        path = os.path.expandvars(raw)
        if os.path.isfile(path):
            return path
    return None


def _windows_of(cls: str) -> set[int]:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    found: set[int] = set()
    buf = ctypes.create_unicode_buffer(256)

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def each(hwnd, _):
        if user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd) > 0:
            user32.GetClassNameW(hwnd, buf, 256)
            if buf.value == cls:
                found.add(int(hwnd))
        return True

    user32.EnumWindows(each, 0)
    return found


def _work_area() -> tuple[int, int, int, int]:
    import ctypes
    from ctypes import wintypes

    rect = wintypes.RECT()
    ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)  # SPI_GETWORKAREA
    return rect.left, rect.top, rect.right, rect.bottom


def _place(hwnd: int) -> None:
    import ctypes

    user32 = ctypes.windll.user32
    x, y, w, h = compact_rect(_work_area())
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE (sai do maximizado)
    user32.SetWindowPos(hwnd, 0, x, y, w, h, 0x0040)  # SWP_SHOWWINDOW
    user32.SetForegroundWindow(hwnd)


def open_url(url: str) -> bool:
    """Abre a URL numa janela média do navegador. True se deu certo do jeito novo."""
    try:
        from modules import prefs

        mode = prefs.get_all().get("site_window_mode") or "compact"
    except Exception:  # noqa: BLE001
        mode = "compact"
    if mode != "compact" or os.name != "nt":
        webbrowser.open(url, new=2, autoraise=True)
        return False
    kind = _default_browser()
    exe = _exe(kind) or _exe("edge")
    if not exe:
        webbrowser.open(url, new=2, autoraise=True)
        return False
    kind = {"chrome.exe": "chrome", "msedge.exe": "edge", "firefox.exe": "firefox",
            "brave.exe": "brave"}.get(os.path.basename(exe).lower(), kind)
    cls = _WINDOW_CLASS.get(kind, "Chrome_WidgetWin_1")
    try:
        before = _windows_of(cls)
        args = [exe, "-new-window", url] if kind == "firefox" else [exe, "--new-window", url]
        subprocess.Popen(args, close_fds=True)  # noqa: S603 - caminho do navegador instalado
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            time.sleep(0.25)
            new = _windows_of(cls) - before
            if new:
                time.sleep(0.35)  # o navegador termina de se posicionar; depois a gente reposiciona
                _place(max(new))
                return True
        log.info("Não achei a janela nova do navegador; ficou do jeito que ele abriu.")
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("Janela média do navegador falhou (%s); abrindo do jeito normal.", exc)
        webbrowser.open(url, new=2, autoraise=True)
        return False

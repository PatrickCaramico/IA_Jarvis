"""Workspace: acesso às janelas e monitores do Windows (ctypes, sem dependência nova).

`get_desktop()` devolve o WindowsDesktop no Windows e None nos outros sistemas. Os testes trocam por um falso.
Todas as funções são bloqueantes: as skills chamam por asyncio.to_thread (função comum = thread automática).
"""
from __future__ import annotations

import logging
import os
import subprocess
import time
from contextlib import contextmanager
from typing import Optional

from skills.workspace.layouts import Monitor, Rect, Window, order_monitors

log = logging.getLogger("jarvis.skills.workspace")

VK = {"ctrl": 0x11, "shift": 0x10, "alt": 0x12, "tab": 0x09, "w": 0x57, "t": 0x54}  # teclas virtuais do Windows
_SKIP_TITLES = {"program manager", "windows input experience", "configurações", "settings"}
_SKIP_CLASSES = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"}


class WindowsDesktop:
    def __init__(self) -> None:
        import ctypes
        from ctypes import wintypes

        self.ct, self.wt = ctypes, wintypes
        self.u = ctypes.windll.user32
        self.dwm = ctypes.windll.dwmapi
        u = self.u
        u.MonitorFromWindow.restype = wintypes.HMONITOR
        u.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
        u.GetWindow.restype = wintypes.HWND
        u.GetForegroundWindow.restype = wintypes.HWND
        try:
            u.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
            u.SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]
            self._dpi_ok = True
        except AttributeError:  # Windows antigo
            self._dpi_ok = False

    @contextmanager
    def _dpi(self):
        """Coordenadas reais em todos os monitores (cada um com sua escala), só nesta thread."""
        prev = None
        if self._dpi_ok:
            prev = self.u.SetThreadDpiAwarenessContext(self.ct.c_void_p(-4))  # PER_MONITOR_AWARE_V2
        try:
            yield
        finally:
            if prev:
                self.u.SetThreadDpiAwarenessContext(self.ct.c_void_p(prev))

    # ------------------------------------------------------------------ leitura
    def _monitor_handles(self) -> list[tuple[int, Monitor]]:
        ct, wt = self.ct, self.wt

        class MONITORINFO(ct.Structure):
            _fields_ = [("cbSize", wt.DWORD), ("rcMonitor", wt.RECT), ("rcWork", wt.RECT), ("dwFlags", wt.DWORD)]

        found: list[tuple[int, Monitor]] = []

        @ct.WINFUNCTYPE(wt.BOOL, wt.HMONITOR, wt.HDC, ct.POINTER(wt.RECT), wt.LPARAM)
        def each(hmon, _hdc, _rect, _lp):
            info = MONITORINFO()
            info.cbSize = ct.sizeof(MONITORINFO)
            if self.u.GetMonitorInfoW(hmon, ct.byref(info)):
                r = info.rcWork
                found.append((int(hmon or 0), Monitor(0, r.left, r.top, r.right, r.bottom, bool(info.dwFlags & 1))))
            return True

        self.u.EnumDisplayMonitors(None, None, each, 0)
        order_monitors([m for _, m in found])
        return found

    def monitors(self) -> list[Monitor]:
        with self._dpi():
            return sorted((m for _, m in self._monitor_handles()), key=lambda m: m.index)

    def _cloaked(self, hwnd) -> bool:
        val = self.ct.c_int(0)
        try:
            self.dwm.DwmGetWindowAttribute(hwnd, 14, self.ct.byref(val), self.ct.sizeof(val))  # DWMWA_CLOAKED
        except OSError:
            return False
        return val.value != 0

    def windows(self) -> list[Window]:
        """Janelas de programas visíveis, na ordem da tela (a de cima primeiro)."""
        import psutil

        ct, wt, u = self.ct, self.wt, self.u
        with self._dpi():
            handles = {h: m.index for h, m in self._monitor_handles()}
            hwnds: list[int] = []

            @ct.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
            def each(hwnd, _lp):
                hwnds.append(hwnd)
                return True

            u.EnumWindows(each, 0)
            title_buf, cls_buf = ct.create_unicode_buffer(512), ct.create_unicode_buffer(256)
            me = os.getpid()
            out: list[Window] = []
            for hwnd in hwnds:
                if not u.IsWindowVisible(hwnd) or u.GetWindowTextLengthW(hwnd) <= 0:
                    continue
                if u.GetWindow(hwnd, 4):  # GW_OWNER: caixas de diálogo de outra janela
                    continue
                if u.GetWindowLongW(hwnd, -20) & 0x80:  # WS_EX_TOOLWINDOW
                    continue
                if self._cloaked(hwnd):  # apps da loja escondidos/suspensos
                    continue
                u.GetClassNameW(hwnd, cls_buf, 256)
                if cls_buf.value in _SKIP_CLASSES:
                    continue
                u.GetWindowTextW(hwnd, title_buf, 512)
                title = title_buf.value.strip()
                if not title or title.lower() in _SKIP_TITLES:
                    continue
                pid = wt.DWORD()
                u.GetWindowThreadProcessId(hwnd, ct.byref(pid))
                if pid.value == me:
                    continue
                try:
                    proc = psutil.Process(pid.value)
                    name = proc.name()
                    try:
                        exe = proc.exe()
                    except (psutil.AccessDenied, OSError):
                        exe = ""
                except (psutil.Error, OSError):
                    continue
                rect = wt.RECT()
                u.GetWindowRect(hwnd, ct.byref(rect))
                hmon = int(u.MonitorFromWindow(hwnd, 2) or 0)  # MONITOR_DEFAULTTONEAREST
                out.append(Window(hwnd=int(hwnd), title=title, process=name, exe=exe, monitor=handles.get(hmon, 1),
                                  rect=(rect.left, rect.top, rect.right, rect.bottom),
                                  maximized=bool(u.IsZoomed(hwnd)), minimized=bool(u.IsIconic(hwnd))))
            return out

    def foreground(self) -> Optional[int]:
        h = self.u.GetForegroundWindow()
        return int(h) if h else None

    # ------------------------------------------------------------------ ações
    def _margins(self, hwnd) -> tuple[int, int, int, int]:
        """Bordas invisíveis do Windows 10/11 (~7 px): sem compensar, sobra um vão entre as janelas."""
        ct, wt = self.ct, self.wt
        outer, frame = wt.RECT(), wt.RECT()
        self.u.GetWindowRect(hwnd, ct.byref(outer))
        try:
            self.dwm.DwmGetWindowAttribute(hwnd, 9, ct.byref(frame), ct.sizeof(frame))  # EXTENDED_FRAME_BOUNDS
        except OSError:
            return 0, 0, 0, 0
        return (frame.left - outer.left, frame.top - outer.top, outer.right - frame.right, outer.bottom - frame.bottom)

    def move(self, hwnd: int, rect: Rect) -> None:
        x, y, w, h = rect
        with self._dpi():
            if self.u.IsZoomed(hwnd) or self.u.IsIconic(hwnd):
                self.u.ShowWindow(hwnd, 9)  # SW_RESTORE
            ml, mt, mr, mb = self._margins(hwnd)
            self.u.SetWindowPos(hwnd, 0, x - ml, y - mt, w + ml + mr, h + mt + mb, 0x0004 | 0x0010 | 0x0040)

    def maximize(self, hwnd: int) -> None:
        self.u.ShowWindow(hwnd, 3)  # SW_MAXIMIZE

    def minimize(self, hwnd: int) -> None:
        self.u.ShowWindow(hwnd, 7)  # SW_SHOWMINNOACTIVE (não rouba o foco)

    def focus(self, hwnd: int) -> None:
        # O Windows só deixa trocar a janela da frente logo depois de uma tecla: um "Alt" solto resolve.
        self.u.keybd_event(0x12, 0, 0, 0)
        self.u.keybd_event(0x12, 0, 2, 0)
        self.u.SetForegroundWindow(hwnd)

    def focus_checked(self, hwnd: int, timeout: float = 0.6) -> bool:
        """V8.11 (Q6): traz a janela para a frente e CONFERE que ela ficou na frente (antes de mandar teclas)."""
        self.focus(hwnd)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.foreground() == hwnd:
                return True
            time.sleep(0.05)
        return self.foreground() == hwnd

    def send_combo(self, *keys: str) -> None:
        """V8.11 (Q6): aperta uma combinação ("ctrl", "shift", "tab") sem PowerShell."""
        codes = [VK[k] for k in keys]
        for code in codes:
            self.u.keybd_event(code, 0, 0, 0)
        for code in reversed(codes):
            self.u.keybd_event(code, 0, 2, 0)  # KEYEVENTF_KEYUP

    def launch(self, exe: str) -> None:
        subprocess.Popen([exe], cwd=os.path.dirname(exe) or None, close_fds=True)  # noqa: S603 - caminho salvo pelo usuário

    def wait_new_window(self, process: str, known: set[int], timeout: float = 8.0) -> Optional[Window]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            time.sleep(0.4)
            for w in self.windows():
                if w.process.lower() == process.lower() and w.hwnd not in known:
                    time.sleep(0.3)  # o programa termina de se posicionar
                    return w
        return None


_desktop: Optional[WindowsDesktop] = None


def get_desktop():
    """O desktop do Windows (ou None fora do Windows / sem ctypes)."""
    global _desktop
    if os.name != "nt":
        return None
    if _desktop is None:
        try:
            _desktop = WindowsDesktop()
        except Exception:  # noqa: BLE001
            log.exception("Não consegui acessar as janelas do Windows")
            return None
    return _desktop

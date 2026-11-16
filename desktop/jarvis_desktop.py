"""V8.0: o app do JARVIS para Windows (ideia 6, Modo Desk).

- Janela própria com o Modo Desk (sem barra do navegador).
- A ILHA: uma barrinha sempre visível no topo da tela (avatar, hora, música e respostas).
  V8.1.3: o app abre SÓ com a ilha; a janela do JARVIS aparece quando você clica na ilha (ABRIR JARVIS ou dois
  cliques) e, ao fechar no X, volta a esconder (a ilha continua). Para sair de vez: ⏻ SAIR na ilha.
- Tecla de atalho para falar com o JARVIS de qualquer lugar (PageDown por padrão; muda em Configurações › Ilha).
- Se o JARVIS não estiver rodando, liga sozinho (Iniciar-JARVIS.bat site, sem abrir o navegador).

O JARVIS de sempre continua por trás (mesmos dados, voz e celular): o app é só a "casa" dele no Windows.
V8.1.1: instalado pelo Gerar-App-Windows.bat como um atalho "JARVIS" que abre este arquivo com o pythonw.exe
oficial (assinado). Antes era um JARVIS.exe do PyInstaller, que o McAfee acusava como vírus (falso positivo).
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

try:  # gerado pelo build (pasta do JARVIS neste PC e versão)
    from _build_info import JARVIS_ROOT, VERSION  # type: ignore
except Exception:  # noqa: BLE001 - rodando direto do código
    JARVIS_ROOT = str(Path(__file__).resolve().parent.parent)
    VERSION = "dev"

LOG_DIR = Path(os.getenv("APPDATA", ".")) / "JARVIS"
log = logging.getLogger("jarvis.app")

API = "http://127.0.0.1:8000"
FRONT = "http://127.0.0.1:5173"
ISLAND_SIZES = {"pequena": (300, 38), "media": (380, 46), "grande": (460, 56)}
ISLAND_OPEN_H = 120  # altura quando mostra uma resposta
# V8.1.2: modos da ilha (como a "ilha dinâmica"): mini (pílula), resposta (cresce com o texto) e cartão (ao clicar)
ISLAND_MODES = {"mini": (0, 0), "resposta": (80, ISLAND_OPEN_H), "cartao": (180, 210)}
# teclas para o RegisterHotKey (códigos virtuais do Windows)
VK = {"PageDown": 0x22, "F9": 0x78, "Ctrl+Space": 0x20}
MOD_CONTROL, MOD_NOREPEAT = 0x0002, 0x4000
# o backend reconhece o app pelo "JarvisDesktop/" (a janela não ouve pelo navegador: o ouvido do PC atende)
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 "
              "Safari/537.36 Edg/130.0.0.0 JarvisDesktop/" + str(VERSION))


def get_json(url: str, timeout: float = 2.5) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310 - só 127.0.0.1
            return json.loads(r.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None


def jarvis_up() -> bool:
    return bool(get_json(f"{API}/api/health")) and bool(_front_up())


def _front_up() -> bool:
    try:
        with urllib.request.urlopen(FRONT + "/", timeout=2.5) as r:  # noqa: S310
            return r.status < 500
    except Exception:  # noqa: BLE001
        return False


def start_jarvis(root: str = JARVIS_ROOT) -> bool:
    """Liga o JARVIS (sem abrir o navegador) e espera até 60 s."""
    bat = Path(root) / "Iniciar-JARVIS.bat"
    if not bat.exists():
        return False
    # V8.1.1: janela visível (minimizada), nada escondido: processo oculto é o que antivírus vigiam
    info = None
    if hasattr(subprocess, "STARTUPINFO"):
        info = subprocess.STARTUPINFO()
        info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        info.wShowWindow = 7  # SW_SHOWMINNOACTIVE
    flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    subprocess.Popen(["cmd.exe", "/c", str(bat), "site"], cwd=str(bat.parent), creationflags=flags, startupinfo=info)  # noqa: S603,S607
    for _ in range(60):
        if jarvis_up():
            return True
        time.sleep(1)
    return False


def island_position(screen_w: int, size: str, mode: str = "mini") -> tuple[int, int, int, int]:
    """(x, y, largura, altura) da ilha: sempre centralizada no topo da tela (cresce para os dois lados)."""
    w, h = ISLAND_SIZES.get(size, ISLAND_SIZES["media"])
    extra_w, open_h = ISLAND_MODES.get(mode, ISLAND_MODES["mini"])
    w, h = w + extra_w, max(h, open_h)
    return (max(0, (screen_w - w) // 2), 6, w, h)


def island_radius(mode: str, height: int) -> int:
    """Raio do recorte: pílula inteira no modo mini; cantos arredondados quando abre."""
    return height if mode == "mini" else 44


ISLAND_TITLE = "Ilha do JARVIS"


def _user32():
    """user32 com os tipos certos (HWND de 64 bits não pode virar int de 32)."""
    import ctypes
    from ctypes import wintypes

    u = ctypes.WinDLL("user32", use_last_error=True)
    u.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
    u.FindWindowW.restype = wintypes.HWND
    u.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    u.WindowFromPoint.argtypes = [wintypes.POINT]
    u.WindowFromPoint.restype = wintypes.HWND
    u.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    u.GetAncestor.restype = wintypes.HWND
    u.SetWindowRgn.argtypes = [wintypes.HWND, wintypes.HANDLE, wintypes.BOOL]
    u.GetDpiForWindow.argtypes = [wintypes.HWND]
    u.GetDpiForWindow.restype = wintypes.UINT
    return u


def island_hwnd(window=None) -> int:
    """V8.1.4: acha a janela da ilha pelo título (Win32 puro, funciona de qualquer thread)."""
    try:
        h = _user32().FindWindowW(None, ISLAND_TITLE)
        if h:
            return int(h)
    except Exception as exc:  # noqa: BLE001
        log.info("FindWindow falhou: %s", exc)
    try:
        return int(window.native.Handle.ToInt64()) if window is not None else 0
    except Exception as exc:  # noqa: BLE001
        log.info("Handle da ilha indisponível: %s", exc)
        return 0


def shape_window(window, radius: int) -> bool:
    """Recorta a janela da ilha em formato de pílula (SetWindowRgn). Devolve se conseguiu."""
    if sys.platform != "win32" or window is None:
        return False
    try:
        import ctypes
        from ctypes import wintypes

        hwnd = island_hwnd(window)
        if not hwnd:
            log.info("recorte da ilha: janela não encontrada")
            return False
        user32 = _user32()
        gdi32 = ctypes.WinDLL("gdi32")
        gdi32.CreateRoundRectRgn.restype = wintypes.HANDLE
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        w, h = rect.right - rect.left, rect.bottom - rect.top
        try:
            scale = (user32.GetDpiForWindow(hwnd) or 96) / 96
        except Exception:  # noqa: BLE001 - Windows antigo
            scale = 1
        r = min(int(radius * scale), h)
        rgn = gdi32.CreateRoundRectRgn(0, 0, w + 1, h + 1, r, r)
        ok = bool(user32.SetWindowRgn(hwnd, rgn, True))
        log.info("recorte da ilha %sx%s raio %s: %s", w, h, r, "ok" if ok else "falhou")
        return ok
    except Exception as exc:  # noqa: BLE001 - sem recorte a ilha continua funcionando (só fica retangular)
        log.info("recorte da ilha falhou: %s", exc)
        return False


def hotkey_spec(name: str) -> tuple[int, int]:
    """(modificadores, tecla) para o RegisterHotKey."""
    vk = VK.get(name, VK["PageDown"])
    mods = MOD_NOREPEAT | (MOD_CONTROL if name.startswith("Ctrl+") else 0)
    return mods, vk


class Bridge:
    """Funções que as páginas chamam pelo window.pywebview.api."""

    def __init__(self) -> None:
        self.main = None
        self.island = None
        self.size = "media"
        self.mode = "mini"
        self.screen_w = 1920
        self.quitting = False

    def show_main(self) -> None:
        log.info("mostrando a janela do JARVIS")
        if self.main:
            self.main.show()
            self.main.restore()

    def hide_main(self) -> None:
        if self.main:
            self.main.hide()

    def on_main_closing(self):
        """X da janela: com a ilha ligada, só esconde (a ilha continua no topo). Devolver False cancela o fechamento."""
        if self.quitting or not self.island:
            return True
        threading.Thread(target=self.hide_main, daemon=True).start()
        return False

    def quit(self) -> None:
        """⏻ SAIR na ilha: fecha o app de vez (o JARVIS continua rodando no PC)."""
        self.quitting = True
        for w in (self.island, self.main):
            try:
                if w:
                    w.destroy()
            except Exception:  # noqa: BLE001
                pass

    def log(self, msg: str) -> None:
        """A página da ilha registra problemas aqui (%APPDATA%\\JARVIS\\app.log)."""
        log.info("ilha: %s", str(msg)[:300])

    def island_expand(self, open_: bool) -> None:  # 8.0 (ainda usado por versões antigas da página)
        self.island_mode("resposta" if open_ else "mini")

    def island_mode(self, mode: str) -> None:
        """mini | resposta | cartao: muda o tamanho mantendo a ilha centralizada e recorta o formato."""
        if not self.island or mode not in ISLAND_MODES:
            return
        self.mode = mode
        log.info("ilha: modo %s", mode)
        x, y, w, h = island_position(self.screen_w, self.size, mode)
        self.island.resize(w, h)
        self.island.move(x, y)
        shape_window(self.island, island_radius(mode, h))

    def talk(self) -> None:
        """Botão 🎙 da ilha: abre a janela do JARVIS já ouvindo."""
        self.show_main()
        if self.main:
            self.main.evaluate_js("window.dispatchEvent(new CustomEvent('jarvis-desktop-talk'))")

    def version(self) -> str:
        return VERSION


def island_hit(pt: tuple[int, int], rect: tuple[int, int, int, int], scale: float) -> tuple[int, int] | None:
    """Clique da tela (pixels reais) -> ponto dentro da página da ilha (pixels CSS), ou None se for fora."""
    x, y = pt
    left, top, right, bottom = rect
    if not (left <= x < right and top <= y < bottom):
        return None
    scale = scale or 1
    return int((x - left) / scale), int((y - top) / scale)


def watch_island_clicks(bridge: Bridge) -> None:
    """V8.1.3/8.1.4: garante o clique na ilha, sem depender do WebView2 receber o mouse.

    - 1 clique em cima da ilha: a página recebe o toque (abre/fecha o cartão; ela ignora o clique repetido).
    - 2 cliques rápidos: o próprio app mostra a janela do JARVIS (funciona mesmo se a página não responder).
    O ponto é testado contra a janela da ilha achada pelo título (Win32), não pelo .NET.
    """
    if sys.platform != "win32":
        return
    import ctypes
    from ctypes import wintypes

    user32 = _user32()
    user32.GetAsyncKeyState.restype = ctypes.c_short
    was_down, last_click, shaped = False, 0.0, False
    started = time.time()
    while not bridge.quitting:
        time.sleep(0.03)
        if not shaped and time.time() - started > 1.5:  # o recorte de novo, depois que a janela existe de verdade
            shaped = shape_window(bridge.island, 9999 if bridge.mode == "mini" else 44) or time.time() - started > 20
        down = bool(user32.GetAsyncKeyState(0x01) & 0x8000)  # VK_LBUTTON
        if down and not was_down and bridge.island:
            try:
                hwnd = island_hwnd(bridge.island)
                pt = wintypes.POINT()
                user32.GetCursorPos(ctypes.byref(pt))
                under = user32.GetAncestor(user32.WindowFromPoint(pt), 2) or 0  # GA_ROOT
                r = wintypes.RECT()
                if hwnd:
                    user32.GetWindowRect(hwnd, ctypes.byref(r))
                    try:
                        scale = (user32.GetDpiForWindow(hwnd) or 96) / 96
                    except Exception:  # noqa: BLE001
                        scale = 1
                    hit = island_hit((pt.x, pt.y), (r.left, r.top, r.right, r.bottom), scale)
                else:
                    hit = None
                if hit and (int(under) == hwnd or not under):
                    now = time.time()
                    if now - last_click < 0.45:
                        log.info("dois cliques na ilha: abrindo o JARVIS")
                        bridge.show_main()
                        last_click = 0.0
                    else:
                        last_click = now
                        log.info("clique na ilha em %s", hit)
                        bridge.island.evaluate_js(f"window.__jarvisIslandPress && window.__jarvisIslandPress({hit[0]}, {hit[1]})")
                elif hit:
                    log.info("clique sobre a ilha, mas outra janela está por cima (%s)", under)
            except Exception as exc:  # noqa: BLE001
                log.info("clique na ilha falhou: %s", exc)
        was_down = down


def listen_hotkey(bridge: Bridge, name: str) -> None:
    """Tecla de atalho global (Windows): manda a janela do JARVIS começar a ouvir."""
    if sys.platform != "win32":
        return
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    mods, vk = hotkey_spec(name)
    if not user32.RegisterHotKey(None, 1, mods, vk):
        return
    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
        if msg.message == 0x0312 and bridge.main:  # WM_HOTKEY
            bridge.talk()


def main() -> None:
    import webview  # pywebview

    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(filename=str(LOG_DIR / "app.log"), level=logging.INFO, format="%(asctime)s %(message)s", encoding="utf-8")
        log.info("app %s abrindo (pywebview %s)", VERSION, getattr(webview, "__version__", "?"))
    except Exception:  # noqa: BLE001
        pass

    if not jarvis_up() and not start_jarvis():
        webview.create_window("JARVIS", html=(
            "<body style='background:#0b0d12;color:#eef2f7;font-family:sans-serif;display:grid;place-items:center;height:100vh;margin:0'>"
            "<div style='text-align:center'><h2>O JARVIS não está rodando</h2>"
            f"<p>Abra a pasta do JARVIS ({JARVIS_ROOT}) e rode o Iniciar-JARVIS.bat. Depois abra o atalho JARVIS de novo.</p></div></body>"))
        webview.start()
        return
    cfg = (get_json(f"{API}/api/desk") or {}).get("ilha") or {}
    bridge = Bridge()
    bridge.size = cfg.get("tamanho", "media")
    island_on = cfg.get("ligada", True)
    # V8.1.3: com a ilha ligada, a janela do JARVIS começa escondida e só aparece quando você clica na ilha
    bridge.main = webview.create_window("JARVIS", f"{FRONT}/?desk=1&app=windows", width=1280, height=820, min_size=(900, 600),
                                        background_color="#0b0d12", js_api=bridge, text_select=True, hidden=island_on)
    bridge.main.events.closing += bridge.on_main_closing
    if island_on:
        screens = webview.screens
        bridge.screen_w = screens[0].width if screens else 1920
        x, y, w, h = island_position(bridge.screen_w, bridge.size)
        # V8.1.2: sem transparent (o clique atravessava); a pílula é recortada no shown (SetWindowRgn)
        bridge.island = webview.create_window(ISLAND_TITLE, f"{FRONT}/?ilha=1", x=x, y=y, width=w, height=h, frameless=True,
                                              on_top=True, resizable=False, easy_drag=False, background_color="#000000",
                                              js_api=bridge, focus=True, min_size=(120, 30))  # o padrão (200x100) esticava a ilha
        bridge.island.events.shown += lambda: shape_window(bridge.island, island_radius("mini", 9999))
        threading.Thread(target=watch_island_clicks, args=(bridge,), daemon=True).start()
    threading.Thread(target=listen_hotkey, args=(bridge, cfg.get("atalho", "PageDown")), daemon=True).start()
    os.environ.setdefault("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "--autoplay-policy=no-user-gesture-required")
    webview.start(private_mode=False, user_agent=USER_AGENT, storage_path=str(Path(os.getenv("APPDATA", ".")) / "JARVIS" / "webview"))


if __name__ == "__main__":
    main()

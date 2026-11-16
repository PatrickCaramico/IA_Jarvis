"""V8.0: o app do JARVIS para Windows (ideia 6, Modo Desk).

- Janela própria com o Modo Desk (sem barra do navegador).
- A ILHA: uma barrinha sempre visível no topo da tela (avatar, hora, música e respostas). Tocar nela mostra a janela.
- Tecla de atalho para falar com o JARVIS de qualquer lugar (PageDown por padrão; muda em Configurações › Ilha).
- Se o JARVIS não estiver rodando, liga sozinho (Iniciar-JARVIS.bat site, sem abrir o navegador).

O JARVIS de sempre continua por trás (mesmos dados, voz e celular): o app é só a "casa" dele no Windows.
V8.1.1: instalado pelo Gerar-App-Windows.bat como um atalho "JARVIS" que abre este arquivo com o pythonw.exe
oficial (assinado). Antes era um JARVIS.exe do PyInstaller, que o McAfee acusava como vírus (falso positivo).
"""
from __future__ import annotations

import json
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


def shape_window(window, radius: int) -> None:
    """V8.1.2: recorta a janela da ilha em formato de pílula (SetWindowRgn).

    Antes a ilha usava janela "transparente" (cor-chave do Windows): com o WebView2, o clique atravessava a ilha
    e ia para o que estava atrás. Agora a janela é normal (100% clicável) e só o formato é recortado.
    """
    if sys.platform != "win32" or window is None:
        return
    try:
        import ctypes
        from ctypes import wintypes

        hwnd = int(window.native.Handle.ToInt32())
        user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        w, h = rect.right - rect.left, rect.bottom - rect.top
        try:
            scale = user32.GetDpiForWindow(hwnd) / 96
        except Exception:  # noqa: BLE001 - Windows antigo
            scale = 1
        r = min(int(radius * scale), h) if radius < 999 else h
        rgn = gdi32.CreateRoundRectRgn(0, 0, w + 1, h + 1, r, r)
        user32.SetWindowRgn(hwnd, rgn, True)
    except Exception:  # noqa: BLE001 - sem recorte a ilha continua funcionando (só fica retangular)
        pass


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

    def show_main(self) -> None:
        if self.main:
            self.main.show()
            self.main.restore()

    def island_expand(self, open_: bool) -> None:  # 8.0 (ainda usado por versões antigas da página)
        self.island_mode("resposta" if open_ else "mini")

    def island_mode(self, mode: str) -> None:
        """mini | resposta | cartao: muda o tamanho mantendo a ilha centralizada e recorta o formato."""
        if not self.island or mode not in ISLAND_MODES:
            return
        self.mode = mode
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
    bridge.main = webview.create_window("JARVIS", f"{FRONT}/?desk=1&app=windows", width=1280, height=820, min_size=(900, 600),
                                        background_color="#0b0d12", js_api=bridge, text_select=True)
    if cfg.get("ligada", True):
        screens = webview.screens
        bridge.screen_w = screens[0].width if screens else 1920
        x, y, w, h = island_position(bridge.screen_w, bridge.size)
        # V8.1.2: sem transparent (o clique atravessava); a pílula é recortada no shown (SetWindowRgn)
        bridge.island = webview.create_window("Ilha do JARVIS", f"{FRONT}/?ilha=1", x=x, y=y, width=w, height=h, frameless=True,
                                              on_top=True, resizable=False, easy_drag=False, background_color="#000000",
                                              js_api=bridge, focus=True)
        bridge.island.events.shown += lambda: shape_window(bridge.island, island_radius("mini", h))
    threading.Thread(target=listen_hotkey, args=(bridge, cfg.get("atalho", "PageDown")), daemon=True).start()
    os.environ.setdefault("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "--autoplay-policy=no-user-gesture-required")
    webview.start(private_mode=False, user_agent=USER_AGENT, storage_path=str(Path(os.getenv("APPDATA", ".")) / "JARVIS" / "webview"))


if __name__ == "__main__":
    main()

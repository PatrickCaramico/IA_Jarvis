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
ISLAND_SIZES = {"pequena": (340, 52), "media": (420, 60), "grande": (500, 70)}  # V8.6.2: maior (avatar bem visível)
POKE_ZONE_PX = 64  # V8.6.2: o avatar na ponta esquerda da pílula: cliques ali são cutucadas (não abrem a janela grande)
ISLAND_OPEN_H = 120  # altura quando mostra uma resposta
# V8.1.2: modos da ilha (como a "ilha dinâmica"): mini (pílula), resposta (cresce com o texto) e cartão (ao clicar)
ISLAND_MODES = {"mini": (0, 0), "resposta": (80, ISLAND_OPEN_H), "cartao": (180, 210), "painel": (0, 0)}
# V8.3.0 (ideia 9): "painel" = os menus abertos na própria ilha (tamanho fixo, cresce para baixo)
ISLAND_PANEL = (980, 600)  # V8.4.1: o app inteiro (Modo Desk) dentro da ilha, como no vídeo
# V8.5.0: tamanhos do painel aberto (Configurações › Ilha)
PANEL_SIZES = {"compacto": (860, 540), "medio": ISLAND_PANEL, "grande": (1200, 740)}
DRAG_PX = 6  # arrastar: depois de mover o mouse isso com o botão apertado (senão é um clique)
BAR_H = 40  # altura (px da página) da barra de cima do painel aberto, por onde se arrasta
# teclas para o RegisterHotKey (códigos virtuais do Windows)
VK = {"PageDown": 0x22, "F9": 0x78, "Ctrl+Space": 0x20}
MOD_CONTROL, MOD_NOREPEAT = 0x0002, 0x4000
# o backend reconhece o app pelo "JarvisDesktop/" (a janela não ouve pelo navegador: o ouvido do PC atende)
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 "
              "Safari/537.36 Edg/130.0.0.0 JarvisDesktop/" + str(VERSION))


def patch_json(url: str, body: dict, timeout: float = 4) -> bool:
    """PATCH no JARVIS deste PC (só 127.0.0.1)."""
    try:
        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="PATCH",
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 - só 127.0.0.1
            return 200 <= r.status < 300
    except Exception as exc:  # noqa: BLE001
        log.info("não consegui salvar a posição da ilha: %s", exc)
        return False


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


def island_position(screen_w: int, size: str, mode: str = "mini", pos: float = 0.5,
                    panel: str = "medio") -> tuple[int, int, int, int]:
    """(x, y, largura, altura) da ilha no topo da tela. `pos` (0..1): onde fica o MEIO da ilha na largura da tela
    (0,5 = centro; V8.4.1: você arrasta para os lados e ela lembra). Nunca sai da tela."""
    w, h = ISLAND_SIZES.get(size, ISLAND_SIZES["media"])
    if mode == "painel":
        pw, ph = PANEL_SIZES.get(panel, ISLAND_PANEL)
        w, h = min(max(w, pw), max(screen_w - 12, 300)), ph
    else:
        extra_w, open_h = ISLAND_MODES.get(mode, ISLAND_MODES["mini"])
        w, h = w + extra_w, max(h, open_h)
    pos = min(1.0, max(0.0, float(pos if pos is not None else 0.5)))
    x = round(pos * screen_w - w / 2)
    return (max(0, min(x, screen_w - w)), 6, w, h)


def drag_x(start_win_x: int, start_cursor_x: int, cursor_x: int, win_w: int, screen_w: int) -> int:
    """Nova posição (x) da janela enquanto arrasta, sem sair da tela."""
    return max(0, min(start_win_x + (cursor_x - start_cursor_x), screen_w - win_w))


def center_fraction(win_x: int, win_w: int, screen_w: int) -> float:
    """Onde está o meio da ilha (0..1) na largura da tela."""
    if screen_w <= 0:
        return 0.5
    return round(min(1.0, max(0.0, (win_x + win_w / 2) / screen_w)), 4)


def island_radius(mode: str, height: int) -> int:
    """Raio do recorte: pílula inteira no modo mini; cantos arredondados quando abre."""
    if mode == "mini":
        return height
    return 28 if mode == "painel" else 44


ISLAND_TITLE = "Ilha do JARVIS"
PACMAN_TITLE = "Pac-Man do JARVIS"  # V8.6.0: a janelinha do avatar que corre atrás do mouse
PACMAN_SIZE = 120
PACMAN_MAX_CHASE_S = 12  # corre no máximo isso (depois "alcança" de qualquer jeito)
PACMAN_CHEW_S = 2.6  # mastigando o mouse
PACMAN_FRAME_S = 0.015


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
    u.SetForegroundWindow.argtypes = [wintypes.HWND]
    u.GetForegroundWindow.restype = wintypes.HWND
    return u


def focus_window(hwnd: int) -> bool:
    """V8.3.0: traz a ilha para a frente com o foco do teclado (para digitar nos menus).

    V8.3.2: o Windows só deixa pegar o foco quem está "ligado" à janela da frente; aqui a ilha se liga
    por um instante à fila de entrada dela (AttachThreadInput), pega o foco e se solta. Antes apertava o Alt
    de mentira, o que podia abrir o menu do programa que estava na frente."""
    if sys.platform != "win32" or not hwnd:
        return False
    try:
        import ctypes
        from ctypes import wintypes

        u = _user32()
        k32 = ctypes.WinDLL("kernel32")
        fg = u.GetForegroundWindow()
        if int(fg or 0) == hwnd:
            return True
        u.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        u.GetWindowThreadProcessId.restype = wintypes.DWORD
        u.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
        u.BringWindowToTop.argtypes = [wintypes.HWND]
        u.SetFocus.argtypes = [wintypes.HWND]
        mine = k32.GetCurrentThreadId()
        other = u.GetWindowThreadProcessId(fg, None) if fg else 0
        attached = bool(other and other != mine and u.AttachThreadInput(mine, other, True))
        try:
            u.BringWindowToTop(hwnd)
            ok = bool(u.SetForegroundWindow(hwnd))
        finally:
            if attached:
                u.AttachThreadInput(mine, other, False)
        return ok
    except Exception as exc:  # noqa: BLE001
        log.info("foco na ilha falhou: %s", exc)
        return False


def copy_to_clipboard(text: str) -> bool:
    """V8.3.0: copia um texto pela área de transferência do Windows (a ilha sem foco não consegue pelo navegador)."""
    if sys.platform != "win32":
        return False
    import ctypes
    from ctypes import wintypes

    data = (str(text) + "\0").encode("utf-16-le")
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    u = ctypes.WinDLL("user32", use_last_error=True)
    k32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    k32.GlobalAlloc.restype = wintypes.HGLOBAL
    k32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    k32.GlobalLock.restype = ctypes.c_void_p
    k32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    u.OpenClipboard.argtypes = [wintypes.HWND]
    u.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    u.SetClipboardData.restype = wintypes.HANDLE
    if not u.OpenClipboard(None):
        return False
    try:
        u.EmptyClipboard()
        h = k32.GlobalAlloc(0x0002, len(data))  # GMEM_MOVEABLE
        if not h:
            return False
        ptr = k32.GlobalLock(h)
        if not ptr:
            return False
        ctypes.memmove(ptr, data, len(data))
        k32.GlobalUnlock(h)
        return bool(u.SetClipboardData(13, h))  # CF_UNICODETEXT
    finally:
        u.CloseClipboard()


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
        # V8.6.2: o recorte fica 1 px para dentro: some o filete claro que aparecia na borda da pílula
        rgn = gdi32.CreateRoundRectRgn(1, 1, w, h, max(2, r - 2), max(2, r - 2))
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
    """Funções que as páginas chamam pelo window.pywebview.api.

    V8.1.6: TODO o estado fica em atributos com "_" na frente. O pywebview publica para a página tudo o que é
    público aqui, entrando nos objetos (de forma recursiva): com as janelas guardadas em "main"/"island" ele
    varria os objetos .NET das janelas, travava ("Python não está respondendo") e a página ficava sem as funções
    (por isso a ilha não respondia ao clique). Só os métodos abaixo podem ser públicos.
    """

    def __init__(self) -> None:
        self._main = None
        self._island = None
        self._size = "media"
        self._mode = "mini"
        self._screen_w = 1920
        self._pos = 0.5  # V8.4.1: onde fica a ilha (0..1 na largura da tela)
        self._panel = "medio"  # V8.5.0: tamanho do painel aberto
        self._chaser = None  # V8.6.0: janela do modo Pac-Man
        self._pac_running = False
        self._quitting = False

    def show_main(self) -> None:
        log.info("mostrando a janela do JARVIS")
        if self._main:
            self._main.show()
            self._main.restore()

    def hide_main(self) -> None:
        if self._main:
            self._main.hide()

    def on_main_closing(self):
        """X da janela: com a ilha ligada, só esconde (a ilha continua no topo). Devolver False cancela o fechamento."""
        if self._quitting or not self._island:
            return True
        threading.Thread(target=self.hide_main, daemon=True).start()
        return False

    def quit(self) -> None:
        """⏻ SAIR na ilha: fecha o app de vez (o JARVIS continua rodando no PC)."""
        self._quitting = True
        for w in (self._island, self._main):
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
        if not self._island or mode not in ISLAND_MODES:
            return
        self._mode = mode
        log.info("ilha: modo %s", mode)
        x, y, w, h = island_position(self._screen_w, self._size, mode, self._pos, self._panel)
        self._island.resize(w, h)
        self._island.move(x, y)
        shape_window(self._island, island_radius(mode, h))
        # V8.5.0: o Windows muda o tamanho um instante DEPOIS; o recorte feito antes ficava com o tamanho antigo
        # (a pílula voltava com cantos "quadrados"). Refaz o recorte quando o tamanho novo já valeu.
        threading.Thread(target=self._reshape_later, args=(mode, h), daemon=True).start()
        if mode == "painel":  # os menus abertos: a ilha pega o foco do teclado (para digitar)
            focus_window(island_hwnd(self._island))

    def _reshape_later(self, mode: str, h: int) -> None:
        for wait in (0.15, 0.5, 1.2):
            time.sleep(wait)
            if self._mode != mode:
                return
            shape_window(self._island, island_radius(mode, h))

    def island_layout(self, panel: str) -> None:
        """V8.5.0: tamanho do painel aberto (compacto | medio | grande), escolhido em Configurações › Ilha."""
        if panel not in PANEL_SIZES or panel == self._panel:
            return
        self._panel = panel
        if self._mode == "painel":
            self.island_mode("painel")

    def idle_seconds(self) -> float:
        """V8.6.0: há quanto tempo ninguém mexe no PC (mouse/teclado), para as brincadeiras do avatar. -1 se não sabe."""
        return system_idle_seconds()

    def pacman_start(self) -> bool:
        """V8.6.0: cutucaram demais o avatar: ele sai da ilha e corre atrás do mouse (Pac-Man)."""
        if self._pac_running or sys.platform != "win32":
            return False
        if not self._chaser:  # V8.6.2: a janelinha não foi criada na abertura: cria agora
            self._chaser = create_chaser_window()
            if not self._chaser:
                log.info("pac-man: sem a janelinha, não dá")
                return False
            time.sleep(1.0)
        self._pac_running = True
        threading.Thread(target=run_pacman, args=(self,), daemon=True).start()
        return True

    def island_set_pos(self, pos: float) -> None:
        """A posição mudou em Configurações › Ilha (ex.: "Centralizar"): move a ilha (sem salvar de novo)."""
        try:
            p = min(1.0, max(0.0, float(pos)))
        except (TypeError, ValueError):
            return
        if abs(p - self._pos) < 0.001:
            return
        self._pos = p
        self.island_mode(self._mode)

    def island_center(self) -> None:
        """Dois cliques no espaço vazio da barra: a ilha volta para o meio da tela."""
        self._set_pos(0.5)
        self.island_mode(self._mode)

    def _set_pos(self, pos: float) -> None:
        """Guarda a posição (aqui e no JARVIS, para lembrar na próxima vez)."""
        self._pos = min(1.0, max(0.0, float(pos)))
        threading.Thread(target=patch_json, args=(f"{API}/api/desk", {"ilha": {"posicao": self._pos}}), daemon=True).start()

    def copy_text(self, text: str) -> bool:
        """⧉ Copiados na ilha: copia de novo pelo Windows."""
        try:
            return copy_to_clipboard(str(text)[:100000])
        except Exception as exc:  # noqa: BLE001
            log.info("copiar pela ilha falhou: %s", exc)
            return False

    def talk(self) -> None:
        """Botão 🎙 da ilha: abre a janela do JARVIS já ouvindo."""
        self.show_main()
        if self._main:
            self._main.evaluate_js("window.dispatchEvent(new CustomEvent('jarvis-desktop-talk'))")

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

    V8.4.1: e ARRASTA a ilha para os lados (como no vídeo):
    - botão desce em cima da pílula (ou da barra de cima do painel aberto): começa a acompanhar;
    - mexeu mais que DRAG_PX com o botão apertado: é arraste (a ilha anda junto e, ao soltar, lembra o lugar);
    - soltou sem arrastar: na pílula é um clique (a página recebe o toque); dois cliques rápidos abrem a janela
      grande do JARVIS. Com o painel aberto, o resto do painel recebe o mouse normalmente (não é repassado);
    - clicou fora com o painel aberto: fecha o painel.
    O ponto é testado contra a janela da ilha achada pelo título (Win32), não pelo .NET.
    """
    if sys.platform != "win32":
        return
    import ctypes
    from ctypes import wintypes

    user32 = _user32()
    user32.GetAsyncKeyState.restype = ctypes.c_short
    user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
    swp = 0x0001 | 0x0004 | 0x0010  # SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE
    was_down, last_click, shaped = False, 0.0, False
    last_mode = "mini"  # V8.3.2: o modo da ilha no PRIMEIRO clique (o 1º clique já abre o painel)
    press = None  # {"hit", "cursor_x", "win_x", "win_w", "y", "dragging", "mode"} enquanto o botão está apertado
    started = time.time()

    def js(code: str) -> None:
        try:
            bridge._island.evaluate_js(code)
        except Exception as exc:  # noqa: BLE001
            log.info("ilha: js falhou: %s", exc)

    while not bridge._quitting:
        time.sleep(0.02 if press else 0.03)
        if not shaped and time.time() - started > 1.5:  # o recorte de novo, depois que a janela existe de verdade
            shaped = shape_window(bridge._island, 9999 if bridge._mode == "mini" else 44) or time.time() - started > 20
        down = bool(user32.GetAsyncKeyState(0x01) & 0x8000)  # VK_LBUTTON
        try:
            if down and not was_down and bridge._island:  # o botão DESCEU
                hwnd = island_hwnd(bridge._island)
                pt = wintypes.POINT()
                user32.GetCursorPos(ctypes.byref(pt))
                under = user32.GetAncestor(user32.WindowFromPoint(pt), 2) or 0  # GA_ROOT
                r = wintypes.RECT()
                hit = None
                if hwnd:
                    user32.GetWindowRect(hwnd, ctypes.byref(r))
                    try:
                        scale = (user32.GetDpiForWindow(hwnd) or 96) / 96
                    except Exception:  # noqa: BLE001
                        scale = 1
                    hit = island_hit((pt.x, pt.y), (r.left, r.top, r.right, r.bottom), scale)
                if hit and (int(under) == hwnd or not under):
                    on_bar = bridge._mode != "painel" or hit[1] < BAR_H
                    if on_bar:
                        press = {"hit": hit, "cursor_x": pt.x, "win_x": r.left, "win_w": r.right - r.left, "y": r.top,
                                 "dragging": False, "mode": bridge._mode, "hwnd": hwnd}
                        if bridge._mode != "painel":
                            js("window.__jarvisIslandDown && window.__jarvisIslandDown()")
                elif hit:
                    log.info("clique sobre a ilha, mas outra janela está por cima (%s)", under)
                elif hwnd and bridge._mode == "painel":  # clicou fora: fecha o painel
                    js("window.__jarvisIslandOutside && window.__jarvisIslandOutside()")
            elif down and press:  # segurando: arrastou?
                pt = wintypes.POINT()
                user32.GetCursorPos(ctypes.byref(pt))
                if press["dragging"] or abs(pt.x - press["cursor_x"]) > DRAG_PX:
                    press["dragging"] = True
                    screen_w = user32.GetSystemMetrics(0) or 1920  # SM_CXSCREEN (mesma escala do cursor)
                    x = drag_x(press["win_x"], press["cursor_x"], pt.x, press["win_w"], screen_w)
                    user32.SetWindowPos(press["hwnd"], None, x, press["y"], 0, 0, swp)
                    press["x"] = x
            elif not down and was_down and press:  # SOLTOU
                if press["dragging"]:
                    screen_w = user32.GetSystemMetrics(0) or 1920
                    bridge._set_pos(center_fraction(press.get("x", press["win_x"]), press["win_w"], screen_w))
                    log.info("ilha arrastada para %.2f da tela", bridge._pos)
                    js("window.__jarvisIslandDragged && window.__jarvisIslandDragged()")
                else:
                    now = time.time()
                    # dois cliques na pílula fechada (o 1º já abriu o painel: vale o modo do 1º clique)
                    on_avatar = press["mode"] != "painel" and press["hit"][0] < POKE_ZONE_PX  # cutucando o avatar
                    if not on_avatar and last_mode != "painel" and now - last_click < 0.45:
                        log.info("dois cliques na ilha: abrindo o JARVIS")
                        js("window.__jarvisIslandDragged && window.__jarvisIslandDragged()")
                        js("window.__jarvisIslandOutside && window.__jarvisIslandOutside()")
                        bridge.show_main()
                        last_click = 0.0
                    elif press["mode"] != "painel":  # um clique na pílula
                        last_click, last_mode = now, press["mode"]
                        hit = press["hit"]
                        log.info("clique na ilha em %s", hit)
                        js(f"window.__jarvisIslandPress && window.__jarvisIslandPress({hit[0]}, {hit[1]})")
                press = None
        except Exception as exc:  # noqa: BLE001
            log.info("clique na ilha falhou: %s", exc)
            press = None
        was_down = down


def system_idle_seconds() -> float:
    """Segundos desde a última vez que mexeram no mouse/teclado (Windows: GetLastInputInfo). -1 fora do Windows."""
    if sys.platform != "win32":
        return -1.0
    try:
        import ctypes
        from ctypes import wintypes

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            return -1.0
        ticks = ctypes.windll.kernel32.GetTickCount() & 0xFFFFFFFF
        return max(0.0, ((ticks - info.dwTime) & 0xFFFFFFFF) / 1000.0)
    except Exception:  # noqa: BLE001
        return -1.0


def chase_step(pos: tuple[float, float], target: tuple[float, float], speed: float) -> tuple[tuple[float, float], float]:
    """Um passo do Pac-Man na direção do mouse. Devolve (nova posição, distância que faltava)."""
    dx, dy = target[0] - pos[0], target[1] - pos[1]
    dist = (dx * dx + dy * dy) ** 0.5
    if dist <= speed or dist == 0:
        return (float(target[0]), float(target[1])), dist
    return (pos[0] + dx / dist * speed, pos[1] + dy / dist * speed), dist


def chase_speed(elapsed: float, scale: float = 1.0) -> float:
    """Pixels por quadro: começa devagar (dá para fugir um pouco) e vai acelerando."""
    return scale * min(26.0, 7.0 + elapsed * 2.2)


def create_chaser_window():
    """A janelinha transparente do modo Pac-Man (começa escondida). None se o Windows/pywebview não deixar."""
    try:
        import webview

        # V8.6.3: sem "transparent" (no Windows o pywebview não faz janela transparente: ficava um quadrado branco);
        # a janela é RECORTADA no formato da cabeça do robô (shape_chaser), então só o robô aparece.
        return webview.create_window(PACMAN_TITLE, f"{FRONT}/?pacman=1", width=PACMAN_SIZE, height=PACMAN_SIZE,
                                     frameless=True, on_top=True, hidden=True, background_color="#000000",
                                     resizable=False, easy_drag=False, focus=False, min_size=(60, 60))
    except Exception as exc:  # noqa: BLE001 - sem o Pac-Man o resto continua
        log.info("pac-man indisponível: %s", exc)
        return None


# V8.6.3: a cabeça do robô dentro da janelinha do Pac-Man (px da página, janela de PACMAN_SIZE): o rosto arredondado
# e as duas "orelhas". Bate com o RoboAvatar "tight" (viewBox 2 16 116 96) ocupando a janela toda.
PACMAN_HEAD = (11, 17, 109, 103, 70)  # x1, y1, x2, y2, diâmetro do canto
PACMAN_EARS = ((2, 45, 18, 75, 10), (102, 45, 118, 75, 10))


def chaser_shape(scale: float = 1.0) -> list[tuple[int, int, int, int, int]]:
    """Os pedaços (retângulos arredondados) que formam a cabeça, já na escala da tela."""
    return [tuple(round(v * scale) for v in part) for part in (PACMAN_HEAD, *PACMAN_EARS)]


def shape_chaser(hwnd: int, scale: float) -> bool:
    """Recorta a janelinha no formato da cabeça (fora dela, nada aparece: nem fundo branco nem preto)."""
    try:
        import ctypes
        from ctypes import wintypes

        gdi32 = ctypes.WinDLL("gdi32")
        gdi32.CreateRoundRectRgn.restype = wintypes.HANDLE
        gdi32.CombineRgn.argtypes = [wintypes.HANDLE, wintypes.HANDLE, wintypes.HANDLE, ctypes.c_int]
        parts = [gdi32.CreateRoundRectRgn(x1, y1, x2, y2, r, r) for x1, y1, x2, y2, r in chaser_shape(scale)]
        rgn = parts[0]
        for extra in parts[1:]:
            gdi32.CombineRgn(rgn, rgn, extra, 2)  # RGN_OR
        return bool(_user32().SetWindowRgn(hwnd, rgn, True))
    except Exception as exc:  # noqa: BLE001
        log.info("pac-man: recorte falhou: %s", exc)
        return False


def run_pacman(bridge: Bridge) -> None:
    """V8.6.0: o avatar sai da ilha, corre atrás do mouse com a boca abrindo e fechando; quando alcança, "come" o
    mouse (segura o cursor na boca enquanto mastiga) e depois devolve, feliz, e volta para a ilha.
    Esc a qualquer momento: para tudo e devolve o mouse na hora."""
    import ctypes
    from ctypes import wintypes

    def js(phase: str, direction: str = "") -> None:
        try:
            bridge._chaser.evaluate_js(f"window.__pac && window.__pac({json.dumps(phase)}, {json.dumps(direction)})")
        except Exception:  # noqa: BLE001
            log.info("pac-man: página não respondeu")

    u = _user32()
    u.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
    u.GetAsyncKeyState.restype = ctypes.c_short
    flags = 0x0001 | 0x0010 | 0x0040  # SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
    topmost = wintypes.HWND(-1)
    esc = lambda: bool(u.GetAsyncKeyState(0x1B) & 0x8000)  # noqa: E731
    try:
        bridge._chaser.show()
        time.sleep(0.3)
        hwnd = u.FindWindowW(None, PACMAN_TITLE)
        if not hwnd:
            log.info("pac-man: janela não encontrada")
            return
        r = wintypes.RECT()
        u.GetWindowRect(hwnd, ctypes.byref(r))
        w, h = r.right - r.left, r.bottom - r.top
        scale = (u.GetDpiForWindow(hwnd) or 96) / 96
        shape_chaser(hwnd, w / PACMAN_SIZE if w else scale)
        home = (u.GetSystemMetrics(0) / 2, 40 * scale)
        ih = island_hwnd(bridge._island)
        if ih:
            ir = wintypes.RECT()
            u.GetWindowRect(ih, ctypes.byref(ir))
            home = ((ir.left + ir.right) / 2, ir.bottom + h / 2)
        mouth_dy = h * 0.12  # a boca fica um pouco abaixo do meio
        pos = home
        last_dir = ""
        place = lambda p: u.SetWindowPos(hwnd, topmost, int(p[0] - w / 2), int(p[1] - h / 2), 0, 0, flags)  # noqa: E731
        place(pos)
        log.info("pac-man: correndo atrás do mouse")
        js("corre", "right")
        started = time.time()
        while not bridge._quitting:
            if esc():
                log.info("pac-man: Esc, parando")
                return
            pt = wintypes.POINT()
            u.GetCursorPos(ctypes.byref(pt))
            target = (pt.x, pt.y - mouth_dy)
            elapsed = time.time() - started
            pos, dist = chase_step(pos, target, chase_speed(elapsed, scale))
            direction = "left" if target[0] < pos[0] - 2 else "right" if target[0] > pos[0] + 2 else last_dir
            if direction and direction != last_dir:
                last_dir = direction
                js("corre", direction)
            place(pos)
            if dist < 16 * scale or elapsed > PACMAN_MAX_CHASE_S:
                break
            time.sleep(PACMAN_FRAME_S)
        # pegou: mastiga segurando o mouse na boca
        log.info("pac-man: pegou o mouse, mastigando")
        js("mastiga", last_dir)
        mouth = (int(pos[0]), int(pos[1] + mouth_dy))
        end = time.time() + PACMAN_CHEW_S
        while time.time() < end and not bridge._quitting and not esc():
            u.SetCursorPos(*mouth)
            time.sleep(0.012)
        # devolve o mouse (cospe um pouco para o lado) e volta feliz para a ilha
        side = -1 if last_dir == "left" else 1
        u.SetCursorPos(mouth[0] + int(70 * scale) * side, mouth[1] + int(20 * scale))
        js("feliz", last_dir)
        time.sleep(0.9)
        for _ in range(80):
            pos, dist = chase_step(pos, home, 30 * scale)
            place(pos)
            if dist < 4:
                break
            time.sleep(PACMAN_FRAME_S)
    except Exception as exc:  # noqa: BLE001
        log.info("pac-man falhou: %s", exc)
    finally:
        js("parado")
        try:
            bridge._chaser.hide()
        except Exception:  # noqa: BLE001
            log.info("pac-man: não consegui esconder a janela")
        bridge._pac_running = False


def source_fingerprint(path: Path | None = None) -> str:
    """Impressão digital do código deste app (muda quando uma atualização troca o arquivo)."""
    import hashlib

    return hashlib.sha256(Path(path or __file__).read_bytes()).hexdigest()


def should_relaunch(changed_at: float | None, now: float, mode: str, up: bool, settle_s: float = 45) -> bool:
    """Reabre o app quando: o código mudou há um tempinho (a atualização terminou), o JARVIS já está de pé de
    novo e a ilha não está aberta (não interrompe você)."""
    return changed_at is not None and now - changed_at >= settle_s and up and mode != "painel"


def relaunch() -> bool:
    """Abre uma cópia nova deste app (o pythonw do atalho) e deixa esta fechar."""
    try:
        flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        subprocess.Popen([sys.executable, str(Path(__file__).resolve())], cwd=str(Path(__file__).resolve().parent),  # noqa: S603
                         creationflags=flags, close_fds=True, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as exc:  # noqa: BLE001
        log.info("não consegui reabrir o app: %s", exc)
        return False


def watch_self_update(bridge: Bridge, every: float = 30) -> None:
    """V8.5.0: depois de uma atualização que mexeu neste app, ele se reabre sozinho (sem atalho nem CMD)."""
    if getattr(sys, "frozen", False):
        return
    try:
        start = source_fingerprint()
    except OSError:
        return
    changed_at = None
    while not bridge._quitting:
        time.sleep(every)
        try:
            if changed_at is None and source_fingerprint() != start:
                changed_at = time.time()
                log.info("o código do app mudou (atualização): vou reabrir quando o JARVIS voltar")
        except OSError:
            continue
        if should_relaunch(changed_at, time.time(), bridge._mode, jarvis_up()):
            log.info("reabrindo o app com a versão nova")
            if relaunch():
                bridge.quit()
            return


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
        if msg.message == 0x0312 and bridge._main:  # WM_HOTKEY
            bridge.talk()


def main() -> None:
    # V8.6.3: o fundo padrão do navegador embutido (WebView2) é BRANCO e aparecia nas pontas da pílula e em volta do
    # Pac-Man. Preto combina com tudo do app (e é o que fica por baixo das partes recortadas).
    os.environ.setdefault("WEBVIEW2_DEFAULT_BACKGROUND_COLOR", "FF000000")
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
    bridge._size = cfg.get("tamanho", "media")
    try:
        bridge._pos = min(1.0, max(0.0, float(cfg.get("posicao", 0.5))))
    except (TypeError, ValueError):
        bridge._pos = 0.5
    if cfg.get("painel") in PANEL_SIZES:
        bridge._panel = cfg["painel"]
    island_on = cfg.get("ligada", True)
    # V8.1.3: com a ilha ligada, a janela do JARVIS começa escondida e só aparece quando você clica na ilha
    bridge._main = webview.create_window("JARVIS", f"{FRONT}/?desk=1&app=windows", width=1280, height=820, min_size=(900, 600),
                                        background_color="#0b0d12", js_api=bridge, text_select=True, hidden=island_on)
    bridge._main.events.closing += bridge.on_main_closing
    if island_on:
        screens = webview.screens
        bridge._screen_w = screens[0].width if screens else 1920
        x, y, w, h = island_position(bridge._screen_w, bridge._size, "mini", bridge._pos)
        # V8.1.2: sem transparent (o clique atravessava); a pílula é recortada no shown (SetWindowRgn)
        bridge._island = webview.create_window(ISLAND_TITLE, f"{FRONT}/?ilha=1", x=x, y=y, width=w, height=h, frameless=True,
                                              on_top=True, resizable=False, easy_drag=False, background_color="#000000",
                                              js_api=bridge, focus=True, min_size=(120, 30))  # o padrão (200x100) esticava a ilha
        bridge._island.events.shown += lambda: shape_window(bridge._island, island_radius("mini", 9999))
        # V8.6.0: a janelinha do modo Pac-Man (transparente e "atravessável": só o avatar aparece; começa escondida)
        bridge._chaser = create_chaser_window()
        threading.Thread(target=watch_island_clicks, args=(bridge,), daemon=True).start()
    threading.Thread(target=listen_hotkey, args=(bridge, cfg.get("atalho", "PageDown")), daemon=True).start()
    threading.Thread(target=watch_self_update, args=(bridge,), daemon=True).start()  # V8.5.0
    os.environ.setdefault("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "--autoplay-policy=no-user-gesture-required")
    webview.start(private_mode=False, user_agent=USER_AGENT, storage_path=str(Path(os.getenv("APPDATA", ".")) / "JARVIS" / "webview"))


if __name__ == "__main__":
    main()

"""V8.5.0: ATUALIZAÇÃO AUTOMÁTICA (sem abrir a pasta nem o CMD).

De tempos em tempos o JARVIS confere se tem versão nova no GitHub. Se tiver, espera um momento em que ele está
PARADO (ninguém falando com ele há alguns minutos, nada rodando) e atualiza sozinho, igual ao botão ATUALIZAR,
mas sem falar: só avisa na ilha. Depois do reinício:
- a interface nova vem pronta do site (ou é montada em segundo plano);
- a ilha e a janela do app se recarregam sozinhas;
- o app do Windows se reabre sozinho quando o código dele mudou (desktop/jarvis_desktop.py).
Dá para desligar em Configurações › Atualizações (Modo Desk).
"""
from __future__ import annotations

import asyncio
import logging
import os
import time

log = logging.getLogger("jarvis.auto_update")

FIRST_CHECK_S = 10 * 60  # deixa o JARVIS ligar com calma
CHECK_EVERY_S = 30 * 60
QUIET_FOR_S = 5 * 60  # ninguém falou com ele por esse tempo
# V8.7.2: e o PC parado de verdade (antes atualizava no meio de um vídeo do YouTube, que engasgava):
USER_IDLE_S = 30 * 60  # ninguém mexeu no mouse/teclado por 30 min...
NIGHT_HOURS = range(1, 6)  # ...ou de madrugada (1h às 6h)


def user_idle_seconds() -> float:
    """Segundos sem mexer no mouse/teclado (Windows). Fora do Windows: "muito tempo" (não segura a atualização)."""
    import sys

    if sys.platform != "win32":
        return float("inf")
    try:
        import ctypes
        from ctypes import wintypes

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            return 0.0
        return (((ctypes.windll.kernel32.GetTickCount() & 0xFFFFFFFF) - info.dwTime) & 0xFFFFFFFF) / 1000.0
    except Exception:  # noqa: BLE001
        return 0.0


def fullscreen_app() -> bool:
    """Tem algo em TELA CHEIA na frente (vídeo, jogo, apresentação)? Aí não atualiza. Falso fora do Windows."""
    import sys

    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        u = ctypes.windll.user32
        u.GetForegroundWindow.restype = wintypes.HWND
        hwnd = u.GetForegroundWindow()
        if not hwnd or hwnd in (u.GetDesktopWindow(), u.GetShellWindow()):
            return False
        r = wintypes.RECT()
        u.GetWindowRect(hwnd, ctypes.byref(r))
        return r.left <= 0 and r.top <= 0 and r.right >= u.GetSystemMetrics(0) and r.bottom >= u.GetSystemMetrics(1)
    except Exception:  # noqa: BLE001
        return False


def pc_free(now_hour: int | None = None, idle_s: float | None = None, fullscreen: bool | None = None) -> bool:
    """O PC está livre para atualizar? Nada em tela cheia e (madrugada ou 30 min sem mexer no mouse/teclado)."""
    import datetime as _dt

    hour = _dt.datetime.now().hour if now_hour is None else now_hour
    idle = user_idle_seconds() if idle_s is None else idle_s
    full = fullscreen_app() if fullscreen is None else fullscreen
    return not full and (hour in NIGHT_HOURS or idle >= USER_IDLE_S)


def enabled() -> bool:
    try:
        from modules import desk

        return bool(desk.config().get("atualizacao", {}).get("automatica", True))
    except Exception:  # noqa: BLE001
        return False


def on_open_enabled() -> bool:
    """V8.11: atualizar ao abrir a central (Configurações; ligado por padrão)."""
    try:
        from modules import desk

        return bool(desk.config().get("atualizacao", {}).get("ao_abrir", True))
    except Exception:  # noqa: BLE001
        return False


def is_quiet(now: float | None = None) -> bool:
    """O JARVIS está parado? (nada rodando, ilha parada e nenhuma resposta nos últimos minutos)."""
    from core import runtime, session

    now = time.time() if now is None else now
    if session.busy or runtime.island_state(now) != "idle":
        return False
    if now - float(runtime.ISLAND.get("resposta_em") or 0) <= QUIET_FOR_S:
        return False
    return pc_free()


async def check_and_update(sleep=asyncio.sleep, now=time.time) -> str:
    """Uma rodada: "desligada" | "em dia" | "ocupado" | "atualizando" | "erro"."""
    from core import runtime
    from modules import self_update

    if not enabled():
        return "desligada"
    info = await asyncio.to_thread(self_update.check, True)
    if not info.get("available"):
        return "em dia"
    for _ in range(36):  # espera até ~3 h por um momento parado (madrugada ou PC sem uso)
        if is_quiet(now()):
            break
        await sleep(5 * 60)
    else:
        return "ocupado"
    latest = info.get("latest") or "nova"
    log.info("Atualização automática: versão %s encontrada, atualizando com o JARVIS parado.", latest)
    runtime.note_island({"type": "response", "text": f"⬆ Atualizando o JARVIS para a versão {latest}… volto em instantes."})
    from routes.system import perform_update

    res = await perform_update(announce=False)
    return "atualizando" if res.get("status") == "restarting" else "erro"


async def auto_update_loop() -> None:
    if os.name != "nt":  # o reinício automático é pelo Iniciar-JARVIS.bat (Windows)
        return
    await asyncio.sleep(FIRST_CHECK_S)
    while True:
        try:
            if await check_and_update() == "atualizando":
                return
        except Exception as exc:  # noqa: BLE001 - sem internet etc.: tenta na próxima
            log.info("Atualização automática: não deu agora (%s).", exc)
        await asyncio.sleep(CHECK_EVERY_S)

"""V8.5.0: ATUALIZAÇÃO AUTOMÁTICA (sem abrir a pasta nem o CMD).

De tempos em tempos o JARVIS confere se tem versão nova no GitHub. Se tiver, espera um momento em que ele está
PARADO (ninguém falando com ele há alguns minutos, nada rodando) e atualiza sozinho, igual ao botão ATUALIZAR,
mas sem falar: só avisa na ilha. Depois do reinício:
- a interface nova vem pronta do site (ou é montada em segundo plano);
- a ilha e a janela do app se recarregam sozinhas;
- o app do Windows se reabre sozinho quando o código dele mudou (desktop/jarvis_desktop.py).
Dá para desligar em Configurações › Atualizações (Modo Desk).

V9.4.1 (pedido do usuário: "ele mesmo atualizar e me avisar"): antes só atualizava com o PC 30 min sem uso ou de
madrugada, e calado. Na prática quase nunca rodava com o PC em uso, e a versão nova ficava esperando o botão (que às
vezes nem funcionava). Agora:
  - confere a cada 40 minutos (a primeira, 3 minutos depois de ligar);
  - achou versão nova: AVISA na tela (com ATUALIZAR AGORA e ADIAR 1 H), no celular e por voz, e espera 2 minutos;
  - depois atualiza sozinho assim que o JARVIS estiver parado (sem falar nem responder há 2 minutos) e não houver
    nada em tela cheia (vídeo, jogo, apresentação). A central aberta mostra a tela de atualização e volta sozinha.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time

log = logging.getLogger("jarvis.auto_update")

FIRST_CHECK_S = 3 * 60  # V9.4.1: era 10 min
CHECK_EVERY_S = 40 * 60  # V9.4.1: o usuário pediu "a cada 40 minutos" (era 30, mas só atualizava com o PC parado)
QUIET_FOR_S = 2 * 60  # V9.4.1: ninguém falou com ele por esse tempo (era 5 min)
NOTICE_S = 120  # o aviso fica 2 min na tela antes de atualizar (dá para adiar)
POSTPONE_S = 60 * 60
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
    """O PC está livre para atualizar? V9.4.1: basta não ter nada em tela cheia (vídeo, jogo, apresentação).

    Antes exigia também madrugada ou 30 min sem mexer no mouse/teclado, e por isso quase nunca atualizava sozinho.
    now_hour e idle_s ficam por compatibilidade (não decidem mais)."""
    full = fullscreen_app() if fullscreen is None else fullscreen
    return not full


# ------------------------------------------------------------------ V9.4.1: aviso, adiar e atualizar agora
_state: dict = {"postponed_until": 0.0, "now": False, "notice": None, "failed": None}
FAILED_QUIET_S = 6 * 60 * 60  # a mesma versão que falhou não é anunciada de novo por 6 h (o botão continua valendo)


def postpone(seconds: float = POSTPONE_S, now: float | None = None) -> dict:
    """ADIAR 1 H: a atualização avisada espera (a próxima conferência respeita o prazo)."""
    now = time.time() if now is None else now
    _state["postponed_until"] = now + seconds
    _state["now"] = False
    return {"postponed_until": _state["postponed_until"]}


def update_now() -> None:
    """ATUALIZAR AGORA: pula o resto da espera do aviso."""
    _state["now"] = True
    _state["postponed_until"] = 0.0


def postponed(now: float | None = None) -> bool:
    return (time.time() if now is None else now) < _state["postponed_until"]


def pending_notice() -> dict | None:
    """O aviso em andamento (a central que abrir no meio da contagem mostra o mesmo aviso)."""
    return _state.get("notice")


def reset_for_tests() -> None:
    _state.update(postponed_until=0.0, now=False, notice=None, failed=None)


async def _announce(latest: str, notes: list) -> None:
    from core import runtime, speech

    notice = {"type": "update_soon", "version": latest, "in_s": NOTICE_S, "at": time.time(), "notes": notes[:4]}
    _state["notice"] = notice
    await runtime.manager.broadcast(notice)
    runtime.note_island({"type": "response", "text": f"⬆ Versão {latest} disponível: atualizo em 2 minutos."})
    runtime.notify("system", "⬆ Atualização do JARVIS", f"A versão {latest} chegou. Atualizo sozinho em 2 minutos.")
    try:
        await speech.say_quietly(f"Senhor, chegou a versão {latest}. Atualizo sozinho em dois minutos; se preferir, adie na tela.")
    except Exception:  # noqa: BLE001 - sem voz, o aviso na tela e no celular continua
        log.warning("Aviso falado da atualização falhou", exc_info=True)


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
    """Uma rodada: "desligada" | "em dia" | "adiada" | "ocupado" | "atualizando" | "erro"."""
    from core import runtime
    from modules import self_update

    if not enabled():
        return "desligada"
    if postponed(now()):
        return "adiada"
    info = await asyncio.to_thread(self_update.check, True)
    if not info.get("available"):
        return "em dia"
    latest = info.get("latest") or "nova"
    failed = _state.get("failed")
    if failed and failed[0] == latest and now() - failed[1] < FAILED_QUIET_S:
        return "erro"  # já avisei que essa não deu; não repete o aviso a cada 40 min
    await _announce(latest, info.get("notes") or [])
    # V9.4.1: 2 minutos de aviso (ATUALIZAR AGORA pula; ADIAR 1 H cancela esta rodada)
    waited = 0
    while waited < NOTICE_S and not _state["now"]:
        if postponed(now()):
            _state["notice"] = None
            await runtime.manager.broadcast({"type": "update_soon", "cancelled": True})
            return "adiada"
        await sleep(5)
        waited += 5
    for _ in range(36):  # espera até ~3 h por um momento sem fala nem tela cheia (antes: PC parado 30 min)
        if postponed(now()):
            _state["notice"] = None
            await runtime.manager.broadcast({"type": "update_soon", "cancelled": True})
            return "adiada"
        if _state["now"] or is_quiet(now()):
            break
        await sleep(5 * 60)
    else:
        return "ocupado"
    _state["now"] = False
    _state["notice"] = None
    log.info("Atualização automática: versão %s encontrada, atualizando.", latest)
    runtime.note_island({"type": "response", "text": f"⬆ Atualizando o JARVIS para a versão {latest}… volto em instantes."})
    from routes.system import perform_update

    res = await perform_update(announce=False)
    if res.get("status") == "restarting":
        # a central aberta entra na tela de atualização e recarrega quando a versão nova subir
        await runtime.manager.broadcast({"type": "update_started", "boot_id": res.get("boot_id"), "before": res.get("before"),
                                         "after": res.get("after"), "changed": res.get("changed"),
                                         "versao_nova": res.get("versao_nova", latest), "destaques": res.get("destaques", [])})
        return "atualizando"
    _state["failed"] = (latest, now())
    msg = res.get("message") or "Não consegui atualizar agora."
    await runtime.manager.broadcast({"type": "update_soon", "cancelled": True, "error": msg})
    runtime.notify("system", "⚠ Atualização do JARVIS", msg)
    try:
        from modules import event_log

        event_log.add("error", "A atualização automática não deu certo", msg)
    except Exception:  # noqa: BLE001
        log.debug("event_log indisponível", exc_info=True)
    return "erro"


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

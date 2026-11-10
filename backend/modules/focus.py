"""Modo Foco / Pomodoro do JARVIS: timer de concentração, pausas e som ambiente opcional.
"""
import asyncio
import logging
import re
import time
from typing import Awaitable, Callable, Optional

log = logging.getLogger("jarvis.focus")

_announcer: Optional[Callable[[str], Awaitable[None]]] = None
_ws_broadcaster: Optional[Callable[[dict], Awaitable[None]]] = None
_current_channel = None


def set_focus_announcer(fn: Callable[[str], Awaitable[None]]) -> None:
    global _announcer
    _announcer = fn


def set_ws_broadcaster(fn: Callable[[dict], Awaitable[None]]) -> None:
    global _ws_broadcaster
    _ws_broadcaster = fn


class FocusSession:
    def __init__(self) -> None:
        self.active: bool = False
        self.phase: str = "idle"  # "work" | "break" | "idle"
        self.focus_duration: int = 25 * 60
        self.break_duration: int = 5 * 60
        self.end_time: float = 0
        self.task: Optional[asyncio.Task] = None
        self.sound_playing: bool = False

    def status(self) -> dict:
        remaining = max(0, int(self.end_time - time.monotonic())) if self.active else 0
        return {
            "active": self.active,
            "phase": self.phase,
            "remaining_seconds": remaining,
            "focus_duration": self.focus_duration,
            "break_duration": self.break_duration,
            "sound_playing": self.sound_playing,
        }


session = FocusSession()


def _play_ambient_sound(start: bool = True) -> None:
    """O áudio ambiente agora é sintetizado no frontend com Web Audio API."""
    global _current_channel
    try:
        import pygame
        if pygame.mixer.get_init():
            pygame.mixer.stop()
    except Exception:
        pass
    session.sound_playing = False


async def _run_session() -> None:
    try:
        # 1. Fase de foco
        session.phase = "work"
        session.end_time = time.monotonic() + session.focus_duration
        if _ws_broadcaster:
            await _ws_broadcaster({"type": "focus_status", **session.status()})

        # O áudio ambiente (ruído branco/marrom/binaural) agora é gerenciado pelo frontend com controle de volume e silêncio
        # _play_ambient_sound(True)

        await asyncio.sleep(session.focus_duration)

        # 2. Aviso de pausa
        _play_ambient_sound(False)
        session.phase = "break"
        session.end_time = time.monotonic() + session.break_duration
        if _ws_broadcaster:
            await _ws_broadcaster({"type": "focus_status", **session.status()})

        if _announcer:
            await _announcer(f"Parabéns! Sua sessão de foco terminou. Hora de uma pausa de {session.break_duration // 60} minutos.")

        await asyncio.sleep(session.break_duration)

        # 3. Conclusão
        session.active = False
        session.phase = "idle"
        _play_ambient_sound(False)
        if _ws_broadcaster:
            await _ws_broadcaster({"type": "focus_status", **session.status()})

        if _announcer:
            await _announcer("Intervalo concluído. Pronto para voltar ao foco quando quiser!")

    except asyncio.CancelledError:
        _play_ambient_sound(False)
        session.active = False
        session.phase = "idle"
        if _ws_broadcaster:
            await _ws_broadcaster({"type": "focus_status", **session.status()})
        raise


def start_focus(minutes: int = 25, break_minutes: int = 5) -> str:
    if session.active or session.sound_playing:
        stop_focus()
    session.active = True
    session.focus_duration = minutes * 60
    session.break_duration = break_minutes * 60
    session.task = asyncio.create_task(_run_session())
    return f"Modo foco ativado por {minutes} minutos. Bom trabalho, senhor."


def stop_focus() -> str:
    was_running = session.active or session.sound_playing
    if session.task and not session.task.done():
        session.task.cancel()
    _play_ambient_sound(False)
    session.active = False
    session.phase = "idle"
    return "Modo Foco cancelado e som desligado." if was_running else "O som do modo foco já está desligado."


async def handle_voice(message: str, norm: str, words: int, name: str) -> Optional[str]:
    # 1. Parar / Desligar foco ou som
    stop_words = (
        "parar", "para", "pare", "cancela", "cancelar", "desativar", "desativa",
        "desligar", "desliga", "desligue", "encerrar", "encerra", "silenciar", "silencia"
    )
    target_words = ("foco", "pomodoro", "som do foco", "musica do foco", "barulho do foco", "barulho", "som de fundo")

    if any(sw in norm for sw in stop_words) and any(tw in norm for tw in target_words):
        return stop_focus()

    # 2. Iniciar foco / pomodoro
    start_match = re.search(
        r"\b(?:iniciar|inicia|comecar|comeca|ativar|ativa|liga|ligar|modo)\s+(?:modo\s+)?(?:foco|pomodoro)\b",
        norm
    )
    if start_match:
        match_min = re.search(r"\b(\d+)\s+minutos?\b", norm)
        mins = int(match_min.group(1)) if match_min else 25
        return start_focus(minutes=mins)

    # 3. Status do foco
    if any(q in norm for q in ("tempo de foco", "quanto tempo de foco", "status do foco", "status do pomodoro")):
        st = session.status()
        if not st["active"]:
            return "O modo foco não está ativo no momento."
        rem_min = st["remaining_seconds"] // 60
        fase_nome = "concentração" if st["phase"] == "work" else "pausa"
        return f"Você está na fase de {fase_nome}. Faltam aproximadamente {rem_min} minutos."

    return None

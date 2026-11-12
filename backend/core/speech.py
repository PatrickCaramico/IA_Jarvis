"""Fala do JARVIS: voz com estados da tela, avisos falados, saudação e volume noturno."""

import logging
import asyncio
from datetime import datetime
from config import settings
from modules import tools, prefs, reminders, focus, alarms
from modules import access, sentinel
from modules import tts as tts_module
from modules.tts import generate_and_play_speech
from core import runtime, session

log = logging.getLogger("jarvis.speech")


FILLERS = [
    "Senhor, essa informação exige uma análise mais aprofundada. Vou investigar os dados necessários e retorno com uma resposta precisa assim que concluir.",
    "Um instante, senhor, estou verificando as informações na rede.",
    "Estou processando a busca, senhor. Já volto com os resultados completos.",
]


def canceled(turn: int) -> bool:
    return turn != session.turn_id


def time_greeting() -> str:
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Bom dia"
    if 12 <= hour < 18:
        return "Boa tarde"
    return "Boa noite"


async def speak(text: str, release_busy: bool = True, idle_after: bool = True) -> None:
    """Sintetiza e toca a voz, mantendo o frontend informado sobre cada fase.

    idle_after=False (V4.3, briefing em etapas): não volta a tela para "em espera" entre uma parte e outra.
    """
    turn = session.turn_id
    if prefs.is_silent_mode():
        await runtime.manager.broadcast({"type": "step", "step": "tts", "status": "done"})
        if not canceled(turn):
            if release_busy:
                session.busy = False
            if idle_after:
                await runtime.manager.broadcast({"type": "state", "state": "idle"})
        return

    await runtime.manager.broadcast({"type": "step", "step": "tts", "status": "active"})

    async def on_start() -> None:
        await runtime.manager.broadcast({"type": "state", "state": "speaking"})

    session.speaking += 1
    try:
        await generate_and_play_speech(text, on_playback_start=on_start)
        await runtime.manager.broadcast({"type": "step", "step": "tts", "status": "done"})
    except asyncio.CancelledError:
        raise  # cancelado pelo usuário: o /api/cancel já cuidou do estado da tela
    except Exception as exc:  # noqa: BLE001
        log.exception("Falha na síntese de voz")
        await runtime.manager.broadcast({"type": "step", "step": "tts", "status": "error"})
        await runtime.manager.broadcast({"type": "error", "message": f"Falha na voz: {exc}"})
    finally:
        session.speaking = max(0, session.speaking - 1)
        if not canceled(turn):
            if release_busy:
                session.busy = False
            if idle_after:
                await runtime.manager.broadcast({"type": "state", "state": "idle"})


async def say_quietly(text: str) -> None:
    """Fala sem mexer em estados da tela (avisos, erros)."""
    if prefs.is_silent_mode():
        return
    try:
        await generate_and_play_speech(text)
    except Exception:  # noqa: BLE001
        log.exception("Falha ao falar aviso")


LOCKED_ALERT = (
    "Senhor, um alarme ou lembrete que o senhor programou acabou de disparar. Libere a central para ver os detalhes."
)


async def announce(text: str) -> None:
    """Aviso de timer/lembrete: aparece na tela e é falado.

    Com a central bloqueada (ou no modo visitante), o aviso é genérico: o conteúdo pode ser pessoal.
    O celular pareado (V4.5) recebe o texto completo: ele é do dono e pede a chave de pareamento.
    """
    runtime.notify("reminder", "Lembrete do JARVIS", text)
    if access.is_restricted():
        text = LOCKED_ALERT
    await runtime.manager.broadcast({"type": "alert", "text": text})
    await say_quietly(text)


async def broadcast_access() -> None:
    await runtime.manager.broadcast({"type": "access_state", **access.snapshot()})


def night_volume() -> str:
    """Modo noturno da Sentinela: voz mais baixa entre 22h e 7h com a central bloqueada."""
    hour = datetime.now().hour
    if not (hour >= 22 or hour < 7) or not access.is_restricted():
        return "+0%"
    p = prefs.get_all()
    return "-35%" if p.get("sentinel_enabled") and p.get("sentinel_night_dim", True) else "+0%"


tts_module.volume_provider = night_volume


tools.set_announcer(announce)


reminders.set_announcer(announce)


# V5.1: alarmes avisam a tela e falam a hora; com a central bloqueada, sem o rótulo
alarms.configure(broadcast=runtime.manager.broadcast, speak=say_quietly, is_restricted=access.is_restricted)

# V5.6: contagens regressivas avisam as telas (widget) quando mudam
from modules import countdowns as _countdowns  # noqa: E402

_countdowns.configure(broadcast=runtime.manager.broadcast)


focus.set_focus_announcer(announce)


focus.set_ws_broadcaster(runtime.manager.broadcast)
# frases fixas tocam do cache de voz, sem esperar nova síntese (otimização 4.2)
tts_module.register_phrases([*FILLERS, LOCKED_ALERT, *sentinel.AWAKE_REPLIES])


async def filler_loop(stop: asyncio.Event) -> None:
    """Enquanto a IA processa, avisa por voz: 'só um minutinho...' de tempos em tempos."""
    if settings.FILLER_FIRST_DELAY <= 0:
        return
    wait, n = settings.FILLER_FIRST_DELAY, 0
    while True:
        try:
            await asyncio.wait_for(stop.wait(), timeout=wait)
            return
        except asyncio.TimeoutError:
            pass
        await say_quietly(FILLERS[n % len(FILLERS)])  # se a resposta chegar, ela espera este aviso terminar
        n += 1
        wait = max(settings.FILLER_INTERVAL, 5)

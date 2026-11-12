"""V4.3: briefing do "bom dia" (e fechamento do "boa noite") em etapas, com um card por assunto.

Sequência enviada pelo WebSocket:
  briefing_start {mode, title, tabs, greeting, opening, opening_sub, text, total, plan}
                 (plan = todos os cards já no início: a tela mostra a pauta desde a saudação)
  briefing_step  {index, total, tab, progress, card, text}   (um por assunto, antes da fala dele)
  briefing_end   {cards, readiness, closing}
  response       {text: closing, cards: [{type: "briefing", ...}]}  (fica no Canal Ativo)
"text" é o que o JARVIS vai falar agora (legenda e Canal Ativo ao vivo).
A fala de cada parte termina antes do próximo card entrar. "Próximo" (skip) corta só a parte atual;
o botão Cancelar corta a sequência inteira.
"""

import asyncio
import logging

from modules import briefing, memory, prefs
from modules import tts as tts_module
from core import runtime, session, speech

log = logging.getLogger("jarvis.briefing_flow")

SILENT_STEP_SECONDS = 2.5  # no modo silencioso, tempo de cada card na tela

_skip: asyncio.Event | None = None  # existe só enquanto um briefing está passando


def active() -> bool:
    return _skip is not None


def skip() -> bool:
    """Pula para o próximo assunto (botão PRÓXIMO ▸ ou seta para a direita). False sem briefing ativo."""
    if _skip is None:
        return False
    _skip.set()
    tts_module.stop_playback()
    # V6.5.3: a voz pode estar tocando no celular: cala só a fala atual dele (a próxima parte segue)
    from core import voice_route

    if voice_route.playing_on_device:
        runtime.track(runtime.manager.broadcast({"type": "speech_stop", "say_id": voice_route.playing_on_device}))
    return True


async def _say(text: str) -> None:
    if not text:
        await asyncio.sleep(0.8)
        return
    if prefs.is_silent_mode():
        await asyncio.sleep(SILENT_STEP_SECONDS)
        return
    await speech.speak(text, release_busy=False, idle_after=False)


async def _say_or_skip(text: str) -> None:
    """Fala uma parte; se pedirem "próximo", corta a fala e segue."""
    if _skip is None:
        await _say(text)
        return
    _skip.clear()
    talk = asyncio.create_task(_say(text))
    skipped = asyncio.create_task(_skip.wait())
    try:
        await asyncio.wait({talk, skipped}, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for task in (talk, skipped):
            if not task.done():
                task.cancel()
        await asyncio.gather(talk, skipped, return_exceptions=True)


async def run_sequence(message: str, turn: int, data: dict, max_history: int) -> None:
    """Fala o briefing parte a parte. Libera o JARVIS (busy) ao terminar ou cancelar."""
    global _skip
    _skip = asyncio.Event()
    if data.get("mode") in ("morning", "afternoon", "evening"):
        try:  # V5.4: "bom dia" pedido por voz também conta: a próxima entrada não repete o briefing
            from modules import entry_greeting

            entry_greeting.mark_briefed()
        except Exception as exc:  # noqa: BLE001
            log.warning("Não consegui registrar o briefing do dia: %s", exc)
    try:
        segments = data["segments"]
        opening_text = " ".join(p for p in (data["greeting"], data["opening_speech"]) if p)
        if not prefs.is_silent_mode():
            # V6.5.1: gera a voz de todas as partes já (no celular, o texto inteiro, como ele pede)
            from core import voice_route

            tts_module.prefetch([opening_text, *(s["speech"] for s in segments), data.get("closing") or ""],
                                whole=voice_route.current() is not None)
        await runtime.manager.broadcast({
            "type": "briefing_start",
            "mode": data["mode"],
            "title": data["title"],
            "tabs": data["tabs"],
            "greeting": data["greeting"],
            "opening": data["opening"],
            "opening_sub": data["opening_sub"],
            "text": opening_text,
            "total": len(segments),
            "plan": [seg["card"] for seg in segments],
        })
        if opening_text:
            await _say_or_skip(opening_text)
        for index, seg in enumerate(segments):
            if speech.canceled(turn):
                return
            await runtime.manager.broadcast({
                "type": "briefing_step",
                "index": index,
                "total": len(segments),
                "tab": seg["tab"],
                "progress": seg["progress"],
                "card": seg["card"],
                "text": seg["speech"],
            })
            await _say_or_skip(seg["speech"])
        if speech.canceled(turn):
            return
        _skip = None  # a recomendação final não é pulada

        cards = [seg["card"] for seg in segments]
        await runtime.manager.broadcast({
            "type": "briefing_end",
            "cards": cards,
            "readiness": data["readiness"],
            "closing": data["closing"],
        })
        text = data["speech"]
        summary_card = {"type": "briefing", "data": {"cards": cards, "closing": data["closing"], "mode": data["mode"]}}
        session.history.extend([{"role": "user", "content": message}, {"role": "assistant", "content": text}])
        memory.add_conversation(message, text)
        del session.history[:-max_history]
        # O Canal Ativo já mostrou cada parte ao vivo; aqui entra só a recomendação com o resumo dos cards
        await runtime.manager.broadcast(
            {"type": "response", "text": data["closing"] or f"{data['opening']}: pronto.", "cards": [summary_card],
             "local": True}
        )
        if data["closing"] and not prefs.is_silent_mode():
            await speech.speak(data["closing"], release_busy=False, idle_after=False)
    except asyncio.CancelledError:
        raise
    except Exception:  # noqa: BLE001
        log.exception("Falha no briefing em etapas")
        await runtime.manager.broadcast({"type": "error", "message": "O briefing foi interrompido por uma falha."})
    finally:
        _skip = None
        tts_module.clear_prefetch()  # V6.5.1: sobras de um briefing cancelado não ficam gerando voz
        if not speech.canceled(turn):
            session.busy = False
            await runtime.manager.broadcast({"type": "state", "state": "idle"})


async def start(message: str, turn: int, max_history: int, mode: str = "morning") -> dict:
    """Monta o briefing (manhã ou fechamento da noite) e dispara a sequência em segundo plano.

    A resposta HTTP volta na hora; o conteúdo chega pelo WebSocket.
    """
    if mode.startswith("topic:"):
        from modules import briefing_topics

        data = await briefing_topics.build(mode.split(":", 1)[1])
    else:
        data = await briefing.build_for(mode)()
    if speech.canceled(turn):
        session.busy = False
        return {"status": "canceled"}
    runtime.track(run_sequence(message, turn, data, max_history))
    return {"status": "ok", "response": "", "cards": [], "source": "briefing", "briefing": data}

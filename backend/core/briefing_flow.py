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
from typing import Optional

from modules import briefing, memory, prefs
from modules import tts as tts_module
from core import runtime, session, speech

log = logging.getLogger("jarvis.briefing_flow")

SILENT_STEP_SECONDS = 2.5  # no modo silencioso, tempo de cada card na tela
# V9.5.4: no "bom dia", o briefing só começa a falar depois que a música da manhã entra (abrindo o Spotify se
# estiver fechado). Antes os dois começavam juntos e a música chegava atrasada ou nem chegava. Limite para nunca
# ficar preso: sem Spotify, ele fala na hora (e a música tenta de novo no fim).
MUSIC_START_TIMEOUT_S = 35
MUSIC_WAIT_S = 30
# V9.5.5: a música ainda não entrou depois desse tempo (o Spotify está abrindo): ele avisa antes de esperar
CONNECT_NOTICE_AFTER_S = 1.5
CONNECT_SPEECH = "Conectando ao Spotify, senhor."

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


VOICE_RETRY_S = 1.5  # V9.5.4: espera antes de tentar falar a parte de novo
MAX_READ_S = 15.0  # V9.5.4: sem voz, o cartão fica no máximo esse tempo na tela


async def _say(text: str) -> None:
    if not text:
        await asyncio.sleep(0.8)
        return
    if prefs.is_silent_mode():
        await asyncio.sleep(SILENT_STEP_SECONDS)
        return
    if await speech.speak(text, release_busy=False, idle_after=False) is not False:
        return
    # V9.5.4: a voz falhou (logo depois de ligar o PC, o serviço de voz às vezes ainda não responde). Antes a parte
    # passava na hora: clima, agenda e e-mails voavam pela tela e o briefing "pulava" direto para as notícias.
    # Agora tenta de novo e, se ainda não der, deixa o cartão na tela o tempo de ler.
    log.warning("Briefing: a voz falhou nesta parte; tentando de novo.")
    await asyncio.sleep(VOICE_RETRY_S)
    if await speech.speak(text, release_busy=False, idle_after=False) is not False:
        return
    from core import voice_route

    await asyncio.sleep(min(MAX_READ_S, voice_route.estimate_seconds(text)))


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


def _morning_music_wanted() -> bool:
    """V9.5.5: a música da manhã vai tentar tocar? (rápido: só preferências e se o Spotify está conectado)"""
    from modules import morning_music

    try:
        return bool(morning_music.wanted())
    except Exception:  # noqa: BLE001
        log.exception("Não consegui conferir a música da manhã")
        return False


async def _morning_music_start():
    """V8.14.1: Back in Black baixinho na inicialização do dia (em paralelo: o briefing não espera)."""
    from modules import morning_music

    try:
        return await asyncio.wait_for(asyncio.to_thread(morning_music.start), timeout=MUSIC_START_TIMEOUT_S)
    except Exception:  # noqa: BLE001 - a música nunca atrapalha o briefing
        log.exception("Música da manhã não começou")
        return None


async def _pause_music():
    """V8.15.1: música tocando no Spotify? Pausa para o JARVIS ler o briefing (rápido; no máximo 6 s)."""
    from modules import briefing_music

    try:
        return await asyncio.wait_for(asyncio.to_thread(briefing_music.pause_if_playing), timeout=6)
    except Exception:  # noqa: BLE001 - sem pausar, o briefing segue igual
        log.exception("Não consegui pausar a música para o briefing")
        return None


async def _resume_music(paused) -> None:
    from modules import briefing_music

    try:
        await asyncio.wait_for(asyncio.to_thread(briefing_music.resume, paused), timeout=20)
    except Exception:  # noqa: BLE001
        log.exception("Não consegui retomar a música depois do briefing")


class Music:
    """V9.4: a música do briefing começa JÁ, enquanto o briefing ainda está sendo montado.

    Antes, pausar a sua música e tocar a da manhã (Back in Black) só começava depois de montar o briefing inteiro
    (notícias, clima, e-mails, agenda...), e a música chegava muitos segundos atrasada. Agora:
      1. pausa a música que estiver tocando (V8.15.1) e avisa (pause_done), para o JARVIS não falar por cima dela;
      2. no "bom dia", sem música sua tocando, já começa a da manhã baixinho, em paralelo com a montagem.
    No fim, a música da manhã sobe de volume e a sua volta de onde parou."""

    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.paused = None
        self.plan = None
        self.pause_done = asyncio.Event()
        self.ready = asyncio.Event()  # V9.5.4: a música da manhã já entrou (ou não vai entrar)
        self.trying = False  # V9.5.5: a música da manhã vai mesmo tentar tocar (Spotify conectado, ainda não tocou hoje)
        self.task: Optional[asyncio.Task] = None

    async def _run(self) -> None:
        try:
            self.paused = await _pause_music()
        finally:
            self.pause_done.set()
        # a música da manhã (Back in Black) não entra no lugar da sua: só quando não havia nada tocando
        try:
            if self.mode == "morning" and not self.paused:
                self.trying = _morning_music_wanted()
                if self.trying:
                    self.plan = await _morning_music_start()
        finally:
            self.ready.set()

    def start(self) -> "Music":
        self.task = runtime.track(self._run())
        return self

    async def wait_ready(self, timeout: float = MUSIC_WAIT_S, say=None) -> None:
        """V9.5.4: no "bom dia", espera a música da manhã entrar antes de começar a falar (com limite).

        V9.5.5: se ela ainda não entrou depois de um instante (o Spotify está abrindo), avisa "Conectando ao
        Spotify, senhor." e espera; o briefing começa com a música já tocando."""
        if self.mode != "morning":
            return
        try:
            await asyncio.wait_for(asyncio.shield(self.ready.wait()), timeout=CONNECT_NOTICE_AFTER_S)
            return
        except asyncio.TimeoutError:
            pass
        if self.trying and say is not None:
            await say(CONNECT_SPEECH)
        try:
            await asyncio.wait_for(self.ready.wait(), timeout=max(0.0, timeout - CONNECT_NOTICE_AFTER_S))
        except asyncio.TimeoutError:
            log.warning("Briefing: a música da manhã não entrou a tempo; começo a falar sem ela.")

    async def wait_pause(self, timeout: float = 7.0) -> None:
        try:
            await asyncio.wait_for(self.pause_done.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            log.warning("Briefing: pausar a música demorou; sigo sem esperar.")

    async def finish(self, canceled: bool) -> None:
        from modules import morning_music

        try:
            if self.task is not None:
                await asyncio.wait_for(asyncio.shield(self.task), timeout=40)
        except Exception:  # noqa: BLE001 - a música nunca atrapalha o briefing
            log.exception("Música do briefing não terminou de começar")
        if self.plan is not None:
            try:
                await asyncio.wait_for(asyncio.to_thread(morning_music.finish, self.plan, canceled), timeout=20)
            except Exception:  # noqa: BLE001
                log.exception("Música da manhã não terminou")
        elif self.mode == "morning" and not self.paused and not canceled:
            # V9.5.4: a música da manhã não começou junto (Spotify ainda abrindo ou rede chegando, logo depois de
            # ligar o PC). Antes ficava sem música; agora tenta de novo no fim, já no volume de depois do briefing.
            try:
                await asyncio.wait_for(asyncio.to_thread(morning_music.start_late), timeout=40)
            except Exception:  # noqa: BLE001
                log.exception("Música da manhã não tocou nem no fim do briefing")
        if self.paused:  # V8.15.1: a sua música continua de onde parou
            await _resume_music(self.paused)


def start_music(mode: str) -> Music:
    return Music(mode).start()


async def run_sequence(message: str, turn: int, data: dict, max_history: int, music: Optional[Music] = None) -> None:
    """Fala o briefing parte a parte. Libera o JARVIS (busy) ao terminar ou cancelar."""
    global _skip
    _skip = asyncio.Event()
    music = music or start_music(data.get("mode", ""))
    await music.wait_pause()  # V8.15.1: a sua música pausa antes de ele começar a ler
    # V9.5.4/V9.5.5: no "bom dia", a música da manhã entra antes da primeira fala ("Conectando ao Spotify" se demorar)
    await music.wait_ready(say=None if prefs.is_silent_mode() else _say)
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
        # V8.14.1: sobe o volume da música da manhã (ou toca agora a que esperou); V8.15.1: a sua volta
        runtime.track(music.finish(speech.canceled(turn)))
        if not speech.canceled(turn):
            session.busy = False
            await runtime.manager.broadcast({"type": "state", "state": "idle"})


async def start(message: str, turn: int, max_history: int, mode: str = "morning") -> dict:
    """Monta o briefing (manhã ou fechamento da noite) e dispara a sequência em segundo plano.

    A resposta HTTP volta na hora; o conteúdo chega pelo WebSocket.
    """
    music = start_music("topic" if mode.startswith("topic:") else mode)  # V9.4: a música não espera a montagem
    try:
        if mode.startswith("topic:"):
            from modules import briefing_topics

            data = await briefing_topics.build(mode.split(":", 1)[1])
        else:
            data = await briefing.build_for(mode)()
    except BaseException:
        runtime.track(music.finish(True))
        raise
    if speech.canceled(turn):
        runtime.track(music.finish(True))
        session.busy = False
        return {"status": "canceled"}
    runtime.track(run_sequence(message, turn, data, max_history, music))
    return {"status": "ok", "response": "", "cards": [], "source": "briefing", "briefing": data}

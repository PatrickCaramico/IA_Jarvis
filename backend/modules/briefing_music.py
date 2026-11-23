"""V8.15.1: pausar o Spotify durante o briefing (e continuar depois).

Antes, pedir o briefing com música tocando fazia o JARVIS falar por cima dela. Agora, quando o briefing começa e o
Spotify está tocando, a música pausa; no fim (ou se o briefing for cancelado) ela continua de onde parou. Não retoma
se você mesmo trocou de música ou deu play em outra coisa no meio. Vale para todos os briefings (bom dia, boa tarde,
boa noite e por assunto); nunca no modo silencioso (lá o briefing não é falado). Desliga no painel VOZ
("Pausar a música durante o briefing") — preferência briefing_pause_music.
"""
from __future__ import annotations

import logging
from typing import Optional

from modules import prefs, spotify

log = logging.getLogger("jarvis.briefing_music")


def enabled() -> bool:
    data = prefs.get_all()
    return bool(data.get("briefing_pause_music", True)) and not data.get("silent_mode") and spotify.connected()


def pause_if_playing() -> Optional[dict]:
    """Pausa a música se estiver tocando. Devolve o que pausou ({"title": ...}) ou None."""
    if not enabled():
        return None
    try:
        now = spotify.now_playing()
        if now.get("state") != "playing":
            return None
        spotify.pause()
        log.info("Briefing: música pausada (%s).", now.get("title", ""))
        return {"title": now.get("title", "")}
    except Exception:  # noqa: BLE001 - a música nunca atrapalha o briefing
        log.exception("Briefing: não consegui pausar a música")
        return None


def resume(paused: Optional[dict]) -> bool:
    """Continua a música que o briefing pausou (se você não mexeu nela no meio). Devolve se retomou."""
    if not paused:
        return False
    try:
        now = spotify.now_playing()
        if now.get("state") == "playing":
            return False  # você já deu play em alguma coisa
        if paused.get("title") and now.get("title") and now["title"] != paused["title"]:
            return False  # trocou de música no meio: respeita
        spotify.play()
        log.info("Briefing: música retomada.")
        return True
    except Exception:  # noqa: BLE001
        log.exception("Briefing: não consegui retomar a música")
        return False

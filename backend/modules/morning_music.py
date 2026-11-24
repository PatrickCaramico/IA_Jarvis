"""V8.14.1: a música de entrada (Back in Black) na INICIALIZAÇÃO DO DIA — o briefing de "bom dia".

Antes ela só tocava nas entradas seguintes (junto da saudação curta): a 1ª entrada do dia roda o briefing e esse
caminho não chamava a música. Agora, no briefing da manhã:
  - começa a música BAIXINHO (trilha de fundo, BACKGROUND_VOLUME) para não abafar a voz do JARVIS;
  - no fim do briefing o volume sobe aos poucos até NORMAL_VOLUME;
  - se o aparelho não deixa mudar o volume, a música espera o briefing acabar (nunca por cima da fala);
  - uma vez por dia, nunca no modo silencioso e nunca por cima de uma música que você já está ouvindo.
Desliga no painel VOZ ("Tocar na inicialização do dia") — preferência intro_song_morning.
"""
from __future__ import annotations

import logging
import time
from datetime import date
from typing import Optional

from modules import prefs, spotify

log = logging.getLogger("jarvis.morning_music")

BACKGROUND_VOLUME = 25
NORMAL_VOLUME = 60  # padrão; V8.15.1: no fim sobe até o volume que você escolheu no painel VOZ (music_volume)


END_VOLUME = 80  # V9.4: no fim do briefing do dia, a música sobe ainda mais (preferência briefing_end_volume)


def _int(value, default: int) -> int:
    try:
        return int(value if value not in (None, "") else default)
    except (TypeError, ValueError):
        return default


def target_volume() -> int:
    """O volume da música depois do briefing.

    V8.15.1: subia até o volume do painel VOZ (music_volume, 60). V9.4: o senhor pediu para subir ainda mais ao fim
    do briefing do dia: vai até o maior entre o music_volume e o briefing_end_volume (80 por padrão)."""
    data = prefs.get_all()
    v = max(_int(data.get("music_volume"), NORMAL_VOLUME), _int(data.get("briefing_end_volume"), END_VOLUME))
    return max(BACKGROUND_VOLUME, min(100, v))
DEFAULT_SONG = "Back in Black AC/DC"


class Plan:
    """O que ficou combinado no começo do briefing (para o fim saber o que fazer)."""

    def __init__(self, song: str, device_id: str = "", uri: str = "", playing: bool = False, deferred: bool = False):
        self.song, self.device_id, self.uri, self.playing, self.deferred = song, device_id, uri, playing, deferred


def wanted(today: Optional[date] = None) -> Optional[str]:
    """A música a tocar nesta manhã, ou None (desligado, silencioso, sem Spotify ou já tocou hoje)."""
    data = prefs.get_all()
    today = today or date.today()
    if not data.get("intro_song_morning", True) or data.get("silent_mode") or not spotify.connected():
        return None
    if data.get("intro_song_morning_day") == today.isoformat():
        return None
    return (data.get("intro_song") or DEFAULT_SONG).strip() or None


def start(today: Optional[date] = None) -> Optional[Plan]:
    """Começo do briefing da manhã (roda numa thread). Devolve o plano, ou None se não for tocar."""
    song = wanted(today)
    if not song:
        return None
    try:
        if spotify.now_playing().get("state") == "playing":
            log.info("Música da manhã: já tem música tocando; não interrompo.")
            return None
        track = spotify.find_track(song)
        if not track:
            log.info("Música da manhã: não achei %s no Spotify.", song)
            return None
        device_id = spotify.ensure_device()
        prefs.update(intro_song_morning_day=(today or date.today()).isoformat())
        try:
            spotify.set_volume(BACKGROUND_VOLUME, device_id)
        except Exception:  # noqa: BLE001 - aparelho sem controle de volume: toca depois do briefing
            log.info("Música da manhã: o aparelho não deixa baixar o volume; toco no fim do briefing.")
            return Plan(song, device_id, track["uri"], deferred=True)
        spotify._play({"uris": [track["uri"]]}, device_id=device_id)
        return Plan(song, device_id, track["uri"], playing=True)
    except spotify.SpotifyError as exc:
        log.info("Música da manhã não tocou: %s", exc.code)
    except Exception:  # noqa: BLE001 - a música nunca atrapalha o briefing
        log.exception("Música da manhã falhou")
    return None


def finish(plan: Optional[Plan], canceled: bool = False, sleep=time.sleep) -> None:
    """Fim do briefing (thread): sobe o volume aos poucos, ou toca agora a que esperou."""
    if plan is None:
        return
    try:
        if plan.deferred:
            if not canceled:
                spotify._play({"uris": [plan.uri]}, device_id=plan.device_id)
            return
        if plan.playing:
            target = target_volume()
            for vol in range(BACKGROUND_VOLUME + 10, target + 1, 10):
                sleep(0.6)
                spotify.set_volume(vol, plan.device_id)
            spotify.set_volume(target, plan.device_id)
    except Exception:  # noqa: BLE001
        log.exception("Música da manhã: não consegui terminar (volume)")

"""Rotas das integrações Google Agenda e Spotify."""

import logging
import asyncio
import time
from fastapi import HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel
from modules import google_calendar, spotify
from fastapi import APIRouter


log = logging.getLogger("jarvis.integrations")
router = APIRouter()


class SpotifyControlRequest(BaseModel):
    action: str  # play | pause | next | previous


@router.post("/api/integrations/spotify/control")
async def spotify_control(req: SpotifyControlRequest) -> dict:
    """Controles simples de música (também liberados no modo visitante)."""
    actions = {
        "play": spotify.play,
        "pause": spotify.pause,
        "next": spotify.next_track,
        "previous": spotify.previous_track,
    }
    fn = actions.get(req.action)
    if fn is None:
        raise HTTPException(status_code=400, detail="Ação inválida. Use play, pause, next ou previous.")
    try:
        await asyncio.to_thread(fn)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        log.warning("Falha no controle do Spotify: %s", exc)
        raise HTTPException(status_code=502, detail="Não foi possível controlar o Spotify.") from exc
    return {"status": "ok"}


@router.get("/api/integrations/google-calendar/status")
async def google_calendar_status() -> dict:
    return {
        "configured": google_calendar.configured(),
        "connected": google_calendar.connected(),
    }


@router.get("/api/integrations/google-calendar/authorize")
async def google_calendar_authorize():
    try:
        return RedirectResponse(google_calendar.authorization_url())
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/api/integrations/google-calendar/callback")
async def google_calendar_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    if error:
        return HTMLResponse(
            f"<h1>Google Calendar não conectado</h1><p>{error}</p><p>Você pode fechar esta janela.</p>",
            status_code=400,
        )
    if not code or not state:
        return HTMLResponse(
            "<h1>Resposta OAuth incompleta</h1><p>Você pode fechar esta janela.</p>",
            status_code=400,
        )
    try:
        await asyncio.to_thread(google_calendar.exchange_code, code, state)
    except Exception as exc:
        log.exception("Falha no callback do Google Calendar")
        return HTMLResponse(
            f"<h1>Falha ao conectar</h1><p>{exc}</p><p>Você pode fechar esta janela.</p>",
            status_code=500,
        )
    return HTMLResponse("<h1>Google Calendar conectado</h1><p>Volte ao JARVIS. Você pode fechar esta janela.</p>")


@router.delete("/api/integrations/google-calendar")
async def google_calendar_disconnect() -> dict:
    google_calendar.disconnect()
    return {"status": "ok"}


@router.get("/api/integrations/google-calendar/events")
async def google_calendar_events() -> dict:
    try:
        events = await asyncio.to_thread(google_calendar.upcoming_events)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        log.exception("Falha ao carregar eventos do Google Calendar")
        raise HTTPException(status_code=502, detail="Não foi possível carregar o Google Calendar.") from exc
    return {"events": events}


@router.get("/api/integrations/spotify/status")
async def spotify_status() -> dict:
    return {"configured": spotify.configured(), "connected": spotify.connected()}


_TRACK_CACHE: dict = {"at": 0.0, "data": None}


@router.get("/api/integrations/spotify/track")
async def spotify_track() -> dict:
    """Faixa atual em partes para o cartão "Tocando agora" (bloqueado: só com o cartão Spotify ligado).

    V4.2.2. Com a central bloqueada, a rota confere o cartão em Configurações > Bloqueio.
    """
    from modules import access, prefs

    if access.is_restricted() and "spotify" not in (prefs.get_all().get("lock_cards") or []):
        raise HTTPException(status_code=403, detail={"code": "locked", "message": "Cartão do Spotify desligado no bloqueio."})
    if not spotify.configured() or not spotify.connected():
        return {"state": "off"}
    now = time.monotonic()
    if _TRACK_CACHE["data"] is not None and now - _TRACK_CACHE["at"] < 5:
        return _TRACK_CACHE["data"]
    try:
        data = await asyncio.to_thread(spotify.now_playing)
    except Exception as exc:  # noqa: BLE001 - sem internet ou token expirado: o cartão some
        log.debug("Spotify sem faixa atual: %s", exc)
        data = {"state": "error"}
    _TRACK_CACHE.update(at=now, data=data)
    return data


@router.get("/api/integrations/spotify/now-playing")
async def spotify_now_playing() -> dict:
    try:
        return {"track": await asyncio.to_thread(spotify.current_track)}
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        log.exception("Falha ao consultar a faixa atual do Spotify")
        raise HTTPException(status_code=502, detail="Não foi possível consultar o Spotify.") from exc


class SpotifyPlayRequest(BaseModel):
    query: str
    playlist: bool = False


@router.post("/api/integrations/spotify/play")
async def spotify_play_search(req: SpotifyPlayRequest) -> dict:
    try:
        response = await asyncio.to_thread(spotify.search_and_play, req.query, req.playlist)
        return {"response": response}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        log.exception("Falha ao buscar reprodução no Spotify")
        raise HTTPException(status_code=502, detail="Não foi possível buscar no Spotify.") from exc


@router.get("/api/integrations/spotify/authorize")
async def spotify_authorize():
    try:
        return RedirectResponse(spotify.authorization_url())
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/api/integrations/spotify/callback")
async def spotify_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    if error:
        return HTMLResponse(
            f"<h1>Spotify não conectado</h1><p>{error}</p><p>Você pode fechar esta janela.</p>",
            status_code=400,
        )
    if not code or not state:
        return HTMLResponse(
            "<h1>Resposta OAuth incompleta</h1><p>Você pode fechar esta janela.</p>",
            status_code=400,
        )
    try:
        await asyncio.to_thread(spotify.exchange_code, code, state)
    except Exception as exc:
        log.exception("Falha no callback do Spotify")
        return HTMLResponse(
            f"<h1>Falha ao conectar</h1><p>{exc}</p><p>Você pode fechar esta janela.</p>",
            status_code=500,
        )
    return HTMLResponse("<h1>Spotify conectado</h1><p>Volte ao JARVIS. Você pode fechar esta janela.</p>")


@router.delete("/api/integrations/spotify")
async def spotify_disconnect() -> dict:
    spotify.disconnect()
    return {"status": "ok"}

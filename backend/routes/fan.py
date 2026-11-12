"""Rotas do Modo Torcedor."""

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import settings
from core import runtime
from modules import fan_mode, prefs, sports_provider

router = APIRouter()


@router.get("/api/fan/news")
async def get_fan_news(limit: int = 8) -> dict:
    """Notícias recentes do clube via Google News / GE."""
    all_prefs = prefs.get_all()
    team_id = all_prefs.get("fan_team", "palmeiras")
    items = await asyncio.to_thread(fan_mode.fetch_fan_news, team_id, limit)
    team_info = fan_mode.get_team_info(team_id)
    return {"team": team_info, "items": items}


@router.get("/api/fan/match")
async def get_fan_match() -> dict:
    """Informações da partida atual ou próxima agendada do clube."""
    all_prefs = prefs.get_all()
    team_id = all_prefs.get("fan_team", "palmeiras")
    await asyncio.to_thread(sports_provider.refresh, team_id)  # só usa a rede se o cache venceu
    match_data = await asyncio.to_thread(sports_provider.get_current_or_next_match, team_id)
    team_info = fan_mode.get_team_info(team_id)
    # V4.4: próximos jogos (dados públicos, sem link de agenda) para o painel do bloqueio
    upcoming = [
        {k: s[k] for k in ("id", "opponent", "competition", "date", "date_human", "home_away", "venue")}
        for s in sports_provider.get_schedule(team_id)
        if s["id"] != match_data.get("id") and s["seconds_left"] > 0
    ][:3]
    return {"team": team_info, "match": match_data, "upcoming": upcoming}


@router.get("/api/fan/logo/{side}", response_model=None)
async def get_fan_logo(side: str):
    """Serve o escudo do Palmeiras local ou o escudo do adversário em cache."""
    side = (side or "").lower()
    if side not in {"ours", "theirs"}:
        raise HTTPException(status_code=400, detail="Lado inválido. Use 'ours' ou 'theirs'.")

    team_id = prefs.get_all().get("fan_team", "palmeiras")
    logo_path = await asyncio.to_thread(sports_provider.resolve_logo_path, team_id, side)

    if side == "ours":
        local_path = Path(settings.BASE_DIR) / "frontend" / "public" / "fan" / team_id / f"{team_id}_shield.png"
        if not logo_path and local_path.exists():
            return FileResponse(local_path, media_type="image/png")

    if not logo_path:
        return Response(status_code=204)

    return FileResponse(logo_path, media_type="image/png")


class FanToggleRequest(BaseModel):
    enabled: bool | None = None  # None = inverte


BACKGROUNDS = ("blueprint", "space", "classic")


class BackgroundRequest(BaseModel):
    style: str | None = None  # sem estilo: passa para o próximo (Blueprint -> Universo -> Clássico)


@router.post("/api/background")
async def set_background(req: BackgroundRequest | None = None) -> dict:
    """V5.9.1: troca o fundo pelo botão da tela de bloqueio.

    Pública (vale com a central bloqueada), como o botão do Modo Torcedor: só muda o visual.
    """
    current = prefs.get_all().get("background_style") or "blueprint"
    if req is not None and req.style:
        if req.style not in BACKGROUNDS:
            raise HTTPException(status_code=400, detail="Fundo inválido. Use blueprint, space ou classic.")
        style = req.style
    else:
        i = BACKGROUNDS.index(current) if current in BACKGROUNDS else 0
        style = BACKGROUNDS[(i + 1) % len(BACKGROUNDS)]
    prefs.update(background_style=style)
    return {"background_style": style}


@router.post("/api/fan/toggle")
async def toggle_fan_mode(req: FanToggleRequest | None = None) -> dict:
    """V4.4: liga/desliga o Modo Torcedor pelo botão da tela de bloqueio.

    Pública (vale com a central bloqueada): só troca o visual do clube, nada pessoal.
    Uma escolha manual conta como do usuário: o JARVIS não desliga sozinho no dia seguinte o que
    você ligou, e não religa no mesmo dia o que você desligou.
    """
    all_prefs = prefs.get_all()
    current = bool(all_prefs.get("fan_mode_enabled"))
    enabled = (not current) if req is None or req.enabled is None else bool(req.enabled)
    team_id = all_prefs.get("fan_team", "palmeiras")
    updated = prefs.update({"fan_mode_enabled": enabled})
    sports_provider.record_manual_activation(enabled, team_id)
    team_id = updated.get("fan_team", team_id)
    await runtime.manager.broadcast({"type": "prefs_updated", "fan_mode_enabled": enabled, "fan_team": team_id})
    return {"fan_mode_enabled": enabled, "fan_team": team_id}


class MatchReminderRequest(BaseModel):
    match_id: str | None = None
    minutes_before: int = 30


@router.get("/api/fan/schedule")
async def get_fan_schedule() -> dict:
    """Retorna os próximos jogos do clube com links para o Google Calendar."""
    all_prefs = prefs.get_all()
    team_id = all_prefs.get("fan_team", "palmeiras")
    await asyncio.to_thread(sports_provider.refresh, team_id)
    sched = await asyncio.to_thread(sports_provider.get_schedule, team_id)
    team_info = fan_mode.get_team_info(team_id)
    return {"team": team_info, "schedule": sched}


@router.post("/api/fan/match/reminder")
async def schedule_match_reminder(req: MatchReminderRequest) -> dict:
    """Cria um lembrete local e link do Google Agenda para a partida."""
    res = await asyncio.to_thread(sports_provider.create_match_reminder, req.match_id, req.minutes_before)
    return res

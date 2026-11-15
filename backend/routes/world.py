"""V7.11: rotas do Olho de Deus (camadas com dados reais, resumo e avisos)."""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()
log = logging.getLogger("jarvis.world")


def _coords(lat: float | None, lon: float | None) -> tuple[float | None, float | None]:
    if lat is None or lon is None:
        return None, None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise HTTPException(status_code=400, detail="Coordenadas inválidas.")
    return lat, lon


@router.get("/api/world/summary")
async def world_summary(lat: float | None = None, lon: float | None = None) -> dict:
    from modules import world_data

    lat, lon = _coords(lat, lon)
    if lat is None:
        h = await asyncio.to_thread(world_data.home)
        if not h:
            raise HTTPException(status_code=400, detail="Configure a cidade do clima.")
        lat, lon = h["lat"], h["lon"]
    return await asyncio.to_thread(world_data.summary, lat, lon)


@router.get("/api/world/home")
async def world_home() -> dict:
    from modules import world_data

    return {"home": await asyncio.to_thread(world_data.home)}


class AlertPrefs(BaseModel):
    chuva: bool | None = None
    perto: bool | None = None
    iss: bool | None = None


@router.get("/api/world/alerts")
async def world_alerts() -> dict:
    from modules import world_data

    return {"ligados": world_data.prefs()["ligados"]}


@router.post("/api/world/alerts")
async def world_alerts_set(body: AlertPrefs) -> dict:
    from modules import world_data

    return {"ligados": world_data.set_prefs(body.model_dump(exclude_none=True))}


@router.get("/api/world/{layer}")
async def world_layer(layer: str, lat: float | None = None, lon: float | None = None,
                      limit: int = Query(default=4000, ge=1, le=6000), leve: bool = False) -> dict:
    from modules import world_data

    if layer not in world_data.LAYERS:
        raise HTTPException(status_code=404, detail="Camada desconhecida.")
    lat, lon = _coords(lat, lon)
    try:
        return await asyncio.to_thread(world_data.layer, layer, lat, lon, limit, leve)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - fonte pública fora do ar
        log.info("Camada %s indisponível: %s", layer, exc)
        raise HTTPException(status_code=502, detail="A fonte desses dados não respondeu agora. Tente em instantes.") from exc

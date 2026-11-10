"""Rotas de hidratação."""

from fastapi import HTTPException
from pydantic import BaseModel
from modules import water
from fastapi import APIRouter
from core import runtime, speech

router = APIRouter()


class WaterAddRequest(BaseModel):
    ml: int = 250
    note: str = "copo de água"


class WaterGoalRequest(BaseModel):
    goal_ml: int


@router.get("/api/water")
async def get_water() -> dict:
    """Retorna o progresso hídrico de hoje."""
    return water.get_status()


@router.post("/api/water/add")
async def add_water(req: WaterAddRequest) -> dict:
    """Registra uma ingestão de água em ml."""
    try:
        before = water.get_status()
        st = water.add_intake(req.ml, req.note)
        await runtime.manager.broadcast({"type": "water_updated", "data": st, "added_ml": req.ml})
        if st["goal_reached"] and not before["goal_reached"]:
            runtime.track(speech.say_quietly("Meta de água do dia batida, senhor. Bom trabalho."))
        return st
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class WaterReminderRequest(BaseModel):
    interval_min: int | None = None  # 0 desliga; 30, 60, 90, 120, 180 ou 240
    start_hour: int | None = None
    end_hour: int | None = None


@router.post("/api/water/reminder")
async def set_water_reminder(req: WaterReminderRequest) -> dict:
    """Ajusta a frequência e o horário do lembrete de água."""
    try:
        st = water.set_reminder(req.interval_min, req.start_hour, req.end_hour)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await runtime.manager.broadcast({"type": "water_updated", "data": st})
    return st


@router.post("/api/water/undo")
async def undo_water() -> dict:
    """Desfaz o último registro de hoje."""
    st = water.undo_last()
    await runtime.manager.broadcast({"type": "water_updated", "data": st, "undo": True})
    return st


@router.post("/api/water/goal")
async def set_water_goal(req: WaterGoalRequest) -> dict:
    """Atualiza a meta diária de ingestão de água."""
    try:
        st = water.set_goal(req.goal_ml)
        await runtime.manager.broadcast({"type": "water_updated", "data": st})
        return st
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/water/reset")
async def reset_water() -> dict:
    """Zera o consumo de hoje."""
    st = water.reset_today()
    await runtime.manager.broadcast({"type": "water_updated", "data": st})
    return st

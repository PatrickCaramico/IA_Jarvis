"""V8.0: rotas do MODO DESK (aparência, nível e XP, hábitos, copiados, memória em mapa, testar a IA)."""
from __future__ import annotations

import asyncio
import logging
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from modules import desk

router = APIRouter()
log = logging.getLogger("jarvis.desk")


@router.get("/api/desk")
async def desk_get() -> dict:
    return desk.config()


@router.patch("/api/desk")
async def desk_patch(body: dict) -> dict:
    return desk.update_config(body if isinstance(body, dict) else {})


@router.get("/api/desk/xp")
async def desk_xp() -> dict:
    d = desk._load()
    return {**desk.level_info(d["xp"]["total"]), "eventos": d["xp"].get("eventos", [])[:10]}


class HabitRequest(BaseModel):
    nome: str
    icone: str = ""
    lembrete: str = ""


class HabitToggle(BaseModel):
    feito: bool | None = None


@router.get("/api/desk/habits")
async def habits_get() -> dict:
    return desk.habits()


@router.post("/api/desk/habits")
async def habits_add(req: HabitRequest) -> dict:
    try:
        out = desk.habit_add(req.nome, req.icone, req.lembrete)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await _broadcast()
    return out


@router.post("/api/desk/habits/{ref}/toggle")
async def habits_toggle(ref: str, req: HabitToggle) -> dict:
    try:
        out = desk.habit_toggle(ref, req.feito)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await _broadcast()
    return out


@router.delete("/api/desk/habits/{ref}")
async def habits_delete(ref: str) -> dict:
    try:
        out = desk.habit_remove(ref)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await _broadcast()
    return out


class ClipPause(BaseModel):
    pausado: bool


@router.get("/api/desk/clips")
async def clips_get() -> dict:
    return desk.clips()


@router.post("/api/desk/clips/pause")
async def clips_pause(req: ClipPause) -> dict:
    return desk.clip_pause(req.pausado)


@router.delete("/api/desk/clips")
async def clips_clear() -> dict:
    return desk.clip_remove(None)


@router.delete("/api/desk/clips/{item_id}")
async def clips_delete(item_id: str) -> dict:
    return desk.clip_remove(item_id)


@router.get("/api/desk/memory-map")
async def memory_map() -> dict:
    return desk.memory_map()


class ForgetRequest(BaseModel):
    texto: str


@router.post("/api/desk/memory/forget")
async def memory_forget(req: ForgetRequest) -> dict:
    """Apaga uma memória do mapa (fato, rotina ou preferência "chave: valor")."""
    from modules import memory

    texto = (req.texto or "").strip()
    if not texto:
        raise HTTPException(status_code=400, detail="Qual memória?")
    data = memory.get_memory()
    n = 0
    for cat in ("facts", "routine"):
        keep = [x for x in data.get(cat, []) if x.get("text") != texto]
        n += len(data.get(cat, [])) - len(keep)
        data[cat] = keep
    key = texto.split(": ", 1)[0]
    if ": " in texto and key in (data.get("preferences") or {}):
        data["preferences"].pop(key)
        n += 1
    if n:
        memory._save(data)
    return {"apagadas": n, **desk.memory_map()}


@router.post("/api/desk/test-ai")
async def test_ai() -> dict:
    """Cérebro (IA) › Testar esta IA: a resposta e quanto tempo levou."""
    from config import settings
    from services import llm_orchestrator

    start = time.perf_counter()
    try:
        text = await asyncio.to_thread(llm_orchestrator.ask_text, "Diga em uma frase curta uma curiosidade rápida, em português do Brasil.")
    except Exception as exc:  # noqa: BLE001
        log.info("Teste da IA falhou: %s", exc)
        raise HTTPException(status_code=502, detail=f"A IA não respondeu: {exc}"[:200]) from exc
    return {"resposta": (text or "").strip()[:400], "segundos": round(time.perf_counter() - start, 1),
            "provedor": getattr(settings, "LLM_PROVIDER", "")}


async def _broadcast() -> None:
    try:
        from core import runtime

        await runtime.manager.broadcast({"type": "desk_habits", "data": desk.habits()})
    except Exception:  # noqa: BLE001
        pass


@router.get("/api/desk/island")
async def island() -> dict:
    """V8.0: a ilha do JARVIS.exe (estado, última resposta recente, hora e aparência)."""
    from datetime import datetime

    from core import runtime

    st = runtime.ISLAND
    fresh = time.time() - float(st.get("resposta_em") or 0) < 25
    cfg = desk.config()
    return {"estado": st.get("estado", "idle"), "resposta": st.get("resposta", "") if fresh else "",
            "hora": datetime.now().strftime("%H:%M"), "avatar": cfg["avatar"], "cor": cfg["cor"], "ilha": cfg["ilha"]}

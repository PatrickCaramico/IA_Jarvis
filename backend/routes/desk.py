"""V8.0: rotas do MODO DESK (aparência, nível e XP, hábitos, copiados, memória em mapa, testar a IA)."""
from __future__ import annotations

import asyncio
import logging
import time

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from modules import desk, desk_missions

router = APIRouter()
log = logging.getLogger("jarvis.desk")


@router.get("/api/desk")
async def desk_get() -> dict:
    return desk.config()


@router.patch("/api/desk")
async def desk_patch(body: dict) -> dict:
    try:
        return desk.update_config(body if isinstance(body, dict) else {})
    except ValueError as exc:  # item do guarda-roupa ainda bloqueado
        raise HTTPException(status_code=403, detail=str(exc)) from exc


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


class TestAi(BaseModel):
    provedor: str | None = None


@router.post("/api/desk/test-ai")
async def test_ai(req: TestAi | None = None) -> dict:
    """Cérebro (IA) › Testar esta IA: a resposta e quanto tempo levou (V8.2: dá para escolher qual IA)."""
    from config import settings
    from services import llm_orchestrator

    prov = (req.provedor if req else None) or ""
    if prov and prov not in ("auto", "groq", "gemini", "openai", "anthropic"):
        raise HTTPException(status_code=400, detail="IA desconhecida.")
    start = time.perf_counter()
    try:
        pergunta = "Diga em uma frase curta uma curiosidade rápida, em português do Brasil."
        if prov:
            text = await asyncio.to_thread(llm_orchestrator.ask_with_provider, pergunta, prov)
        else:
            text = await asyncio.to_thread(llm_orchestrator.ask_text, pergunta)
    except Exception as exc:  # noqa: BLE001
        log.info("Teste da IA falhou: %s", exc)
        raise HTTPException(status_code=502, detail=f"A IA não respondeu: {exc}"[:200]) from exc
    return {"resposta": (text or "").strip()[:400], "segundos": round(time.perf_counter() - start, 1),
            "provedor": llm_orchestrator.last_provider() or getattr(settings, "LLM_PROVIDER", "")}


# --------------------------------------------------------------------------- V8.2: Cérebro (IA)
class BrainKey(BaseModel):
    provedor: str
    chave: str


@router.get("/api/brain")
async def brain_status() -> dict:
    from modules import brain_keys

    return brain_keys.status()


@router.post("/api/brain/key")
async def brain_key(req: BrainKey, request: Request) -> dict:
    """Cola a chave da Groq/Gemini: salva só no .env deste PC (pedido feito no próprio PC, central liberada)."""
    from core import runtime
    from modules import access, brain_keys, prefs

    if not runtime.is_local_conn(request) or access.is_restricted():
        raise HTTPException(status_code=403, detail="A chave só pode ser colada no próprio PC, com a central liberada.")
    try:
        out = await asyncio.to_thread(brain_keys.save_key, req.provedor, req.chave)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="IA desconhecida.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if req.provedor == "groq" and str(prefs._load().get("llm_provider") or "") != "auto":
        prefs.update({"llm_provider": "auto"})  # conectou a Groq: liga o Automático grátis
        out = brain_keys.status()
    log.info("Cérebro: chave da %s conectada.", req.provedor)
    return out


@router.delete("/api/brain/key/{provedor}")
async def brain_key_remove(provedor: str, request: Request) -> dict:
    from core import runtime
    from modules import access, brain_keys

    if not runtime.is_local_conn(request) or access.is_restricted():
        raise HTTPException(status_code=403, detail="Só no próprio PC, com a central liberada.")
    try:
        return await asyncio.to_thread(brain_keys.remove_key, provedor)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="IA desconhecida.") from exc


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
            "hora": datetime.now().strftime("%H:%M"), "avatar": cfg["avatar"], "cor": cfg["cor"], "ilha": cfg["ilha"], "tema": cfg.get("tema"),
            "desempenho": cfg["desempenho"]}


# --------------------------------------------------------------------------- V8.1: missões e ofensiva
class MissionAnswer(BaseModel):
    id: str
    resposta: str


@router.get("/api/desk/missions")
async def missions_get() -> dict:
    return desk_missions.view()


@router.post("/api/desk/missions/{ref}/done")
async def missions_done(ref: str) -> dict:
    try:
        out = desk_missions.mark_done(ref)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Missão não encontrada.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await _broadcast_missions()
    return out


@router.post("/api/desk/missions/answer")
async def missions_answer(req: MissionAnswer) -> dict:
    try:
        out = await asyncio.to_thread(desk_missions.answer, req.id, req.resposta)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Missão não encontrada.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await _broadcast_missions()
    return out


@router.post("/api/desk/missions/seen")
async def missions_seen() -> dict:
    desk_missions.seen()
    return {"ok": True}


@router.post("/api/desk/missions/track/{kind}")
async def missions_track(kind: str) -> dict:
    """O app avisa quando você abre o Holograma ou o Olho de Deus (contam para as missões de uso)."""
    if kind not in ("holograma", "olho"):
        raise HTTPException(status_code=400, detail="Ação desconhecida.")
    done = desk_missions.track(kind)
    if done:
        await _broadcast_missions()
    return {"completas": done}


async def _broadcast_missions() -> None:
    try:
        from core import runtime

        await runtime.manager.broadcast({"type": "desk_missions", "data": desk_missions.view()})
    except Exception:  # noqa: BLE001
        pass


# --------------------------------------------------------------------------- V8.4.0: voz pela Groq (ilha e app)
@router.post("/api/voice/transcribe")
async def voice_transcribe(request: Request) -> dict:
    """O 🎙 da ilha e do app do Windows manda o áudio gravado (corpo cru, audio/webm); volta o texto.

    Só para este PC (o app e a ilha rodam aqui); o áudio não é guardado."""
    from core import runtime
    from modules import voice_groq

    if not runtime.is_local_conn(request):
        raise HTTPException(status_code=403, detail="A voz pela Groq é só para o app deste PC.")
    try:  # recusa antes de ler um corpo grande demais
        size = int(request.headers.get("content-length") or 0)
    except ValueError:
        size = 0
    if size > voice_groq.MAX_BYTES:
        raise HTTPException(status_code=413, detail="Áudio grande demais. Fale um pedido mais curto.")
    data = await request.body()
    try:
        texto = await asyncio.to_thread(voice_groq.transcribe, data, request.headers.get("content-type", "audio/webm"))
    except voice_groq.VoiceError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc
    return {"texto": texto}


@router.get("/api/voice/groq")
async def voice_groq_status() -> dict:
    from modules import voice_groq

    return {"disponivel": voice_groq.available()}

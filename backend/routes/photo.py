"""V7.8: FOTO ENVIADA (galeria, clipe e arrastar). Ver modules/photo_ask.py.

POST /api/photo/ask   {image, question, mode}  -> analisar | ler | pesquisar | holograma (a foto não é gravada)
POST /api/photo/apply {acao}                   -> executa uma ação de "ler e agir" que o usuário CONFIRMOU
"""
from __future__ import annotations

import asyncio
import logging
import time

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

log = logging.getLogger("jarvis.photo")
router = APIRouter()

RATE_LIMIT = 10  # fotos por minuto por aparelho
_recent: dict[str, list[float]] = {}


def _rate(request: Request) -> None:
    who = request.headers.get("X-Jarvis-Token") or (request.client.host if request.client else "?")
    key = str(hash(who))  # não guarda a chave em memória por extenso
    now = time.monotonic()
    hits = [t for t in _recent.get(key, []) if now - t < 60]
    if len(hits) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Muitas fotos em seguida. Espere um minuto, senhor.")
    hits.append(now)
    _recent[key] = hits


class PhotoAsk(BaseModel):
    image: str
    question: str = ""
    mode: str = "auto"


@router.post("/api/photo/ask")
async def photo_ask(req: PhotoAsk, request: Request) -> dict:
    from modules import camera_ask, photo_ask
    from services import llm_orchestrator

    _rate(request)
    try:
        image = photo_ask.validate_image(req.image)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    mode = req.mode if req.mode in photo_ask.MODES else photo_ask.guess_mode(req.question)
    try:
        if mode == "analisar":
            raw = await asyncio.to_thread(llm_orchestrator.ask_with_image, camera_ask.build_prompt(req.question), image)
            text, diag = camera_ask.parse_answer(raw or "")
            return {"mode": mode, "text": text or "Não consegui ver direito, senhor.", "diagnostico": diag}
        if mode == "ler":
            raw = await asyncio.to_thread(llm_orchestrator.ask_with_image, photo_ask.read_prompt(req.question), image)
            leitura = photo_ask.parse_read(raw or "")
            return {"mode": mode, "text": leitura["fala"], "leitura": leitura}
        found = photo_ask.parse_identify(await asyncio.to_thread(
            llm_orchestrator.ask_with_image, photo_ask.identify_prompt(req.question, mode), image))
        if not found["item"]:
            return {"mode": mode, "text": "Não consegui identificar o que está na foto, senhor. Tente outra mais nítida."}
        if mode == "holograma":
            return {"mode": mode, "text": found["fala"], "holo_topic": found["consulta"], "item": found["item"]}
        answer = await asyncio.to_thread(
            llm_orchestrator.ask_text, photo_ask.search_prompt(found["item"], found["consulta"], req.question), True)
        sources = [{"name": s.get("name", ""), "url": s.get("url", "")}
                   for s in (llm_orchestrator.get_last_grounding_data().get("sources") or [])[:5] if s.get("url")]
        return {"mode": mode, "text": answer or found["fala"],
                "pesquisa": {"item": found["item"], "consulta": found["consulta"], "resposta": answer, "fontes": sources}}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - a foto não aparece no log, só o erro
        log.warning("Foto enviada: a IA falhou (%s): %s", mode, exc)
        raise HTTPException(status_code=502, detail="Não consegui analisar a foto agora.") from exc


class PhotoApply(BaseModel):
    acao: dict


@router.post("/api/photo/apply")
async def photo_apply(req: PhotoApply) -> dict:
    from modules import photo_ask, shopping

    try:
        result = await asyncio.to_thread(photo_ask.apply, req.acao)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if req.acao.get("tipo") == "compras":
        await shopping.announce()
    return {"status": "ok", "text": result}

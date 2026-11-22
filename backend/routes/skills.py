"""V8.11: rotas genéricas das Skills (uma rota serve para todas; uma skill nova não cria rota nova).

- GET  /api/skills                  catálogo (nome, permissão, se está ligada, chamadas, falhas, último erro)
- POST /api/skills/{nome}/toggle    liga/desliga ({"enabled": true|false})
- POST /api/skills/{nome}/run       roda com parâmetros ({"args": {...}}), só no próprio PC (para testar)

Todas exigem a central liberada (modules/access.py nega por padrão as rotas que não estão na lista pública).
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from core import runtime
from core.skills import executor, registry
from core.skills.base import SkillContext

router = APIRouter()


class ToggleRequest(BaseModel):
    enabled: bool


class RunRequest(BaseModel):
    args: Optional[dict[str, Any]] = None


@router.get("/api/skills")
async def list_skills() -> dict:
    return {"items": registry.catalog(), "errors": registry.errors()}


@router.post("/api/skills/{name}/toggle")
async def toggle_skill(name: str, req: ToggleRequest) -> dict:
    if not registry.set_enabled(name, req.enabled):
        raise HTTPException(status_code=404, detail="Habilidade não encontrada.")
    return {"name": name, "enabled": req.enabled}


@router.post("/api/skills/{name}/run")
async def run_skill(name: str, req: RunRequest, request: Request) -> dict:
    if not runtime.is_local_conn(request):
        raise HTTPException(status_code=403, detail="Testar habilidades só pelo próprio computador.")
    if registry.get(name) is None:
        raise HTTPException(status_code=404, detail="Habilidade não encontrada.")
    result = await executor.execute(name, req.args or {}, SkillContext(origin="api"))
    return {"ok": result.ok, "pending": result.pending, "speech": result.speech, "cards": result.cards,
            "data": result.data, "url": result.url}

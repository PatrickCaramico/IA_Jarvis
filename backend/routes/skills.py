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
    # V8.11: a tela do Modo Desk já perguntou "Fechar o Discord?" (botão + confirmação na própria tela).
    # Só vale para pedido do próprio PC (a rota recusa os outros) e continua passando pelas outras regras.
    confirm: bool = False
    # V8.11: texto livre ("5 milhas em km"): os parâmetros saem do reconhecedor da própria skill
    text: Optional[str] = None


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
    sk = registry.get(name)
    if sk is None:
        raise HTTPException(status_code=404, detail="Habilidade não encontrada.")
    args = dict(req.args or {})
    if req.text and not args:
        from modules.quick_replies import _norm

        parsed = registry.parse_with(sk, _norm(req.text), req.text)
        if parsed is None:
            return {"ok": False, "pending": False, "speech": "Não entendi esse pedido para essa função.", "cards": [],
                    "data": None, "url": ""}
        args = parsed
    result = await executor.execute(name, args, SkillContext(origin="api", message=req.text or "",
                                                               confirmed=bool(req.confirm)))
    return {"ok": result.ok, "pending": result.pending, "speech": result.speech, "cards": result.cards,
            "data": result.data, "url": result.url}

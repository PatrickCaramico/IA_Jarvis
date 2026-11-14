"""V7.6: SEGURANÇA. Chave por aparelho, aprovação de aparelho novo no PC e lista de aparelhos.

- POST /api/security/claim: o aparelho (com a chave do QR) pede a própria chave;
- GET  /api/security/claim: o aparelho pergunta se já foi aprovado;
- GET  /api/security/pending e POST /api/security/pending/{id}: SÓ a tela do próprio PC aprova ou recusa;
- GET  /api/security/devices, DELETE /api/security/devices/{id}, POST /api/security/disconnect-all.
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from core import runtime

log = logging.getLogger("jarvis.security")
router = APIRouter()

KIND_LABEL = {"celular": "celular", "tablet": "tablet", "tv": "TV", "pc": "computador", "outro": "aparelho"}


def _ip(request: Request) -> str:
    return request.client.host if request.client else "?"


def _require_local(request: Request) -> None:
    if not runtime.is_local_conn(request):
        raise HTTPException(status_code=403, detail="Só a tela do próprio PC pode fazer isso.")


class ClaimRequest(BaseModel):
    name: str = ""
    kind: str = "outro"


@router.post("/api/security/claim")
async def claim(req: ClaimRequest, request: Request) -> dict:
    from modules import device_access

    if runtime.is_local_conn(request):
        return {"status": "local"}  # o próprio PC não precisa de chave
    token = request.headers.get("X-Jarvis-Token") or request.query_params.get("token") or ""
    kind, _ = device_access.classify(token)
    if kind != "pairing":
        raise HTTPException(status_code=403, detail="Use o QR code do JARVIS para pedir acesso.")
    result = await asyncio.to_thread(device_access.claim, req.name.strip(), req.kind, _ip(request))
    if result["status"] == "pending":
        name = req.name.strip() or "Aparelho"
        await runtime.manager.send_local({"type": "device_request", "items": device_access.pending_requests()})
        from core import speech

        runtime.track(speech.say_quietly(
            f"Senhor, um {KIND_LABEL.get(req.kind, 'aparelho')} novo quer se conectar ao JARVIS: {name}. Permito?"))
    return result


@router.get("/api/security/claim")
async def claim_status(id: str = "", secret: str = "") -> dict:  # noqa: A002 - nome na URL
    from modules import device_access

    return await asyncio.to_thread(device_access.claim_status, id, secret)


@router.get("/api/security/pending")
async def pending(request: Request) -> dict:
    from modules import device_access

    _require_local(request)
    return {"items": device_access.pending_requests()}


class DecisionRequest(BaseModel):
    approve: bool


@router.post("/api/security/pending/{req_id}")
async def decide(req_id: str, req: DecisionRequest, request: Request) -> dict:
    from modules import device_access

    _require_local(request)
    if not await asyncio.to_thread(device_access.decide, req_id, req.approve):
        raise HTTPException(status_code=404, detail="Esse pedido já expirou. Peça para o aparelho tentar de novo.")
    await runtime.manager.send_local({"type": "device_request", "items": device_access.pending_requests()})
    return {"status": "ok", "approved": req.approve}


@router.get("/api/security/devices")
async def devices(request: Request) -> dict:
    from modules import device_access

    token = request.headers.get("X-Jarvis-Token") or request.query_params.get("token") or ""
    kind, me = device_access.classify(token)
    return {
        "devices": [d | {"this": bool(me and d["id"] == me["id"])} for d in device_access.list_devices()],
        "pending": device_access.pending_requests() if runtime.is_local_conn(request) else [],
        "migration": device_access.migration_active(),
        "migration_until": device_access._load()["migration_until"],  # noqa: SLF001
        "events": device_access.recent_events(24, ("info", "warn", "alert"))[:30],
        "local": runtime.is_local_conn(request),
    }


@router.delete("/api/security/devices/{dev_id}")
async def remove_device(dev_id: str) -> dict:
    from modules import device_access

    if not await asyncio.to_thread(device_access.remove, dev_id):
        raise HTTPException(status_code=404, detail="Aparelho não encontrado.")
    return {"status": "ok", "devices": device_access.list_devices()}


@router.post("/api/security/disconnect-all")
async def disconnect_all(request: Request) -> dict:
    from modules import device_access

    _require_local(request)
    count = await asyncio.to_thread(device_access.remove_all)
    return {"status": "ok", "removed": count}


@router.post("/api/security/end-migration")
async def end_migration(request: Request) -> dict:
    """Encerra já a migração automática (a partir daqui, aparelho novo só entra com aprovação)."""
    from modules import device_access

    _require_local(request)
    await asyncio.to_thread(device_access.end_migration)
    return {"status": "ok"}


# --------------------------------------------------------------------------- V7.7: https na rede de casa
@router.get("/api/security/https")
async def https_status() -> dict:
    from modules import tls

    return await asyncio.to_thread(tls.status)


class HttpsRequest(BaseModel):
    on: bool


@router.post("/api/security/https")
async def https_toggle(req: HttpsRequest, request: Request) -> dict:
    """Liga/desliga a conexão criptografada. Só a tela do PC. O JARVIS reinicia para valer."""
    from modules import self_update, tls

    _require_local(request)
    await asyncio.to_thread(tls.set_enabled, req.on)
    from modules import device_access

    device_access.add_event("warn", "Conexão criptografada (https) " + ("LIGADA" if req.on else "DESLIGADA") + " na rede de casa.")
    restarting = await asyncio.to_thread(self_update.restart)
    return {"status": "ok", "enabled": req.on, "restarting": restarting, **(await asyncio.to_thread(tls.status))}

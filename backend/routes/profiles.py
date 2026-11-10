"""V4.5: rotas dos perfis por pessoa (rosto + PIN, guardados só neste PC)."""

import asyncio
import base64
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core import speech
from modules import access, face, lock_log, lock_pin, profiles

log = logging.getLogger("jarvis.profiles")
router = APIRouter()


class NewProfileRequest(BaseModel):
    name: str
    photo: str                     # data URL ou base64 (JPEG/PNG), com exatamente um rosto
    pin: str | None = None         # PIN da pessoa nova (opcional, 4 a 8 dígitos)
    owner_pin: str | None = None   # PIN do dono: autoriza criar pela tela de bloqueio


@router.get("/api/profiles/lock-info")
async def lock_info() -> dict:
    """Pública (tela de bloqueio): só diz se dá para criar e se pede o PIN do dono. Nenhum nome."""
    owner_has_pin = (profiles._base(profiles.OWNER_ID) / "lock_pin.json").exists()  # noqa: SLF001
    return {
        "count": profiles.count(),
        "can_create": profiles.count() < profiles.MAX_PROFILES,
        "owner_pin_required": owner_has_pin and not (access.get_state() == access.UNLOCKED and profiles.is_owner_active()),
    }


@router.get("/api/profiles")
async def list_all() -> dict:
    """Com a central liberada: lista as pessoas deste PC."""
    return {"profiles": profiles.list_profiles(), "active": profiles.active_id(), "max": profiles.MAX_PROFILES}


@router.post("/api/profiles")
async def create_profile(req: NewProfileRequest) -> dict:
    """Cria o perfil de uma pessoa nova, entra com ele e libera a central para a configuração inicial."""
    owner_inside = access.get_state() == access.UNLOCKED and profiles.is_owner_active()
    if not owner_inside and not await asyncio.to_thread(profiles.owner_pin_ok, req.owner_pin):
        lock_log.add("profile", "fail")
        raise HTTPException(status_code=403, detail="PIN do perfil principal incorreto.")
    if req.pin:
        try:
            lock_pin.validate_format(req.pin)
        except lock_pin.PinError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        image = base64.b64decode(req.photo.split(",", 1)[-1])
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Foto inválida.") from exc

    try:
        pid = profiles.create(req.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    profiles.activate(pid)
    try:
        await asyncio.to_thread(face.save_profile, image, req.name)
        if req.pin:
            await asyncio.to_thread(lock_pin.set_pin, req.pin)
    except (ValueError, lock_pin.PinError) as exc:
        profiles.delete(pid)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    lock_log.add("profile", "ok")
    snap = access.unlock("new_profile")  # mantém o perfil novo ativo
    await speech.broadcast_access()
    log.info("Perfil novo criado: %s", pid)
    return {"profile": pid, "name": face.get_name(), "access": snap, "first_run": True}


@router.delete("/api/profiles/{profile_id}")
async def delete_profile(profile_id: str) -> dict:
    """Só o dono, com a central liberada, remove perfis (a pasta da pessoa é apagada)."""
    if not profiles.is_owner_active():
        raise HTTPException(status_code=403, detail="Só o perfil principal remove pessoas.")
    try:
        profiles.delete(profile_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"profiles": profiles.list_profiles()}

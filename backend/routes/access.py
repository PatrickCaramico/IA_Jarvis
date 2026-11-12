"""Rotas de acesso: verificação facial, PIN, visitante, registro de bloqueio e entrada."""

import logging
import asyncio
import base64
import time
from typing import Any, Optional
from fastapi import HTTPException, Request
from pydantic import BaseModel
from config import settings
from modules import face, prefs, spotify, sports_provider, water
from modules import access, lock_log, lock_pin, profiles
from modules import tts as tts_module
from fastapi import APIRouter
from core import runtime, session, speech

log = logging.getLogger("jarvis.access")
router = APIRouter()


class VerifyRequest(BaseModel):
    mode: str = "login"  # "login" | "recheck" (reverificação por palma, já logado)
    trigger: str = "button"  # "button" | "clap" | "wake" (só para o registro de tentativas)


def _thumbnail(jpeg: bytes, width: int = 200) -> bytes:
    """Miniatura pequena para o registro opcional de tentativas (lock_save_failed_photo)."""
    try:
        import cv2
        import numpy as np

        img = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return b""
        h, w = img.shape[:2]
        if w > width:
            img = cv2.resize(img, (width, int(h * width / w)))
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 70])
        return buf.tobytes() if ok else b""
    except Exception:  # noqa: BLE001
        return b""


@router.post("/api/auth/verify")
async def auth_verify(req: Optional[VerifyRequest] = None) -> dict:
    """Olha pela webcam, compara com a foto de perfil e fala a saudação.

    Durante a verificação, envia a câmera ao vivo (face_frame) SOMENTE para conexões locais.
    mode="recheck": reverificação por palma com a central já aberta (fala só uma confirmação curta).
    O contrato de resposta continua: verified, name, message.
    """
    req = req or VerifyRequest()
    mode = req.mode if req.mode in {"login", "recheck"} else "login"
    trigger = req.trigger if req.trigger in {"button", "clap", "wake"} else "button"
    if not face.has_profile():
        raise HTTPException(status_code=404, detail="Nenhuma foto de perfil cadastrada.")

    if session.auth_lock.locked():
        raise HTTPException(
            status_code=409,
            detail="Verificação facial já em andamento. Aguarde um instante.",
        )
    if mode == "recheck" and session.busy:
        raise HTTPException(status_code=409, detail="O JARVIS está ocupado.")

    async with session.auth_lock:
        # Interrompe qualquer reprodução de voz anterior para liberar o processo de autenticação
        tts_module.stop_playback()
        session.busy = True
        await runtime.manager.broadcast({"type": "state", "state": "processing"})
        await runtime.manager.send_local({"type": "face_scan_start", "mode": mode, "trigger": trigger})

        loop = asyncio.get_running_loop()
        pending: dict[str, Any] = {"future": None, "last_jpeg": None}

        def on_frame(frame: dict) -> None:
            """Roda na thread da câmera: entrega o quadro ao loop sem acumular fila."""
            if frame.get("saw_face"):
                pending["last_jpeg"] = frame["jpeg"]
            fut = pending["future"]
            if fut is not None and not fut.done() and frame.get("phase") not in {"verified", "failed"}:
                return  # o quadro anterior ainda está sendo enviado: pula este
            event = {
                "type": "face_frame",
                "jpeg": base64.b64encode(frame["jpeg"]).decode("ascii"),
                "box": frame.get("box"),
                "score": frame.get("score", 0.0),
                "threshold": settings.FACE_THRESHOLD,
                "phase": frame.get("phase", "searching"),
                "mode": mode,
            }
            pending["future"] = asyncio.run_coroutine_threadsafe(runtime.manager.send_local(event), loop)

        # V4.5: no login, reconhece entre todas as pessoas do PC; na reverificação, só quem está dentro
        refs = profiles.face_refs() if mode == "login" and profiles.count() > 1 else None
        try:
            args = (None, on_frame, refs) if refs else (None, on_frame)
            result = await asyncio.to_thread(face.verify_against_profile, *args)
        except Exception as exc:  # noqa: BLE001
            session.busy = False
            log.exception("Falha na verificação facial")
            await runtime.manager.send_local(
                {
                    "type": "face_scan_end",
                    "verified": False,
                    "mode": mode,
                    "error": True,
                }
            )
            await runtime.manager.broadcast({"type": "state", "state": "idle"})
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        # Garante que o último quadro chegue antes do fim da verificação
        if pending["future"] is not None:
            try:
                await asyncio.wait_for(asyncio.wrap_future(pending["future"]), timeout=1.0)
            except Exception:  # noqa: BLE001
                pass
        if result["verified"] and mode == "login" and refs:
            profiles.activate(result.get("profile_id") or profiles.OWNER_ID)
        name = face.get_name()
        method = "clap" if trigger == "clap" else "wake" if trigger == "wake" else "face"
        lock_log.add(
            method,
            "ok" if result["verified"] else "fail",
            result.get("score"),
            mode=mode,
        )
        failures_note = ""
        if result["verified"]:
            session.face_ok_at = time.monotonic()  # V5.1: libera "Esqueci o PIN" por alguns minutos
            if mode == "login":
                access.unlock(method)
                failures = lock_log.failures_before_last_success()
                if failures:
                    failures_note = (
                        f" Houve {failures} tentativa{'s' if failures != 1 else ''} não "
                        f"reconhecida{'s' if failures != 1 else ''} desde o último acesso."
                    )
                who = f", {name}" if name else ""
                from modules import entry_greeting

                if entry_greeting.briefing_pending():
                    # V6.1: o briefing vem logo em seguida com "Bom dia, Patrick..."; aqui só confirma
                    message = f"Identidade confirmada{who}.{failures_note}"
                else:
                    message = f"Olá, {speech.time_greeting().lower()}{who}. Tudo bem?{failures_note}"
            else:
                message = f"Identidade confirmada{', ' + name if name else ''}."
        else:
            if prefs.get_all().get("lock_save_failed_photo") and result["saw_face"] and pending["last_jpeg"]:
                lock_log.save_intruder(_thumbnail(pending["last_jpeg"]))
            if mode == "recheck":
                message = "Rosto não reconhecido."
                if prefs.get_all().get("clap_relock_on_fail") and access.enforcement_active():
                    access.lock("recheck_fail")
            elif not result["saw_face"]:
                message = "Não consegui ver o seu rosto. Chegue mais perto da câmera e tente de novo."
            else:
                message = "Não reconheci você. Quer tentar de novo?"

        await runtime.manager.send_local({"type": "face_scan_end", "verified": result["verified"], "mode": mode})
        await speech.broadcast_access()
        # Libera busy ao final da fala de feedback
        runtime.track(speech.speak(message, release_busy=True))
        return {
            "verified": result["verified"],
            "name": name if result["verified"] else "",
            "message": message,
            "mode": mode,
            "failures_since_last": failures_note != "",
            "access": access.snapshot(),
            "profile": profiles.active_id(),
        }


# ---------------------------------------------------------------- acesso: PIN, bloqueio e visitante
class PinRequest(BaseModel):
    pin: str


class PinSetRequest(BaseModel):
    new_pin: str
    current_pin: str | None = None


class PinDeleteRequest(BaseModel):
    current_pin: str


class PinResetRequest(BaseModel):
    new_pin: str


PIN_RESET_WINDOW_S = 180  # o rosto confirmado vale por 3 minutos para criar o PIN novo


@router.get("/api/access")
async def get_access() -> dict:
    return access.snapshot()


@router.post("/api/access/lock")
async def lock_access() -> dict:
    """Volta para a tela de bloqueio (botão sair, bloqueio por ausência ou F5)."""
    if access.get_state() == access.UNLOCKED:
        lock_log.add("auto", "lock")
    snap = access.lock("manual")
    await speech.broadcast_access()
    return snap


@router.get("/api/auth/pin/status")
async def pin_status() -> dict:
    return lock_pin.status()


class DeviceEnrollRequest(BaseModel):
    name: str = "Celular"


class DeviceUnlockRequest(BaseModel):
    secret: str


@router.post("/api/auth/device/enroll")
async def device_enroll(req: DeviceEnrollRequest) -> dict:
    """V6.0: cria a chave do aparelho para entrar com a digital (só com a central liberada)."""
    from modules import device_keys

    return await asyncio.to_thread(device_keys.enroll, req.name)


@router.post("/api/auth/device/unlock")
async def device_unlock(req: DeviceUnlockRequest) -> dict:
    """V6.0: o app manda a chave do aparelho depois que a digital confirma. Libera como o PIN."""
    from modules import device_keys

    key = await asyncio.to_thread(device_keys.verify, req.secret)
    if not key:
        lock_log.add("device", "fail")
        await asyncio.sleep(1.0)  # sem pressa para quem tenta adivinhar
        return {"verified": False, "message": "Esta digital não está mais ligada ao JARVIS. Entre com o PIN e ative de novo."}
    if profiles.count() > 1:
        profiles.activate_owner()
    lock_log.add("device", "ok")
    access.unlock("device")
    await speech.broadcast_access()
    name = face.get_name()
    from modules import entry_greeting

    if not entry_greeting.briefing_pending():
        runtime.track(speech.speak(f"Olá, {speech.time_greeting().lower()}{', ' + name if name else ''}."))
    return {"verified": True, "name": name, "message": f"Acesso liberado pela digital{', ' + name if name else ''}."}


@router.get("/api/auth/device")
async def device_list() -> dict:
    from modules import device_keys

    return {"items": device_keys.list_keys()}


@router.delete("/api/auth/device")
async def device_revoke(key_id: Optional[str] = None) -> dict:
    """Esquece a digital de um aparelho (ou de todos, sem key_id)."""
    from modules import device_keys

    return {"removed": device_keys.revoke(key_id)}


@router.post("/api/auth/pin")
async def pin_verify(req: PinRequest) -> dict:
    # V4.5: com várias pessoas, descobre de quem é o PIN sem gastar tentativas; as tentativas
    # erradas contam sempre no PIN do perfil principal (um único limite para o PC todo).
    if profiles.count() > 1 and access.get_state() != access.UNLOCKED:
        profiles.activate_owner()
        if lock_pin.status().get("locked_until"):
            return {"verified": False, "reason": "locked_out", "remaining_attempts": 0,
                    "locked_until": lock_pin.status()["locked_until"], "name": "",
                    "message": "PIN bloqueado temporariamente por excesso de tentativas."}
        owner = await asyncio.to_thread(profiles.match_pin, req.pin)
        if owner and owner != profiles.OWNER_ID:
            profiles.activate(owner)
        elif not owner and not lock_pin.has_pin():
            # Dono sem PIN e nenhum outro PIN bateu: não há contador para gastar, só recusa
            return {"verified": False, "reason": "wrong", "remaining_attempts": lock_pin.MAX_ATTEMPTS,
                    "locked_until": None, "name": "", "message": "PIN incorreto."}
    result = await asyncio.to_thread(lock_pin.verify, req.pin)
    if result["reason"] == "no_pin":
        raise HTTPException(status_code=404, detail="Nenhum PIN cadastrado.")
    if result["verified"]:
        lock_log.add("pin", "ok")
        access.unlock("pin")
        failures = lock_log.failures_before_last_success()
        await speech.broadcast_access()
        name = face.get_name()
        note = (
            (
                f" Houve {failures} tentativa{'s' if failures != 1 else ''} não reconhecida{'s' if failures != 1 else ''}"
                " desde o último acesso."
            )
            if failures
            else ""
        )
        message = f"Acesso liberado por PIN{', ' + name if name else ''}.{note}"
        runtime.track(speech.speak(message))
        return {**result, "name": name, "message": message}
    lock_log.add("pin", "locked_out" if result["reason"] == "locked_out" else "fail")
    if result["reason"] == "locked_out":
        message = "PIN bloqueado temporariamente por excesso de tentativas."
    else:
        message = f"PIN incorreto. Restam {result['remaining_attempts']} tentativas."
    return {**result, "name": "", "message": message}


@router.post("/api/auth/pin/set")
async def pin_set(req: PinSetRequest) -> dict:
    try:
        st = await asyncio.to_thread(lock_pin.set_pin, req.new_pin, req.current_pin)
    except lock_pin.PinError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {**st, "weak": lock_pin.is_weak(req.new_pin)}


@router.post("/api/auth/pin/reset")
async def pin_reset(req: PinResetRequest, request: Request) -> dict:
    """V5.1 "Esqueci o PIN": cria um PIN novo sem o atual, logo depois de confirmar o rosto.

    Só no próprio PC (o rosto é lido pela webcam dele) e só até 3 min depois da confirmação.
    Vale para a pessoa ativa (o rosto escolheu o perfil).
    """
    client = request.client.host if request.client else ""
    if client not in {"127.0.0.1", "::1", "localhost", "testclient"}:
        raise HTTPException(status_code=403, detail="Redefinir o PIN só pode ser feito no próprio PC.")
    if not session.face_ok_at or time.monotonic() - session.face_ok_at > PIN_RESET_WINDOW_S:
        raise HTTPException(status_code=403, detail="Confirme o seu rosto primeiro (botão Esqueci o PIN).")
    try:
        st = await asyncio.to_thread(lock_pin.reset_pin, req.new_pin)
    except lock_pin.PinError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    session.face_ok_at = 0.0  # uma redefinição por confirmação
    lock_log.add("face", "pin_reset")
    return {**st, "weak": lock_pin.is_weak(req.new_pin)}


@router.delete("/api/auth/pin")
async def pin_delete(req: PinDeleteRequest) -> dict:
    try:
        return await asyncio.to_thread(lock_pin.clear_pin, req.current_pin)
    except lock_pin.PinError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/guest/enter")
async def guest_enter() -> dict:
    """Modo visitante: só relógio, clima e música. As rotas pessoais passam a responder 403."""
    if not prefs.get_all().get("lock_guest_enabled"):
        raise HTTPException(status_code=403, detail="O modo visitante está desligado nas configurações.")
    snap = access.enter_guest()
    lock_log.add("guest", "enter")
    await speech.broadcast_access()
    runtime.track(speech.speak("Modo visitante ativado. Relógio, clima e música disponíveis."))
    return snap


@router.post("/api/guest/exit")
async def guest_exit() -> dict:
    """Sai do modo visitante para a tela de bloqueio (liberar exige rosto ou PIN)."""
    snap = access.exit_guest()
    lock_log.add("guest", "exit")
    await speech.broadcast_access()
    return snap


@router.get("/api/lock/log")
async def get_lock_log(limit: int = 50) -> dict:
    return {
        "entries": lock_log.list_entries(limit),
        "intruder_photos": len(list(lock_log.INTRUDERS_DIR.glob("*.jpg"))) if lock_log.INTRUDERS_DIR.exists() else 0,
    }


@router.delete("/api/lock/log")
async def clear_lock_log() -> dict:
    lock_log.clear()
    removed = lock_log.clear_intruders()
    return {"status": "ok", "intruder_photos_removed": removed}


@router.get("/api/presence")
async def presence() -> dict:
    """Quantas páginas do JARVIS estão abertas (usado pelo Ouvinte de Palmas). Sem dados sensíveis."""
    return {"clients": len(runtime.manager.connections)}


@router.get("/api/face/present")
async def face_present() -> dict:
    """Checagem rápida de presença (bloqueio por ausência): só detecta rosto, não compara nem salva."""
    if session.busy or session.auth_lock.locked():
        raise HTTPException(status_code=409, detail="Câmera ocupada agora.")
    try:
        seen = await asyncio.to_thread(face.detect_presence, 1.2)
    except Exception as exc:  # noqa: BLE001
        log.warning("Checagem de presença falhou: %s", exc)
        raise HTTPException(status_code=503, detail="Câmera indisponível para a checagem de presença.") from exc
    return {"face_seen": seen}


class EnterRequest(BaseModel):
    silent: bool = False  # o frontend fala a saudação/resumo do dia por conta própria


@router.post("/api/enter")
async def enter(req: Optional[EnterRequest] = None) -> dict:
    """Chamado quando o usuário entra na tela principal."""
    if not (req and req.silent):
        runtime.track(speech.speak("Em que posso ajudar?", release_busy=True))
    return {"status": "ok"}


@router.get("/api/lock/status")
async def lock_status() -> dict:
    """V5.6.1: cartão "SISTEMAS" do lado esquerdo do bloqueio. Nada pessoal: quantos aparelhos estão
    conectados (sem nomes) e a HORA do próximo alarme (sem o rótulo)."""
    from datetime import datetime

    from core import runtime
    from modules import alarms
    from modules.when import describe

    devices = runtime.manager.devices()
    phones = sum(1 for d in devices if d["kind"] in ("app", "browser"))
    next_alarm = None
    try:
        items = alarms.list_alarms()
        if items:
            at = datetime.strptime(items[0]["proximo"], "%Y-%m-%d %H:%M")
            next_alarm = describe(at, None, datetime.now())
    except Exception:  # noqa: BLE001 - sem alarmes legíveis: o cartão só não mostra a linha
        next_alarm = None
    return {"devices": len(devices), "phones": phones, "next_alarm": next_alarm}


_PUBLIC_INFO: dict = {"at": 0.0, "data": None}


@router.get("/api/lock/public-info")
async def lock_public_info() -> dict:
    """V5.8: lado direito do bloqueio: cotações (dólar, euro, bitcoin) e a manchete do momento.
    Só informação pública; cache de 10 min. Fonte que falhar fica de fora (o cartão some)."""
    from modules import news_radar
    from services import quotes

    now = time.monotonic()
    if _PUBLIC_INFO["data"] is not None and now - _PUBLIC_INFO["at"] < 600:
        return _PUBLIC_INFO["data"]

    async def rates() -> list[dict]:
        try:
            return quotes.summarize(await asyncio.to_thread(quotes.fetch_rates))
        except Exception as exc:  # noqa: BLE001
            log.debug("Bloqueio: cotações indisponíveis: %s", exc)
            return []

    async def headline() -> Optional[dict]:
        for category in ("brasil", "mundo"):
            try:
                items = await asyncio.to_thread(news_radar.fetch_news_by_category, category, 3)
            except Exception as exc:  # noqa: BLE001
                log.debug("Bloqueio: manchete indisponível (%s): %s", category, exc)
                continue
            if items:
                top = items[0]
                return {"title": top.get("title", ""), "source": top.get("source", ""),
                        "published": top.get("published", ""), "category": category,
                        # V5.9: mais manchetes para a janela de detalhes
                        "more": [{"title": i.get("title", ""), "source": i.get("source", "")} for i in items[1:3]]}
        return None

    r, h = await asyncio.gather(rates(), headline())
    data = {"rates": r, "headline": h}
    if r or h:
        _PUBLIC_INFO.update(at=now, data=data)
    return data


@router.get("/api/lock/summary-data")
async def lock_summary_data() -> dict:
    """Dados extras do resumo do dia (seção 17.3): próximo jogo (Modo Torcedor) e água de ontem."""
    all_prefs = prefs.get_all()
    out: dict[str, Any] = {"fan_match": None, "water_yesterday": None}
    if all_prefs.get("fan_mode_enabled"):
        try:
            out["fan_match"] = await asyncio.to_thread(
                sports_provider.get_current_or_next_match,
                all_prefs.get("fan_team", "palmeiras"),
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("Resumo: jogo indisponível (%s)", exc)
    try:
        out["water_yesterday"] = water.get_day_total(1)
    except Exception as exc:  # noqa: BLE001
        log.warning("Resumo: água de ontem indisponível (%s)", exc)
    return out


class IntroMusicRequest(BaseModel):
    wait_speech: bool = True


async def _play_intro_music(uri: str, wait_speech: bool) -> None:
    """Espera a saudação terminar e inicia a playlist com o volume subindo aos poucos."""
    if wait_speech:
        await asyncio.sleep(1.0)
        deadline = time.monotonic() + 40
        while (session.speaking or session.busy) and time.monotonic() < deadline:
            await asyncio.sleep(0.5)
    try:
        await asyncio.to_thread(spotify.play_playlist, uri, True)
    except Exception as exc:  # noqa: BLE001 - sem Premium, sem dispositivo ativo etc.: ignora em silêncio
        log.info("Música de abertura não iniciada: %s", exc)
        await runtime.manager.broadcast({"type": "notice", "text": "Música de abertura indisponível (Spotify)."})


@router.post("/api/lock/intro-music")
async def lock_intro_music(req: Optional[IntroMusicRequest] = None) -> dict:
    """Som/música de abertura (seção 17.7): só depois do login, nunca no modo silencioso."""
    all_prefs = prefs.get_all()
    if all_prefs.get("silent_mode"):
        return {"status": "skipped", "reason": "silent_mode"}
    uri = (
        (all_prefs.get("fan_intro_playlist_uri") if all_prefs.get("fan_mode_enabled") else "")
        or all_prefs.get("lock_intro_playlist_uri")
        or ""
    )
    if not uri:
        return {"status": "skipped", "reason": "no_playlist"}
    if not spotify.connected():
        return {"status": "skipped", "reason": "spotify_not_connected"}
    runtime.track_service(_play_intro_music(uri, (req or IntroMusicRequest()).wait_speech))
    return {"status": "scheduled"}

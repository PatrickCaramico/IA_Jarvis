"""Rotas de sistema: saúde, token, rede, cancelar, chat, fala, câmeras, logs e WebSocket."""

import logging
import asyncio
import socket
import secrets
from fastapi import HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from config import settings
from modules import face, tools, prefs, event_log, self_update
from modules import access
from modules import tts as tts_module
from services.llm_orchestrator import get_quota_cooldown
from fastapi import APIRouter
from core import runtime, session, speech, turns
from version import VERSION

log = logging.getLogger("jarvis.system")
router = APIRouter()


# ---------------------------------------------------------------- rotas
class ChatRequest(BaseModel):
    message: str


class TriggerRequest(BaseModel):
    message: str = "Bom dia"


@router.get("/api/health")
async def health() -> dict:
    provider, personality = prefs.get_llm_config()
    in_cooldown, remaining = get_quota_cooldown()
    return {
        "status": "ok",
        "version": VERSION,
        "boot_id": self_update.BOOT_ID,  # muda a cada início: a central sabe quando a atualização subiu
        "provider": provider,
        "personality": personality,
        "busy": session.busy,
        "has_profile": face.has_profile(),
        "timers": tools.active_timers(),
        "cooldown": {"active": in_cooldown, "remaining": remaining},
        "services": {
            "ai": bool(settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY or settings.GEMINI_API_KEY),
            "microphone": True,
            "camera": face.has_profile(),
            "internet": True,
            "backend": True,
        },
    }


_LOOPBACK = {"127.0.0.1", "::1", "localhost", "testclient"}
UPDATE_SPEECH = "Senhor, estou atualizando os meus sistemas. Volto em instantes."
UPDATE_SPEECH_SAME = "Senhor, já estou na versão mais nova. Vou reiniciar os meus sistemas mesmo assim."


class UpdateRequest(BaseModel):
    confirm: bool = False


@router.post("/api/system/update")
async def system_update(req: UpdateRequest, request: Request) -> dict:
    """Botão ATUALIZAR (tela de bloqueio): baixa a versão nova, avisa por voz e reinicia.

    Só no próprio PC e só pela central: pedido de outra máquina, de outro site ou sem JSON é recusado.
    """
    client = request.client.host if request.client else ""
    if client not in _LOOPBACK:
        raise HTTPException(status_code=403, detail="A atualização só pode ser pedida no próprio PC.")
    origin = request.headers.get("origin")
    if origin and origin not in settings.CORS_ORIGINS:
        raise HTTPException(status_code=403, detail="Origem não autorizada.")
    if "application/json" not in request.headers.get("content-type", "") or not req.confirm:
        raise HTTPException(status_code=400, detail="Confirme a atualização.")

    result = await asyncio.to_thread(self_update.pull)
    if not result["ok"]:
        return {"status": "error", **result}

    async def speak_and_restart() -> None:
        try:
            await speech.say_quietly(UPDATE_SPEECH if result["changed"] else UPDATE_SPEECH_SAME)
        except Exception:  # noqa: BLE001 - sem voz, reinicia do mesmo jeito
            log.warning("Não consegui falar o aviso de atualização", exc_info=True)
        if not self_update.restart():
            await runtime.manager.broadcast({"type": "error", "message": "Não consegui reiniciar sozinho. Use o Iniciar-JARVIS.bat."})

    runtime.track(speak_and_restart())
    return {"status": "restarting", "boot_id": self_update.BOOT_ID, **result}


@router.get("/api/auth/token")
async def get_auth_token(request: Request) -> dict:
    """Retorna o token de acesso (permitido apenas para requisições locais)."""
    client_ip = request.client.host if request.client else ""
    if client_ip not in {"127.0.0.1", "::1", "localhost", "testclient"}:
        raise HTTPException(status_code=403, detail="Acesso restrito ao computador local.")
    return {"token": runtime.ACCESS_TOKEN}


def local_ip() -> str:
    """Endereço deste PC na rede de casa (ex.: 192.168.0.10), ou "" se não houver rede."""
    try:
        candidates = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
        ip = next(
            (
                item[4][0]
                for item in candidates
                if not item[4][0].startswith("127.") and not item[4][0].startswith("169.254.")
            ),
            "",
        )
        if not ip:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
                probe.connect(("8.8.8.8", 80))
                ip = probe.getsockname()[0]
        return ip
    except OSError:
        return ""


@router.get("/api/network-access")
async def network_access() -> dict:
    """Retorna o endereço local para outro dispositivo na mesma rede."""
    ip = local_ip()
    url = f"http://{ip}:5173?token={runtime.ACCESS_TOKEN}" if ip else ""
    return {
        "url": url,
        "host": ip,
        "token": runtime.ACCESS_TOKEN,
        "network_mode": settings.NETWORK_MODE,
        # V4.5: app Android. A página de pareamento leva o token; só aparece com a central liberada.
        "app_pair_url": f"http://{ip}:8000/api/mobile/pair?token={runtime.ACCESS_TOKEN}" if ip else "",
        "app_download_url": f"http://{ip}:8000/api/mobile" if ip else "",
    }


@router.get("/api/timers")
async def list_timers() -> dict:
    return {"timers": tools.get_active_timers_list()}


@router.post("/api/cancel")
async def cancel_operation() -> dict:
    """Botão Cancelar: corta a voz na hora, para os avisos e descarta a resposta que estiver a caminho.

    Timers e lembretes já programados NÃO são cancelados (para isso: "cancele os timers").
    """
    session.turn_id += 1  # invalida qualquer resposta que ainda esteja sendo gerada
    if session.current_stop is not None:
        session.current_stop.set()
    tts_module.stop_playback()  # corta o som que está tocando
    for task in list(runtime.background_tasks):
        if not task.done():
            task.cancel()
    session.busy = False
    await runtime.manager.broadcast({"type": "state", "state": "idle"})
    log.info("Operação cancelada pelo usuário.")
    return {"status": "ok"}


@router.post("/api/chat")
async def chat(req: ChatRequest) -> dict:
    """Conversa (digitada ou falada)."""
    return await turns.handle_turn(req.message, routine=False)


@router.post("/api/trigger-jarvis")
async def trigger_jarvis(req: TriggerRequest) -> dict:
    """Rotina completa: câmera + notícias + IA."""
    return await turns.handle_turn(req.message, routine=True)


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    client_ip = ws.client.host if ws.client else ""
    is_local = client_ip in {"127.0.0.1", "::1", "localhost", "testclient"}
    if not is_local:
        if not settings.NETWORK_MODE:
            await ws.close(code=1008, reason="Acesso externo desativado")
            return
        token = ws.query_params.get("token") or ws.headers.get("x-jarvis-token")
        if not token or not secrets.compare_digest(token, runtime.ACCESS_TOKEN):
            await ws.close(code=1008, reason="Não autorizado")
            return
    await runtime.manager.connect(ws)
    await ws.send_json({"type": "state", "state": "processing" if session.busy else "idle"})
    await ws.send_json({"type": "access_state", **access.snapshot()})
    # V5.5: aparelhos conectados (a central mostra quem está ligado; o celular aparece ao conectar)
    await runtime.manager.broadcast({"type": "devices", "items": runtime.manager.devices()})
    try:
        while True:
            message = await ws.receive_text()  # mantém a conexão viva
            if message == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        runtime.manager.disconnect(ws)
        await runtime.manager.broadcast({"type": "devices", "items": runtime.manager.devices()})


@router.get("/api/devices")
async def connected_devices() -> dict:
    """V5.5: aparelhos com a central aberta agora (PC, app do celular, navegadores)."""
    return {"items": runtime.manager.devices()}


class TtsRequest(BaseModel):
    text: str


@router.post("/api/tts")
async def tts_audio(req: TtsRequest):
    """V5.5: devolve a fala em MP3 para tocar NO APARELHO (botão 🔊 e alto-falante do chat no celular)."""
    import os
    import tempfile

    from fastapi.responses import Response

    text = tts_module._clean_for_speech(req.text or "")[:1500]  # noqa: SLF001
    if not text:
        raise HTTPException(status_code=400, detail="Nada para falar.")
    fd, path = tempfile.mkstemp(suffix=".mp3", prefix="jarvis_dev_")
    os.close(fd)
    try:
        await tts_module._synthesize(text, path)  # noqa: SLF001
        with open(path, "rb") as f:
            data = f.read()
    except Exception as exc:  # noqa: BLE001
        log.warning("Voz para o aparelho falhou: %s", exc)
        raise HTTPException(status_code=503, detail="Não consegui gerar a voz agora.") from exc
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
    if not data:
        raise HTTPException(status_code=503, detail="Não consegui gerar a voz agora.")
    return Response(content=data, media_type="audio/mpeg", headers={"Cache-Control": "no-store"})


class SpeakRequest(BaseModel):
    text: str


@router.post("/api/speak")
async def speak_text(req: SpeakRequest) -> dict:
    """Fala um texto com o TTS do assistente (feedback de opções selecionadas)."""
    text = req.text.strip()
    if text:
        runtime.track(speech.speak(text, release_busy=True))
    return {"status": "ok"}


@router.get("/api/cameras")
async def get_cameras() -> dict:
    """Detecta webcams conectadas e retorna o índice selecionado."""
    from modules.vision import list_available_cameras

    cameras = await asyncio.to_thread(list_available_cameras)
    current = prefs.get_camera_index()
    return {"cameras": cameras, "current": current}


@router.get("/api/logs")
async def get_logs(limit: int = 50) -> dict:
    return {"events": event_log.list_events(limit)}


@router.get("/api/diagnostics")
async def diagnostics(format: str = "json"):  # noqa: A002 - nome do parâmetro na URL
    """V4.2.2: diagnóstico sem segredos para o botão "Copiar diagnóstico" (rota protegida pelo bloqueio)."""
    from modules import diagnostics as diag_module

    in_cooldown, remaining = get_quota_cooldown()
    runtime_info = {
        "busy": session.busy,
        "screens_connected": len(runtime.manager.connections),
        "quota_cooldown_s": remaining if in_cooldown else 0,
        "face_profile": face.has_profile(),
    }
    data = diag_module.build(event_log.list_events(diag_module.MAX_EVENTS), prefs.get_all(), runtime_info)
    if format == "text":
        return {"text": diag_module.as_text(data)}
    return data

"""Rotas de sistema: saúde, token, rede, cancelar, chat, fala, câmeras, logs e WebSocket."""

import logging
import asyncio
import socket
import secrets
from fastapi import HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from config import settings
from modules import face, tools, prefs, event_log
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
    try:
        while True:
            message = await ws.receive_text()  # mantém a conexão viva
            if message == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        runtime.manager.disconnect(ws)


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

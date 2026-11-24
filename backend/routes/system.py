"""Rotas de sistema: saúde, token, rede, cancelar, chat, fala, câmeras, logs e WebSocket."""

import logging
import asyncio
import re
import socket
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


def _startup_info() -> dict:
    from core import startup_timing

    return startup_timing.info()


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
        "speaking": session.speaking > 0,  # V6.3: o ouvido offline não escuta enquanto o JARVIS fala
        "has_profile": face.has_profile(),
        "timers": tools.active_timers(),
        # V8.12.3: a tela de "reconectando" do site lembra se este PC liga sozinho (nada pessoal)
        "always_on": bool(prefs.get_all().get("always_on", True)),
        "cooldown": {"active": in_cooldown, "remaining": remaining},
        "startup": _startup_info(),  # V9.4.1: quanto tempo levou para ligar (por etapa)
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


@router.get("/api/system/update/progress")
async def system_update_progress() -> dict:
    """V8.1.7: em que etapa está a atualização (a tela mostra os passos de verdade)."""
    return self_update.progress()


@router.get("/api/system/update/status")
async def system_update_status(force: bool = False) -> dict:
    """V6.7.2: tem versão nova? (a central mostra a bolinha com o número no botão ATUALIZAR)

    V8.11: diz também se a central deve atualizar sozinha ao abrir (auto_on_open) e se o JARVIS está ocupado."""
    from modules import auto_update

    info = await asyncio.to_thread(self_update.check, force)
    return {**info, "auto_on_open": await asyncio.to_thread(auto_update.on_open_enabled), "busy": session.busy,
            "notice": auto_update.pending_notice()}  # V9.4.1: aviso de atualização em andamento (contagem)


@router.post("/api/system/update/postpone")
async def system_update_postpone() -> dict:
    """V9.4.1: ADIAR 1 H no aviso da atualização automática."""
    from modules import auto_update

    return auto_update.postpone()


@router.post("/api/system/update/now")
async def system_update_now() -> dict:
    """V9.4.1: ATUALIZAR AGORA no aviso da atualização automática (pula o resto da espera)."""
    from modules import auto_update

    auto_update.update_now()
    return {"status": "ok"}


class AutostartRequest(BaseModel):
    enabled: bool


@router.get("/api/system/autostart")
async def autostart_status() -> dict:
    """V8.11: o JARVIS liga junto com o Windows?"""
    from modules import autostart

    return await asyncio.to_thread(autostart.status)


@router.post("/api/system/autostart")
async def autostart_set(req: AutostartRequest, request: Request) -> dict:
    """V8.11: liga/desliga o início junto com o Windows (só pelo próprio PC)."""
    if not runtime.is_local_conn(request):
        raise HTTPException(status_code=403, detail="Isso só pode ser mudado no próprio PC.")
    from modules import always_on

    # V8.12.3: desligar aqui também desliga o "sempre ligado" (senão o backend recriaria o atalho)
    return await asyncio.to_thread(always_on.set_autostart, req.enabled)


class AlwaysOnRequest(BaseModel):
    keep_awake: bool


@router.get("/api/system/always-on")
async def always_on_status() -> dict:
    """V8.12.3: sempre ligado (início com o Windows, guardião e PC acordado na tomada)."""
    from modules import always_on

    return await asyncio.to_thread(always_on.status)


@router.post("/api/system/always-on")
async def always_on_set(req: AlwaysOnRequest, request: Request) -> dict:
    """V8.12.3: liga/desliga "não deixar o PC dormir na tomada" (só pelo próprio PC)."""
    from modules import always_on

    if not runtime.is_local_conn(request):
        raise HTTPException(status_code=403, detail="Isso só pode ser mudado no próprio PC.")
    await asyncio.to_thread(prefs.update, keep_awake=req.keep_awake)
    return await asyncio.to_thread(always_on.status)


@router.post("/api/system/update")
async def system_update(req: UpdateRequest, request: Request) -> dict:
    """Botão ATUALIZAR (tela de bloqueio): baixa a versão nova, avisa por voz e reinicia.

    Só no próprio PC e só pela central: pedido de outra máquina, de outro site ou sem JSON é recusado.
    """
    if not runtime.is_local_conn(request):  # V6.3: nem pelo túnel
        raise HTTPException(status_code=403, detail="A atualização só pode ser pedida no próprio PC.")
    origin = request.headers.get("origin")
    if origin and origin not in settings.CORS_ORIGINS:
        raise HTTPException(status_code=403, detail="Origem não autorizada.")
    if "application/json" not in request.headers.get("content-type", "") or not req.confirm:
        raise HTTPException(status_code=400, detail="Confirme a atualização.")

    return await perform_update(announce=True)


async def perform_update(announce: bool = True) -> dict:
    """Baixa a versão nova e reinicia (o botão ATUALIZAR e, V8.5.0, a atualização automática).

    announce: fala o aviso (o botão). A automática não fala: só mostra na ilha."""
    self_update.set_progress("baixando", "Baixando a versão nova…")
    result = await asyncio.to_thread(self_update.pull)
    if not result["ok"]:
        self_update.set_progress("erro", result.get("message", ""))
        return {"status": "error", **result}
    notes = []
    try:
        notes = (await asyncio.to_thread(self_update.check, False)).get("notes") or []
    except Exception:  # noqa: BLE001
        pass
    try:  # V8.12.2: número da versão e destaques do CHANGELOG para a tela (no lugar do código do commit)
        release = await asyncio.to_thread(self_update.new_release_info)
    except Exception:  # noqa: BLE001 - sem isso a tela mostra o que já mostrava
        log.warning("Não consegui ler a versão nova do disco", exc_info=True)
        release = {}
    self_update.set_progress("baixado", result.get("message", ""), antes=result.get("before", ""), depois=result.get("after", ""), notas=notes[:6], **release)

    async def speak_and_restart() -> None:
        # V8.1.7: a voz começa, mas não segura o reinício (no máximo 4 s de espera)
        talk = asyncio.create_task(speech.say_quietly(UPDATE_SPEECH if result["changed"] else UPDATE_SPEECH_SAME)) if announce else None
        try:
            if await asyncio.to_thread(self_update.frontend_stale):
                # V8.2.3: só tenta a interface pronta (segundos). Montar no PC não segura mais o reinício:
                # o Iniciar-JARVIS.bat liga o JARVIS na hora e monta em segundo plano, se precisar.
                self_update.set_progress("interface", "Baixando a interface pronta…")
                await asyncio.to_thread(self_update.fetch_prebuilt)
            if talk:
                await asyncio.wait_for(asyncio.shield(talk), timeout=4)
        except asyncio.TimeoutError:
            pass
        except Exception:  # noqa: BLE001 - sem voz ou sem build, reinicia do mesmo jeito
            log.warning("Preparação da atualização com problema", exc_info=True)
        self_update.set_progress("reiniciando", "Reiniciando os sistemas…")
        access.remember_for_restart()  # V8.12.2: liberada antes, liberada depois (sem pedir o rosto de novo)
        if not self_update.restart():
            access.forget_restart()
            self_update.set_progress("erro", "Não consegui reiniciar sozinho. Use o Iniciar-JARVIS.bat.")
            await runtime.manager.broadcast({"type": "error", "message": "Não consegui reiniciar sozinho. Use o Iniciar-JARVIS.bat."})

    runtime.track(speak_and_restart())
    return {"status": "restarting", "boot_id": self_update.BOOT_ID, **result, **release}


@router.get("/api/auth/token")
async def get_auth_token(request: Request) -> dict:
    """Retorna o token de acesso (permitido apenas para requisições locais)."""
    if not runtime.is_local_conn(request):  # V6.3: a chave nunca sai pelo túnel
        raise HTTPException(status_code=403, detail="Acesso restrito ao computador local.")
    return {"token": runtime.ACCESS_TOKEN}


def is_tailscale_ip(ip: str) -> bool:
    """V6.0: endereços do Tailscale ficam em 100.64.0.0/10 (100.64.x.x a 100.127.x.x)."""
    parts = ip.split(".")
    return len(parts) == 4 and parts[0] == "100" and parts[1].isdigit() and 64 <= int(parts[1]) <= 127


def tailscale_ip() -> str:
    """V6.0: endereço deste PC no Tailscale (acesso fora de casa), ou "" se o Tailscale não estiver ligado."""
    try:
        import psutil

        for addrs in psutil.net_if_addrs().values():
            for a in addrs:
                if a.family == socket.AF_INET and is_tailscale_ip(a.address):
                    return a.address
    except Exception:  # noqa: BLE001
        pass
    return ""


def local_ip() -> str:
    """Endereço deste PC na rede de casa (ex.: 192.168.0.10), ou "" se não houver rede."""
    try:
        candidates = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
        ip = next(
            (
                item[4][0]
                for item in candidates
                if not item[4][0].startswith("127.") and not item[4][0].startswith("169.254.")
                and not is_tailscale_ip(item[4][0])  # V6.0: o da rede de casa, não o do Tailscale
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
    from modules import tls

    ip = local_ip()
    url = f"{tls.frontend_url(ip)}/?token={runtime.ACCESS_TOKEN}" if ip else ""  # V7.7: https quando ligado
    return {
        "url": url,
        "host": ip,
        "token": runtime.ACCESS_TOKEN,
        "network_mode": settings.NETWORK_MODE,
        # V4.5: app Android. A página de pareamento leva o token; só aparece com a central liberada.
        "app_pair_url": f"{tls.backend_url(ip)}/api/mobile/pair?token={runtime.ACCESS_TOKEN}" if ip else "",
        "https": tls.enabled(),
        "certificate_url": f"http://{ip}:8000/api/mobile/certificado" if ip else "",
        "app_download_url": f"http://{ip}:8000/api/mobile" if ip else "",
        # V6.0: acesso fora de casa pelo Tailscale (vazio se ele não estiver ligado neste PC)
        "remote_host": tailscale_ip(),
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
    from core import turn_queue

    turn_queue.cancel_all()  # V9.0: quem esperava na fila também desiste
    if session.current_stop is not None:
        session.current_stop.set()
    tts_module.stop_playback()  # corta o som que está tocando
    for task in list(runtime.background_tasks):
        if not task.done():
            task.cancel()
    session.busy = False
    tts_module.clear_prefetch()
    # V6.5.3: cala também a voz que estiver tocando no celular (e a fila dele)
    await runtime.manager.broadcast({"type": "speech_stop"})
    await runtime.manager.broadcast({"type": "state", "state": "idle"})
    log.info("Operação cancelada pelo usuário.")
    return {"status": "ok"}


@router.post("/api/chat")
async def chat(req: ChatRequest) -> dict:
    """Conversa (digitada ou falada)."""
    from modules import desk

    desk.xp_quietly("conversa")  # V8.0: XP do Modo Desk
    return await turns.handle_turn(req.message, routine=False)


@router.get("/api/search/local")
async def search_local(q: str = "", limit: int = 8) -> dict:
    """V9.0: memória pesquisável (conversas, memórias, tarefas, lembretes, copiados), para a paleta Ctrl+K."""
    from modules import memory_index

    q = (q or "").strip()[:200]
    if len(q) < 2:
        return {"items": []}
    items = await asyncio.to_thread(memory_index.search, q, limit)
    return {"items": items}


@router.post("/api/trigger-jarvis")
async def trigger_jarvis(req: TriggerRequest) -> dict:
    """Rotina completa: câmera + notícias + IA."""
    return await turns.handle_turn(req.message, routine=True)


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    is_local = runtime.is_local_conn(ws)  # V6.3: túnel não conta como "este PC"
    if not is_local:
        if not settings.NETWORK_MODE:
            await ws.close(code=1008, reason="Acesso externo desativado")
            return
        from modules import device_access, tls

        if ws.url.scheme == "ws" and tls.enabled():  # V7.7: na rede, só por wss (https)
            await ws.close(code=1008, reason="Use a conexão criptografada (https)")
            return
        token = ws.query_params.get("token") or ws.headers.get("x-jarvis-token")
        kind, dev = device_access.classify(token or "")
        ok = kind == "device" or (kind == "pairing" and device_access.migration_active())  # V7.6
        if not ok:
            await ws.close(code=1008, reason="Não autorizado")
            return
        if dev:
            device_access.touch(dev, ws.client.host if ws.client else "?")
    await runtime.manager.connect(ws)
    await ws.send_json({"type": "state", "state": "processing" if session.busy else "idle"})
    if session.busy and session.doing:  # V9.1.2: central aberta no meio de um pedido demorado
        await ws.send_json({"type": "doing", "text": session.doing})
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
    if not text or not tts_module.speakable(text):
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


class LockMic(BaseModel):
    on: bool


@router.post("/api/lock/mic")
async def lock_mic(req: LockMic) -> dict:
    """V6.5.20: liga/desliga o microfone do bloqueio e lembra a escolha (vale com a central bloqueada)."""
    from modules import prefs

    prefs.update(lock_mic_on=bool(req.on))
    return {"lock_mic_on": bool(req.on)}


class ChatClear(BaseModel):
    scope: str = "today"  # "today" | "all"


@router.post("/api/chat/clear")
async def chat_clear(req: ChatClear) -> dict:
    """V6.5.16: botão LIMPAR do Canal Ativo. Apaga a conversa (hoje ou tudo) no PC e avisa os aparelhos."""
    from modules import memory

    if req.scope not in ("today", "all"):
        raise HTTPException(status_code=400, detail="Use 'today' ou 'all'.")
    removed = await asyncio.to_thread(memory.clear_conversation, req.scope)
    session.history.clear()  # o contexto da IA recomeça (não lembra do que foi apagado)
    await runtime.manager.broadcast({"type": "chat_cleared", "scope": req.scope})
    return {"status": "ok", "removed": removed}


class BrowserPick(BaseModel):
    browser: str
    remember: bool = False


@router.get("/api/browser")
async def browser_list() -> dict:
    """V6.5.11: navegadores instalados e a preferência (perguntar, padrão ou um deles)."""
    from modules import browser_choice

    return {"browsers": await asyncio.to_thread(browser_choice.installed), "mode": browser_choice.mode(),
            "pending": browser_choice.pending()}


@router.post("/api/browser/choose")
async def browser_choose(req: BrowserPick) -> dict:
    """V6.5.11: tocar num navegador da lista "Em qual navegador?"."""
    from modules import browser_choice

    if req.browser not in (*browser_choice.NAMES, "default", "cancel"):
        raise HTTPException(status_code=400, detail="Navegador desconhecido.")
    reply = await asyncio.to_thread(browser_choice.choose, req.browser, req.remember)
    await runtime.manager.broadcast({"type": "browser_choice_done"})
    await runtime.manager.broadcast({"type": "response", "text": reply, "cards": [], "local": True})
    runtime.track(speech.speak(reply))
    return {"status": "ok", "response": reply}


class AudioChoice(BaseModel):
    output: str | None = None
    input: str | None = None


@router.get("/api/audio")
async def audio_devices_list() -> dict:
    """V6.5.8: caixas de som e microfones do PC (botão de áudio da tela de bloqueio)."""
    from modules import audio_devices

    return await asyncio.to_thread(audio_devices.snapshot)


@router.post("/api/audio")
async def audio_devices_choose(req: AudioChoice) -> dict:
    from modules import audio_devices

    try:
        return await asyncio.to_thread(audio_devices.choose, req.output, req.input)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/audio/test")
async def audio_test() -> dict:
    """Fala uma frase curta na caixa escolhida (sempre no PC, mesmo pedindo pelo celular)."""
    from core import voice_route

    token = voice_route.set_target(None)
    try:
        runtime.track(speech.speak("Teste de áudio. Esta é a minha voz, senhor.", release_busy=False))
    finally:
        voice_route.reset(token)
    return {"status": "ok"}


class PlayedRequest(BaseModel):
    say_id: str


@router.post("/api/tts/played")
async def tts_played(req: PlayedRequest) -> dict:
    """V6.5.1: o aparelho terminou de tocar a fala (o briefing passa para o próximo card na hora certa)."""
    from core import voice_route

    return {"ok": voice_route.mark_played((req.say_id or "")[:32])}


class SpeakRequest(BaseModel):
    text: str
    speed: float | None = None  # V8.14: narração do holograma mais rápida (1, 1.25 ou 1.5)


@router.post("/api/speak")
async def speak_text(req: SpeakRequest) -> dict:
    """Fala um texto com o TTS do assistente (feedback de opções selecionadas)."""
    text = req.text.strip()
    if text:
        token = tts_module.use_speed(req.speed)  # a tarefa da fala copia a velocidade daqui
        try:
            runtime.track(speech.speak(text, release_busy=True))
        finally:
            tts_module.reset_speed(token)
    return {"status": "ok"}


@router.post("/api/speak/pc")
async def speak_on_pc(req: SpeakRequest) -> dict:
    """V5.7: "FALAR NO PC" do celular: o PC fala em voz alta o texto, mesmo o pedido vindo do celular."""
    from core import voice_route

    text = (req.text or "").strip()[:300]
    if not text:
        raise HTTPException(status_code=400, detail="Digite o que o PC deve falar.")
    token = voice_route.set_target(None)  # força a caixa de som do PC
    try:
        runtime.track(speech.say_quietly(text))
    finally:
        voice_route.reset(token)
    return {"status": "ok"}


@router.get("/api/system/health-check")
async def system_health_check(request: Request) -> dict:
    """V7.4: 🩺 DIAGNÓSTICO: testa de verdade IA, voz, internet, nuvem, disco, dados e erros recentes."""
    from modules import device_access, health_check

    # V7.6: com a central bloqueada, no máximo 1 diagnóstico por minuto por aparelho
    if access.effective_state() != access.UNLOCKED and not device_access.rate_ok(f"diag:{request.client.host if request.client else '?'}", 60):
        raise HTTPException(status_code=429, detail="Espere um minuto para rodar o diagnóstico de novo.")

    return await health_check.run()


class PcFixRequest(BaseModel):
    acao: str
    nomes: list[str] = []


@router.get("/api/pc/scan")
async def pc_scan_route() -> dict:
    """V8.10.0 (ideia 13): a varredura do PC lento (só mede; nada é mudado)."""
    from modules import pc_scan

    return await asyncio.to_thread(pc_scan.scan)


@router.post("/api/pc/fix")
async def pc_fix_route(body: PcFixRequest) -> dict:
    """V8.10.0: as correções da varredura, cada uma só quando o usuário aperta o botão e confirma."""
    from modules import pc_scan

    if body.acao == "fechar":
        if not body.nomes:
            raise HTTPException(status_code=400, detail="Escolha pelo menos um programa.")
        return await asyncio.to_thread(pc_scan.close_programs, body.nomes[:20])
    if body.acao == "temporarios":
        return await asyncio.to_thread(pc_scan.clean_temp)
    if body.acao == "lixeira":
        return await asyncio.to_thread(pc_scan.empty_recycle_bin)
    raise HTTPException(status_code=400, detail="Correção desconhecida.")


@router.post("/api/system/optimize")
async def system_optimize(request: Request) -> dict:
    """V7.2: botão ⚡ OTIMIZAR: limpa sobras de áudio (falas interrompidas), cache de voz velho e libera memória."""
    from modules import device_access, optimizer

    if access.effective_state() != access.UNLOCKED and not device_access.rate_ok(f"opt:{request.client.host if request.client else '?'}", 60):
        raise HTTPException(status_code=429, detail="Espere um minuto para otimizar de novo.")  # V7.6

    return await asyncio.to_thread(optimizer.run)


class PrefetchRequest(BaseModel):
    texts: list[str] = []
    speed: float | None = None  # V8.14


@router.post("/api/tts/prefetch")
async def tts_prefetch(req: PrefetchRequest) -> dict:
    """V7.5: gera a voz destas falas JÁ (holograma: troca de cena sem esperar a voz ficar pronta).

    Se a voz desta tela toca no próprio aparelho (celular), gera a fala inteira, como o /api/tts pede.
    """
    from core import voice_route
    from modules import tts as tts_module

    texts = [t[:600] for t in (req.texts or [])[:10] if isinstance(t, str) and t.strip()]
    token = tts_module.use_speed(req.speed)  # V8.14: gera já na velocidade da narração (senão o cache não bate)
    try:
        started = tts_module.prefetch(texts, whole=bool(voice_route.current()))
    finally:
        tts_module.reset_speed(token)
    return {"started": started}


class HoloRequest(BaseModel):
    query: str
    kind: str = "auto"
    req_id: str = ""  # V8.14: a tela que pediu reconhece as cenas que chegam aos poucos (holo_partial)


def _holo_partial_sender(req_id: str, loop):
    """V8.14: a cada pedaço da IA, manda as cenas JÁ completas para a tela (ela começa sem esperar o resto)."""
    from modules import holo
    from services import llm_stream

    sent = {"n": 0}

    def on_event(event: dict) -> None:
        if event.get("reset"):
            sent["n"] = 0
            return
        text = event.get("text") or ""
        scenes = holo.partial_scenes(text)
        if len(scenes) > sent["n"]:
            sent["n"] = len(scenes)
            runtime.track(runtime.manager.broadcast({"type": "holo_partial", "req_id": req_id,
                                                     "titulo": holo.partial_title(text), "cenas": scenes}))

    return llm_stream.StreamSink(loop, on_event, min_interval=0.25)


@router.post("/api/holo")
async def holo_build(req: HoloRequest) -> dict:
    """V7.1: HOLOGRAMA: a pesquisa vira uma apresentação narrada ou uma receita viva (tela HoloStage).

    V8.14: a apresentação pesquisa no Google antes (Gemini; as fontes voltam em "fontes") e as cenas vão para a
    tela assim que ficam prontas (evento holo_partial). Antes: só o que a IA já sabia, e tudo de uma vez no final."""
    from modules import holo
    from services import llm_orchestrator, llm_stream

    query = (req.query or "").strip()[:240]
    if not query:
        raise HTTPException(status_code=400, detail="Diga o assunto.")
    kind = req.kind if req.kind in holo.KINDS else holo.guess_kind(query)
    web = kind == "apresentacao"
    prompt = holo.build_prompt(query, kind) + (holo.web_note() if web else "")
    req_id = re.sub(r"[^A-Za-z0-9_-]", "", req.req_id or "")[:40]
    sink = _holo_partial_sender(req_id, asyncio.get_running_loop()) if web and req_id else None

    def run() -> tuple[str, list]:
        token = llm_stream.use(sink)
        if sink is not None:
            sink.claim()
        try:
            if web:
                return llm_orchestrator.ask_web(prompt, max_tokens=2400)
            return llm_orchestrator.ask_text(prompt, False, 2400), []
        finally:
            llm_stream.reset(token)

    try:
        raw, sources = await asyncio.wait_for(asyncio.to_thread(run), timeout=90)
        data = holo.parse(raw, kind)
        if web:
            data["fontes"] = holo.clean_sources(sources)
            data["pesquisado"] = bool(data["fontes"])
        return data
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="O holograma demorou demais. Tente de novo, senhor.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=f"{exc} Tente de novo, senhor.") from exc
    except Exception as exc:  # noqa: BLE001
        log.warning("Holograma falhou: %s", exc)
        raise HTTPException(status_code=502, detail="Não consegui montar o holograma agora.") from exc
    finally:
        if sink is not None:
            sink.close()


class HoloAskRequest(BaseModel):
    titulo: str = ""
    cena: str = ""
    pergunta: str


@router.post("/api/holo/ask")
async def holo_ask(req: HoloAskRequest) -> dict:
    """V7.14: pergunta no meio da apresentação: resposta curta no contexto da cena."""
    from modules import holo_extra
    from services import llm_orchestrator

    if not (req.pergunta or "").strip():
        raise HTTPException(status_code=400, detail="Faça a pergunta.")
    try:
        raw = await asyncio.to_thread(llm_orchestrator.ask_text, holo_extra.ask_prompt(req.titulo, req.cena, req.pergunta))
        return {"resposta": holo_extra.parse_ask(raw)}
    except Exception as exc:  # noqa: BLE001
        log.warning("Pergunta no holograma falhou: %s", exc)
        raise HTTPException(status_code=502, detail="Não consegui responder agora, senhor.") from exc


class HoloQuizRequest(BaseModel):
    titulo: str = ""
    falas: list[str] = []


@router.post("/api/holo/quiz")
async def holo_quiz(req: HoloQuizRequest) -> dict:
    """V7.14: quiz de 3 perguntas sobre a apresentação."""
    from modules import holo_extra
    from services import llm_orchestrator

    falas = [f for f in req.falas if isinstance(f, str) and f.strip()][:7]
    if not falas:
        raise HTTPException(status_code=400, detail="Sem apresentação para o quiz.")
    try:
        raw = await asyncio.to_thread(llm_orchestrator.ask_text, holo_extra.quiz_prompt(req.titulo, falas), False, 1500)
        return {"perguntas": holo_extra.parse_quiz(raw)}
    except Exception as exc:  # noqa: BLE001
        log.warning("Quiz do holograma falhou: %s", exc)
        raise HTTPException(status_code=502, detail="Não consegui montar o quiz agora, senhor.") from exc


class HoloSaveRequest(BaseModel):
    data: dict
    query: str = ""


@router.get("/api/holo/saved")
async def holo_saved() -> dict:
    from modules import holo_extra

    return {"itens": holo_extra.listing()}


@router.get("/api/holo/saved/{item_id}")
async def holo_saved_get(item_id: str) -> dict:
    from modules import holo_extra

    item = holo_extra.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Não achei essa apresentação salva.")
    return item


@router.post("/api/holo/saved")
async def holo_saved_add(req: HoloSaveRequest) -> dict:
    """V7.14: ⭐ SALVAR: guarda a apresentação (ou receita) para rever sem gastar IA."""
    from modules import holo_extra

    try:
        return {"item": holo_extra.save(req.data, req.query), "itens": holo_extra.listing()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/api/holo/saved/{item_id}")
async def holo_saved_delete(item_id: str) -> dict:
    from modules import holo_extra

    if not holo_extra.delete(item_id):
        raise HTTPException(status_code=404, detail="Não achei essa apresentação salva.")
    return {"itens": holo_extra.listing()}


class QuickCardRequest(BaseModel):
    pergunta: str
    resposta: str = ""


@router.post("/api/quickcard")
async def quick_card(req: QuickCardRequest) -> dict:
    """V7.14: cartão animado das perguntas rápidas ("quanto está o dólar?", "quem ganhou o jogo?")."""
    from modules import holo_extra
    from services import llm_orchestrator

    q = (req.pergunta or "").strip()[:240]
    if not holo_extra.is_quick(q):
        return {"card": None}
    code = holo_extra.currency_of(q)
    if code:
        try:
            return {"card": await asyncio.to_thread(holo_extra.currency_card, code)}
        except Exception as exc:  # noqa: BLE001 - cai no cartão montado pela IA
            log.info("Cotação para o cartão indisponível: %s", exc)
    if not (req.resposta or "").strip():
        return {"card": None}
    try:
        raw = await asyncio.to_thread(llm_orchestrator.ask_text, holo_extra.card_prompt(q, req.resposta))
        return {"card": holo_extra.parse_card(raw)}
    except Exception as exc:  # noqa: BLE001
        log.info("Cartão rápido falhou: %s", exc)
        return {"card": None}


class CameraAskRequest(BaseModel):
    image: str
    question: str = ""


@router.post("/api/camera/ask")
async def camera_ask(req: CameraAskRequest) -> dict:
    """V6.8.2: "o que é isso?" com a foto da câmera do aparelho (celular ou PC). A foto não é guardada."""
    from modules import camera_ask as cam
    from services import llm_orchestrator

    try:
        image = cam.clean_image(req.image)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        text = await asyncio.to_thread(llm_orchestrator.ask_with_image, cam.build_prompt(req.question), image)
    except Exception as exc:  # noqa: BLE001
        log.warning("Pergunta pela câmera falhou: %s", exc)
        raise HTTPException(status_code=502, detail="Não consegui analisar a foto agora.") from exc
    speech_text, diagnosis = cam.parse_answer(text or "")
    return {"text": speech_text or "Não consegui ver direito, senhor. Tente aproximar ou iluminar melhor.", "diagnostico": diagnosis}


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


@router.get("/api/logs/file")
async def get_log_file(level: str = "WARNING", q: str = "", limit: int = 200) -> dict:
    """V9.4.2: janela LOGS da central: erros e avisos (ou tudo) do logs/jarvis.log, com o rastro de cada erro."""
    from modules import log_view

    return await asyncio.to_thread(log_view.read, level, q[:80], limit)


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

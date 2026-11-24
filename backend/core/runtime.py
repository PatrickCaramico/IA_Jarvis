"""Infraestrutura compartilhada: token de acesso, conexões WebSocket e tarefas em segundo plano."""

import logging
import asyncio
import secrets
from fastapi import WebSocket
from config import settings

log = logging.getLogger("jarvis.runtime")


def get_or_create_access_token() -> str:
    """Carrega o token de acesso persistido ou gera um novo na primeira execução."""
    if settings.ACCESS_TOKEN_FILE.exists():
        try:
            token = settings.ACCESS_TOKEN_FILE.read_text(encoding="utf-8").strip()
            if token:
                return token
        except Exception:
            log.exception("Falha ao ler token de acesso existente")
    token = secrets.token_urlsafe(32)
    try:
        settings.ACCESS_TOKEN_FILE.write_text(token, encoding="utf-8")
    except Exception:
        log.exception("Falha ao salvar token de acesso")
    return token


ACCESS_TOKEN = get_or_create_access_token()


LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}
# V6.3: túneis (Cloudflare, ngrok, proxies) entregam a conexão a partir de 127.0.0.1, mas o pedido veio
# da internet. Com estes cabeçalhos, a conexão NUNCA conta como "este PC" (exige a chave, não ganha a chave).
_PROXY_HEADERS = ("cf-connecting-ip", "cf-ray", "x-forwarded-for", "x-forwarded-host", "x-real-ip", "forwarded")


def is_local_conn(conn) -> bool:
    """O pedido (HTTP ou WebSocket) veio mesmo deste PC? Falso para qualquer coisa que passou por túnel."""
    client = getattr(conn, "client", None)
    host = client.host if client else ""
    if host not in LOCAL_HOSTS:
        return False
    try:
        headers = conn.headers
        return not any(h in headers for h in _PROXY_HEADERS)
    except Exception:  # noqa: BLE001
        return True


def describe_device(ip: str, user_agent: str, local: bool) -> dict:
    """V5.5: nome amigável do aparelho a partir do user agent ("Celular · SM-A546E", "Este PC")."""
    import re
    import time as _time

    ua = user_agent or ""
    app = "JarvisApp/" in ua
    model = ""
    m = re.search(r"Android [\d.]+; (?:[a-z]{2}-[a-z]{2}; )?([^;)]+?)(?: Build/[^;)]*)?[;)]", ua)
    if m:
        model = m.group(1).strip()
        if model.lower() in ("k", "wv"):  # Chrome novo esconde o modelo ("Android 10; K")
            model = ""
    if "JarvisDesktop/" in ua:  # V8.0: o JARVIS.exe (não ouve pelo navegador: o ouvido do PC continua atendendo)
        kind, name = "desktop", "App JARVIS (Windows)"
    elif app:
        kind, name = "app", f"Celular · {model}" if model else "Celular (app JARVIS)"
    elif local:
        kind, name = "pc", "Este PC"
    elif "Android" in ua or "iPhone" in ua:
        kind, name = "browser", f"Navegador do celular{' · ' + model if model else ''}"
    else:
        kind, name = "browser", "Outro computador"
    return {"kind": kind, "name": name, "ip": ip, "since": _time.time()}


SEND_TIMEOUT_S = 2.0  # V8.11: prazo para cada aparelho receber um aviso pelo WebSocket


async def _close_quietly(ws: WebSocket) -> None:
    """Fecha a conexão travada para o aparelho perceber e reconectar (o frontend já faz isso sozinho)."""
    try:
        await asyncio.wait_for(ws.close(code=1011), timeout=SEND_TIMEOUT_S)
    except Exception:  # noqa: BLE001
        pass


class ConnectionManager:
    """Mantém os WebSockets abertos e distribui eventos para todos."""

    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()
        self.meta: dict[int, dict] = {}  # V5.5: aparelho de cada conexão (id(ws) -> dados)

    @staticmethod
    def is_local(ws: WebSocket) -> bool:
        return is_local_conn(ws)

    async def send_local(self, event: dict) -> int:
        """Envia SOMENTE para conexões deste computador (câmera ao vivo nunca vai para a rede)."""
        targets = [ws for ws in list(self.connections) if self.is_local(ws)]
        results = await asyncio.gather(*(self._send(ws, event) for ws in targets))
        return sum(1 for ok in results if ok)

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.connections.add(ws)
        host = ws.client.host if getattr(ws, "client", None) else ""
        try:
            ua = ws.headers.get("user-agent", "")
        except Exception:  # noqa: BLE001
            ua = ""
        self.meta[id(ws)] = describe_device(host, ua, is_local_conn(ws))

    def disconnect(self, ws: WebSocket) -> None:
        self.connections.discard(ws)
        self.meta.pop(id(ws), None)

    def devices(self) -> list[dict]:
        """V5.5: aparelhos conectados agora, sem repetir (várias abas do mesmo aparelho contam uma vez)."""
        seen: dict[str, dict] = {}
        for ws in list(self.connections):
            info = self.meta.get(id(ws))
            if not info:
                continue
            key = f"{info['kind']}|{info['ip']}|{info['name']}"
            if key not in seen or info["since"] < seen[key]["since"]:
                seen[key] = info
        order = {"pc": 0, "app": 1, "browser": 2}
        return sorted(seen.values(), key=lambda d: (order.get(d["kind"], 9), d["since"]))

    async def broadcast(self, event: dict) -> None:
        note_island(event)  # V8.0: a ilha do JARVIS.exe mostra o estado e a última resposta
        targets = list(self.connections)
        if len(targets) == 1:
            await self._send(targets[0], event)
        elif targets:
            # V8.11: todos ao mesmo tempo. Antes um por vez: um celular lento no Wi-Fi atrasava a tela do PC.
            await asyncio.gather(*(self._send(ws, event) for ws in targets))

    async def _send(self, ws: WebSocket, event: dict) -> bool:
        """V8.11: envia com prazo. Conexão morta ou travada sai da lista (o aparelho reconecta sozinho)."""
        try:
            await asyncio.wait_for(ws.send_json(event), timeout=SEND_TIMEOUT_S)
            return True
        except asyncio.TimeoutError:
            log.warning("Aparelho %s não recebeu o aviso em %.1f s; desconectando.",
                        (self.meta.get(id(ws)) or {}).get("name", "?"), SEND_TIMEOUT_S)
            self.disconnect(ws)
            track(_close_quietly(ws))
            return False
        except Exception:  # noqa: BLE001 - conexão morta
            self.disconnect(ws)
            return False


# V8.0: o que a ilha do JARVIS.exe mostra (estado e última resposta), sem depender de WebSocket
ISLAND: dict = {"estado": "idle", "estado_em": 0.0, "resposta": "", "resposta_em": 0.0}
STUCK_STATE_S = 45  # V8.5.0: "Pensando…"/"Falando…" sem novidade por mais que isso (e nada rodando) = parado


def island_state(now: float | None = None) -> str:
    """O estado da ilha, sem ficar preso: se o aviso de "parado" se perdeu (ex.: a voz falhou no meio), depois
    de STUCK_STATE_S sem nada rodando volta para "idle"."""
    import time as _time

    from core import session

    estado = ISLAND.get("estado", "idle")
    if estado == "idle":
        return estado
    now = _time.time() if now is None else now
    if now - float(ISLAND.get("estado_em") or 0) > STUCK_STATE_S and not session.busy:
        return "idle"
    return estado


def note_island(event: dict) -> None:
    import time as _time

    kind = event.get("type") if isinstance(event, dict) else None
    if kind == "state" and isinstance(event.get("state"), str):
        ISLAND["estado"] = event["state"][:20]
        ISLAND["estado_em"] = _time.time()
    elif kind == "response" and isinstance(event.get("text"), str) and event["text"].strip():
        ISLAND["resposta"] = " ".join(event["text"].split())[:220]
        ISLAND["resposta_em"] = _time.time()


manager = ConnectionManager()


# ---------------------------------------------------------------- V4.5: avisos para o celular
# Fila curta (em memória) do que vale notificar no app Android: lembretes, água, gatilhos e Modo
# Torcedor. O app consulta /api/mobile/notifications com a chave de pareamento.
import collections  # noqa: E402
import itertools  # noqa: E402
import time  # noqa: E402

_notify_ids = itertools.count(1)
NOTIFY_FEED: collections.deque[dict] = collections.deque(maxlen=50)
_feed_loaded = False


def _ensure_feed() -> None:
    """V6.5.4: na primeira vez, recupera do disco os avisos de antes do reinício (e continua a numeração)."""
    global _feed_loaded, _notify_ids
    if _feed_loaded:
        return
    _feed_loaded = True
    from modules import phone_feed

    saved = phone_feed.load()
    if saved:
        known = {n["id"] for n in NOTIFY_FEED}
        merged = sorted([n for n in saved if n["id"] not in known] + list(NOTIFY_FEED), key=lambda n: n["id"])
        NOTIFY_FEED.clear()
        NOTIFY_FEED.extend(merged[-NOTIFY_FEED.maxlen:])
    top = max((n["id"] for n in NOTIFY_FEED), default=0)
    _notify_ids = itertools.count(top + 1)


def notify(kind: str, title: str, body: str) -> dict:
    """Guarda um aviso para o celular. kind: reminder | water | trigger | fan | news."""
    _ensure_feed()
    item = {"id": next(_notify_ids), "ts": time.time(), "kind": kind, "title": title, "body": (body or "").strip()}
    NOTIFY_FEED.append(item)
    from modules import phone_feed

    phone_feed.save(NOTIFY_FEED)
    return item


def notifications_since(since: int) -> dict:
    _ensure_feed()
    items = [n for n in NOTIFY_FEED if n["id"] > since]
    latest = NOTIFY_FEED[-1]["id"] if NOTIFY_FEED else 0
    return {"items": items, "latest": latest}


background_tasks: set[asyncio.Task] = set()


service_tasks: set[asyncio.Task] = set()


def track(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    return task


def track_service(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    service_tasks.add(task)
    task.add_done_callback(service_tasks.discard)
    return task


async def doing(text: str) -> None:
    """V9.1.2: conta para as telas o que o JARVIS está fazendo ("pensando com a IA", "esperando o pedido anterior").

    Antes a central só mostrava PROCESSANDO e, depois de 25 s, "Está demorando", sem dizer com o quê.
    """
    from core import session

    session.doing = (text or "")[:120]
    try:
        await manager.broadcast({"type": "doing", "text": session.doing})
    except Exception:  # noqa: BLE001 - o aviso na tela nunca atrapalha o pedido
        log.debug("Aviso do que estou fazendo não foi para a tela", exc_info=True)

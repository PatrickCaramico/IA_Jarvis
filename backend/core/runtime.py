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


class ConnectionManager:
    """Mantém os WebSockets abertos e distribui eventos para todos."""

    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()

    @staticmethod
    def is_local(ws: WebSocket) -> bool:
        host = ws.client.host if getattr(ws, "client", None) else ""
        return host in LOCAL_HOSTS

    async def send_local(self, event: dict) -> int:
        """Envia SOMENTE para conexões deste computador (câmera ao vivo nunca vai para a rede)."""
        sent = 0
        for ws in list(self.connections):
            if not self.is_local(ws):
                continue
            try:
                await ws.send_json(event)
                sent += 1
            except Exception:  # noqa: BLE001 - conexão morta
                self.disconnect(ws)
        return sent

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.connections.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.connections.discard(ws)

    async def broadcast(self, event: dict) -> None:
        for ws in list(self.connections):
            try:
                await ws.send_json(event)
            except Exception:  # noqa: BLE001 - conexão morta
                self.disconnect(ws)


manager = ConnectionManager()


# ---------------------------------------------------------------- V4.5: avisos para o celular
# Fila curta (em memória) do que vale notificar no app Android: lembretes, água, gatilhos e Modo
# Torcedor. O app consulta /api/mobile/notifications com a chave de pareamento.
import collections  # noqa: E402
import itertools  # noqa: E402
import time  # noqa: E402

_notify_ids = itertools.count(1)
NOTIFY_FEED: collections.deque[dict] = collections.deque(maxlen=50)


def notify(kind: str, title: str, body: str) -> dict:
    """Guarda um aviso para o celular. kind: reminder | water | trigger | fan."""
    item = {"id": next(_notify_ids), "ts": time.time(), "kind": kind, "title": title, "body": (body or "").strip()}
    NOTIFY_FEED.append(item)
    return item


def notifications_since(since: int) -> dict:
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

"""V9.0: FILA DE PEDIDOS. Antes, um pedido feito enquanto o JARVIS pensava em outro levava "já está ocupado"
(erro 409) e se perdia: o ouvido apitava e o celular mostrava erro. Agora ele espera a vez numa fila curta
(até MAX_WAITING pedidos, por até WAIT_LIMIT_S segundos) e é atendido na ordem em que chegou.

O "cancelar" (botão ou "Jarvis, para") esvazia a fila também. Quem espera é avisado na tela ("na fila").
"""
from __future__ import annotations

import asyncio
import itertools
import logging
import time

from core import runtime, session

log = logging.getLogger("jarvis.turn_queue")

MAX_WAITING = 3
WAIT_LIMIT_S = 60.0
POLL_S = 0.1

_waiting: list[int] = []
_tickets = itertools.count(1)
_epoch = 0


def waiting() -> int:
    return len(_waiting)


def cancel_all() -> None:
    """Cancelar: todo mundo que esperava desiste (devolve "canceled")."""
    global _epoch
    _epoch += 1
    _waiting.clear()


async def _announce(message: str) -> None:
    try:
        await runtime.manager.broadcast({"type": "queued", "text": message[:120], "waiting": len(_waiting)})
    except Exception:  # noqa: BLE001 - o aviso na tela nunca atrapalha a fila
        log.debug("Aviso de fila não foi para a tela", exc_info=True)


async def wait_turn(message: str) -> str:
    """Espera a vez. "ok" = é a vez dele (quem chama marca session.busy na hora, sem await no meio);
    "full" = fila cheia; "timeout" = esperou demais; "canceled" = o usuário cancelou."""
    if len(_waiting) >= MAX_WAITING:
        return "full"
    ticket, epoch = next(_tickets), _epoch
    _waiting.append(ticket)
    await _announce(message)
    deadline = time.monotonic() + WAIT_LIMIT_S
    try:
        while True:
            if epoch != _epoch:
                return "canceled"
            if _waiting and _waiting[0] == ticket and not session.busy:
                _waiting.pop(0)
                log.info("Pedido da fila liberado: %s", message[:80])
                return "ok"
            if time.monotonic() >= deadline:
                return "timeout"
            await asyncio.sleep(POLL_S)
    finally:
        if ticket in _waiting:
            _waiting.remove(ticket)

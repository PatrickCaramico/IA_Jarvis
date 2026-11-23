"""V8.13: STREAMING da IA para o chat.

Antes, o chat só mostrava a resposta quando a IA terminava de escrever tudo (1 a 5 s olhando para "pensando…").
Agora cada pedaço que a IA devolve vai para a tela na hora, pelo WebSocket:

    {"type": "response_stream", "seq": 7, "text": "texto acumulado até agora"}
    {"type": "response_stream", "seq": 8, "text": "", "reset": true}   # trocou de IA no meio: recomeça

Manda sempre o texto ACUMULADO (não só o pedaço novo): se dois avisos chegarem fora de ordem, a tela fica com
o de maior "seq" e nada se perde. A resposta final continua vindo no "response" de sempre (ela manda).

A IA roda numa thread (asyncio.to_thread). O canal vive numa ContextVar e só aceita texto da thread dona dele:
uma Skill chamada pela IA que pergunte algo à IA (ask_text, em outra thread) não aparece no chat. Depois que o
turno acaba (ou estoura o prazo), o canal fecha: a thread que ficou para trás não mexe mais na tela.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from contextvars import ContextVar
from typing import Callable, Optional

log = logging.getLogger("jarvis.llm.stream")

MIN_INTERVAL_S = 0.06  # no máximo ~16 avisos por segundo (a tela não precisa de mais)


class StreamSink:
    def __init__(self, loop: asyncio.AbstractEventLoop, emit: Callable[[dict], None],
                 min_interval: float = MIN_INTERVAL_S) -> None:
        self.loop, self.emit, self.min_interval = loop, emit, min_interval
        self.owner: Optional[int] = None
        self.text = ""
        self.seq = 0
        self.closed = False
        self._last = 0.0
        self._lock = threading.Lock()

    def claim(self) -> None:
        """A thread que chama a IA vira a dona do canal."""
        self.owner = threading.get_ident()

    def active(self) -> bool:
        return not self.closed and self.owner == threading.get_ident()

    def begin(self) -> None:
        """Nova tentativa (outra IA, outro modelo ou a frase depois das Skills): a tela recomeça do zero."""
        if not self.active():
            return
        with self._lock:
            if self.text:
                self.text = ""
                self._send(reset=True)

    def delta(self, piece: Optional[str]) -> None:
        if not piece or not self.active():
            return
        with self._lock:
            self.text += piece
            if time.monotonic() - self._last >= self.min_interval:
                self._send()

    def close(self) -> None:
        self.closed = True

    def _send(self, reset: bool = False) -> None:
        self.seq += 1
        self._last = time.monotonic()
        event = {"type": "response_stream", "seq": self.seq, "text": self.text}
        if reset:
            event["reset"] = True
        try:
            self.loop.call_soon_threadsafe(self._deliver, event)
        except RuntimeError:  # laço já fechado (desligando): só não mostra
            self.closed = True

    def _deliver(self, event: dict) -> None:
        # o que já estava na fila sai mesmo depois do close(): o close() só impede pedaços NOVOS da thread
        try:
            self.emit(event)
        except Exception:  # noqa: BLE001 - a tela não pode derrubar a resposta
            log.debug("Falha ao mandar o pedaço da resposta", exc_info=True)


_sink_var: ContextVar[Optional[StreamSink]] = ContextVar("jarvis_llm_stream", default=None)


def current() -> Optional[StreamSink]:
    """O canal desta chamada, só se a thread atual é a dona (senão a IA responde sem streaming)."""
    sink = _sink_var.get()
    return sink if sink is not None and sink.active() else None


def use(sink: Optional[StreamSink]):
    return _sink_var.set(sink)


def reset(token) -> None:
    _sink_var.reset(token)

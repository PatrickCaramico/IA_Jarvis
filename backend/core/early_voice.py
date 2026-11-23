"""V9.0: VOZ QUE COMEÇA ANTES. Antes a voz só começava quando a IA terminava de escrever a resposta inteira
(mais a síntese): numa resposta longa, 3 a 6 s de silêncio com o texto já correndo na tela. Agora, assim que
as primeiras frases completas chegam pelo streaming (V8.13), elas já vão para a voz; o resto é falado em
seguida, sem repetir o começo.

Regras:
  - só frases INTEIRAS (ponto, exclamação ou interrogação seguidos de mais texto), entre MIN_HEAD e MAX_HEAD
    caracteres: resposta curta continua indo inteira, com a entonação contínua da V6.1;
  - "Sr.", "Dr.", "etc." e itens numerados ("1.") não contam como fim de frase;
  - se a IA recomeçar a resposta no meio (trocou de IA ou chamou uma Skill) depois de a voz já ter começado,
    a resposta final é falada inteira (melhor repetir o começo do que falar pela metade).
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional

log = logging.getLogger("jarvis.early_voice")

MIN_HEAD = 40
MAX_HEAD = 240
_END = re.compile(r"[.!?](?=\s+\S)")
_NOT_END = re.compile(r"(?:\b(?:sr|sra|dr|dra|srta|etc|ex|obs|av|n|nº|p|pag|vs)|\b\d+|\b[A-Za-z])$", re.I)


def first_sentences(text: str) -> str:
    """As frases completas do começo (até MAX_HEAD caracteres), ou "" se ainda não dá para começar."""
    text = text or ""
    if text.lstrip().startswith(("```", "|", "-", "*", "#")):
        return ""  # lista, tabela ou código: deixa a resposta inteira chegar
    best = ""
    for m in _END.finditer(text):
        end = m.end()
        if end > MAX_HEAD:
            break
        if _NOT_END.search(text[:m.start()]):
            continue
        best = text[:end]
    return best.strip() if len(best.strip()) >= MIN_HEAD else ""


def _clean(text: str) -> str:
    from modules import tts

    return tts._clean_for_speech(text or "")


class EarlyVoice:
    """Acompanha o streaming de um turno e começa a falar o começo da resposta."""

    def __init__(self) -> None:
        self.head = ""
        self.task: Optional[asyncio.Task] = None
        self.restarted = False

    def feed(self, event: dict) -> None:
        """Recebe cada {"type": "response_stream", "text": ..., "reset"?} (no laço principal)."""
        if event.get("reset"):
            if self.task is not None:
                self.restarted = True
            return
        if self.task is not None:
            return
        head = first_sentences(str(event.get("text", "")))
        if not head:
            return
        from core import runtime, speech

        self.head = head
        self.task = runtime.track(speech.speak(head, release_busy=False, idle_after=False))
        log.info("Voz começou antes do fim da resposta (%d caracteres)", len(head))

    def rest(self, final: str) -> str:
        """O que falta falar da resposta final."""
        if self.task is None:
            return final
        full, head = _clean(final), _clean(self.head)
        if not self.restarted and full.startswith(head):
            return full[len(head):].strip()
        return final  # mudou no meio: fala tudo

    def cancel(self) -> None:
        if self.task is not None and not self.task.done():
            self.task.cancel()

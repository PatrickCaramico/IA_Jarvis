"""V6.7.1: avisar em todos os aparelhos, como o "anúncio" da Alexa.

"Jarvis, avisa em todos os aparelhos que o almoço está pronto"
"Jarvis, anuncia que estou saindo"
"Jarvis, avisa todo mundo que o filme vai começar"
"Jarvis, faz um anúncio: reunião em 5 minutos"

O texto aparece em todas as telas, é falado no PC e nos celulares com a central aberta, e o app
(fechado) recebe uma notificação.
"""
from __future__ import annotations

import re
from typing import Optional

from modules.quick_replies import _norm

_PATTERNS = [
    re.compile(r"^(?:jarvis\s+)?(?:avisa|avise|anuncia|anuncie|fala|fale|diz|diga)\s+(?:em|para|pra|nos|a)\s+"
               r"(?:todos os aparelhos|todos os dispositivos|todas as telas|todo mundo|todos|casa toda|toda a casa)\s*(?:que\s+|:\s*)?(.+)$"),
    re.compile(r"^(?:jarvis\s+)?(?:avisa|avise)\s+(?:todo mundo|todos)\s+(?:que\s+)?(.+)$"),
    re.compile(r"^(?:jarvis\s+)?(?:anuncia|anuncie|faz um anuncio|faca um anuncio|faz um aviso geral)\s*(?:que\s+|:\s*)?(.+)$"),
]


def parse(message: str) -> Optional[str]:
    """Texto do aviso (com acentos, como foi dito) ou None."""
    norm = _norm(message or "")
    for pattern in _PATTERNS:
        m = pattern.match(norm)
        if m and m.group(1).strip():
            # recorta o mesmo trecho no texto original (mantém acentos e maiúsculas)
            words = len(m.group(1).split())
            original = re.sub(r"[.!?]+$", "", (message or "").strip()).split()
            text = " ".join(original[-words:]) if words <= len(original) else m.group(1)
            text = text.strip(" :,")
            return text[:1].upper() + text[1:]
    return None


async def handle_voice(message: str) -> Optional[str]:
    text = parse(message)
    if not text:
        return None
    from core import speech

    await speech.announce_everywhere(text if text.endswith((".", "!", "?")) else text + ".")
    return "Avisado em todos os aparelhos, senhor."

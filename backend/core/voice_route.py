"""V5.7: a voz sai no aparelho que fez o pedido.

Antes, toda resposta tocava na caixa de som do PC, e o celular (com o alto-falante ligado) tocava junto:
o mesmo áudio em dois lugares. Agora a central manda em cada pedido quem é ela (cabeçalhos
X-Jarvis-Client = id da aba, X-Jarvis-Device = "app" ou "web"):

- pedido do app do celular ou de outro aparelho da rede: a voz vai SÓ para aquele aparelho
  (evento "speak_on_device"; ele busca o MP3 em /api/tts e toca), e o PC fica em silêncio;
- pedido feito no próprio PC (central local ou pelo site): a voz sai no PC, como sempre.

O destino vale para o pedido inteiro, inclusive o que ele dispara em segundo plano (o briefing em
etapas), porque fica numa ContextVar que as tarefas criadas a partir do pedido herdam. Avisos que não
vêm de um pedido (alarmes, lembretes, água) continuam no PC.
"""
from __future__ import annotations

import asyncio
import re
from contextvars import ContextVar
from typing import Optional

_target: ContextVar[Optional[str]] = ContextVar("jarvis_voice_target", default=None)
_CLIENT_RE = re.compile(r"^[A-Za-z0-9_-]{6,64}$")


def target_for(client_id: str, device: str, is_local: bool) -> Optional[str]:
    """Id do aparelho que deve falar, ou None para o PC."""
    if not client_id or not _CLIENT_RE.match(client_id):
        return None
    if device == "pc":
        return None  # o aparelho escolheu "voz no PC"
    if device == "app" or not is_local:
        return client_id
    return None


def set_target(client_id: Optional[str]):
    return _target.set(client_id)


def reset(token) -> None:
    _target.reset(token)


def current() -> Optional[str]:
    return _target.get()


# V6.5.1: o aparelho avisa quando terminou de tocar cada fala (POST /api/tts/played). Antes o PC só
# "chutava" a duração e passava para o próximo card: no celular, voz e tela iam se desencontrando.
_played: dict[str, "asyncio.Event"] = {}
playing_on_device: str | None = None  # V6.5.3: fala tocando agora no aparelho (pular/cancelar cala ela)
ACK_SLACK_SECONDS = 6.0  # folga para o aparelho baixar a voz pela rede (túnel, dados móveis)


def new_say_id() -> str:
    import secrets

    return secrets.token_urlsafe(8)


def expect(say_id: str):
    ev = asyncio.Event()
    _played[say_id] = ev
    return ev


def mark_played(say_id: str) -> bool:
    ev = _played.pop(say_id, None)
    if ev is None:
        return False
    ev.set()
    return True


def forget(say_id: str) -> None:
    _played.pop(say_id, None)


def estimate_seconds(text: str) -> float:
    """Quanto a fala dura no aparelho (para o briefing em etapas manter o ritmo sem a caixa do PC)."""
    words = len((text or "").split())
    return max(1.2, min(40.0, words / 2.6 + 0.6))

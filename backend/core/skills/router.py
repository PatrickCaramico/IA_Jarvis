"""V8.11: entrada das Skills no motor de conversa (core/turns.py e modules/sentinel.py chamam daqui)."""
from __future__ import annotations

import logging
from typing import Optional

from core.skills import executor, registry
from core.skills.base import SkillContext, SkillResult

log = logging.getLogger("jarvis.skills")


def _norm(text: str) -> str:
    from modules.quick_replies import _norm as norm

    return norm(text or "")


def _remote() -> bool:
    from core import voice_route

    return voice_route.is_remote()


async def try_fast_path(message: str, user_name: str = "", public_only: bool = False) -> Optional[SkillResult]:
    """Se a frase bate com o gatilho de alguma skill, executa e devolve o resultado (sem IA). Senão, None."""
    norm = _norm(message)
    if not norm:
        return None
    try:
        hit = registry.match(norm, message, public_only=public_only)
    except Exception:  # noqa: BLE001 - o catálogo nunca derruba a conversa
        log.exception("Falha ao procurar skill")
        return None
    if hit is None:
        return None
    sk, args = hit
    from core import voice_route

    ctx = SkillContext(message=message, norm=norm, origin="voice", user_name=user_name,
                       device=voice_route.current(), remote=_remote())
    return await executor.execute(sk.name, args, ctx)

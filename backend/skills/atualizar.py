"""Atualizar o JARVIS por voz (V9.5.4).

Antes: subia o aviso "chegou a versão X, atualizo sozinho em dois minutos" e, se o senhor dissesse "pode atualizar" ou
"atualiza agora", ele não entendia (só os botões ATUALIZAR AGORA e ADIAR 1 H da tela funcionavam). Agora:
  - com o aviso na tela: "atualiza agora" / "pode atualizar" = o botão ATUALIZAR AGORA;
    "adia a atualização" / "atualiza depois" = o botão ADIAR 1 H;
  - sem aviso: "atualiza o JARVIS" confere se há versão nova e atualiza (só no próprio PC, como o botão ATUALIZAR);
    sem versão nova, diz que já está em dia.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional

from core.skills import Permission, SkillContext, SkillResult, skill

log = logging.getLogger("jarvis.skill.atualizar")

_FILLER = re.compile(r"\b(?:jarvis|por favor|pfv|ai|entao|ja que|senhor)\b")
_NOW = re.compile(
    r"^(?:(?:pode|podes|pode ja|vamos|vai|bora|quero|quero que)\s+)?"
    r"(?:atualiza|atualize|atualizar|atualizando|faz a atualizacao|faca a atualizacao|instala a atualizacao|"
    r"instale a atualizacao|baixa a atualizacao|baixa a versao nova|instala a versao nova)"
    r"(?:\s+(?:o|os|a|voce|se))?(?:\s+(?:jarvis|sistema|sistemas|tudo|versao nova))?"
    r"(?:\s+(?:agora|ja|agora mesmo|sim))?$"
)
_LATER = re.compile(
    r"^(?:(?:pode|podes)\s+)?(?:adia|adie|adiar|deixa|deixe)\s+(?:a\s+)?atualizacao(?:\s+(?:pra|para)\s+depois|\s+depois)?$"
    r"|^(?:atualiza|atualize|atualizar)\s+(?:mais tarde|depois)$"
    r"|^(?:nao atualiza|nao atualize)(?:\s+agora)?$"
)


def _clean(norm: str) -> str:
    text = _FILLER.sub(" ", norm)
    return re.sub(r"\s+", " ", text).strip(" ,.!?")


def _parse(norm: str, _original: str) -> Optional[dict]:
    text = _clean(norm)
    if not text or len(text.split()) > 7:
        return None
    if _LATER.match(text):
        return {"acao": "adiar"}
    if _NOW.match(text):
        return {"acao": "agora"}
    return None


async def _start_update() -> None:
    """Baixa e reinicia (o mesmo caminho da atualização automática); a central acompanha a tela de atualização."""
    from core import runtime
    from routes.system import perform_update

    try:
        res = await perform_update(announce=False)
    except Exception:  # noqa: BLE001 - falha visível no log e na tela
        log.exception("Atualização por voz falhou")
        await runtime.manager.broadcast({"type": "error", "message": "Não consegui atualizar agora. Tente pelo botão ATUALIZAR."})
        return
    if res.get("status") == "restarting":
        await runtime.manager.broadcast({"type": "update_started", "boot_id": res.get("boot_id"), "before": res.get("before"),
                                         "after": res.get("after"), "changed": res.get("changed"),
                                         "versao_nova": res.get("versao_nova", ""), "destaques": res.get("destaques", [])})
        return
    msg = res.get("message") or "Não consegui atualizar agora."
    await runtime.manager.broadcast({"type": "error", "message": msg})


@skill(
    name="atualizar_jarvis",
    title="atualizar o JARVIS",
    description="Atualiza o JARVIS para a versão mais nova agora (ou adia a atualização avisada). Use quando o usuário "
                "pedir para atualizar o JARVIS/o sistema ou responder ao aviso de atualização.",
    permission=Permission.ACTION,
    timeout=30,
    parse=_parse,
    params={
        "type": "object",
        "properties": {"acao": {"type": "string", "enum": ["agora", "adiar"],
                                "description": "agora = atualizar já; adiar = esperar 1 hora."}},
        "required": ["acao"],
    },
    examples=["pode atualizar", "atualiza agora", "adia a atualização"],
)
async def atualizar_jarvis(ctx: SkillContext, acao: str) -> SkillResult:
    from core import runtime
    from modules import auto_update, self_update

    notice = auto_update.pending_notice()
    if acao == "adiar":
        if not notice:
            return SkillResult(speech="Não há atualização marcada agora, senhor.")
        auto_update.postpone()
        return SkillResult(speech="Certo, senhor. Deixo a atualização para daqui a uma hora.")

    if notice:  # o aviso já está na tela: é o ATUALIZAR AGORA
        auto_update.update_now()
        return SkillResult(speech="Atualizando agora, senhor. Volto em instantes.")

    if ctx.remote:  # como o botão ATUALIZAR: só no próprio PC
        return SkillResult(speech="A atualização só pode ser pedida no próprio PC, senhor.")
    try:
        info = await asyncio.to_thread(self_update.check, True)
    except Exception:  # noqa: BLE001
        log.exception("Não consegui procurar versão nova por voz")
        return SkillResult(speech="Não consegui procurar a versão nova agora, senhor. Tente de novo em instantes.")
    if not info.get("available"):
        return SkillResult(speech="Já estou na versão mais nova, senhor.")
    runtime.track(_start_update())
    latest = info.get("latest") or "nova"
    return SkillResult(speech=f"Atualizando para a versão {latest}, senhor. Volto em instantes.")

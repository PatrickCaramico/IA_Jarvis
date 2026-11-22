"""Skill do microfone (V8.11): "microfone só no botão" ou "pode ficar me ouvindo".

Microfone só no botão (padrão): nada fica ouvindo sozinho. O microfone abre quando o senhor toca no 🎙 (ou na tecla
do app do Windows) e fecha ao terminar a frase. Assim o Windows não trata o PC como "em chamada": a música no fone
Bluetooth não fica abafada/distorcida e os outros sons não abaixam.
Ouvindo sempre: "Jarvis, ..." sem tocar em nada (central, bloqueio, palmas e ouvido offline).
"""
from __future__ import annotations

import re
from typing import Optional

from core.skills import Permission, SkillContext, SkillResult, skill

_PUSH = re.compile(r"\b(?:microfone|mic)\s+(?:so|somente|apenas)\s+(?:no|quando\s+eu\s+apertar\s+o|pelo)\s+botao\b"
                   r"|\b(?:para|pare|parar)\s+de\s+(?:me\s+)?(?:ouvir|escutar)\s+(?:o\s+tempo\s+todo|toda\s+hora|sempre)\b"
                   r"|\b(?:desliga|desligue|desativa|desative)\s+(?:a\s+)?escuta\s+continua\b")
_ALWAYS = re.compile(r"\b(?:pode\s+)?(?:fica|ficar|fique)\s+(?:me\s+)?(?:ouvindo|escutando)\s+(?:o\s+tempo\s+todo|sempre|toda\s+hora)\b"
                     r"|\b(?:liga|ligue|ativa|ative)\s+(?:a\s+)?escuta\s+continua\b"
                     r"|\b(?:microfone|mic)\s+sempre\s+(?:ligado|ativo|ouvindo)\b")


def _parse(norm: str, _original: str) -> Optional[dict]:
    if _PUSH.search(norm):
        return {"so_no_botao": True}
    if _ALWAYS.search(norm):
        return {"so_no_botao": False}
    return None


@skill(
    name="modo_microfone",
    title="mudar o modo do microfone",
    description=("Escolhe se o microfone fica só no botão (padrão; não atrapalha música nem chamadas) ou ouvindo o "
                 "tempo todo a palavra de ativação."),
    permission=Permission.ACTION,
    timeout=5,
    parse=_parse,
    params={"type": "object", "required": ["so_no_botao"], "properties": {"so_no_botao": {"type": "boolean"}}},
    examples=["microfone só no botão", "pode ficar me ouvindo o tempo todo"],
)
async def modo_microfone(ctx: SkillContext, so_no_botao: bool) -> SkillResult:
    import asyncio

    from modules import prefs

    await asyncio.to_thread(prefs.update, mic_push_to_talk=bool(so_no_botao))
    await ctx.broadcast({"type": "prefs_updated", "mic_push_to_talk": bool(so_no_botao)})
    if so_no_botao:
        return SkillResult(speech="Certo, senhor: o microfone só abre quando o senhor tocar no botão. Nada fica ouvindo "
                                  "sozinho, então a música não é mais atrapalhada.")
    return SkillResult(speech="Certo, senhor: volto a ouvir o tempo todo; é só dizer Jarvis. Se a música no fone ficar "
                              "abafada, diga: microfone só no botão.")

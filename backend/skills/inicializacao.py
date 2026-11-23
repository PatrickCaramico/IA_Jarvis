"""Skill de inicialização (V8.11): o JARVIS liga junto com o Windows?

Frases:
- "liga o JARVIS junto com o Windows", "inicia com o Windows", "quero que você ligue sozinho"
- "não liga mais com o Windows", "para de iniciar com o Windows"
- "você liga junto com o Windows?"
O atalho fica na pasta Inicializar do usuário (modules/autostart.py); o guardião mantém o JARVIS no ar depois.
"""
from __future__ import annotations

import re
from typing import Optional

from core.skills import Permission, SkillContext, SkillResult, skill

_WIN = r"(?:junto\s+com\s+o\s+|com\s+o\s+|quando\s+(?:o\s+)?(?:pc|computador|windows)\s+ligar|ao\s+ligar\s+o\s+(?:pc|computador))\s*(?:windows|pc|computador)?"
_OFF = re.compile(r"\b(?:nao\s+(?:liga|ligue|inicia|inicie|abre|abra)\s+mais|para\s+de\s+(?:ligar|iniciar|abrir)|"
                  r"desliga\s+o\s+inicio\s+automatico|tira\s+da\s+inicializacao)\b")
_ON = re.compile(r"\b(?:liga|ligue|ligar|inicia|inicie|iniciar|abre|abra|abrir)\s+(?:o\s+jarvis\s+|voce\s+|sozinho\s+)?" + _WIN
                 + r"|\b(?:quero\s+que\s+(?:voce|o\s+jarvis)\s+(?:ligue|inicie)\s+sozinho)\b"
                 r"|\bcoloca\s+(?:o\s+jarvis\s+)?na\s+inicializacao\b")
_ASK = re.compile(r"^(?:jarvis\s+)?(?:voce|o\s+jarvis)\s+(?:ja\s+)?(?:liga|inicia|abre)\b")


def _parse(norm: str, _original: str) -> Optional[dict]:
    if not re.search(r"\b(?:windows|inicializacao|inicio automatico|sozinho)\b", norm):
        return None
    if _OFF.search(norm):
        return {"acao": "desligar"}
    if _ASK.search(norm):
        return {"acao": "consultar"}
    if _ON.search(norm):
        return {"acao": "ligar"}
    return None


@skill(
    name="iniciar_com_windows",
    title="ligar junto com o Windows",
    description="Liga, desliga ou consulta se o JARVIS inicia sozinho quando o usuário entra no Windows.",
    permission=Permission.ACTION,
    allow_remote=False,
    timeout=25,
    parse=_parse,
    params={"type": "object", "required": ["acao"], "properties": {
        "acao": {"type": "string", "enum": ["ligar", "desligar", "consultar"]}}},
    examples=["liga o JARVIS junto com o Windows", "não liga mais com o Windows"],
)
def iniciar_com_windows(ctx: SkillContext, acao: str) -> SkillResult:
    from modules import autostart

    st = autostart.status()
    if not st["available"]:
        return SkillResult(ok=False, speech="Ligar junto com o Windows só funciona no PC com Windows, senhor.")
    if acao == "consultar":
        return SkillResult(speech="Sim, senhor: ligo sozinho quando o senhor entra no Windows." if st["enabled"]
                           else "Ainda não, senhor. Se quiser, diga: liga o JARVIS junto com o Windows.")
    if acao == "ligar":
        res = autostart.enable()
        if not res.get("ok"):
            return SkillResult(ok=False, speech="Não consegui criar o atalho na inicialização do Windows, senhor. "
                                                "Tente pelo Instalar-JARVIS-no-Windows.bat.")
        return SkillResult(speech="Feito, senhor: a partir de agora eu ligo sozinho, em segundo plano, quando o senhor "
                                  "entrar no Windows. E se eu cair, o guardião me liga de novo.")
    res = autostart.disable()
    if not res.get("ok"):
        return SkillResult(ok=False, speech="Não consegui tirar o atalho da inicialização, senhor.")
    return SkillResult(speech="Certo, senhor: não ligo mais sozinho com o Windows. Para me ligar, use o Iniciar-JARVIS.")

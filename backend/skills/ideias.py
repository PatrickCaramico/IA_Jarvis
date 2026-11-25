"""Bloco de ideias por voz (V9.5.6).

  - "anota uma ideia: app de receitas com a câmera" / "tive uma ideia: ..." -> salva no 💡 BLOCO DE IDEIAS;
  - "nova ideia de projeto: ..." / "anota um projeto: ..." -> salva já marcada como projeto (entra no briefing do dia);
  - "quais são minhas ideias" / "quais são meus projetos" -> lê os títulos.
A mesma lista do botão CONTROLES › 💡 BLOCO DE IDEIAS (modules/ideas.py).
"""
from __future__ import annotations

import re
from typing import Optional

from core.skills import Permission, SkillContext, SkillResult, skill

_ADD = re.compile(
    r"^(?:jarvis\s+)?(?:(?:anota|anote|salva|salve|guarda|guarde|registra|registre)\s+(?:uma\s+|um\s+|essa\s+|esse\s+|a\s+|o\s+)?"
    r"(?P<kind1>ideia(?:\s+de\s+projeto)?|projeto)|(?:tive|tenho)\s+uma\s+(?P<kind2>ideia)|nova\s+(?P<kind3>ideia(?:\s+de\s+projeto)?|projeto))"
    r"\s*[:,-]?\s+(?:que\s+)?(?P<texto>.{3,})$"
)
_LIST = re.compile(
    r"^(?:jarvis\s+)?(?:quais\s+(?:sao\s+)?(?:as\s+|os\s+)?minhas\s+ideias|quais\s+(?:sao\s+)?(?:os\s+)?meus\s+projetos|"
    r"(?:le|leia|mostra|mostre)\s+(?:as\s+|os\s+)?(?:minhas\s+ideias|meus\s+projetos)|meu\s+bloco\s+de\s+ideias|"
    r"o\s+que\s+tem\s+no\s+(?:meu\s+)?bloco\s+de\s+ideias)$"
)


def _parse_add(norm: str, original: str) -> Optional[dict]:
    m = _ADD.match(norm.strip(" .!?"))
    if not m:
        return None
    kind = m.group("kind1") or m.group("kind2") or m.group("kind3") or ""
    # o texto sai da frase ORIGINAL (com acentos e maiúsculas): pula as mesmas palavras do começo do pedido
    prefix_words = len(norm.strip(" .!?")[: m.start("texto")].split())
    text = " ".join(str(original or "").split()[prefix_words:]).strip(" .:,;-—")
    return {"texto": text or m.group("texto"), "projeto": "projeto" in kind}


@skill(
    name="anotar_ideia",
    title="anotar a ideia",
    description="Salva uma ideia ou um projeto no bloco de ideias do usuário (os projetos entram no briefing do dia).",
    permission=Permission.ACTION,
    timeout=8,
    parse=_parse_add,
    params={
        "type": "object",
        "properties": {
            "texto": {"type": "string", "description": "A ideia, com as palavras do usuário."},
            "projeto": {"type": "boolean", "description": "True quando ele disser que é um projeto."},
        },
        "required": ["texto"],
    },
    examples=["anota uma ideia: app de receitas com a câmera", "nova ideia de projeto: site do churrasco"],
)
async def anotar_ideia(ctx: SkillContext, texto: str, projeto: bool = False) -> SkillResult:
    import asyncio

    from modules import ideas

    try:
        idea = await asyncio.to_thread(ideas.add_idea, texto, "", bool(projeto))
    except ValueError:
        return SkillResult(ok=False, speech="Não entendi a ideia, senhor. Pode repetir?")
    await ctx.broadcast({"type": "ideas_updated"})
    if idea["projeto"]:
        return SkillResult(speech="Projeto anotado no bloco de ideias, senhor. Ele entra no briefing de amanhã.")
    return SkillResult(speech="Ideia anotada no bloco de ideias, senhor.")


@skill(
    name="ler_ideias",
    title="ler o bloco de ideias",
    description="Lê os títulos das ideias e projetos do bloco de ideias do usuário.",
    permission=Permission.READ,
    timeout=8,
    triggers=[_LIST.pattern],
    params={"type": "object", "properties": {}},
    examples=["quais são meus projetos", "quais são minhas ideias"],
)
async def ler_ideias(ctx: SkillContext) -> SkillResult:
    import asyncio

    from modules import ideas

    items = await asyncio.to_thread(ideas.projects, 5)
    if not items:
        return SkillResult(speech="Seu bloco de ideias está vazio, senhor. Diga, por exemplo: anota uma ideia, e o que pensou.")
    rows = [{"label": "📌 projeto" if i.get("projeto") else "💡 ideia", "value": i.get("titulo") or "sem título"} for i in items]
    card = {"type": "skill", "data": {"tag": "BLOCO DE IDEIAS", "source": f"{len(items)} em destaque", "rows": rows}}
    fala = ideas.briefing_speech(items).replace("No seu bloco de ideias, ", "")
    return SkillResult(speech=fala[:1].upper() + fala[1:], cards=[card])  # (capitalize() baixava os títulos)

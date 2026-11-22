"""Skill "ver as habilidades" (V8.11): o JARVIS diz o que sabe fazer e abre a aba ⚡ HABILIDADES da Central.

Frases: "quais são suas habilidades?", "mostra suas habilidades", "abre a central de habilidades".
A aba abre no aparelho que pediu (evento open_panel para a tela dele).
"""
from __future__ import annotations

from core.skills import Permission, SkillContext, SkillResult, skill

GROUP_NAMES = {"workspace": "janelas e monitores", "system_guard": "o PC", "context_autopilot": "agenda e reuniões",
               "deep_brief": "dossiês", "clipboard_ai": "texto copiado", "dia_a_dia": "conversões e senhas"}
HIDDEN = {"habilidades", "abrir_programa"}


def groups(skills) -> list[str]:
    out: list[str] = []
    for sk in skills:
        key = sk.module.split(".")[1] if sk.module.startswith("skills.") else sk.module
        if key in HIDDEN:
            continue
        name = GROUP_NAMES.get(key, key.replace("_", " "))
        if name not in out:
            out.append(name)
    return out


@skill(
    name="ver_habilidades",
    title="ver as habilidades",
    description="Diz quais habilidades (skills) o JARVIS tem ligadas e abre a lista na tela.",
    permission=Permission.READ,
    timeout=5,
    triggers=[r"\b(?:quais|que)\s+(?:sao\s+)?(?:as\s+)?(?:suas|tuas)\s+habilidades\b",
              r"\b(?:mostra|mostre|abre|abra|lista|liste)\s+(?:as\s+)?(?:suas\s+|minhas\s+|a central de\s+)?habilidades\b"],
    examples=["quais são suas habilidades?"],
)
async def ver_habilidades(ctx: SkillContext) -> SkillResult:
    from core.skills import registry
    from skills.workspace.layouts import spoken_list

    on = [s for s in registry.available() if s.name != "ver_habilidades"]
    names = groups(on)
    await ctx.broadcast({"type": "open_panel", "panel": "agents", "agent": "habilidades", "client_id": ctx.device})
    if not names:
        return SkillResult(speech="Não há habilidades ligadas agora, senhor. Abri a lista para o senhor escolher.")
    return SkillResult(speech=f"Tenho {len(on)} habilidades ligadas, senhor: {spoken_list(names)}. Abri a lista na "
                              "tela; dá para ligar, desligar e testar cada uma.")

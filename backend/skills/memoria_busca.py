"""Memória pesquisável (V9.0): procura em tudo o que o JARVIS guarda de você, na hora e sem IA.

Frases:
- "o que eu te falei sobre a viagem?", "o que eu anotei sobre o dentista?", "o que eu copiei de endereço?"
- "procura na memória sobre o carro", "busca nas minhas conversas a senha do wifi"
- "quando eu falei do aniversário da minha mãe?"
Procura em: conversas (todas, não só as 20 últimas), memórias ("lembre que…"), tarefas, lembretes e copiados.
O índice é local (modules/memory_index.py); nada sai do PC.
"""
from __future__ import annotations

import re
from typing import Optional

from core.skills import Permission, SkillContext, SkillResult, skill

_PATTERNS = [
    re.compile(r"^(?:jarvis\s+)?o que (?:eu )?(?:te |lhe )?(?:falei|disse|contei|anotei|pedi|copiei|guardei)\s+"
               r"(?:sobre|de|do|da|dos|das|a respeito d[eoa]s?)\s+(?P<consulta>.+)$"),
    re.compile(r"\b(?:procura|procure|busca|busque|pesquisa|pesquise|acha|ache)\s+(?:na|nas|no|em)\s+(?:minha |minhas |sua |meu )?"
               r"(?:memoria|memorias|conversas|historico|anotacoes|copiados)\s+(?:sobre |por |de |do |da |o |a )?(?P<consulta>.+)$"),
    re.compile(r"^(?:jarvis\s+)?quando (?:foi que )?eu (?:te )?(?:falei|disse|contei)\s+(?:sobre |de |do |da )?(?P<consulta>.+)$"),
]


def _parse(norm: str, _original: str) -> Optional[dict]:
    for rx in _PATTERNS:
        m = rx.search(norm)
        if m:
            q = m.group("consulta").strip(" ?.!")
            return {"consulta": q} if len(q) >= 2 else None
    return None


def _clean(snippet: str) -> str:
    return re.sub(r"\s+", " ", (snippet or "").replace("[", "").replace("]", "")).strip()


def _when(at: str) -> str:
    at = str(at or "")
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", at)
    if m:
        return f"{m.group(3)}/{m.group(2)}/{m.group(1)}"
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", at)
    return f"{m.group(1)}/{m.group(2)}/{m.group(3)}" if m else ""


@skill(
    name="buscar_memoria",
    title="buscar na memória",
    description=("Procura no histórico local do usuário (todas as conversas com o JARVIS, memórias, tarefas, lembretes "
                 "e textos copiados) e devolve os trechos mais relevantes. Use quando ele perguntar o que falou, anotou, "
                 "pediu ou copiou sobre algum assunto."),
    permission=Permission.READ,
    timeout=8,
    parse=_parse,
    params={"type": "object", "required": ["consulta"], "properties": {
        "consulta": {"type": "string", "description": "O assunto a procurar (poucas palavras)."}}},
    examples=["o que eu te falei sobre a viagem?", "procura na memória sobre o carro"],
)
def buscar_memoria(ctx: SkillContext, consulta: str) -> SkillResult:
    from modules import memory_index

    results = memory_index.search(consulta, limit=6)
    if not results:
        return SkillResult(speech=f"Não achei nada sobre {consulta} na sua memória, senhor.", data={"resultados": []})
    top = results[0]
    when = _when(top["at"])
    speech = (f"Achei {len(results)} {'coisa' if len(results) == 1 else 'coisas'} sobre {consulta}. A mais relevante, "
              f"{top['label'].lower()}{f' de {when}' if when else ''}: {_clean(top['snippet'])[:220]}")
    rows = []
    for r in results:
        day = _when(r["at"])
        rows.append({"label": r["label"] + (f" · {day}" if day else ""), "value": _clean(r["snippet"])[:160]})
    card = {"type": "skill", "data": {"tag": "MEMÓRIA", "source": f"busca: {consulta}", "rows": rows}}
    return SkillResult(speech=speech, cards=[card], data={"resultados": [{**r, "snippet": _clean(r["snippet"])} for r in results]})

"""Sorteios (V8.13): cara ou coroa, dados, número e "escolhe entre", na hora e sem IA.

Frases:
- "cara ou coroa", "joga uma moeda"
- "joga um dado", "rola dois dados", "joga um dado de 20 lados" (d20)
- "sorteia um número de 1 a 100", "escolhe um número entre 1 e 10"
- "escolhe entre pizza, hambúrguer ou sushi", "sorteia entre Ana e Bruno"
Sorteio de verdade (secrets.SystemRandom), nada de "sorteio combinado".
"""
from __future__ import annotations

import re
import secrets
from typing import Optional

from core.skills import Permission, SkillContext, SkillResult, skill

_rng = secrets.SystemRandom()  # os testes trocam por um random.Random com semente
_WORDS = {"um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6}
MAX_DICE, MAX_SIDES, MAX_OPTIONS = 10, 1000, 12
MAX_RANGE = 10**9


def _int(tok: Optional[str], default: int) -> int:
    if not tok:
        return default
    return int(tok) if tok.isdigit() else _WORDS.get(tok, default)


def _options(original: str) -> list[str]:
    """Opções ditas depois de "entre"/"escolhe" no texto ORIGINAL (com acentos e maiúsculas)."""
    m = re.search(r"\b(?:entre|escolh\w*|decid\w*|sorte\w*)\b[\s:,]*(?:(?:pra|para)\s+mim[\s:,]*)?(?:entre\s+)?(.+)$",
                  original, re.I)
    if not m:
        return []
    raw = re.sub(r"[?!.]+$", "", m.group(1)).strip()
    parts = [p.strip(" \"'") for p in re.split(r"\s*,\s*|\s+ou\s+|\s+e\s+", raw, flags=re.I)]
    seen, out = set(), []
    for p in parts:
        if p and p.lower() not in seen and len(p) <= 60:
            seen.add(p.lower())
            out.append(p)
    return out


def _parse(norm: str, original: str) -> Optional[dict]:
    t = norm
    if re.search(r"\bcara ou coroa\b|\b(?:joga|jogue|lanca|lance|gira|gire)\s+(?:uma\s+)?moeda\b", t):
        return {"tipo": "moeda"}
    m = re.search(r"\b(?:joga|jogue|rola|role|lanca|lance|tira|tire)\s+(um|uma|dois|duas|tres|quatro|cinco|seis|\d+)?\s*"
                  r"dados?\b(?:\s+de\s+(\d+)\s+(?:lados|faces))?", t) or re.search(r"\brola\s+(?:um\s+)?d(\d+)\b()", t)
    if m:
        if m.re.pattern.startswith(r"\brola"):
            return {"tipo": "dado", "quantidade": 1, "lados": int(m.group(1))}
        return {"tipo": "dado", "quantidade": _int(m.group(1), 1), "lados": _int(m.group(2), 6)}
    m = re.search(r"\b(?:sorteia|sorteie|escolhe|escolha|gera|gere|fala|diga|diz)\s+um\s+numero\s+(?:de|entre)\s+"
                  r"(-?\d+)\s+(?:a|e|ate)\s+(-?\d+)\b", t)
    if m:
        return {"tipo": "numero", "minimo": int(m.group(1)), "maximo": int(m.group(2))}
    if re.search(r"\b(?:escolhe|escolha|sorteia|sorteie|decide|decida)\b(?:\s+pra mim|\s+para mim)?\s+entre\b", t) or \
            re.search(r"\b(?:escolhe|escolha|decide|decida)\s+pra mim\b.*\bou\b", t):
        opts = _options(original)
        return {"tipo": "escolha", "opcoes": opts} if len(opts) >= 2 else None
    return None


@skill(
    name="sortear",
    title="sortear",
    description=("Sorteios na hora: cara ou coroa (tipo moeda), dados (tipo dado, com quantidade e lados), um número "
                 "entre mínimo e máximo (tipo numero) ou uma opção de uma lista (tipo escolha, com opcoes)."),
    permission=Permission.READ,
    public=True,
    timeout=3,
    parse=_parse,
    params={"type": "object", "required": ["tipo"], "properties": {
        "tipo": {"type": "string", "enum": ["moeda", "dado", "numero", "escolha"]},
        "quantidade": {"type": "integer"}, "lados": {"type": "integer"},
        "minimo": {"type": "integer"}, "maximo": {"type": "integer"},
        "opcoes": {"type": "array", "items": {"type": "string"}},
    }},
    examples=["cara ou coroa", "joga dois dados", "sorteia um número de 1 a 100", "escolhe entre pizza ou sushi"],
)
def sortear(ctx: SkillContext, tipo: str, quantidade: int = 1, lados: int = 6, minimo: int = 1, maximo: int = 10,
            opcoes: Optional[list] = None) -> SkillResult:
    if tipo == "moeda":
        side = _rng.choice(["cara", "coroa"])
        return SkillResult(speech=f"Deu {side}, senhor.", data={"resultado": side})
    if tipo == "dado":
        if not 1 <= quantidade <= MAX_DICE or not 2 <= lados <= MAX_SIDES:
            return SkillResult(ok=False, speech=f"Consigo jogar de 1 a {MAX_DICE} dados, de 2 a {MAX_SIDES} lados, senhor.")
        rolls = [_rng.randint(1, lados) for _ in range(quantidade)]
        kind = "" if lados == 6 else f" de {lados} lados"
        if quantidade == 1:
            return SkillResult(speech=f"Deu {rolls[0]} no dado{kind}, senhor.", data={"resultados": rolls})
        listed = ", ".join(map(str, rolls[:-1])) + f" e {rolls[-1]}"
        return SkillResult(speech=f"Deu {listed}. Total: {sum(rolls)}, senhor.", data={"resultados": rolls, "total": sum(rolls)})
    if tipo == "numero":
        lo, hi = sorted((minimo, maximo))
        if hi - lo > MAX_RANGE:
            return SkillResult(ok=False, speech="Esse intervalo é grande demais, senhor.")
        n = _rng.randint(lo, hi)
        return SkillResult(speech=f"Saiu o {n}, senhor.", data={"resultado": n})
    if tipo == "escolha":
        opts = [str(o).strip() for o in (opcoes or []) if str(o).strip()][:MAX_OPTIONS]
        if len(opts) < 2:
            return SkillResult(ok=False, speech="Diga pelo menos duas opções, senhor. Por exemplo: escolhe entre pizza ou sushi.")
        pick = _rng.choice(opts)
        return SkillResult(speech=f"Eu fico com {pick}, senhor.", data={"escolha": pick, "opcoes": opts})
    return SkillResult(ok=False, speech="Não entendi o sorteio, senhor.")

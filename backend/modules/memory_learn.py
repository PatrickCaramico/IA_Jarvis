"""V6.7.3: memória que aprende sozinha com as conversas.

Depois de cada resposta da IA, se a frase do usuário fala dele mesmo ("eu", "meu", "gosto", "trabalho"...),
o JARVIS pede à IA, em segundo plano, até 3 FATOS DURADOUROS sobre o usuário (gostos, rotina, pessoas,
metas, trabalho, lugares) e guarda em modules/memory (fonte "auto"), sem repetir o que já sabe.

Fica de fora: coisas passageiras ("hoje estou cansado"), dados sensíveis (senhas, documentos, banco,
detalhes de saúde) e qualquer coisa sobre outras pessoas que não seja a relação delas com o usuário.

Comandos: "pare de aprender sobre mim" / "pode voltar a aprender sobre mim"
(o que já aprendeu: "o que você sabe de mim?"; apagar: "esqueça ...", em modules/memory.py).
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Optional

from modules import memory, prefs
from modules.quick_replies import _norm

log = logging.getLogger("jarvis.memory_learn")

MAX_PER_TURN = 3
_ABOUT_ME = re.compile(
    r"\b(?:eu|meu|minha|meus|minhas|comigo|gosto|prefiro|adoro|amo|odeio|detesto|trabalho|moro|estudo|"
    r"sou|tenho|treino|costumo|sempre|nunca|quero|pretendo|meta|sonho)\b"
)
_SENSITIVE = re.compile(r"\b(?:senha|cpf|rg|cartao|conta bancaria|agencia|pix|token|codigo de seguranca|cvv)\b")
_STOP = re.compile(r"\b(?:pare|para|parar|nao)\s+(?:de\s+)?(?:aprender|guardar|memorizar)\b.*\b(?:mim|eu|minhas? coisas)\b")
_START = re.compile(r"\b(?:pode|volte a|voltar a|volta a)\s+(?:voltar a\s+)?(?:aprender|guardar|memorizar)\b.*\b(?:mim|eu)\b")

PROMPT = (
    "Tarefa interna (não é uma conversa): leia a frase do usuário e extraia FATOS DURADOUROS sobre ele "
    "(gostos e preferências, rotina, pessoas próximas e a relação com ele, metas, trabalho ou estudo, lugares, "
    "time do coração, hobbies). Escreva cada fato curto, em terceira pessoa, começando com verbo ou substantivo "
    "(ex.: \"Gosta de café sem açúcar\", \"Treina às 18h de segunda a sexta\", \"A esposa se chama Ana\"). "
    "NÃO inclua: coisas passageiras do momento (\"está cansado hoje\"), senhas, documentos, dados bancários, "
    "detalhes de saúde, nem fatos que já estão na lista de memórias. Se não houver nada duradouro, devolva []. "
    "Responda APENAS com um array JSON de textos, no máximo 3, sem nenhum texto fora dele.\n\n"
    "Memórias que você já tem:\n{known}\n\nFrase do usuário: \"{message}\""
)


def enabled() -> bool:
    try:
        return bool(prefs._load().get("memory_auto_learn", True))  # noqa: SLF001
    except Exception:  # noqa: BLE001
        return True


def worth_trying(message: str) -> bool:
    norm = _norm(message or "")
    if len(norm.split()) < 4 or _SENSITIVE.search(norm):
        return False
    return bool(_ABOUT_ME.search(norm))


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"\w{3,}", _norm(text)) if w not in {"que", "com", "para", "dos", "das", "uma", "ele", "ela"}}


def is_duplicate(fact: str, known: list[str]) -> bool:
    new = _tokens(fact)
    if not new:
        return True
    for old in known:
        o = _tokens(old)
        if o and len(new & o) / min(len(new), len(o)) >= 0.75:
            return True
    return False


def parse_facts(raw: str) -> list[str]:
    text = (raw or "").strip()
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end <= start:
        return []
    try:
        items = json.loads(text[start:end + 1])
    except ValueError:
        return []
    out = []
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, str):
            continue
        fact = re.sub(r"\s+", " ", it).strip().rstrip(".")
        if 5 <= len(fact) <= 140 and not _SENSITIVE.search(_norm(fact)):
            out.append(fact[:1].upper() + fact[1:])
    return out[:MAX_PER_TURN]


def _ask_llm(prompt: str) -> str:
    from services import llm_orchestrator

    return llm_orchestrator._call_llm(prompt, None, [], False)  # noqa: SLF001


async def learn_from(message: str) -> list[str]:
    """Roda em segundo plano depois da resposta. Devolve os fatos novos guardados."""
    if not enabled() or not worth_trying(message):
        return []
    known = memory.facts(40)
    prompt = PROMPT.format(known="\n".join(f"- {k}" for k in known) or "(nenhuma)", message=message.strip()[:600])
    try:
        raw = await asyncio.to_thread(_ask_llm, prompt)
    except Exception as exc:  # noqa: BLE001 - sem IA agora: tenta na próxima
        log.debug("Aprendizado da memória pulado: %s", exc)
        return []
    added = []
    for fact in parse_facts(raw):
        if not is_duplicate(fact, known + added):
            memory.remember(fact, source="auto")
            added.append(fact)
    if added:
        log.info("Memória: aprendi %d fato(s) novo(s).", len(added))
    return added


def handle_voice(norm: str) -> Optional[str]:
    """Liga/desliga o aprendizado sozinho."""
    if _STOP.search(norm):
        prefs.update(memory_auto_learn=False)
        return ("Certo, senhor. Paro de aprender sozinho sobre o senhor. O que já sei continua guardado; "
                "para ver, pergunte o que eu sei do senhor, e para apagar, diga esqueça e o assunto.")
    if _START.search(norm):
        prefs.update(memory_auto_learn=True)
        return "Pode deixar, senhor. Volto a guardar o que for importante nas nossas conversas."
    return None

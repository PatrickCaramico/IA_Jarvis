"""Copiar e colar (V9.0): o histórico de copiados por voz, em qualquer tela.

Frases:
- "o que eu copiei?", "qual foi a última coisa que eu copiei?"            -> lê o último e mostra os 5 mais novos
- "copia de novo o último link", "copia de novo o penúltimo", "cola o e-mail que eu copiei",
  "copia de novo o endereço"                                               -> devolve à área de transferência (Ctrl+V)
- "fixa o último copiado"                                                  -> ★ não sai por limite nem no LIMPAR
- "limpa os copiados"                                                      -> pergunta antes; os fixados ficam
Para procurar por assunto ("o que eu copiei sobre o hotel?") vale a memória pesquisável (skills/memoria_busca.py).
O histórico é o mesmo dos Copiados do Modo Desk (modules/desk.py), só no PC e sem o que parece senha.
"""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

from core.skills import Permission, SkillContext, SkillResult, skill

_URL = re.compile(r"https?://\S+|www\.\S+", re.I)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_NUMBER = re.compile(r"^[\d\s().+-]{6,}$")
_ADDRESS = re.compile(r"\b(rua|r\.|avenida|av\.|travessa|alameda|rodovia|estrada|praça)\b", re.I)
KINDS = ("ultimo", "penultimo", "link", "email", "numero", "endereco")


def _is(kind: str, text: str) -> bool:
    t = text.strip()
    return {"link": bool(_URL.search(t)), "email": bool(_EMAIL.search(t)), "numero": bool(_NUMBER.match(t)),
            "endereco": bool(_ADDRESS.search(t))}.get(kind, True)


def pick(items: list[dict], qual: str) -> Optional[dict]:
    """O copiado pedido: último, penúltimo ou o mais novo de um tipo (link, e-mail, número, endereço)."""
    if qual == "penultimo":
        return items[1] if len(items) > 1 else None
    if qual == "ultimo":
        return items[0] if items else None
    return next((i for i in items if _is(qual, i["texto"])), None)


def describe(text: str) -> str:
    """Como falar um copiado: link vira "um link do site X"; texto longo é encurtado."""
    t = re.sub(r"\s+", " ", text).strip()
    url = _URL.search(t)
    if url and len(url.group(0)) >= len(t) - 2:
        host = urlparse(url.group(0) if "://" in url.group(0) else f"http://{url.group(0)}").netloc.replace("www.", "")
        return f"um link do site {host}"
    return t if len(t) <= 140 else t[:137] + "…"


_WHICH = (r"(?P<qual>ultimo link|penultimo|ultimo|link|e[\s-]?mail|numero|telefone|endereco)")  # "e-mail" vira "e mail"
_PATTERNS = [
    (re.compile(r"^(?:jarvis\s+)?(?:o que|qual (?:foi )?a ultima coisa que) eu copiei(?: por ultimo)?\??$"), "ler"),
    (re.compile(r"^(?:jarvis\s+)?(?:o que (?:tem|ha) nos (?:meus )?copiados|mostra (?:os )?(?:meus )?copiados)\??$"), "ler"),
    (re.compile(r"\b(?:copia|copie|cola|cole|me da|me de)\s+(?:de novo\s+|outra vez\s+)?(?:o|a)\s+" + _WHICH +
                r"(?:\s+(?:que eu copiei|copiado|da area de transferencia))?(?:\s+de novo)?$"), "copiar"),
    (re.compile(r"\b(?:fixa|fixe|fixar|guarda|guarde)\s+(?:o\s+)?(?:ultimo\s+)?copiado\b"), "fixar"),
]  # "limpa os copiados" é a skill limpar_copiados (pergunta antes)


def _qual(word: str) -> str:
    w = re.sub(r"^e[\s-]?mail$", "email", word).replace("ultimo link", "link")
    return {"telefone": "numero", "email": "email"}.get(w, w)


def _parse(norm: str, _original: str) -> Optional[dict]:
    for rx, acao in _PATTERNS:
        m = rx.search(norm)
        if m:
            out = {"acao": acao}
            if acao == "copiar":
                out["qual"] = _qual(m.group("qual"))
            return out
    return None


def _clear_question(_args: dict) -> str:
    return "Apago o histórico de copiados, senhor? Os fixados com estrela ficam. Diga sim para confirmar."


@skill(
    name="copiados",
    title="usar os copiados",
    description=("Histórico do que o usuário copiou no PC (Ctrl+C): ler o último (acao ler), devolver um item à área de "
                 "transferência para colar (acao copiar, com qual: ultimo, penultimo, link, email, numero, endereco), "
                 "ou fixar o último (acao fixar). Para apagar o histórico, use limpar_copiados."),
    permission=Permission.ACTION,
    allow_remote=False,
    timeout=8,
    parse=_parse,
    params={"type": "object", "required": ["acao"], "properties": {
        "acao": {"type": "string", "enum": ["ler", "copiar", "fixar"]},
        "qual": {"type": "string", "enum": list(KINDS)}}},
    examples=["o que eu copiei?", "copia de novo o último link", "fixa o último copiado"],
)
def copiados(ctx: SkillContext, acao: str, qual: str = "ultimo") -> SkillResult:
    from modules import desk

    items = desk.clips().get("itens", [])
    if not items:
        return SkillResult(ok=False, speech="Ainda não tenho nada nos copiados, senhor. Eles funcionam com o JARVIS rodando no Windows.")
    if acao == "ler":
        rows = [{"label": ("★ " if i.get("fixado") else "") + i.get("em", ""), "value": describe(i["texto"])} for i in items[:5]]
        return SkillResult(speech=f"A última coisa que o senhor copiou foi {describe(items[0]['texto'])}",
                           cards=[{"type": "skill", "data": {"tag": "COPIADOS", "source": "os mais recentes", "rows": rows}}],
                           data={"itens": [i["texto"][:500] for i in items[:5]]})
    if acao == "fixar":
        desk.clip_pin(items[0]["id"], True)
        return SkillResult(speech="Fixado com estrela, senhor: esse não sai mais da lista.")
    item = pick(items, qual if qual in KINDS else "ultimo")
    if item is None:
        nome = {"link": "nenhum link", "email": "nenhum e-mail", "numero": "nenhum número", "endereco": "nenhum endereço",
                "penultimo": "um penúltimo item"}.get(qual, "esse item")
        return SkillResult(ok=False, speech=f"Não achei {nome} nos copiados, senhor.")
    from skills.clipboard_ai import write_clipboard

    if not write_clipboard(item["texto"]):
        return SkillResult(ok=False, speech="Não consegui pôr na área de transferência agora, senhor.")
    return SkillResult(speech=f"Pronto, {describe(item['texto'])} está na área de transferência. É só colar.")


@skill(
    name="limpar_copiados",
    title="limpar os copiados",
    description="Apaga o histórico de copiados (os fixados com estrela ficam). Pede confirmação antes.",
    permission=Permission.CRITICAL,
    timeout=5,
    triggers=[r"^(?:jarvis\s+)?(?:limpa|limpe|apaga|apague)\s+(?:os\s+|o historico de\s+)?(?:meus\s+)?copiados$"],
    params={"type": "object", "properties": {}},
    confirm_text=_clear_question,
    examples=["apaga os copiados"],
)
def limpar_copiados(ctx: SkillContext) -> SkillResult:
    from modules import desk

    left = len(desk.clip_remove(None).get("itens", []))
    return SkillResult(speech="Copiados apagados, senhor." + (f" Ficaram os {left} fixados." if left else ""))

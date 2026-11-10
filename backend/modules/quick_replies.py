"""Respostas instantâneas (sem chamar a IA) para perguntas simples e frequentes.

- Cumprimentos e conversa rápida ("boa noite, tudo bem?") e hora/data são tratados no código.
- Perguntas e respostas fixas ficam em data/respostas.json (criado na primeira execução).
  Você pode editar esse arquivo à vontade; as mudanças valem na hora, sem reiniciar.
"""
import json
import logging
import random
import re
import unicodedata
from datetime import datetime
from typing import Optional

from config import settings

log = logging.getLogger("jarvis.quick")

CUSTOM_PATH = settings.DATA_DIR / "respostas.json"

# "{nome}" vira o seu nome (ou "você" se não houver nome cadastrado).
# "requer_nome": true -> a regra só vale se houver nome cadastrado.
DEFAULTS = [
    {
        "perguntas": ["quem desenvolveu você", "quem criou você", "quem fez você", "quem te criou",
                      "quem te desenvolveu", "quem te fez", "quem é o seu criador", "quem é seu criador"],
        "resposta": "Fui desenvolvido por {nome}, com a ajuda do Claude, da Anthropic. Por dentro, sou Python e React, e converso usando um modelo de inteligência artificial.",
    },
    {
        "perguntas": ["o que você faz", "o que você sabe fazer", "o que você pode fazer", "para que você serve",
                      "pra que você serve", "quais são as suas funções", "o que você consegue fazer",
                      "funcionalidades", "ajuda", "comandos", "o que posso pedir", "o que posso te pedir"],
        "resposta": "Converso com você por voz ou texto e respondo perguntas com inteligência artificial. Também resumo as notícias do dia, olho pela câmera quando você pede, faço contas, crio timers e lembretes, guardo anotações, digo o clima e a cotação do dólar, abro sites e programas e pesquiso no navegador. Por exemplo: me avise em 10 minutos, anote comprar leite, abra o YouTube, ou quanto é 15 vezes 8.",
    },
    {
        "perguntas": ["quem é você", "qual é o seu nome", "como você se chama", "se apresente", "qual é a sua versão", "sua versão"],
        "resposta": "Sou o JARVIS, seu assistente pessoal, na versão 2.1. Estou aqui para ajudar no que precisar.",
    },
    {
        "perguntas": ["qual é o meu nome", "como eu me chamo", "você sabe o meu nome", "você sabe meu nome"],
        "resposta": "Você se chama {nome}.",
        "requer_nome": True,
    },
    {
        "perguntas": ["obrigado", "obrigada", "valeu", "muito obrigado", "muito obrigada"],
        "resposta": ["Disponha, {nome}.", "Sempre às ordens, {nome}."],
    },
    {
        "perguntas": ["tchau", "até logo", "até mais", "falou"],
        "resposta": "Até logo, {nome}. Estarei por aqui quando precisar.",
    },
]

_MONTHS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
           "agosto", "setembro", "outubro", "novembro", "dezembro"]
_WEEKDAYS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
             "sexta-feira", "sábado", "domingo"]

_TIME_Q = ("que horas sao", "que hora e", "que horas e", "me diz as horas", "me diga as horas", "horas")
_DATE_Q = ("que dia e hoje", "que dia eh hoje", "qual e a data de hoje", "qual a data de hoje",
           "que data e hoje", "em que dia estamos", "data de hoje")

# Conversa rápida: se a mensagem for SÓ isso, responde local.
_NICE = ("muito prazer", "prazer em conhecer", "prazer")
_HOW = ("tudo bem", "tudo bom", "tudo certo", "tudo joia", "como voce esta", "como voce ta", "como vai voce",
        "como vai", "como esta", "e com voce", "e voce", "como anda", "beleza")
_TIME_GREETS = ("boa tarde", "boa noite")
_HELLO = ("e ai", "oi", "ola", "opa", "ei", "hey", "hello", "fala", "salve")
_NOISE = ("por favor", "entao", "ai")


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _strip(text: str, phrases: tuple) -> tuple[str, bool]:
    pattern = r"\b(?:" + "|".join(re.escape(p) for p in sorted(phrases, key=len, reverse=True)) + r")\b"
    new, count = re.subn(pattern, " ", text)
    return re.sub(r"\s+", " ", new).strip(), count > 0


def time_greeting() -> str:
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Bom dia"
    if 12 <= hour < 18:
        return "Boa tarde"
    return "Boa noite"


def _spoken_time(now: datetime) -> str:
    h, m = now.hour, now.minute
    if h == 0:
        base, exact = "É meia-noite", ""
    elif h == 12:
        base, exact = "É meio-dia", ""
    elif h == 1:
        base, exact = "É uma hora", " em ponto"
    else:
        base, exact = f"São {h} horas", " em ponto"
    if m == 0:
        return f"{base}{exact}."
    return f"{base} e {m} minuto{'s' if m != 1 else ''}."


def _fill(text: str, name: str) -> str:
    text = text.replace(", {nome}", f", {name}" if name else "")
    return text.replace("{nome}", name or "você")


def _load_custom() -> list[dict]:
    if not CUSTOM_PATH.exists():
        try:
            CUSTOM_PATH.write_text(json.dumps(DEFAULTS, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass
        return DEFAULTS
    try:
        data = json.loads(CUSTOM_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except (OSError, ValueError) as exc:
        log.warning("respostas.json inválido (%s); usando as respostas padrão.", exc)
    return DEFAULTS


def _match_custom(norm: str, name: str) -> Optional[str]:
    words = len(norm.split())
    for rule in _load_custom():
        if rule.get("requer_nome") and not name:
            continue
        for question in rule.get("perguntas", []):
            q = _norm(str(question))
            if not q:
                continue
            q_words = len(q.split())
            extra = 5 if q_words >= 3 else 1  # frases curtas só valem se a mensagem for curta também
            if re.search(rf"\b{re.escape(q)}\b", norm) and words <= q_words + extra:
                answer = rule.get("resposta", "")
                if isinstance(answer, list):
                    answer = random.choice(answer) if answer else ""
                return _fill(str(answer), name) or None
    return None


def _match_smalltalk(norm: str, name: str) -> Optional[str]:
    rest, nice = _strip(norm, _NICE)
    rest, how = _strip(rest, _HOW)
    rest, time_greet = _strip(rest, _TIME_GREETS)
    rest, hello = _strip(rest, _HELLO)
    rest, _ = _strip(rest, _NOISE)
    if rest or not (nice or how or time_greet or hello):
        return None  # sobrou algo além de conversa rápida -> deixa a IA responder

    parts = []
    if time_greet:
        parts.append(f"{time_greeting()}, {name}!" if name else f"{time_greeting()}!")
    elif hello:
        parts.append(f"Olá, {name}!" if name else "Olá!")
    if nice:
        parts.append("O prazer é meu.")
    if how:
        parts.append(random.choice(["Tudo bem por aqui, obrigado por perguntar.", "Tudo ótimo por aqui, obrigado.", "Tudo em ordem por aqui, obrigado por perguntar."]))
    parts.append(random.choice(["Em que posso ajudar?", "Como posso ajudar?", "O que posso fazer por você?"]))
    return " ".join(parts)


def match(message: str, name: str = "") -> Optional[str]:
    """Devolve a resposta instantânea, ou None se a IA precisar responder."""
    norm = re.sub(r"\bjarvis\b", " ", _norm(message))
    norm = re.sub(r"\s+", " ", norm).strip()
    if not norm or len(norm.split()) > 12:
        return None

    now = datetime.now()
    if len(norm.split()) <= 6:
        if any(re.search(rf"\b{p}\b", norm) for p in _TIME_Q):
            return _spoken_time(now)
        if any(re.search(rf"\b{p}\b", norm) for p in _DATE_Q):
            return f"Hoje é {_WEEKDAYS[now.weekday()]}, {now.day} de {_MONTHS[now.month - 1]} de {now.year}."

    return _match_custom(norm, name) or _match_smalltalk(norm, name)

"""Calculadora de datas (V8.13): contas com o calendário, na hora e sem IA.

Frases:
- "quantos dias se passaram desde 10 de março", "há quantos dias foi o carnaval", "quantos dias faz desde 01/01/2024"
- "que dia vai ser daqui a 45 dias", "que dia cai daqui a 3 semanas", "que data é daqui a 2 meses"
- "que dia da semana cai o natal", "25/12/2027 cai em que dia da semana", "que dia da semana foi 7 de setembro de 2022"
- "quantos dias entre 10/03 e 25/12"
"Quanto falta para o Natal" continua com a contagem regressiva (modules/countdowns.py, que também procura na agenda):
esta skill não captura "quanto falta" nem "quantos dias faltam".
Datas aceitas: "10/03", "10/03/2025", "10 de março", "10 de março de 2025", "hoje", "amanhã", "ontem" e as festas
natal, ano novo, páscoa, carnaval, tiradentes, independência, dia das crianças, finados, dia dos namorados, halloween.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta
from typing import Optional

from core.skills import Permission, SkillContext, SkillResult, skill

_MONTHS = {"janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
           "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12}
_MONTH_NAMES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
                "novembro", "dezembro"]
_WEEKDAYS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
_NUMWORDS = {"um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6, "sete": 7,
             "oito": 8, "nove": 9, "dez": 10, "onze": 11, "doze": 12, "quinze": 15, "vinte": 20, "trinta": 30,
             "quarenta": 40, "cinquenta": 50, "sessenta": 60, "noventa": 90, "cem": 100}
_FIXED = {"natal": (12, 25, "o Natal"), "ano novo": (1, 1, "o Ano-Novo"), "reveillon": (1, 1, "o Ano-Novo"),
          "tiradentes": (4, 21, "Tiradentes"), "independencia": (9, 7, "a Independência"),
          "dia das criancas": (10, 12, "o Dia das Crianças"), "finados": (11, 2, "Finados"),
          "dia dos namorados": (6, 12, "o Dia dos Namorados"), "halloween": (10, 31, "o Halloween")}
MAX_AMOUNT = 100_000


def _today() -> date:
    return date.today()


def easter(year: int) -> date:
    """Domingo de Páscoa (algoritmo de Meeus/Jones/Butcher)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    month = (h + m - 7 * n + 114) // 31
    day = (h + m - 7 * n + 114) % 31 + 1
    return date(year, month, day)


def _holiday(key: str, year: int) -> date:
    if key == "pascoa":
        return easter(year)
    if key == "carnaval":
        return easter(year) - timedelta(days=47)  # terça-feira de carnaval
    month, day, _label = _FIXED[key]
    return date(year, month, day)


def _pick_year(build, today: date, explicit: Optional[int], direction: str) -> Optional[date]:
    """Sem ano dito: a próxima ocorrência ("future"), a última ("past") ou a deste ano ("any")."""
    try:
        if explicit:
            return build(explicit)
        this = build(today.year)
        if direction == "future" and this < today:
            return build(today.year + 1)
        if direction == "past" and this > today:
            return build(today.year - 1)
        return this
    except ValueError:
        return None


def parse_date(text: str, today: Optional[date] = None, direction: str = "any") -> Optional[tuple[date, str]]:
    """(data, como falar dela) a partir do texto normalizado. None se não houver data."""
    today = today or _today()
    t = f" {text} "
    if re.search(r"\bhoje\b", t):
        return today, "hoje"
    if re.search(r"\bamanha\b", t):
        return today + timedelta(days=1), "amanhã"
    if re.search(r"\bontem\b", t):
        return today - timedelta(days=1), "ontem"
    year_m = re.search(r"\b(?:de\s+)?((?:19|20)\d{2})\b", t)
    for key in ("pascoa", "carnaval", *_FIXED):
        if re.search(rf"\b{key}\b", t):
            label = {"pascoa": "a Páscoa", "carnaval": "o Carnaval"}.get(key) or _FIXED[key][2]
            found = _pick_year(lambda y, k=key: _holiday(k, y), today, int(year_m.group(1)) if year_m else None, direction)
            return (found, label) if found else None
    m = re.search(r"\b(\d{1,2})\s*/\s*(\d{1,2})(?:\s*/\s*(\d{2,4}))?\b", t)
    if m:
        day, month = int(m.group(1)), int(m.group(2))
        year = int(m.group(3)) if m.group(3) else None
        if year is not None and year < 100:
            year += 2000
    else:
        m = re.search(r"\b(\d{1,2})\s+de\s+(" + "|".join(_MONTHS) + r")(?:\s+de\s+(\d{4}))?\b", t)
        if not m:
            return None
        day, month = int(m.group(1)), _MONTHS[m.group(2)]
        year = int(m.group(3)) if m.group(3) else None
    if not 1 <= month <= 12:
        return None
    found = _pick_year(lambda y: date(y, month, day), today, year, direction)
    return (found, _say(found, today)) if found else None


def _say(d: date, today: Optional[date] = None) -> str:
    today = today or _today()
    base = f"{d.day} de {_MONTH_NAMES[d.month - 1]}"
    return base if d.year == today.year else f"{base} de {d.year}"


def _full(d: date, today: Optional[date] = None) -> str:
    return f"{_WEEKDAYS[d.weekday()]}, {_say(d, today)}"


def _amount(text: str) -> Optional[int]:
    if text.isdigit():
        return int(text)
    return _NUMWORDS.get(text)


def _add_months(d: date, months: int) -> date:
    month0 = d.month - 1 + months
    year, month = d.year + month0 // 12, month0 % 12 + 1
    for day in (d.day, 30, 29, 28):  # 31 de janeiro + 1 mês = 28 (ou 29) de fevereiro
        try:
            return date(year, month, day)
        except ValueError:
            continue
    return date(year, month, 28)


_IN = re.compile(r"\b(?:daqui\s+a|dentro\s+de|em)\s+(\d+|" + "|".join(_NUMWORDS) + r")\s+(dias?|semanas?|mes(?:es)?|anos?)\b")
_AGO = re.compile(r"\b(?:ha|faz|fazem)\s+(\d+|" + "|".join(_NUMWORDS) + r")\s+(dias?|semanas?|mes(?:es)?|anos?)(?:\s+atras)?\b"
                  r"|\b(\d+|" + "|".join(_NUMWORDS) + r")\s+(dias?|semanas?|mes(?:es)?|anos?)\s+atras\b")
_UNIT = {"d": "dias", "s": "semanas", "m": "meses", "a": "anos"}


def _norm_keep_slash(text: str) -> str:
    """Como a frase normalizada do JARVIS, mas sem perder a barra das datas ("25/12" não pode virar "25 12")."""
    t = unicodedata.normalize("NFD", (text or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9/]+", " ", t)).strip()


def _parse(norm: str, original: str) -> Optional[dict]:
    t = _norm_keep_slash(original) if original else norm
    if re.search(r"\bquanto(?:s dias)? falta|\bquantos dias faltam\b|\bcontagem regressiva\b", t):
        return None  # é da contagem regressiva (procura também na agenda)
    asks_date = re.search(r"\bque\s+(?:dia|data)\b|\bqual\s+(?:o\s+dia|a\s+data)\b|\bque dia da semana\b|"
                          r"\bem que dia(?: da semana)?\b|\bcai\b", t)
    for rx, sign in ((_IN, 1), (_AGO, -1)):
        m = rx.search(t)
        if m and asks_date:
            amount_s = next(g for g in m.groups()[0::2] if g)
            unit_s = next(g for g in m.groups()[1::2] if g)
            amount = _amount(amount_s)
            if amount is None:
                return None
            return {"acao": "somar", "quantidade": sign * amount, "unidade": _UNIT[unit_s[0]]}
    if re.search(r"\bquantos\s+dias\b.*\bentre\b", t):
        parts = re.split(r"\bentre\b", t, maxsplit=1)[1]
        halves = re.split(r"\s+e\s+(?=\d|hoje|amanha|ontem|natal|ano novo|pascoa|carnaval|dia\s)", parts, maxsplit=1)
        if len(halves) == 2:
            a, b = parse_date(halves[0]), parse_date(halves[1])
            if a and b:
                return {"acao": "entre", "data": a[0].isoformat(), "data_fim": b[0].isoformat()}
        return None
    if re.search(r"\bdesde\b|\bse passaram\b|\bha quantos dias\b|\bquantos dias (?:faz|fazem|tem)\b", t) and "quantos" in t:
        found = parse_date(t, direction="past")
        return {"acao": "desde", "data": found[0].isoformat()} if found else None
    if re.search(r"\bdia da semana\b|\bque dia (?:cai|caiu|foi|vai ser|sera)\b|\bcai (?:em|num|numa) que dia\b", t):
        found = parse_date(t, direction="future")
        return {"acao": "dia_semana", "data": found[0].isoformat()} if found else None
    return None


def _days(n: int) -> str:
    return "1 dia" if abs(n) == 1 else f"{abs(n)} dias"


@skill(
    name="calcular_datas",
    title="calcular datas",
    description=("Contas com o calendário: quantos dias se passaram desde uma data, que dia será daqui a N dias, "
                 "semanas, meses ou anos (ou foi há N), em que dia da semana cai uma data e quantos dias há entre "
                 "duas datas. Datas no formato AAAA-MM-DD. Não use para 'quanto falta para' (isso é a contagem regressiva)."),
    permission=Permission.READ,
    public=True,  # só contas com o calendário, nada pessoal
    timeout=5,
    parse=_parse,
    params={"type": "object", "required": ["acao"], "properties": {
        "acao": {"type": "string", "enum": ["desde", "somar", "dia_semana", "entre"]},
        "data": {"type": "string", "description": "AAAA-MM-DD (desde, dia_semana, entre)"},
        "data_fim": {"type": "string", "description": "AAAA-MM-DD (entre)"},
        "quantidade": {"type": "integer", "description": "somar: positivo = daqui a, negativo = há"},
        "unidade": {"type": "string", "enum": ["dias", "semanas", "meses", "anos"]},
    }},
    examples=["que dia vai ser daqui a 45 dias", "quantos dias se passaram desde 10 de março",
              "que dia da semana cai o natal"],
)
def calcular_datas(ctx: SkillContext, acao: str, data: str = "", data_fim: str = "", quantidade: int = 0,
                   unidade: str = "dias") -> SkillResult:
    today = _today()
    try:
        d = date.fromisoformat(data) if data else None
        d2 = date.fromisoformat(data_fim) if data_fim else None
    except ValueError:
        return SkillResult(ok=False, speech="Não entendi a data, senhor. Diga, por exemplo, 10 de março ou 10/03/2025.")
    if acao == "somar":
        if not quantidade or abs(quantidade) > MAX_AMOUNT:
            return SkillResult(ok=False, speech="Quantos dias, senhor?")
        try:
            if unidade == "meses":
                target = _add_months(today, quantidade)
            elif unidade == "anos":
                target = _add_months(today, 12 * quantidade)
            else:
                target = today + timedelta(days=quantidade * (7 if unidade == "semanas" else 1))
        except (OverflowError, ValueError):
            return SkillResult(ok=False, speech="Essa data fica longe demais para o calendário, senhor.")
        when = "Daqui a" if quantidade > 0 else "Há"
        unit = unidade if abs(quantidade) != 1 else {"dias": "dia", "semanas": "semana", "meses": "mês", "anos": "ano"}[unidade]
        verb = "será" if quantidade > 0 else "foi"
        return SkillResult(speech=f"{when} {abs(quantidade)} {unit} {verb} {_full(target, today)}, senhor.",
                           data={"data": target.isoformat()})
    if d is None:
        return SkillResult(ok=False, speech="De qual data, senhor?")
    if acao == "desde":
        n = (today - d).days
        if n < 0:
            return SkillResult(speech=f"Essa data ainda não chegou, senhor: faltam {_days(n)}.", data={"dias": n})
        if n == 0:
            return SkillResult(speech="É hoje, senhor.", data={"dias": 0})
        weeks = f", ou {n // 7} semanas" if n >= 14 else ""
        return SkillResult(speech=f"Desde {_say(d, today)} se passaram {_days(n)}{weeks}, senhor.", data={"dias": n})
    if acao == "dia_semana":
        verb = "foi" if d < today else "cai"
        if d == today:
            return SkillResult(speech=f"Hoje é {_WEEKDAYS[d.weekday()]}, senhor.", data={"dia_semana": _WEEKDAYS[d.weekday()]})
        return SkillResult(speech=f"{_say(d, today)[0].upper()}{_say(d, today)[1:]} {verb} numa {_WEEKDAYS[d.weekday()]}, senhor."
                           .replace("numa sábado", "num sábado").replace("numa domingo", "num domingo"),
                           data={"dia_semana": _WEEKDAYS[d.weekday()]})
    if acao == "entre":
        if d2 is None:
            return SkillResult(ok=False, speech="Entre quais datas, senhor?")
        n = abs((d2 - d).days)
        return SkillResult(speech=f"Entre {_say(min(d, d2), today)} e {_say(max(d, d2), today)} são {_days(n)}, senhor.",
                           data={"dias": n})
    return SkillResult(ok=False, speech="Não entendi a conta com a data, senhor.")

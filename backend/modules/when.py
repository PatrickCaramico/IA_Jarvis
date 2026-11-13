"""Entende "quando" em português falado, para alarmes e lembretes (V5.1).

Recebe o texto normalizado (minúsculas, sem acentos, sem pontuação, como tools._norm) e devolve:
  When(at, days, rest)
  - at:   próximo datetime (ou None se não achou horário)
  - days: dias da semana da repetição (0 = segunda ... 6 = domingo) ou None se é só uma vez
  - rest: o texto que sobrou (rótulo do alarme / assunto do lembrete)

Exemplos: "as 7", "as 6 e meia", "as 7 da noite", "6h30", "meio dia", "meia noite",
"daqui a 20 minutos", "em 2 horas", "em meia hora", "amanha as 8", "sexta as 10",
"dia 15 as 9", "todo dia as 7", "de segunda a sexta as 6", "fim de semana as 9", "toda terca as 19".
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

WEEKDAYS = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]
WEEKDAY_NAMES = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]

_NUM = {
    "zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6,
    "sete": 7, "oito": 8, "nove": 9, "dez": 10, "onze": 11, "doze": 12, "treze": 13, "catorze": 14,
    "quatorze": 14, "quinze": 15, "dezesseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19,
    "vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50,
}
_NUM_WORDS = "|".join(sorted(_NUM, key=len, reverse=True))
_N = rf"(?:\d{{1,2}}|{_NUM_WORDS})"


@dataclass
class When:
    at: Optional[datetime]
    days: Optional[list[int]]
    rest: str


def _num(token: str) -> int:
    token = token.strip()
    if token.isdigit():
        return int(token)
    if " e " in token:  # "vinte e cinco"
        return sum(_NUM.get(p, 0) for p in token.split(" e "))
    return _NUM.get(token, 0)


def _cut(text: str, span: tuple[int, int]) -> str:
    return re.sub(r"\s+", " ", (text[: span[0]] + " " + text[span[1]:])).strip()


def _days(text: str) -> tuple[Optional[list[int]], Optional[int], str]:
    """(dias da repetição, dia da semana único, texto sem eles)."""
    rules = [
        (r"\b(?:todo\s+dia|todos\s+os\s+dias|diariamente|todo\s+santo\s+dia)\b", list(range(7))),
        # "fim de semana" antes de "dias de semana" (senão "de semana" casaria primeiro)
        (r"\b(?:(?:nos?\s+)?(?:fim|fins)\s+de\s+semana|sabado\s+e\s+domingo|sabados\s+e\s+domingos)\b", [5, 6]),
        (r"\b(?:dias?\s+de\s+semana|dias?\s+uteis|de\s+segunda\s+a\s+sexta)\b", [0, 1, 2, 3, 4]),
    ]
    for pattern, days in rules:
        m = re.search(pattern, text)
        if m:
            return days, None, _cut(text, m.span())
    m = re.search(rf"\b(?:toda|todo|todas|todos)\s+(?:as\s+|os\s+)?({'|'.join(WEEKDAYS)})s?(?:\s*-?\s*feiras?)?\b", text)
    if m:
        return [WEEKDAYS.index(m.group(1))], None, _cut(text, m.span())
    m = re.search(rf"\b(?:na\s+|no\s+|nesta\s+|neste\s+|essa\s+|esse\s+|proxima\s+|proximo\s+)?({'|'.join(WEEKDAYS)})(?:\s*-?\s*feira)?\b", text)
    if m:
        return None, WEEKDAYS.index(m.group(1)), _cut(text, m.span())
    return None, None, text


def _clock(text: str) -> tuple[Optional[tuple[int, int]], str]:
    """Hora do dia (h, m) e o texto sem ela."""
    m = re.search(r"\b(?:ao\s+|as\s+|para\s+o\s+|pro\s+)?meio\s+dia(?:\s+e\s+meia)?\b", text)
    if m:
        return (12, 30 if "meia" in m.group(0).split("dia")[-1] else 0), _cut(text, m.span())
    m = re.search(r"\b(?:a\s+|as\s+|para\s+a\s+)?meia\s+noite(?:\s+e\s+meia)?\b", text)
    if m:
        return (0, 30 if "meia" in m.group(0).split("noite")[-1] else 0), _cut(text, m.span())

    m = re.search(
        rf"\b(?:(?:para\s+|pras?\s+)?d?as?\s+)?(\d{{1,2}})\s*(?:h|:)\s*(\d{{2}})\b"        # 6h30, 6:30
        rf"|\b(?:para\s+|pras?\s+)?d?as?\s+({_N})(?:\s*(?:h|hs|horas?))?"                  # as 7, das 7, as sete horas
        rf"(?:\s+e\s+(meia|quinze|{_N}(?:\s+e\s+{_N})?)(?:\s+minutos?)?)?\b"               # e meia, e 15
        rf"|\b(\d{{1,2}})\s*(?:h|hs|horas)\b(?:\s+e\s+(meia|{_N}))?",                      # 7h, 7 horas
        text,
    )
    if not m:
        return None, text
    if m.group(1):
        h, mi = int(m.group(1)), int(m.group(2))
    elif m.group(3):
        h = _num(m.group(3))
        extra = m.group(4)
        mi = 30 if extra == "meia" else (_num(extra) if extra else 0)
    else:
        h = int(m.group(5))
        extra = m.group(6)
        mi = 30 if extra == "meia" else (_num(extra) if extra else 0)
    rest = _cut(text, m.span())

    period = re.search(r"\b(?:da|de)\s+(manha|tarde|noite|madrugada)\b", rest)
    if period:
        p = period.group(1)
        if p in ("tarde", "noite") and h < 12:
            h += 12
        if p == "noite" and h == 12:  # "12 da noite" = meia-noite
            h = 0
        if p in ("manha", "madrugada") and h == 12:
            h = 0
        rest = _cut(rest, period.span())
    if not (0 <= h <= 23 and 0 <= mi <= 59):
        return None, text
    return (h, mi), rest


def _relative(text: str) -> tuple[Optional[timedelta], str]:
    m = re.search(r"\b(?:daqui\s+(?:a\s+)?|em\s+|dentro\s+de\s+)(?:uma\s+)?meia\s+hora\b", text)
    if m:
        return timedelta(minutes=30), _cut(text, m.span())
    m = re.search(
        rf"\b(?:daqui\s+(?:a\s+)?|em\s+|dentro\s+de\s+)({_N})\s+horas?(?:\s+e\s+(meia|{_N})(?:\s+minutos?)?)?\b"
        rf"|\b(?:daqui\s+(?:a\s+)?|em\s+|dentro\s+de\s+)({_N}(?:\s+e\s+{_N})?)\s+minutos?\b",
        text,
    )
    if not m:
        return None, text
    if m.group(1):
        extra = m.group(2)
        delta = timedelta(hours=_num(m.group(1)), minutes=30 if extra == "meia" else (_num(extra) if extra else 0))
    else:
        delta = timedelta(minutes=_num(m.group(3)))
    if delta.total_seconds() <= 0:
        return None, text
    return delta, _cut(text, m.span())


def next_on_days(h: int, mi: int, days: list[int], now: datetime) -> datetime:
    """Próximo horário h:mi num dos dias da semana (a partir de agora, sem contar o minuto atual)."""
    for add in range(0, 8):
        cand = (now + timedelta(days=add)).replace(hour=h, minute=mi, second=0, microsecond=0)
        if cand.weekday() in days and cand > now:
            return cand
    return (now + timedelta(days=7)).replace(hour=h, minute=mi, second=0, microsecond=0)


def parse(text: str, now: Optional[datetime] = None) -> When:
    now = now or datetime.now()
    text = re.sub(r"\s+", " ", text or "").strip()

    delta, rest = _relative(text)
    if delta:
        return When(now.replace(second=0, microsecond=0) + delta + (timedelta(minutes=1) if now.second else timedelta()), None, rest)

    days, weekday, rest = _days(text)
    day_offset = None
    m = re.search(r"\bdepois\s+de\s+amanha\b", rest)
    if m:
        day_offset, rest = 2, _cut(rest, m.span())
    else:
        m = re.search(r"\bamanha\b", rest)
        if m:
            day_offset, rest = 1, _cut(rest, m.span())
        else:
            m = re.search(r"\bhoje\b", rest)
            if m:
                day_offset, rest = 0, _cut(rest, m.span())
    date_match = re.search(r"\bdia\s+(\d{1,2})(?:\s+(?:de\s+)?(\d{1,2}))?\b", rest)
    fixed_date = None
    if date_match:
        day = int(date_match.group(1))
        month = int(date_match.group(2)) if date_match.group(2) else now.month
        try:
            fixed_date = now.replace(month=month, day=day)
            if fixed_date.date() < now.date():
                fixed_date = fixed_date.replace(year=now.year + 1) if date_match.group(2) else (
                    fixed_date.replace(month=month % 12 + 1, year=now.year + (1 if month == 12 else 0)))
            rest = _cut(rest, date_match.span())
        except ValueError:
            fixed_date = None

    clock, rest = _clock(rest)
    if clock is None:
        return When(None, days, rest)
    h, mi = clock

    if days:
        return When(next_on_days(h, mi, days, now), days, rest)
    if weekday is not None:
        return When(next_on_days(h, mi, [weekday], now), None, rest)
    if fixed_date is not None:
        return When(fixed_date.replace(hour=h, minute=mi, second=0, microsecond=0), None, rest)
    base = now + timedelta(days=day_offset or 0)
    at = base.replace(hour=h, minute=mi, second=0, microsecond=0)
    if day_offset is None and at <= now:
        # "às 7" quando já passou das 7: se for de manhã e der para ser à noite, prefere hoje à noite
        if h < 12 and at.replace(hour=h + 12) > now and not re.search(r"\bmanha\b", text):
            at = at.replace(hour=h + 12)
        else:
            at += timedelta(days=1)
    return When(at, None, rest)


def describe(at: datetime, days: Optional[list[int]] = None, now: Optional[datetime] = None) -> str:
    """Como o JARVIS fala o horário: "amanhã às 07:00", "hoje às 19:30", "de segunda a sexta às 06:00"."""
    now = now or datetime.now()
    hm = at.strftime("%H:%M")
    if days:
        if sorted(days) == list(range(7)):
            return f"todos os dias às {hm}"
        if sorted(days) == [0, 1, 2, 3, 4]:
            return f"de segunda a sexta às {hm}"
        if sorted(days) == [5, 6]:
            return f"nos fins de semana às {hm}"
        names = [WEEKDAY_NAMES[d] for d in sorted(days)]
        return f"toda {names[0]} às {hm}" if len(names) == 1 else "às " + ", ".join(names[:-1]) + f" e {names[-1]}s às {hm}"
    delta_days = (at.date() - now.date()).days
    if delta_days == 0:
        return f"hoje às {hm}"
    if delta_days == 1:
        return f"amanhã às {hm}"
    if 1 < delta_days < 7:
        return f"{WEEKDAY_NAMES[at.weekday()]} às {hm}"
    return f"dia {at.day:02d}/{at.month:02d} às {hm}"

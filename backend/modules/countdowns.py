"""V5.6: contagem regressiva até um compromisso ou uma data, por voz, com widget na central.

"Jarvis, contagem regressiva para a viagem"      -> acha "Viagem a Maceió" na agenda e põe o widget na tela
"Jarvis, contagem regressiva até dia 20 de dezembro"
"Jarvis, quanto falta para o natal?"             -> só responde (sem widget)
"Jarvis, apaga a contagem regressiva"            -> tira o widget (todas, ou a que for citada)

As contagens ficam nas preferências (valem para o PC, o site e o celular) e entram no "bom dia".
"""
from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime, timedelta
from typing import Optional

from modules import prefs

log = logging.getLogger("jarvis.countdowns")

MAX_COUNTDOWNS = 3
_MONTHS = {"janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6, "julho": 7,
           "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12}
_FIXED = {"natal": (12, 25, "Natal"), "ano novo": (1, 1, "Ano-Novo"), "reveillon": (1, 1, "Ano-Novo")}
_STOP = {"a", "o", "as", "os", "de", "da", "do", "das", "dos", "para", "pra", "ate", "ao", "aos", "minha", "meu",
         "minhas", "meus", "uma", "um", "e", "no", "na", "nos", "nas", "dia", "proxima", "proximo"}

_broadcast = None  # main injeta runtime.manager.broadcast (evita import circular)


def configure(broadcast=None) -> None:
    global _broadcast
    _broadcast = broadcast


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFD", (text or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn").strip()


def list_countdowns(now: Optional[datetime] = None) -> list[dict]:
    """Ativas, da mais próxima para a mais distante. As que já passaram há mais de 1 dia somem."""
    now = now or datetime.now()
    items = []
    for c in prefs._load().get("countdowns") or []:
        try:
            target = datetime.fromisoformat(c["target"])
        except (KeyError, ValueError):
            continue
        if target < now - timedelta(days=1):
            continue
        items.append(c)
    items.sort(key=lambda c: c["target"])
    return items


def _save(items: list[dict]) -> None:
    prefs.update(countdowns=items)


async def _announce() -> None:
    if _broadcast:
        try:
            await _broadcast({"type": "countdowns", "items": list_countdowns()})
        except Exception as exc:  # noqa: BLE001
            log.debug("Não consegui avisar as telas da contagem: %s", exc)


def add(title: str, target: datetime, all_day: bool) -> dict:
    items = [c for c in list_countdowns() if _norm(c["title"]) != _norm(title)]
    new = {"id": int(datetime.now().timestamp() * 1000) % 10**10, "title": title[:60],
           "target": target.replace(second=0, microsecond=0).isoformat(), "all_day": all_day}
    items.append(new)
    items.sort(key=lambda c: c["target"])
    _save(items[:MAX_COUNTDOWNS])
    return new


def remove(countdown_id: Optional[int] = None, title_hint: str = "") -> int:
    items = list_countdowns()
    if countdown_id is not None:
        left = [c for c in items if c["id"] != countdown_id]
    elif title_hint:
        hint = set(_words(title_hint))
        left = [c for c in items if not (hint & set(_words(c["title"])))]
    else:
        left = []
    _save(left)
    return len(items) - len(left)


def remaining_text(target: datetime, now: Optional[datetime] = None, all_day: bool = False) -> str:
    """ "3 dias e 4 horas", "amanhã", "2 horas e 10 minutos", "é hoje". """
    now = now or datetime.now()
    if all_day:
        days = (target.date() - now.date()).days
        if days <= 0:
            return "é hoje"
        if days == 1:
            return "falta 1 dia"
        return f"faltam {days} dias"
    delta = target - now
    if delta.total_seconds() <= 0:
        return "já começou"
    days, secs = delta.days, delta.seconds
    hours, minutes = secs // 3600, (secs % 3600) // 60
    if days >= 1:
        parts = f"{days} {'dia' if days == 1 else 'dias'}" + (f" e {hours} {'hora' if hours == 1 else 'horas'}" if hours else "")
        return f"{'falta' if days == 1 and not hours else 'faltam'} {parts}"
    if hours >= 1:
        return f"faltam {hours} {'hora' if hours == 1 else 'horas'}" + (f" e {minutes} minutos" if minutes else "")
    return f"faltam {max(1, minutes)} minutos"


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", _norm(text)) if w not in _STOP and len(w) > 1]


def _date_from_text(text: str, now: datetime) -> Optional[tuple[datetime, str]]:
    """Datas faladas: "dia 20 de dezembro", "dia 20/12", "20/12", "natal", "ano novo"."""
    t = _norm(text)
    for key, (month, day, label) in _FIXED.items():
        if re.search(rf"\b{key}\b", t):
            target = datetime(now.year, month, day)
            if target.date() < now.date():
                target = target.replace(year=now.year + 1)
            return target, label
    m = re.search(r"\b(?:dia\s+)?(\d{1,2})\s*(?:/\s*(\d{1,2})|\s+de\s+([a-z]+))\b", t) or re.search(r"\bdia\s+(\d{1,2})\b()()", t)
    if not m:
        return None
    day = int(m.group(1))
    month = int(m.group(2)) if m.group(2) else _MONTHS.get(m.group(3) or "", now.month if not m.group(3) else 0)
    if not month:
        return None
    try:
        target = datetime(now.year, month, day)
    except ValueError:
        return None
    if target.date() < now.date():
        target = target.replace(year=now.year + 1)
    return target, f"dia {day:02d}/{month:02d}"


def _find_event(hint: str, now: datetime) -> Optional[dict]:
    """Compromisso da agenda (ou lembrete) cujo título mais combina com o que foi dito."""
    from modules import calendar_hub, reminders

    wanted = set(_words(hint))
    if not wanted:
        return None
    candidates = []
    try:
        candidates += calendar_hub.upcoming_events(days=180, limit=150)
    except Exception as exc:  # noqa: BLE001
        log.warning("Contagem: agenda indisponível: %s", exc)
    for r in reminders.get_reminders(only_pending=True):
        dh = r.get("data_hora", "")
        if dh:
            candidates.append({"title": r.get("texto", ""), "start": dh.replace(" ", "T") + ":00"})
    best, best_score = None, 0
    for ev in candidates:
        score = len(wanted & set(_words(ev.get("title", ""))))
        if score > best_score:
            best, best_score = ev, score
    return best


def _target_label(target: datetime, all_day: bool, now: datetime) -> str:
    from modules.when import describe

    if all_day:
        days = (target.date() - now.date()).days
        return "hoje" if days == 0 else "amanhã" if days == 1 else f"dia {target.day:02d}/{target.month:02d}"
    return describe(target, None, now)


async def handle_voice(message: str, now: Optional[datetime] = None) -> Optional[str]:
    from modules import calendar_hub

    now = now or datetime.now()
    t = _norm(message)
    if not re.search(r"contagem regressiva|quanto(s dias)? falta|quantos dias (?:faltam|para|pra)", t):
        return None
    # Timer de cozinha ("contagem regressiva de 5 minutos", "quanto falta no timer") é com o timer
    if re.search(r"\b(timer|temporizador|cronometro)\b", t) or re.search(
            r"contagem regressiva de \d+\s*(?:s|seg|segundos?|min|minutos?|h|horas?)\b", t):
        return None

    if re.search(r"\b(apaga|apague|remove|remova|tira|tire|cancela|cancele|para|pare|desliga)\b.*contagem", t):
        rest = re.sub(r".*contagem regressiva\s*(?:d[aeo]s?|para|pra|ate)?\s*", "", t)
        n = remove(title_hint=rest)
        await _announce()
        return "Contagem regressiva removida da tela." if n else "Não havia contagem regressiva na tela."

    wants_widget = "contagem regressiva" in t
    rest = re.split(r"contagem regressiva|quantos dias faltam|quanto(?:s dias)? falta[m]?", t, maxsplit=1)[-1]
    rest = re.sub(r"^\s*(?:d[aeo]s?|para|pra|ate|ao|a|o)\b\s*", "", rest).strip(" ?.!")
    if not rest:
        return "Para quando, senhor? Diga, por exemplo, \"contagem regressiva para a viagem\" ou \"até dia 20 de dezembro\"."

    found = _date_from_text(rest, now)
    if found:
        target, title, all_day = found[0], found[1], True
        if title.startswith("dia "):
            title = f"Até {title}"
    else:
        ev = _find_event(rest, now)
        if not ev:
            hint = "" if calendar_hub.connected() else (
                " Conecte sua agenda em Fontes de Dados para eu procurar os compromissos.")
            return f"Não encontrei \"{rest}\" na sua agenda nem nos lembretes.{hint}"
        target = calendar_hub.event_start(ev)
        if target is None:
            return "Achei o compromisso, mas não entendi a data dele."
        title = ev.get("title", "Compromisso")
        all_day = "T" not in (ev.get("start") or "")

    falta = remaining_text(target, now, all_day)
    when_label = _target_label(target, all_day, now)
    reply = f"{falta[0].upper()}{falta[1:]} para {title} ({when_label})."
    if wants_widget:
        add(title, target, all_day)
        await _announce()
        reply += " Coloquei a contagem regressiva na tela."
    return reply


def briefing_lines(now: Optional[datetime] = None) -> list[str]:
    """Para o "bom dia": "Faltam 12 dias para Viagem." (o número cai a cada dia)."""
    now = now or datetime.now()
    out = []
    for c in list_countdowns(now):
        try:
            target = datetime.fromisoformat(c["target"])
        except ValueError:
            continue
        falta = remaining_text(target, now, c.get("all_day", False))
        out.append(f"{falta[0].upper()}{falta[1:]} para {c['title']}.")
    return out

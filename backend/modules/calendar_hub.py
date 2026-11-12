"""V5.6: uma porta só para o calendário do usuário.

Duas fontes, na ordem:
1. Google Calendar pela API (OAuth, GOOGLE_CLIENT_ID no .env) — se estiver conectado;
2. o "endereço secreto no formato iCal" do Google Agenda (ou de qualquer agenda .ics), colado uma vez
   em Fontes de Dados. Não precisa criar projeto no Google Cloud: o Google Agenda dá esse link em
   Configurações › (sua agenda) › Integrar agenda › Endereço secreto no formato iCal.

upcoming_events() devolve sempre o mesmo formato do modules/google_calendar:
{id, title, start ("AAAA-MM-DD" no dia todo, "AAAA-MM-DDTHH:MM:SS" com hora), location, link}.
"""
from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta
from typing import Optional

import requests

from modules import google_calendar, prefs

log = logging.getLogger("jarvis.calendar")

CACHE_SECONDS = 10 * 60
_cache: dict[str, tuple[float, bytes]] = {}


def ics_url() -> str:
    return (prefs._load().get("calendar_ics_url") or "").strip()


def connected() -> bool:
    return google_calendar.connected() or bool(ics_url())


def source_name() -> str:
    if google_calendar.connected():
        return "Google Agenda"
    return "Agenda (iCal)" if ics_url() else ""


def _valid_url(url: str) -> bool:
    return url.startswith("https://") and len(url) < 2000 and " " not in url


def _fetch(url: str, force: bool = False) -> bytes:
    now = time.time()
    hit = _cache.get(url)
    if hit and not force and now - hit[0] < CACHE_SECONDS:
        return hit[1]
    res = requests.get(url, timeout=15, headers={"User-Agent": "JARVIS-agenda/1.0"})
    res.raise_for_status()
    if b"BEGIN:VCALENDAR" not in res.content[:2000]:
        raise ValueError("O endereço não devolveu uma agenda no formato iCal.")
    _cache[url] = (now, res.content)
    return res.content


def _to_local_naive(value) -> tuple[datetime, bool]:
    """(início local sem fuso, dia_todo)."""
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone().replace(tzinfo=None)
        return value, False
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day), True
    raise TypeError("data inválida")


def _ics_events(days: int, limit: int, now: Optional[datetime] = None, raw: Optional[bytes] = None) -> list[dict]:
    import icalendar
    import recurring_ical_events

    now = now or datetime.now()
    data = raw if raw is not None else _fetch(ics_url())
    cal = icalendar.Calendar.from_ical(data)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = now + timedelta(days=days)
    out = []
    for ev in recurring_ical_events.of(cal).between(start, end):
        try:
            begin, all_day = _to_local_naive(ev.get("DTSTART").dt)
        except Exception:  # noqa: BLE001 - evento sem data: ignora
            continue
        if not all_day and begin < now:
            continue  # já começou/passou hoje
        title = str(ev.get("SUMMARY") or "Sem título").strip()
        out.append({
            "id": str(ev.get("UID") or f"{title}-{begin.isoformat()}"),
            "title": title,
            "start": begin.strftime("%Y-%m-%d") if all_day else begin.strftime("%Y-%m-%dT%H:%M:%S"),
            "location": str(ev.get("LOCATION") or "").strip(),
            "link": "",
        })
    out.sort(key=lambda e: e["start"])
    return out[:limit]


def upcoming_events(days: int = 14, limit: int = 10) -> list[dict]:
    if google_calendar.connected():
        return google_calendar.upcoming_events(days=days, limit=limit)
    if ics_url():
        return _ics_events(days, limit)
    return []


def set_ics_url(url: str) -> dict:
    """Salva o endereço iCal depois de conferir que ele responde. "" desconecta."""
    url = (url or "").strip()
    if not url:
        prefs.update(calendar_ics_url="")
        return {"connected": google_calendar.connected(), "source": source_name()}
    if url.startswith("webcal://"):
        url = "https://" + url[len("webcal://"):]
    if not _valid_url(url):
        raise ValueError("Cole o endereço completo, começando com https://")
    raw = _fetch(url, force=True)
    events = _ics_events(30, 50, raw=raw)
    prefs.update(calendar_ics_url=url)
    return {"connected": True, "source": source_name(), "next_30_days": len(events)}


def event_start(ev: dict) -> Optional[datetime]:
    s = ev.get("start") or ""
    try:
        if "T" in s:
            dt = datetime.fromisoformat(s)
            return dt.astimezone().replace(tzinfo=None) if dt.tzinfo else dt
        return datetime.strptime(s[:10], "%Y-%m-%d")
    except ValueError:
        return None

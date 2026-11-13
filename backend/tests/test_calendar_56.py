"""V5.6: agenda por iCal, próximos 3 dias no briefing e contagem regressiva por voz."""
import asyncio
from datetime import datetime, timedelta

from modules import briefing, calendar_hub, countdowns, reminders

NOW = datetime(2026, 11, 12, 9, 0)

ICS = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//teste//PT
BEGIN:VEVENT
UID:viagem-1
DTSTART:20261115T080000
DTEND:20261115T100000
SUMMARY:Viagem a Maceio
LOCATION:Aeroporto
END:VEVENT
BEGIN:VEVENT
UID:academia
DTSTART:20261110T183000
DTEND:20261110T193000
RRULE:FREQ=WEEKLY;BYDAY=TU,TH
SUMMARY:Academia
END:VEVENT
BEGIN:VEVENT
UID:aniver
DTSTART;VALUE=DATE:20261113
DTEND;VALUE=DATE:20261114
SUMMARY:Aniversario da Ana
END:VEVENT
END:VCALENDAR
"""


def test_ics_expands_recurring_and_all_day():
    events = calendar_hub._ics_events(days=4, limit=20, now=NOW, raw=ICS)  # noqa: SLF001
    titles = [(e["title"], e["start"]) for e in events]
    assert ("Aniversario da Ana", "2026-11-13") in titles
    assert ("Viagem a Maceio", "2026-11-15T08:00:00") in titles
    assert ("Academia", "2026-11-12T18:30:00") in titles  # quinta: regra semanal expandida


def test_upcoming_segment_counts_down(monkeypatch):
    monkeypatch.setattr(reminders, "get_reminders", lambda only_pending=True: [])
    events = calendar_hub._ics_events(days=4, limit=20, now=NOW, raw=ICS)  # noqa: SLF001
    seg = briefing._upcoming_segment(NOW, events)  # noqa: SLF001
    assert seg["card"]["label"] == "PRÓXIMOS 3 DIAS"
    times = [i["time"] for i in seg["card"]["items"]]
    assert times == ["AMANHÃ", "EM 3D"]
    assert "amanhã, Aniversario da Ana" in seg["speech"] and "em 3 dias, Viagem a Maceio às 08:00" in seg["speech"]


def test_countdown_by_date_and_by_event(monkeypatch):
    monkeypatch.setattr(calendar_hub, "upcoming_events",
                        lambda days=14, limit=10: calendar_hub._ics_events(days, limit, now=NOW, raw=ICS))  # noqa: SLF001
    monkeypatch.setattr(reminders, "get_reminders", lambda only_pending=True: [])
    reply = asyncio.run(countdowns.handle_voice("Jarvis, contagem regressiva para a viagem", NOW))
    assert reply.startswith("Faltam 2 dias e 23 horas para Viagem a Maceio") and "na tela" in reply
    assert [c["title"] for c in countdowns.list_countdowns(NOW)] == ["Viagem a Maceio"]

    natal = asyncio.run(countdowns.handle_voice("quanto falta para o natal", NOW))
    assert natal.startswith("Faltam 43 dias para Natal") and "na tela" not in natal

    asyncio.run(countdowns.handle_voice("contagem regressiva até dia 20 de dezembro", NOW))
    assert len(countdowns.list_countdowns(NOW)) == 2
    assert countdowns.briefing_lines(NOW)[0].startswith("Faltam 2 dias e 23 horas para Viagem")

    removed = asyncio.run(countdowns.handle_voice("apaga a contagem regressiva", NOW))
    assert removed == "Contagem regressiva removida da tela." and countdowns.list_countdowns(NOW) == []


def test_kitchen_timer_is_not_a_countdown():
    assert asyncio.run(countdowns.handle_voice("contagem regressiva de 5 minutos", NOW)) is None
    assert asyncio.run(countdowns.handle_voice("quanto falta no timer", NOW)) is None


def test_remaining_text():
    assert countdowns.remaining_text(NOW + timedelta(days=1), NOW) == "falta 1 dia"
    assert countdowns.remaining_text(NOW + timedelta(hours=2, minutes=5), NOW) == "faltam 2 horas e 5 minutos"
    assert countdowns.remaining_text(datetime(2026, 11, 12), NOW, all_day=True) == "é hoje"


def test_calendar_status_route_68():
    """V6.8.1: seção Google Agenda dos Ajustes mostra se está conectada."""
    from fastapi.testclient import TestClient

    import main
    from modules import access, prefs

    access.reset_for_tests(access.UNLOCKED)
    c = TestClient(main.app)
    assert c.get("/api/calendar/status").json() == {"connected": False, "source": "", "ics": False}
    prefs.update(calendar_ics_url="https://calendar.google.com/calendar/ical/x/basic.ics")
    assert c.get("/api/calendar/status").json() == {"connected": True, "source": "Agenda (iCal)", "ics": True}

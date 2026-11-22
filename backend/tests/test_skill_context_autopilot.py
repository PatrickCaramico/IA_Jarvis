"""V8.11: Skill Context Autopilot (aviso antes da reunião e modo reunião)."""
import asyncio
import time
from datetime import datetime, timedelta

import pytest

from core import confirm, session
from core.skills import executor, registry, router
from modules import access, prefs
from skills import context_autopilot as ap

NOW = datetime(2026, 11, 23, 14, 55)


def run(coro):
    return asyncio.run(coro)


def ev(title, start, **kw):
    return {"id": kw.pop("id", title), "title": title, "start": start.strftime("%Y-%m-%dT%H:%M:%S"), **kw}


@pytest.fixture
def pilot(real_skills, monkeypatch):
    delivered, opened = [], []

    async def fake_deliver(text, phone):
        delivered.append(text)

    async def fake_open(url):
        opened.append(url)

    monkeypatch.setattr(ap, "_deliver", fake_deliver)
    monkeypatch.setattr(ap, "_pause_music", lambda: True)
    monkeypatch.setattr(executor, "_open_on_device", fake_open)
    monkeypatch.setattr(ap, "SILENCE_DELAY_S", 0)
    prefs.set_silent_mode(False)
    return delivered, opened


def test_meeting_link_from_any_field():
    assert ap.meeting_link({"meet": "https://meet.google.com/abc-defg-hij"}) == "https://meet.google.com/abc-defg-hij"
    assert ap.meeting_link({"description": "Entrar: https://us02web.zoom.us/j/123?pwd=x."}) == "https://us02web.zoom.us/j/123?pwd=x"
    assert ap.meeting_link({"location": "https://teams.microsoft.com/l/meetup-join/19%3a"}).startswith("https://teams.")
    assert ap.meeting_link({"location": "Sala 3", "description": "https://example.com/doc"}) == ""


def test_due_events_window():
    events = [ev("Daily", NOW + timedelta(minutes=4)), ev("Almoço", NOW + timedelta(minutes=40)),
              {"id": "f", "title": "Feriado", "start": NOW.strftime("%Y-%m-%d")},
              ev("Já passou", NOW - timedelta(minutes=10))]
    due = ap.due_events(events, NOW, 5, {})
    assert [(e["title"], m) for e, m in due] == [("Daily", 4)]
    assert ap.due_events(events, NOW, 5, {ap.event_key(events[0]): time.time()}) == []


def test_offers_meeting_mode_once(pilot, monkeypatch):
    delivered, _ = pilot
    daily = ev("Daily do time", NOW + timedelta(minutes=5), meet="https://meet.google.com/abc-defg-hij",
               end=(NOW + timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:%S"))
    monkeypatch.setattr(ap, "_fetch_events", lambda force=False: [daily])
    assert run(ap.check_once(NOW)) == 1
    assert delivered == ["Senhor, Daily do time começa em 5 minutos. Quer que eu ative o modo reunião e abra o link "
                         "da chamada? Diga sim para ativar."]
    pending = session.pending_action["data"]
    assert pending["name"] == "modo_reuniao" and pending["args"]["link"].startswith("https://meet.google.com/")
    assert run(ap.check_once(NOW + timedelta(minutes=1))) == 0  # não repete


def test_yes_activates_meeting_mode_and_end_restores(pilot, monkeypatch):
    delivered, opened = pilot
    daily = ev("Daily", NOW + timedelta(minutes=3), meet="https://meet.google.com/abc-defg-hij")
    monkeypatch.setattr(ap, "_fetch_events", lambda force=False: [daily])
    run(ap.check_once(NOW))

    async def say_yes():
        reply = await confirm.answer("sim")
        await asyncio.sleep(0.05)  # o silêncio entra depois da confirmação falada
        return reply

    reply = run(say_yes())
    assert reply.startswith("Modo reunião ativado: música pausada, abrindo o link da chamada.")
    assert opened == ["https://meet.google.com/abc-defg-hij"]
    assert prefs.is_silent_mode() is True
    assert ap.load_state()["meeting"]["active"] is True
    result = run(router.try_fast_path("terminei a reunião"))
    assert result.speech.startswith("Modo reunião encerrado")
    assert prefs.is_silent_mode() is False and ap.load_state()["meeting"] is None


def test_meeting_mode_keeps_silence_the_user_already_had(pilot):
    prefs.set_silent_mode(True)
    run(router.try_fast_path("ativa o modo reunião"))
    run(router.try_fast_path("sai do modo reunião"))
    assert prefs.is_silent_mode() is True


def test_meeting_ends_by_itself_after_the_event(pilot, monkeypatch):
    monkeypatch.setattr(ap, "_fetch_events", lambda force=False: [])
    run(executor.execute("modo_reuniao", {"evento": "Review", "fim": "2026-01-01T10:00:00"}))
    assert ap.load_state()["meeting"]["active"] is True
    run(ap.check_once(NOW))
    assert ap.load_state()["meeting"] is None


def test_busy_jarvis_waits_for_the_next_round(pilot, monkeypatch):
    delivered, _ = pilot
    monkeypatch.setattr(ap, "_fetch_events", lambda force=False: [ev("1:1", NOW + timedelta(minutes=4))])
    session.busy = True
    try:
        assert run(ap.check_once(NOW)) == 0 and delivered == []
    finally:
        session.busy = False
    assert run(ap.check_once(NOW)) == 1


def test_other_pending_question_is_not_overwritten(pilot, monkeypatch):
    delivered, _ = pilot
    confirm.offer("organize", {"x": 1})
    monkeypatch.setattr(ap, "_fetch_events", lambda force=False: [ev("1:1", NOW + timedelta(minutes=4))])
    run(ap.check_once(NOW))
    assert delivered == ["Senhor, 1:1 começa em 4 minutos."]
    assert session.pending_action["kind"] == "organize"


def test_disabled_pilot_stays_quiet(pilot, monkeypatch):
    delivered, _ = pilot
    monkeypatch.setattr(ap, "_fetch_events", lambda force=False: [ev("1:1", NOW + timedelta(minutes=4))])
    assert "desligado" in run(router.try_fast_path("desliga o piloto automático da agenda")).speech
    assert run(ap.check_once(NOW)) == 0
    assert "10 minutos antes" in run(router.try_fast_path("me avise 10 minutos antes das reuniões")).speech
    state = ap.load_state()
    assert state["enabled"] is True and state["lead_min"] == 10
    registry.set_enabled("modo_reuniao", False)
    assert run(ap.check_once(NOW)) == 0


def test_locked_central_only_notifies_the_phone(real_skills, monkeypatch, credentials):
    from core import runtime

    notified, sent = [], []
    monkeypatch.setattr(runtime, "notify", lambda kind, title, body: notified.append(body))

    async def fake_broadcast(event):
        sent.append(event)

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    access.reset_for_tests(access.LOCKED)
    run(ap._deliver("Senhor, Consulta médica começa em 5 minutos.", "Consulta médica às 15:00"))
    assert notified == ["Consulta médica às 15:00"] and sent == []


def test_next_meeting(pilot, monkeypatch):
    from modules import calendar_hub

    start = datetime.now() + timedelta(minutes=30)
    monkeypatch.setattr(calendar_hub, "connected", lambda: True)
    monkeypatch.setattr(ap, "_fetch_events", lambda force=False: [ev("Planejamento", start, location="https://zoom.us/j/1")])
    result = run(router.try_fast_path("qual minha próxima reunião?"))
    assert result.speech.startswith("Sua próxima reunião é Planejamento, daqui a 30 minutos.")
    assert "link de chamada" in result.speech


def test_calendar_events_now_bring_end_and_call_link():
    from modules import calendar_hub

    raw = (b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VEVENT\r\nUID:x1\r\nSUMMARY:Daily\r\n"
           b"DTSTART:20261123T150000\r\nDTEND:20261123T151500\r\n"
           b"DESCRIPTION:Entrar: https://meet.google.com/abc-defg-hij\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n")
    (item,) = calendar_hub._ics_events(2, 5, now=NOW, raw=raw)
    assert item["end"] == "2026-11-23T15:15:00"
    assert ap.meeting_link(item) == "https://meet.google.com/abc-defg-hij"

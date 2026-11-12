"""V5.3: briefing mais pessoal (prioridades, jogo do time, despertador, conselho do clima, próximo compromisso)."""
import asyncio
from datetime import datetime, timedelta

from modules import alarms, briefing, prefs, sports_provider, tasks
from tests.test_briefing_43 import offline  # noqa: F401 - fixture


def test_greeting_follows_the_clock():
    assert briefing.greeting_word(datetime(2026, 11, 11, 8)) == "Bom dia"
    assert briefing.greeting_word(datetime(2026, 11, 11, 15)) == "Boa tarde"
    assert briefing.greeting_word(datetime(2026, 11, 11, 21)) == "Boa noite"


def test_weather_tip_and_icon():
    assert briefing.weather_tip(20, 26, 70) == "Vale levar um guarda-chuva."
    assert "calor" in briefing.weather_tip(24, 33, 10)
    assert "casaco" in briefing.weather_tip(12, 22, 0)
    assert "trovoadas" in briefing.weather_tip(20, 26, 90, code=95)
    assert briefing.weather_tip(18, 26, 10) == ""
    assert briefing.weather_icon(61) == "☂" and briefing.weather_icon(0) == "☀" and briefing.weather_icon(3) == "☁"


def test_morning_weather_card_carries_tip(offline):  # noqa: F811
    data = asyncio.run(briefing.build_morning_briefing())
    weather = data["segments"][0]
    assert weather["card"]["tip"] == "Vale levar um guarda-chuva." and "guarda-chuva" in weather["speech"]


def test_pending_tasks_become_priorities(offline, monkeypatch):  # noqa: F811
    monkeypatch.setattr(tasks, "get_tasks", lambda include_completed=False: [
        {"id": 1, "texto": "Pagar a luz"}, {"id": 2, "texto": "Revisar o contrato"}, {"id": 3, "texto": "Ligar pro banco"}])
    data = asyncio.run(briefing.build_morning_briefing())
    kinds = [s["card"]["kind"] for s in data["segments"]]
    assert kinds[:3] == ["weather", "agenda", "tasks"]
    focus = data["segments"][2]
    assert focus["card"]["label"] == "PRIORIDADES · HOJE" and "Pagar a luz" in focus["card"]["title"]
    assert "Sugiro começar por Pagar a luz" in focus["speech"]
    assert "tarefas" in [t["id"] for t in data["tabs"]]
    assert "Pagar a luz" in data["closing"]


def test_match_day_enters_the_morning(offline, monkeypatch):  # noqa: F811
    prefs.update(fan_mode_enabled=True, fan_team="palmeiras")
    today = datetime.now().replace(hour=21, minute=30, second=0, microsecond=0)
    monkeypatch.setattr(sports_provider, "get_current_or_next_match", lambda team: {
        "opponent": "Remo", "competition": "Brasileirão", "date": today.isoformat(), "venue": "Allianz Parque",
        "status": "scheduled", "is_match_day": True, "time_known": True})
    data = asyncio.run(briefing.build_morning_briefing())
    match = next(s for s in data["segments"] if s["tab"] == "jogo")
    assert match["card"]["title"] == "Palmeiras x Remo"
    assert match["speech"] == "E hoje tem Palmeiras, contra Remo, às 21:30."


def test_no_match_segment_without_fan_mode(offline):  # noqa: F811
    data = asyncio.run(briefing.build_morning_briefing())
    assert all(s["tab"] != "jogo" for s in data["segments"])


def test_evening_mentions_tomorrows_alarm(offline):  # noqa: F811
    tomorrow = (datetime.now() + timedelta(days=1)).replace(hour=6, minute=30, second=0, microsecond=0)
    alarms.add_alarm(tomorrow, label="academia")
    data = asyncio.run(briefing.build_evening_briefing())
    alarm = next(s for s in data["segments"] if s["card"]["label"] == "DESPERTADOR · AMANHÃ")
    assert alarm["speech"] == "Seu despertador de amanhã está marcado para as 06:30."
    assert {"label": "Para", "value": "academia"} in alarm["card"]["items"]


def test_early_day_without_alarm_offers_one():
    closing = briefing._evening_closing(0, [{"time": "07:00", "title": "Voo"}], None, has_alarm=False)
    assert "não há despertador" in closing and "me acorda às" in closing


def test_agenda_speaks_the_next_event_not_a_past_one(monkeypatch):
    from modules import reminders

    now = datetime.now()
    past = (now - timedelta(hours=1)).strftime("%H:%M")
    soon = (now + timedelta(minutes=40)).strftime("%H:%M")
    if past > soon:  # perto da meia-noite: o teste não faz sentido
        return
    day = now.strftime("%Y-%m-%d")
    monkeypatch.setattr(reminders, "get_reminders", lambda only_pending=True: [
        {"texto": "Café", "data_hora": f"{day} {past}"}, {"texto": "Reunião", "data_hora": f"{day} {soon}"}])
    seg = briefing._agenda_segment(now, [])
    assert "O próximo é Reunião" in seg["speech"] and "daqui a" in seg["speech"]
    assert 38 <= seg["card"]["next_in"] <= 40

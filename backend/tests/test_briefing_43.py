"""V4.3: briefing "bom dia" em etapas (segmentos, triagem de e-mail, sequência pelo WebSocket)."""
import asyncio
import copy

import pytest

from core import briefing_flow, runtime, session
from modules import briefing, email_triage, google_calendar, health, news_radar, prefs, reminders, tasks
from modules import tools

WEATHER = {
    "place": "Maragogi",
    "data": {
        "current": {"temperature_2m": 26.7, "apparent_temperature": 30.0, "weather_code": 1, "wind_speed_10m": 18.3},
        "daily": {"temperature_2m_min": [23.3], "temperature_2m_max": [27.5], "precipitation_probability_max": [62]},
    },
}
NEWS = [{"title": "Manchete de teste", "source": "Correio Braziliense",
         "source_url": "https://www.correiobraziliense.com.br", "link": "https://exemplo/x", "published": ""}]


@pytest.fixture
def offline(monkeypatch, isolated_data):
    """Todas as fontes do briefing sem rede."""
    monkeypatch.setattr(tools, "_fetch_weather", lambda city: WEATHER)
    monkeypatch.setattr(google_calendar, "connected", lambda: False)
    monkeypatch.setattr(email_triage, "configured", lambda: False)
    monkeypatch.setattr(news_radar, "fetch_news_by_category", lambda *a, **k: NEWS)
    monkeypatch.setattr(news_radar, "fetch_news_by_query", lambda *a, **k: NEWS)
    monkeypatch.setattr(reminders, "get_reminders", lambda only_pending=True: [])
    monkeypatch.setattr(tasks, "get_tasks", lambda include_completed=False: [])
    monkeypatch.setattr(health, "load_telemetry", lambda: {"recovery": 54, "steps": 0, "stress": 0.2,
                                                          "sleep_hours": 7.4, "bpm": 80, "bpm_history": [80, 81]})


def test_segments_follow_the_video_order(offline):
    data = asyncio.run(briefing.build_morning_briefing())
    kinds = [s["card"]["kind"] for s in data["segments"]]
    assert kinds == ["weather", "agenda", "email", "news", "news", "news", "health"]
    assert data["opening"] == "Sem desvios relevantes"
    weather = data["segments"][0]["card"]
    assert weather["title"] == "Maragogi" and weather["wind"] == 18.3 and weather["rain_probability"] == 62
    assert data["segments"][1]["card"]["title"] == "Agenda livre"
    assert "Correio Braziliense" in data["segments"][3]["speech"]
    assert data["closing"].startswith("Hoje")
    assert [t["id"] for t in data["tabs"]] == ["clima", "agenda", "email", "noticias", "saude"]


def test_health_is_never_spoken(offline):
    data = asyncio.run(briefing.build_morning_briefing())
    health_seg = data["segments"][-1]
    assert health_seg["card"]["chip"] == "sob demanda"
    assert "54" not in data["speech"] and "7,4" not in data["speech"]
    assert data["readiness"]["recovery"] == 54


def test_overdue_reminder_becomes_a_deviation(offline, monkeypatch):
    monkeypatch.setattr(reminders, "get_reminders",
                        lambda only_pending=True: [{"texto": "x", "data_hora": "2000-01-01 08:00"}])
    data = asyncio.run(briefing.build_morning_briefing())
    assert data["opening"].startswith("Atenção") and "lembrete atrasado" in data["opening_sub"]


def test_a_failing_source_is_left_out(offline, monkeypatch):
    def boom(*a, **k):
        raise OSError("sem rede")

    monkeypatch.setattr(tools, "_fetch_weather", boom)
    monkeypatch.setattr(news_radar, "fetch_news_by_query", boom)
    data = asyncio.run(briefing.build_morning_briefing())
    kinds = [s["card"]["kind"] for s in data["segments"]]
    assert "weather" not in kinds and kinds.count("news") == 1


def test_email_triage_counts_only_actionable():
    headers = [
        {"sender": "Stripe", "subject": "Sua fatura vence amanhã", "date": ""},
        {"sender": "Santander", "subject": "Confirme o acesso ao app", "date": ""},
        {"sender": "Loja", "subject": "Oferta: 50% de desconto", "date": ""},
        {"sender": "Ana", "subject": "Fotos do fim de semana", "date": ""},
    ]
    tri = email_triage.summarize(headers)
    assert tri["received"] == 4 and tri["to_act"] == 2
    assert {i["sender"] for i in tri["items"]} == {"Stripe", "Santander"}


def test_email_card_when_not_configured(offline):
    data = asyncio.run(briefing.build_morning_briefing())
    email_seg = data["segments"][2]
    assert email_seg["card"]["connected"] is False and email_seg["speech"] == ""


def test_morning_triggers():
    assert briefing.is_morning_request("bom dia jarvis")
    assert not briefing.is_morning_request("boa tarde")


@pytest.mark.parametrize("phrase, mode", [
    ("boa noite", "evening"),
    ("boa noite resumo do dia", "evening"),  # antes da 4.3 abria o briefing da manhã
    ("boa noite como foi meu dia", "evening"),
    ("fechar o dia", "evening"),
    ("bom dia", "morning"),
    ("como esta meu dia", "morning"),
    ("boa tarde", None),
])
def test_request_mode(phrase, mode):
    assert briefing.request_mode(phrase) == mode


def test_resumo_alone_depends_on_the_hour():
    assert briefing.request_mode("resumo", hour=9) == "morning"
    assert briefing.request_mode("resumo", hour=21) == "evening"


def test_evening_segments(offline, monkeypatch):
    two_days = copy.deepcopy(WEATHER)
    two_days["data"]["daily"].update(temperature_2m_min=[23.3, 21.0], temperature_2m_max=[27.5, 25.0],
                                     precipitation_probability_max=[62, 80], weather_code=[1, 61])
    monkeypatch.setattr(tools, "_fetch_weather", lambda city: two_days)
    monkeypatch.setattr(tasks, "get_tasks", lambda include_completed=False: [{"id": 1, "texto": "Pagar a luz"}])
    from datetime import datetime, timedelta

    amanha = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    monkeypatch.setattr(reminders, "get_reminders",
                        lambda only_pending=True: [{"texto": "Dentista", "data_hora": f"{amanha} 10:00"}])
    data = asyncio.run(briefing.build_evening_briefing())
    kinds = [s["card"]["kind"] for s in data["segments"]]
    assert kinds == ["tasks", "agenda", "weather", "water"]  # sem anotações hoje, o card sai
    assert data["mode"] == "evening" and data["title"] == "FECHAMENTO DO DIA"
    assert "Pagar a luz" in data["segments"][0]["speech"]
    assert data["segments"][1]["card"]["label"] == "AGENDA · AMANHÃ"
    assert "Dentista" in data["segments"][1]["speech"]
    assert data["segments"][2]["card"]["minimum"] == 21.0 and "80 por cento" in data["segments"][2]["speech"]
    assert data["closing"].startswith("Deixe o guarda-chuva")
    assert [t["id"] for t in data["tabs"]] == ["tarefas", "agenda", "clima", "agua"]


def test_evening_clean_day(offline):
    data = asyncio.run(briefing.build_evening_briefing())
    assert data["opening"] == "Dia encerrado sem pendências"
    assert data["segments"][0]["card"]["title"] == "Tudo concluído"


@pytest.mark.parametrize("phrase, mode", [
    ("noticias", "topic:noticias"),
    ("jarvis noticias", "topic:noticias"),
    ("notificacoes", "topic:notificacoes"),
    ("minhas notificacoes", "topic:notificacoes"),
    ("e mails", "topic:email"),  # "e-mails" normalizado
    ("agenda", "topic:agenda"),
    ("meus dados de saude", "topic:saude"),
    ("comandos", "topic:comandos"),
    ("adiciona tarefa comprar pao", None),  # pedido longo segue o comando de sempre
    ("noticias sobre o palmeiras", None),
])
def test_topic_phrases(phrase, mode):
    assert briefing.request_mode(phrase) == mode


def test_topic_news_has_one_card_per_theme(offline):
    from modules import briefing_topics

    data = asyncio.run(briefing_topics.build("noticias"))
    assert data["mode"] == "topic:noticias" and data["title"] == "RADAR · NOTÍCIAS"
    assert [s["card"]["kind"] for s in data["segments"]] == ["news"] * 5
    assert [t["label"] for t in data["tabs"]] == ["Tecnologia", "Novos modelos de IA", "Política", "Economia", "Mundo"]
    assert len({t["id"] for t in data["tabs"]}) == 5


def test_topic_notifications_respects_privacy(offline, monkeypatch):
    from modules import briefing_topics, notifications

    async def reader():
        return [{"id": 1, "app": "WhatsApp", "title": "Ana", "body": "segredo", "at": ""},
                {"id": 2, "app": "WhatsApp", "title": "Bia", "body": "oi", "at": ""},
                {"id": 3, "app": "Outlook", "title": "Reunião", "body": "", "at": ""}]

    notifications.set_reader_for_tests(reader)
    monkeypatch.setattr(prefs, "get_all", lambda: {"notifications_enabled": True, "notifications_read_content": False})
    data = asyncio.run(briefing_topics.build("notificacoes"))
    assert [s["card"]["title"] for s in data["segments"]] == ["WhatsApp", "Outlook"]
    assert "Ana" not in data["speech"] and "segredo" not in data["speech"]  # na tela sim, na fala não
    assert data["segments"][0]["card"]["items"][0]["title"] in {"Ana", "Bia"}
    notifications.reset_for_tests()


def test_topic_notifications_disabled(offline, monkeypatch):
    from modules import briefing_topics

    monkeypatch.setattr(prefs, "get_all", lambda: {})
    data = asyncio.run(briefing_topics.build("notificacoes"))
    assert data["segments"][0]["card"]["title"] == "Central desligada"


def test_topic_health_shows_numbers_on_request(offline):
    from modules import briefing_topics

    data = asyncio.run(briefing_topics.build("saude"))
    assert data["segments"][0]["card"]["kind"] == "metrics" and "54 por cento" in data["speech"]


def test_every_topic_builds(offline, monkeypatch):
    from modules import briefing_topics

    monkeypatch.setattr(prefs, "get_all", lambda: {})
    for topic in briefing_topics.PHRASES:
        data = asyncio.run(briefing_topics.build(topic))
        assert data["mode"] == f"topic:{topic}" and data["segments"], topic


def test_long_greeting_with_another_request_is_not_a_summary():
    reply = asyncio.run(tools._h_briefing("", "boa noite jarvis abre o spotify e toca jazz", 9, ""))
    assert reply is None


def test_sequence_broadcasts_one_step_per_card(offline, monkeypatch):
    events = []

    async def fake_broadcast(event):
        events.append(event)

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    monkeypatch.setattr(prefs, "is_silent_mode", lambda: True)
    monkeypatch.setattr(briefing_flow, "SILENT_STEP_SECONDS", 0)

    async def run():
        data = await briefing.build_morning_briefing()
        session.busy = True
        await briefing_flow.run_sequence("bom dia", session.turn_id, data, 12)
        return data

    data = asyncio.run(run())
    types = [e["type"] for e in events]
    assert types[0] == "briefing_start"
    assert types.count("briefing_step") == len(data["segments"])
    assert types.index("briefing_end") < types.index("response")
    assert events[-1] == {"type": "state", "state": "idle"} and session.busy is False
    response = next(e for e in events if e["type"] == "response")
    assert response["cards"][0]["type"] == "briefing" and response["text"] == data["closing"]
    # cada parte leva o texto falado (legenda e Canal Ativo ao vivo)
    steps = [e for e in events if e["type"] == "briefing_step"]
    assert all(s["text"] == seg["speech"] for s, seg in zip(steps, data["segments"]))
    assert events[0]["text"].startswith(("Bom dia", "Boa tarde", "Boa noite"))  # V5.3: segue a hora
    # a pauta inteira já chega no início, antes da saudação ser falada
    assert events[0]["plan"] == [seg["card"] for seg in data["segments"]]
    assert events[0]["total"] == len(data["segments"])
    assert not briefing_flow.active()


def test_skip_cuts_only_the_current_part(offline, monkeypatch):
    """PRÓXIMO ▸: a fala atual é cortada e o briefing segue para o próximo card."""
    events, said = [], []

    async def fake_broadcast(event):
        events.append(event)

    async def slow_speak(text, release_busy=True, idle_after=True):
        said.append(text)
        await asyncio.sleep(30)  # "fala" longa: só termina se for pulada

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    monkeypatch.setattr(prefs, "is_silent_mode", lambda: False)
    monkeypatch.setattr(briefing_flow.speech, "speak", slow_speak)
    monkeypatch.setattr(briefing_flow.tts_module, "stop_playback", lambda: None)

    async def run():
        data = await briefing.build_morning_briefing()
        session.busy = True
        seq = asyncio.create_task(briefing_flow.run_sequence("bom dia", session.turn_id, data, 12))
        # pula a abertura e todas as partes (a fala vazia do e-mail passa sozinha)
        for _ in range(len(data["segments"]) + 1):
            await asyncio.sleep(0.05)
            briefing_flow.skip()
            await asyncio.sleep(0.9)
        seq.cancel()  # a recomendação final não é pulada; encerra o teste aqui
        await asyncio.gather(seq, return_exceptions=True)
        return data

    data = asyncio.run(run())
    assert [e["type"] for e in events].count("briefing_step") == len(data["segments"])
    assert any(e["type"] == "briefing_end" for e in events)
    assert briefing_flow.skip() is False  # sem briefing ativo

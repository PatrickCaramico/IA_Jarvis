"""V6.5: "boa tarde" ganha o resumo da tarde."""
import asyncio

from modules import briefing, tasks
from tests.test_briefing_43 import offline  # noqa: F401 - fixture com as fontes fora da rede


def test_afternoon_triggers():
    assert briefing.request_mode("boa tarde") == "afternoon"
    assert briefing.request_mode("resumo da tarde") == "afternoon"
    assert briefing.request_mode("boa noite") == "evening"
    assert briefing.request_mode("bom dia") == "morning"
    assert briefing.request_mode("resumo", hour=15) == "afternoon"
    assert briefing.request_mode("resumo", hour=9) == "morning"
    assert briefing.request_mode("resumo", hour=20) == "evening"


def test_routine_follows_the_hour():
    assert briefing.routine_mode(9) == "morning"
    assert briefing.routine_mode(14) == "afternoon"
    assert briefing.routine_mode(19) == "morning"


def test_afternoon_segments(offline, monkeypatch):  # noqa: F811
    monkeypatch.setattr(tasks, "get_tasks", lambda include_completed=False: [{"id": 1, "texto": "Pagar a luz"}])
    data = asyncio.run(briefing.build_afternoon_briefing())
    assert data["mode"] == "afternoon"
    assert data["title"] == "RESUMO DA TARDE"
    assert data["greeting"].startswith("Boa tarde")
    tabs = [s["tab"] for s in data["segments"]]
    assert tabs[0] == "agenda" and "tarefas" in tabs and "noticias" in tabs
    assert "Ainda falta 1 tarefa pendente: Pagar a luz" in data["speech"]
    assert {t["id"] for t in data["tabs"]} <= {t["id"] for t in briefing.AFTERNOON_TABS}


def test_afternoon_free(offline):  # noqa: F811
    data = asyncio.run(briefing.build_afternoon_briefing())
    assert "tarefas" not in [s["tab"] for s in data["segments"]]
    assert data["closing"]


def test_entry_command_follows_the_hour():
    from datetime import datetime

    from modules import entry_greeting

    assert entry_greeting.briefing_command(datetime(2026, 11, 12, 9)) == "bom dia"
    assert entry_greeting.briefing_command(datetime(2026, 11, 12, 14)) == "boa tarde"
    assert entry_greeting.briefing_command(datetime(2026, 11, 12, 20)) == "boa noite"

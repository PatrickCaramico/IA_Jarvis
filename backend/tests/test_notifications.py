"""Central de notificações (4.2, experimental) com um leitor falso no lugar do Windows."""
import asyncio

import pytest

from modules import notifications


@pytest.fixture(autouse=True)
def _reset():
    yield
    notifications.set_reader_for_tests(None)


def _reader(batches):
    calls = iter(batches)

    async def read():
        batch = next(calls)
        if isinstance(batch, Exception):
            raise batch
        return batch

    return read


def test_only_new_items_are_returned_and_kept_in_memory():
    a = {"id": 1, "app": "WhatsApp", "title": "Ana", "body": "oi"}
    b = {"id": 2, "app": "Outlook", "title": "Reunião", "body": ""}
    notifications.set_reader_for_tests(_reader([[a], [a, b]]))
    assert [n["id"] for n in asyncio.run(notifications.poll())] == [1]
    assert [n["id"] for n in asyncio.run(notifications.poll())] == [2]
    assert [n["id"] for n in notifications.items()] == [2, 1]
    assert notifications.status()["available"] is True


def test_unavailable_reports_reason_without_crashing():
    notifications.set_reader_for_tests(_reader([ImportError("winrt"), PermissionError("negado")]))
    assert asyncio.run(notifications.poll()) == []
    assert "requirements-notificacoes" in notifications.status()["reason"]
    assert asyncio.run(notifications.poll()) == []
    assert notifications.status()["reason"] == "negado"


def test_spoken_summary_hides_content_by_default():
    new = [{"app": "WhatsApp", "title": "Ana: senha do banco é 123"}]
    assert notifications.spoken_summary(new, read_content=False) == "Nova notificação do WhatsApp, senhor."
    assert "Ana" in notifications.spoken_summary(new, read_content=True)
    many = [{"app": "WhatsApp"}, {"app": "WhatsApp"}, {"app": "Outlook"}]
    assert notifications.spoken_summary(many, False) == "3 notificações novas: 2 do WhatsApp, 1 do Outlook."


def test_voice_commands_respect_toggle(monkeypatch):
    from modules import prefs

    monkeypatch.setattr(prefs, "get_all", lambda: {"notifications_enabled": False})
    assert "desligada" in asyncio.run(notifications.handle_voice("quais sao minhas notificacoes"))
    monkeypatch.setattr(prefs, "get_all", lambda: {"notifications_enabled": True})
    notifications.set_reader_for_tests(_reader([[{"id": 5, "app": "Teams", "title": "x", "body": ""}]]))
    asyncio.run(notifications.poll())
    assert "1 do Teams" in asyncio.run(notifications.handle_voice("quais sao minhas notificacoes"))
    assert "limpa" in asyncio.run(notifications.handle_voice("limpa as notificacoes"))
    assert notifications.items() == []


def test_notification_route_is_private():
    from modules import access

    assert not access.is_allowed("GET", "/api/notifications", access.LOCKED)
    assert not access.is_allowed("GET", "/api/notifications", access.GUEST)

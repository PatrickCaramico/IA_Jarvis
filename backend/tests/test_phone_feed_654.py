"""V6.5.4: avisos do celular sobrevivem ao reinício do JARVIS."""
from core import runtime
from modules import phone_feed


def test_feed_survives_restart(monkeypatch):
    runtime.NOTIFY_FEED.clear()
    monkeypatch.setattr(runtime, "_feed_loaded", True)
    first = runtime.notify("news", "📰 Marvel", "Filme novo · G1")
    assert phone_feed.load()[-1]["id"] == first["id"]

    # "reinicia": memória vazia, numeração do zero
    runtime.NOTIFY_FEED.clear()
    monkeypatch.setattr(runtime, "_feed_loaded", False)
    import itertools

    monkeypatch.setattr(runtime, "_notify_ids", itertools.count(1))
    feed = runtime.notifications_since(0)
    assert any(n["body"] == "Filme novo · G1" for n in feed["items"])
    second = runtime.notify("news", "📰 Marvel", "Outro filme · Omelete")
    assert second["id"] > first["id"]  # a numeração continua (o celular não perde nada)
    runtime.NOTIFY_FEED.clear()

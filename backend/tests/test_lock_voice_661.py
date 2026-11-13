"""V6.6.1: no bloqueio, clima, notícias e Spotify respondem na tela (sem pedir o rosto)."""
import asyncio

from modules import news, prefs, sentinel, spotify


def ask(text, state="locked"):
    return asyncio.run(sentinel.classify_and_answer(text, state))


def test_news_on_lock_shows_headlines(monkeypatch):
    monkeypatch.setattr(news, "fetch_top_news", lambda limit=None: [
        {"title": "Chuva em SP", "source": "g1", "link": "https://x/1"},
        {"title": "Dólar cai", "source": "Folha", "link": "https://x/2"},
    ])
    r = ask("jarvis, quais as notícias de hoje?")
    assert r["public"] and not r["requires_unlock"]
    assert "Chuva em SP" in r["reply"]
    assert r["card"]["kind"] == "news" and len(r["card"]["items"]) == 2


def test_news_offline_does_not_ask_face(monkeypatch):
    def boom(limit=None):
        raise OSError("sem internet")
    monkeypatch.setattr(news, "fetch_top_news", boom)
    r = ask("jarvis, notícias")
    assert r["public"] and not r["requires_unlock"]


def test_spotify_on_lock(monkeypatch):
    calls = []
    monkeypatch.setattr(spotify, "pause", lambda: calls.append("pause"))
    monkeypatch.setattr(spotify, "next_track", lambda: calls.append("next"))
    monkeypatch.setattr(spotify, "search_and_play", lambda q, pl: calls.append(("play", q, pl)) or f"Tocando {q}, senhor.")
    monkeypatch.setattr(spotify, "current_track", lambda: "Tocando Back in Black, de AC/DC.")
    assert ask("jarvis pausa a música")["public"]
    assert ask("jarvis, próxima música")["public"]
    r = ask("jarvis toca minha playlist")
    assert r["public"] and r["card"]["kind"] == "music"
    assert ask("jarvis, o que está tocando no spotify?")["reply"].startswith("Tocando Back in Black")
    assert calls == ["pause", "next", ("play", "minha playlist", True)]


def test_still_protected():
    r = ask("jarvis, quais são minhas tarefas?")
    assert r["requires_unlock"]
    assert ask("jarvis abre o spotify")["requires_unlock"]


def test_lock_mic_starts_on():
    assert prefs._DEFAULTS["lock_mic_on"] is True  # noqa: SLF001

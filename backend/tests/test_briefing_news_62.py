"""V6.2: temas de notícias do briefing (Marvel com as 3 principais)."""
import asyncio

from fastapi.testclient import TestClient

import main
from modules import access, briefing, news_radar, prefs
from tests.test_briefing_43 import offline  # noqa: F401 - fixture

MARVEL = [
    {"title": "Marvel escala brasileira para viver Lisa Molinari", "source": "Rádio Geek"},
    {"title": "Marvel escala atriz brasileira para viver Lisa Molinari no MCU", "source": "Omelete"},  # repetida
    {"title": "VisionQuest: primeiro episódio grátis no YouTube", "source": "CinePOP"},
    {"title": "Marvel 1943 segue vivo", "source": "Adrenaline"},
    {"title": "Stan Lee: os últimos dias", "source": "Globo"},
]


def test_marvel_reads_three_headlines(offline, monkeypatch):  # noqa: F811
    monkeypatch.setattr(news_radar, "fetch_news_by_query",
                        lambda q, limit=3: MARVEL if q == "Marvel" else [{"title": "Outra", "source": "X"}])
    data = asyncio.run(briefing.build_morning_briefing())
    marvel = next(s for s in data["segments"] if s["card"].get("title") == "Marvel")
    assert [i["title"] for i in marvel["card"]["items"]] == [
        "Marvel escala brasileira para viver Lisa Molinari", "VisionQuest: primeiro episódio grátis no YouTube",
        "Marvel 1943 segue vivo"]
    assert marvel["speech"].startswith("Em Marvel, as três principais. Primeira: Marvel escala brasileira")
    assert "Terceira: Marvel 1943 segue vivo." in marvel["speech"]


def test_user_themes_replace_defaults_and_are_validated():
    prefs.update(briefing_news_themes=[{"title": "Palmeiras", "query": "Palmeiras", "count": 2}])
    assert [t["title"] for t in briefing.news_themes()] == ["Palmeiras"]
    assert briefing.validate_news_themes([{"title": "X", "query": "x", "count": 9}]) is not None
    assert briefing.validate_news_themes([{"title": "", "query": "x"}]) is not None
    access.reset_for_tests(access.UNLOCKED)
    c = TestClient(main.app)
    assert c.patch("/api/prefs", json={"briefing_news_themes": [{"title": "Games", "query": "games", "count": 3}]}).status_code == 200
    assert c.get("/api/briefing/news-themes").json()["items"][0]["title"] == "Games"
    assert c.patch("/api/prefs", json={"briefing_news_themes": [{"title": "Games", "query": "", "count": 3}]}).status_code == 400
    access.reset_for_tests(access.LOCKED)

"""Módulo de notícias: lê o RSS do Google News Brasil e devolve os destaques do dia."""
import logging
import xml.etree.ElementTree as ET

from config import settings
from services import http_client

log = logging.getLogger("jarvis.news")


def fetch_top_news(limit: int | None = None) -> list[dict]:
    """Retorna os principais destaques como lista de dicts: {title, source, link}."""
    limit = settings.NEWS_LIMIT if limit is None else limit

    content = http_client.get_bytes(settings.NEWS_RSS_URL, timeout=10, ttl=300)
    root = ET.fromstring(content)
    news: list[dict] = []

    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        source = (item.findtext("source") or "").strip()
        link = (item.findtext("link") or "").strip()

        # O Google News costuma anexar " - Fonte" ao final do título; removemos a duplicidade.
        suffix = f" - {source}"
        if source and title.endswith(suffix):
            title = title[: -len(suffix)]

        if title:
            news.append({"title": title, "source": source, "link": link})
        if len(news) >= limit:
            break

    log.info("%d notícias coletadas.", len(news))
    return news

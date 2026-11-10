"""Radar de notícias do HUD: destaques por categoria via RSS do Google News Brasil.

Módulo independente (não altera modules/news.py).
"""
import logging
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode
from services import http_client


log = logging.getLogger("jarvis.news_radar")

_TOPICS = {
    "tecnologia": "TECHNOLOGY",
    "economia": "BUSINESS",
    "brasil": "NATION",
    "mundo": "WORLD",
    "ciencia": "SCIENCE",
    "saude": "HEALTH",
    "esportes": "SPORTS",
}
_CACHE_TTL_SECONDS = 300
_cache: dict[str, tuple[float, list[dict]]] = {}


def fetch_news_by_category(category: str, limit: int = 8) -> list[dict]:
    """Destaques de uma categoria: lista de {title, source, source_url, link, published}."""
    key = (category or "").strip().lower()
    topic = _TOPICS.get(key)
    if topic is None:
        raise ValueError("Categoria inválida. Use: " + ", ".join(_TOPICS))
    return _fetch(
        key,
        f"https://news.google.com/rss/headlines/section/topic/{topic}?hl=pt-BR&gl=BR&ceid=BR:pt-419",
        limit,
    )


def fetch_news_by_query(query: str, limit: int = 8) -> list[dict]:
    """V4.3: destaques de um tema livre (ex.: "novos modelos de IA") pela busca do Google News."""
    query = (query or "").strip()
    if not query:
        raise ValueError("Tema vazio.")
    return _fetch(
        "q:" + query.lower(),
        "https://news.google.com/rss/search?" + urlencode({"q": f"{query} when:2d", "hl": "pt-BR", "gl": "BR", "ceid": "BR:pt-419"}),
        limit,
    )


def _fetch(key: str, url: str, limit: int) -> list[dict]:
    limit = max(1, min(int(limit), 20))
    cached = _cache.get(key)
    if cached and time.monotonic() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1][:limit]

    content = http_client.get_bytes(url, timeout=10)
    root = ET.fromstring(content)
    items: list[dict] = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        source_el = item.find("source")
        source = (source_el.text or "").strip() if source_el is not None else ""
        source_url = (source_el.get("url") or "").strip() if source_el is not None else ""
        link = (item.findtext("link") or "").strip()
        suffix = f" - {source}"
        if source and title.endswith(suffix):
            title = title[: -len(suffix)]
        published = ""
        raw_date = (item.findtext("pubDate") or "").strip()
        if raw_date:
            try:
                published = parsedate_to_datetime(raw_date).isoformat()
            except (TypeError, ValueError):
                published = ""
        if title:
            items.append({"title": title, "source": source, "source_url": source_url, "link": link, "published": published})
        if len(items) >= 20:
            break

    _cache[key] = (time.monotonic(), items)
    log.info("%d notícias coletadas (%s).", len(items), key)
    return items[:limit]

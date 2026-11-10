"""Módulo do Modo Torcedor para o JARVIS.
Gerencia registro de clubes, busca de notícias especializadas (via GE / Google News RSS)
e estados relacionados à torcida.
"""
import json
import logging
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from typing import Any, Optional
from urllib.parse import quote_plus

from config import settings
from services import http_client

log = logging.getLogger("jarvis.fan_mode")

NEWS_CACHE_FILE = settings.DATA_DIR / "fan_news_cache.json"

FAN_TEAMS: dict[str, dict[str, Any]] = {
    "palmeiras": {
        "id": "palmeiras",
        "name": "Palmeiras",
        "short_name": "PAL",
        "full_name": "Sociedade Esportiva Palmeiras",
        "colors": {
            "primary": "#046538",
            "secondary": "#022413",
            "accent": "#10b981",
            "text": "#f2fbf6",
        },
        "badge_url": "/fan/palmeiras/palmeiras_shield.png",
        "news_query": "Palmeiras ge",
        "shout": "Avante Palestra!",
        "shout_phrase": "Avante Palestra!",
        "provider_team_id": 1056,
        # V4.4: agenda e placar reais (ESPN, JSON público sem chave) e confirmação pelo Google Notícias
        "espn_team_id": 2029,
        "matchday_query": 'Palmeiras "onde assistir" when:1d',
        "goal_phrase": "GOOOL DO PALMEIRAS! Avante Palestra!",
    }
}

_NEWS_CACHE_TTL = 300  # 5 minutos
_news_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}

_FALLBACK_NEWS = [
    {
        "title": "Palmeiras intensifica preparação tática na Academia de Futebol",
        "source": "ge.globo.com",
        "link": "https://ge.globo.com/futebol/times/palmeiras/",
        "published": "",
    },
    {
        "title": "Com foco na temporada, Verdão projeta sequência decisiva de jogos",
        "source": "ge.globo.com",
        "link": "https://ge.globo.com/futebol/times/palmeiras/",
        "published": "",
    },
    {
        "title": "Elenco alviverde realiza treino com portões fechados no Allianz Parque",
        "source": "ge.globo.com",
        "link": "https://ge.globo.com/futebol/times/palmeiras/",
        "published": "",
    },
    {
        "title": "Ingressos para a próxima partida do Palmeiras já estão à venda",
        "source": "ge.globo.com",
        "link": "https://ge.globo.com/futebol/times/palmeiras/",
        "published": "",
    },
]


def _load_disk_news(team_id: str) -> list[dict[str, Any]]:
    if not NEWS_CACHE_FILE.exists():
        return _FALLBACK_NEWS
    try:
        with open(NEWS_CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get(team_id, _FALLBACK_NEWS)
    except Exception:
        return _FALLBACK_NEWS


def _save_disk_news(team_id: str, items: list[dict[str, Any]]) -> None:
    try:
        NEWS_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if NEWS_CACHE_FILE.exists():
            with open(NEWS_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        data[team_id] = items
        with open(NEWS_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.warning("Falha ao salvar cache em disco de notícias do clube: %s", exc)


def get_team_info(team_id: str) -> Optional[dict[str, Any]]:
    """Retorna os dados do time cadastrado em FAN_TEAMS."""
    return FAN_TEAMS.get(team_id.strip().lower())


def fetch_fan_news(team_id: str = "palmeiras", limit: int = 8) -> list[dict[str, Any]]:
    """Busca as notícias mais recentes do time com foco no GE via Google News RSS."""
    team = get_team_info(team_id)
    if not team:
        team = FAN_TEAMS["palmeiras"]

    cache_key = team["id"]
    limit = max(1, min(int(limit), 20))

    cached = _news_cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < _NEWS_CACHE_TTL:
        return cached[1][:limit]

    query = team.get("news_query", "Palmeiras ge")
    encoded_q = quote_plus(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_q}&hl=pt-BR&gl=BR&ceid=BR:pt-419"

    items: list[dict[str, Any]] = []
    try:
        content = http_client.get_bytes(
            rss_url,
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
        )
        root = ET.fromstring(content)
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            source = (item.findtext("source") or "").strip()
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
                    published = raw_date

            if title and link:
                items.append({
                    "title": title,
                    "source": source or "ge.globo.com",
                    "link": link,
                    "published": published,
                })
                if len(items) >= 20:
                    break

        if items:
            # Prioriza notícias do GE / Globo Esporte
            items.sort(key=lambda x: 0 if ("ge" in x["source"].lower() or "globo" in x["source"].lower()) else 1)
            _news_cache[cache_key] = (time.monotonic(), items)
            _save_disk_news(cache_key, items)
    except Exception as exc:
        log.warning("Falha ao buscar notícias online do time %s: %s", team_id, exc)

    if not items:
        items = _load_disk_news(cache_key)
        _news_cache[cache_key] = (time.monotonic(), items)

    return items[:limit]

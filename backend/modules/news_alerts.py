"""V6.5: notícias novas dos temas do briefing viram aviso no celular.

A cada 45 minutos (fora do horário de silêncio, 22h às 7h), confere os temas de
Configurações › Geral › NOTÍCIAS DO BRIEFING (os mesmos do "bom dia") e manda para o app
as manchetes que ainda não tinham aparecido (no máximo 2 por tema por rodada).
Na primeira vez que vê um tema, só memoriza as manchetes (não manda uma enxurrada).

Desligar: preferência "news_notify_enabled" (Configurações › Geral › NOTÍCIAS DO BRIEFING).
"""
from __future__ import annotations

import json
import logging
import re
import unicodedata
from datetime import datetime

from config import settings

log = logging.getLogger("jarvis.news_alerts")

_PATH = settings.DATA_DIR / "noticias_avisadas.json"
EVERY_SECONDS = 45 * 60
QUIET_FROM, QUIET_TO = 22, 7
PER_THEME = 2
KEEP_PER_THEME = 80


def title_key(title: str) -> str:
    n = unicodedata.normalize("NFD", (title or "").lower())
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    n = re.sub(r"\s+-\s+[^-]+$", "", n)  # " - G1" no fim (o Google repete a fonte no título)
    return " ".join(re.findall(r"[a-z0-9]+", n))[:120]


def theme_key(theme: dict) -> str:
    return (theme.get("topic") and f"t:{theme['topic']}") or f"q:{title_key(theme.get('query', ''))}"


def is_quiet(now: datetime) -> bool:
    return now.hour >= QUIET_FROM or now.hour < QUIET_TO


def pick_new(theme: dict, items: list[dict], seen: dict) -> list[dict]:
    """Manchetes novas do tema (e já marca todas como vistas). Tema nunca visto: só memoriza."""
    key = theme_key(theme)
    known = seen.get(key)
    keys = [title_key(i.get("title", "")) for i in items]
    fresh = []
    if known is not None:
        limit = max(1, min(PER_THEME, int(theme.get("count") or 1)))
        for item, k in zip(items, keys):
            if k and k not in known and len(fresh) < limit:
                fresh.append(item)
    merged = [k for k in keys if k] + [k for k in (known or []) if k not in keys]
    seen[key] = merged[:KEEP_PER_THEME]
    return fresh


def _load() -> dict:
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(seen: dict) -> None:
    try:
        _PATH.parent.mkdir(parents=True, exist_ok=True)
        _PATH.write_text(json.dumps(seen, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        log.warning("Não consegui guardar as notícias avisadas: %s", exc)


def check_once(now: datetime | None = None) -> list[tuple[dict, dict]]:
    """Uma rodada: [(tema, manchete nova)]. Roda em thread (faz rede)."""
    from modules import briefing, news_radar, prefs

    now = now or datetime.now()
    if not prefs.get_all().get("news_notify_enabled", True) or is_quiet(now):
        return []
    seen = _load()
    out = []
    for theme in briefing.news_themes():
        try:
            limit = int(theme.get("count") or 1) + 4
            if theme.get("topic"):
                items = news_radar.fetch_news_by_category(theme["topic"], limit=limit)
            else:
                items = news_radar.fetch_news_by_query(theme["query"], limit=limit)
        except Exception as exc:  # noqa: BLE001 - um tema fora do ar não derruba os outros
            log.warning("Notícias de %s indisponíveis: %s", theme.get("title"), exc)
            continue
        out.extend((theme, item) for item in pick_new(theme, items or [], seen))
    _save(seen)
    return out


def notice_text(theme: dict, item: dict) -> tuple[str, str]:
    title = re.sub(r"\s+-\s+[^-]+$", "", item.get("title", "")).strip() or "Notícia nova"
    source = item.get("source") or "Google Notícias"
    return f"📰 {theme.get('title', 'Notícias')}", f"{title} · {source}"

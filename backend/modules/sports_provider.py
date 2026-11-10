"""Agenda, placar ao vivo e dia de jogo do Modo Torcedor (V4.4: dados reais, sem IA e sem chave).

Fontes, ambas gratuitas e sem token:
1. ESPN (JSON público, site.api.espn.com): agenda do time em todas as competições, horário,
   estádio e placar ao vivo.
2. Google Notícias (RSS): confirma o jogo do dia pelas matérias "onde assistir" publicadas hoje e
   serve de reserva quando a ESPN está fora do ar (aí o horário fica "a confirmar").

Nada aqui chama modelo de IA. Tudo fica em data/fan_cache.json, então a central continua mostrando
o último dado conhecido sem internet. A rede só é usada por refresh() (chamado pelo watcher em
segundo plano e pelas rotas, sempre fora do laço de eventos). As funções de leitura
(get_current_or_next_match, get_schedule...) só leem o cache e nunca travam a conversa.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, Optional
from urllib.parse import quote, quote_plus, urlparse

from config import settings
from services import http_client

log = logging.getLogger("jarvis.sports")

CACHE_FILE = settings.DATA_DIR / "fan_cache.json"
LOGO_DIR = settings.DATA_DIR / "fan_logos"

# Fuso horário de Brasília (UTC-3)
SP_TZ = timezone(timedelta(hours=-3))

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={q}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

SCHEDULE_TTL = timedelta(hours=6)   # agenda completa
LIVE_TTL = timedelta(seconds=50)    # placar durante o jogo
DETAILS_TTL = timedelta(minutes=10) # escudos, tabela e estatísticas no resto do dia de jogo
GOOGLE_TTL = timedelta(minutes=30)  # confirmação pelo Google Notícias
ESPN_TRUST_TTL = timedelta(hours=24)  # agenda da ESPN mais nova que isso manda; o Google só confirma
LIVE_WINDOW_BEFORE = timedelta(minutes=20)
LIVE_WINDOW_AFTER = timedelta(hours=3)
GOOGLE_MIN_ARTICLES = 2             # matérias "onde assistir" de hoje para considerar dia de jogo

_lock = threading.Lock()

# Nomes de competição da ESPN em inglês -> como falamos aqui
_COMPETITION_PT = {
    "brazil serie a": "Brasileirão",
    "brazilian serie a": "Brasileirão",
    "copa do brazil": "Copa do Brasil",
    "copa do brasil": "Copa do Brasil",
    "conmebol libertadores": "Libertadores",
    "conmebol sudamericana": "Sul-Americana",
    "brazil campeonato paulista": "Paulistão",
    "campeonato paulista": "Paulistão",
    "fifa club world cup": "Mundial de Clubes",
    "brazil supercopa": "Supercopa do Brasil",
}

_STATUS_PT = {"pre": "scheduled", "in": "live", "post": "finished"}


def _now_sp() -> datetime:
    return datetime.now(SP_TZ)


def _logo_path_for_team(team_key: str) -> Optional[str]:
    team_key = (team_key or "palmeiras").strip().lower()
    local_path = settings.BASE_DIR / "frontend" / "public" / "fan" / team_key / f"{team_key}_shield.png"
    if local_path.exists():
        return str(local_path)
    return None


def resolve_logo_path(team_key: str = "palmeiras", side: str = "ours") -> Optional[str]:
    """Retorna uma imagem de escudo local ou em cache para o lado informado."""
    side = (side or "").lower()
    if side == "ours":
        return _logo_path_for_team(team_key)

    if side != "theirs":
        return None

    match = get_current_or_next_match(team_key)
    logo_url = (match.get("logos") or {}).get("theirs")
    if not logo_url:
        return None

    parsed = urlparse(logo_url)
    host = (parsed.netloc or "").lower()
    if parsed.scheme not in {"http", "https"} or not host.endswith(".espncdn.com"):
        return None

    opponent = (match.get("opponent") or team_key).strip() or team_key
    cache_name = re.sub(r"[^a-z0-9]+", "_", _norm(opponent).lower()).strip("_") or "opponent"
    cache_file = LOGO_DIR / f"{team_key}_{cache_name}.png"
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    if cache_file.exists():
        return str(cache_file)

    try:
        blob = http_client.get_bytes(logo_url, timeout=8, headers={"User-Agent": BROWSER_UA})
        if blob:
            cache_file.write_bytes(blob)
            return str(cache_file)
    except Exception as exc:  # noqa: BLE001
        log.warning("Falha ao baixar escudo do adversário %s: %s", opponent, exc)
    return None


def _team(team_key: str) -> dict[str, Any]:
    from modules import fan_mode

    return fan_mode.get_team_info(team_key) or fan_mode.FAN_TEAMS["palmeiras"]


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", text).strip().lower()


# ---------------------------------------------------------------- cache em disco
def load_fan_cache() -> Dict[str, Any]:
    """Carrega o cache esportivo persistido."""
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception as exc:  # noqa: BLE001
        log.warning("Falha ao ler cache de partidas: %s", exc)
        return {}


def save_fan_cache(data: Dict[str, Any]) -> None:
    """Salva dados no cache persistido."""
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = CACHE_FILE.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(CACHE_FILE)
    except Exception as exc:  # noqa: BLE001
        log.warning("Falha ao salvar cache de partidas: %s", exc)


def _parse_dt(value: str | None) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=SP_TZ)
    return dt.astimezone(SP_TZ)


def _stale(stamp: str | None, ttl: timedelta) -> bool:
    dt = _parse_dt(stamp)
    return dt is None or _now_sp() - dt > ttl


# ---------------------------------------------------------------- ESPN
def _score_value(raw: Any) -> Optional[int]:
    """A ESPN manda o placar como número, texto ou {value, displayValue}; na agenda às vezes só um link."""
    if isinstance(raw, dict):
        raw = raw.get("value", raw.get("displayValue"))
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def _logo(team: dict) -> Optional[str]:
    return team.get("logo") or ((team.get("logos") or [{}])[0] or {}).get("href")


def _competition_name(event: dict, comp: dict) -> str:
    name = (event.get("league") or {}).get("name") or (comp.get("type") or {}).get("abbreviation") or ""
    return _COMPETITION_PT.get(_norm(name), name or "Campeonato")


def parse_espn_event(event: dict, espn_team_id: str | int) -> Optional[dict[str, Any]]:
    """Converte um evento da ESPN para o formato do JARVIS (None se não for do time)."""
    try:
        comp = event["competitions"][0]
        competitors = comp["competitors"]
        me = next(c for c in competitors if str(c["team"]["id"]) == str(espn_team_id))
        other = next(c for c in competitors if c is not me)
    except (KeyError, IndexError, StopIteration, TypeError):
        return None
    dt = _parse_dt(event.get("date"))
    if dt is None:
        return None
    status_type = (comp.get("status") or {}).get("type") or {}
    status_name = status_type.get("name", "")
    status = _STATUS_PT.get(status_type.get("state", "pre"), "scheduled")
    if status_name in {"STATUS_POSTPONED", "STATUS_CANCELED", "STATUS_SUSPENDED"}:
        status = "postponed"
    home = me if me.get("homeAway") == "home" else other
    away = other if home is me else me
    minute = None
    if status == "live":
        minute = "Intervalo" if status_name == "STATUS_HALFTIME" else (comp.get("status") or {}).get("displayClock")
    elif status == "finished":
        minute = "Fim"
    return {
        "id": f"espn_{event.get('id')}",
        "espn_event_id": str(event.get("id", "")),
        "league_slug": (event.get("league") or {}).get("slug") or "all",
        "opponent": other["team"].get("shortDisplayName") or other["team"].get("displayName", "Adversário"),
        "competition": _competition_name(event, comp),
        "date": dt.isoformat(),
        "time_known": True,
        "venue": (comp.get("venue") or {}).get("fullName") or "A definir",
        "home_away": me.get("homeAway", "home"),
        "status": status,
        "score": {"home": _score_value(home.get("score")) or 0, "away": _score_value(away.get("score")) or 0},
        "minute": minute,
        "logos": {"ours": _logo(me["team"]), "theirs": _logo(other["team"])},
        "source": "espn",
    }


# Estatísticas do boxscore da ESPN -> nomes curtos usados na tela
_STAT_KEYS = {
    "possessionPct": "possession",
    "totalShots": "shots",
    "shotsOnTarget": "on_target",
    "wonCorners": "corners",
    "yellowCards": "yellow",
    "redCards": "red",
}


def parse_espn_details(summary: dict, espn_team_id: str | int) -> dict[str, Any]:
    """Detalhes do jogo a partir do /summary da ESPN: gols e expulsões, estatísticas e tabela."""
    sid = str(espn_team_id)
    events: list[dict[str, Any]] = []
    for ev in summary.get("keyEvents") or []:
        etype = ev.get("type") or {}
        tag = f"{etype.get('type', '')} {etype.get('text', '')}".lower()
        if "own" in tag and "goal" in tag:
            kind = "own_goal"
        elif "goal" in tag and "miss" not in tag and "disallow" not in tag:
            kind = "goal"
        elif "red" in tag:
            kind = "red_card"
        else:
            continue
        people = [((p or {}).get("athlete") or {}).get("displayName") for p in ev.get("participants") or []]
        people = [p for p in people if p]
        events.append({
            "kind": kind,
            "minute": ((ev.get("clock") or {}).get("displayValue") or "").strip(),
            "side": "ours" if str((ev.get("team") or {}).get("id", "")) == sid else "theirs",
            "player": people[0] if people else None,
            "assist": people[1] if kind == "goal" and len(people) > 1 else None,
            "penalty": "penalty" in tag,
        })

    stats: dict[str, dict[str, float]] = {"ours": {}, "theirs": {}}
    for team in (summary.get("boxscore") or {}).get("teams") or []:
        side = "ours" if str((team.get("team") or {}).get("id", "")) == sid else "theirs"
        for st in team.get("statistics") or []:
            key = _STAT_KEYS.get(st.get("name"))
            if not key:
                continue
            try:
                stats[side][key] = float(st.get("displayValue", st.get("value")))
            except (TypeError, ValueError):
                continue

    standing = None
    for group in (summary.get("standings") or {}).get("groups") or []:
        for entry in (group.get("standings") or {}).get("entries") or []:
            if str(entry.get("id", "")) != sid:
                continue
            values = {s.get("name"): s.get("displayValue") for s in entry.get("stats") or []}
            try:
                standing = {
                    "rank": int(values.get("rank") or 0),
                    "points": int(values.get("points") or 0),
                    "played": int(values.get("gamesPlayed") or 0),
                    "table": _COMPETITION_PT.get(_norm(group.get("header", "").replace(" Standings", "")), "Tabela"),
                }
            except ValueError:
                standing = None
    return {"events": events[-14:], "stats": stats if stats["ours"] or stats["theirs"] else None, "standing": standing}


def _fetch_espn_schedule(espn_team_id: str | int) -> list[dict[str, Any]]:
    data = http_client.get_json(
        f"{ESPN_BASE}/all/teams/{espn_team_id}/schedule",
        params={"fixture": "true"},
        headers={"User-Agent": BROWSER_UA},
        timeout=8,
    )
    matches = [m for m in (parse_espn_event(ev, espn_team_id) for ev in data.get("events", [])) if m]
    matches.sort(key=lambda m: m["date"])
    return matches


def _fetch_espn_live(match: dict[str, Any], espn_team_id: str | int) -> Optional[dict[str, Any]]:
    data = http_client.get_json(
        f"{ESPN_BASE}/{match.get('league_slug') or 'all'}/summary",
        params={"event": match["espn_event_id"]},
        headers={"User-Agent": BROWSER_UA},
        timeout=6,
    )
    header = data.get("header") or {}
    event = {
        "id": match["espn_event_id"],
        "date": (header.get("competitions") or [{}])[0].get("date") or match["date"],
        "league": header.get("league") or {"name": match["competition"], "slug": match.get("league_slug")},
        "competitions": header.get("competitions") or [],
    }
    fresh = parse_espn_event(event, espn_team_id)
    if fresh:
        fresh["competition"] = match["competition"]  # o resumo traz o nome em inglês de outro jeito
        if fresh["venue"] == "A definir":
            fresh["venue"] = match.get("venue", "A definir")
        fresh["logos"] = {k: v or (match.get("logos") or {}).get(k) for k, v in (fresh.get("logos") or {}).items()}
        fresh["details"] = parse_espn_details(data, espn_team_id)
    return fresh


# ---------------------------------------------------------------- Google Notícias
_VS_RE = re.compile(r"([A-Za-zÀ-ÿ.'\- ]{2,30}?)\s+[xX×]\s+([A-Za-zÀ-ÿ.'\- ]{2,30}?)(?=\s*[:|,\-–(]|\s+(?:pelo|pela|ao vivo|hoje|onde)\b|$)")


_NOT_MAIN_TEAM_RE = re.compile(r"\bsub[- ]?\d{2}\b|\bu-?\d{2}\b|feminin|\bde base\b|junior|^jogos de hoje|\bjogos de hoje\b")


def parse_google_news_matchday(xml_bytes: bytes, team_name: str, today: datetime) -> dict[str, Any]:
    """Conta matérias de hoje no estilo "Palmeiras x Remo: onde assistir" e descobre o adversário."""
    team_n = _norm(team_name)
    opponents: dict[str, int] = {}
    count = 0
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return {"match_today": False, "articles": 0, "opponent": None}
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        raw_date = (item.findtext("pubDate") or "").strip()
        try:
            published = parsedate_to_datetime(raw_date).astimezone(SP_TZ)
        except (TypeError, ValueError):
            continue
        if published.date() != today.date():
            continue
        # V5: base e feminino ("Palmeiras x Santos sub-20") e listas do dia ("Jogos de hoje: ...") não
        # são jogo do time principal; antes elas faziam o Modo Torcedor "confirmar" jogo em dia sem jogo.
        if _NOT_MAIN_TEAM_RE.search(_norm(title)):
            continue
        m = _VS_RE.search(title)
        if not m:
            continue
        a, b = m.group(1).strip(" -"), m.group(2).strip(" -")
        if _norm(a).endswith(team_n):
            other = b
        elif _norm(b).startswith(team_n):
            other = a
        else:
            continue
        count += 1
        key = other.strip()
        opponents[key] = opponents.get(key, 0) + 1
    opponent = max(opponents, key=opponents.get) if opponents else None
    return {"match_today": count >= GOOGLE_MIN_ARTICLES, "articles": count, "opponent": opponent}


def _fetch_google_matchday(team: dict[str, Any]) -> dict[str, Any]:
    query = team.get("matchday_query") or f'{team["name"]} "onde assistir" when:1d'
    content = http_client.get_bytes(
        GOOGLE_NEWS_RSS.format(q=quote_plus(query)),
        headers={"User-Agent": BROWSER_UA},
        timeout=8,
    )
    return parse_google_news_matchday(content, team["name"], _now_sp())


# ---------------------------------------------------------------- atualização (rede)
def _matches(cache: dict, team_key: str) -> list[dict[str, Any]]:
    return list(((cache.get("schedule") or {}).get(team_key) or {}).get("matches") or [])


def _in_live_window(match: dict[str, Any], now: datetime) -> bool:
    dt = _parse_dt(match.get("date"))
    if not dt or match.get("status") in {"finished", "postponed"} or not match.get("espn_event_id"):
        return False
    return dt - LIVE_WINDOW_BEFORE <= now <= dt + LIVE_WINDOW_AFTER


def refresh(team_key: str = "palmeiras", force: bool = False) -> dict[str, Any]:
    """Atualiza agenda/placar/confirmação do Google conforme a validade de cada um. Usa a rede.

    Chame fora do laço de eventos (asyncio.to_thread). Devolve o que foi atualizado.
    """
    team = _team(team_key)
    espn_id = team.get("espn_team_id")
    done: dict[str, Any] = {"schedule": False, "live": False, "google": False}
    with _lock:
        cache = load_fan_cache()
        sched = (cache.setdefault("schedule", {}).get(team_key)) or {}
        now = _now_sp()
        schedule_attempted = False

        if espn_id and (force or _stale(sched.get("fetched_at"), SCHEDULE_TTL)):
            schedule_attempted = True
            try:
                matches = _fetch_espn_schedule(espn_id)
                sched = {"fetched_at": now.isoformat(), "source": "espn", "matches": matches}
                cache["schedule"][team_key] = sched
                done["schedule"] = True
            except Exception as exc:  # noqa: BLE001
                log.warning("ESPN fora (agenda do %s): %s", team_key, exc)

        matches = list(sched.get("matches") or [])
        checked_ids = set(sched.get("stale_live_rechecked") or [])
        stale_live = next((
            m for m in matches
            if m.get("status") == "live"
            and m.get("espn_event_id")
            and m.get("id") not in checked_ids
            and (match_dt := _parse_dt(m.get("date"))) is not None
            and now > match_dt + LIVE_WINDOW_AFTER
        ), None)
        if stale_live:
            checked_ids.add(stale_live.get("id"))
            if espn_id and not schedule_attempted:
                schedule_attempted = True
                try:
                    matches = _fetch_espn_schedule(espn_id)
                    sched["fetched_at"] = now.isoformat()
                    sched["source"] = "espn"
                    done["schedule"] = True
                except Exception as exc:  # noqa: BLE001
                    log.warning("Falha ao revalidar partida encerrada (%s): %s", stale_live.get("id"), exc)
            sched["stale_live_rechecked"] = list(checked_ids)

        for i, match in enumerate(matches):
            # Placar a cada ~50 s perto/durante o jogo; no resto do dia de jogo, detalhes a cada 10 min.
            in_window = _in_live_window(match, now)
            match_dt = _parse_dt(match.get("date"))
            is_today = bool(match.get("espn_event_id")) and match_dt is not None and match_dt.date() == now.date()
            stale_live = match.get("status") == "live" and match_dt is not None and now > match_dt + LIVE_WINDOW_AFTER
            if not (in_window or (is_today and not stale_live)):
                continue
            if not force and not _stale(match.get("live_checked_at"), LIVE_TTL if in_window else DETAILS_TTL):
                break
            try:
                fresh = _fetch_espn_live(match, espn_id)
                if fresh:
                    fresh["live_checked_at"] = now.isoformat()
                    matches[i] = {**match, **fresh}
                    done["live"] = True
            except Exception as exc:  # noqa: BLE001
                log.warning("ESPN fora (placar ao vivo): %s", exc)
                matches[i] = {**match, "live_checked_at": now.isoformat()}
            break
        if matches:
            sched["matches"] = matches
            cache["schedule"][team_key] = sched

        google = (cache.setdefault("google", {}).get(team_key)) or {}
        if force or _stale(google.get("checked_at"), GOOGLE_TTL) or google.get("date") != now.date().isoformat():
            try:
                found = _fetch_google_matchday(team)
                google = {**found, "checked_at": now.isoformat(), "date": now.date().isoformat()}
                cache["google"][team_key] = google
                done["google"] = True
            except Exception as exc:  # noqa: BLE001
                log.warning("Google Notícias fora (dia de jogo): %s", exc)
        save_fan_cache(cache)
    return done


# ---------------------------------------------------------------- leitura (só cache)
def _google_today(cache: dict, team_key: str, now: datetime) -> dict[str, Any]:
    g = (cache.get("google") or {}).get(team_key) or {}
    return g if g.get("date") == now.date().isoformat() else {}


def _pick_match(matches: list[dict], now: datetime) -> Optional[dict]:
    live = [m for m in matches if m.get("status") == "live" and _in_live_window(m, now)]
    if live:
        return live[0]
    today = [m for m in matches if (_parse_dt(m.get("date")) or now).date() == now.date() and m.get("status") != "postponed"]
    if today:
        return today[0]
    upcoming = [m for m in matches if (_parse_dt(m.get("date")) or now) > now and m.get("status") == "scheduled"]
    return upcoming[0] if upcoming else None


def _countdown(total_seconds: int, status: str, time_known: bool) -> str:
    if status == "live":
        return "BOLA ROLANDO"
    if status == "finished":
        return "Partida encerrada"
    if status == "unknown":
        return "Agenda indisponível"
    if not time_known:
        return "Hoje · horário a confirmar"
    if total_seconds <= 0:
        return "Começando"
    days, rest = divmod(total_seconds, 86400)
    hours, rest = divmod(rest, 3600)
    minutes = rest // 60
    if days > 0:
        return f"Em {days}d {hours}h"
    if hours > 0:
        return f"Em {hours}h {minutes}min"
    return f"Em {minutes} minutos"


def get_current_or_next_match(team_key: str = "palmeiras") -> Dict[str, Any]:
    """Partida ao vivo, a de hoje ou a próxima, com contagem regressiva. Só lê o cache (sem rede)."""
    cache = load_fan_cache()
    now = _now_sp()
    matches = _matches(cache, team_key)
    google = _google_today(cache, team_key, now)
    match = _pick_match(matches, now)
    sources = ["espn"] if match else []

    sched = ((cache.get("schedule") or {}).get(team_key)) or {}
    # V5: com a agenda da ESPN em dia (ela traz todas as competições do time principal), o Google
    # Notícias só confirma; não inventa jogo. Ele vira reserva apenas com a ESPN fora do ar.
    espn_fresh = bool(sched.get("matches")) and not _stale(sched.get("fetched_at"), ESPN_TRUST_TTL)

    if match and (_parse_dt(match["date"]) or now).date() == now.date() and google.get("match_today"):
        sources.append("google_news")
    if (
        not espn_fresh
        and (not match or (_parse_dt(match["date"]) or now).date() != now.date())
        and google.get("match_today")
    ):
        # A ESPN está fora (agenda velha ou vazia), mas o Google Notícias confirma jogo hoje.
        match = {
            "id": f"google_{now.date().isoformat()}",
            "opponent": google.get("opponent") or "Adversário",
            "competition": "Jogo de hoje",
            "date": now.replace(hour=12, minute=0, second=0, microsecond=0).isoformat(),
            "time_known": False,
            "venue": "A confirmar",
            "home_away": "home",
            "status": "scheduled",
            "score": {"home": 0, "away": 0},
            "minute": None,
        }
        sources = ["google_news"]

    if not match:
        return {
            "id": "sem_agenda",
            "team": team_key,
            "opponent": "A definir",
            "competition": "Sem jogos na agenda",
            "date": now.isoformat(),
            "venue": "",
            "home_away": "home",
            "status": "unknown",
            "score": {"home": 0, "away": 0},
            "minute": None,
            "is_match_day": False,
            "countdown": _countdown(0, "unknown", True),
            "seconds_until_match": 0,
            "time_known": False,
            "source": "sem_dados",
            "sources": [],
        }

    match_dt = _parse_dt(match.get("date")) or now
    total_seconds = int((match_dt - now).total_seconds())
    status = match.get("status", "scheduled")
    minute = match.get("minute")
    time_known = match.get("time_known", True)
    if status == "live" and now > match_dt + LIVE_WINDOW_AFTER:
        status, minute = "finished", "Fim"
    # Sem placar ao vivo recente (ESPN fora): estima pelo horário.
    if status == "scheduled" and time_known and total_seconds <= 0 and _stale(match.get("live_checked_at"), timedelta(minutes=5)):
        elapsed = -total_seconds
        if elapsed <= 2 * 3600:
            status, minute = "live", f"{min(90, max(1, elapsed // 60))}'"
        else:
            status, minute = "finished", "Fim"

    return {
        "id": match.get("id", "match"),
        "team": team_key,
        "opponent": match.get("opponent", "Adversário"),
        "competition": match.get("competition", "Campeonato"),
        "date": match_dt.isoformat(),
        "venue": match.get("venue", ""),
        "home_away": match.get("home_away", "home"),
        "status": status,
        "score": match.get("score", {"home": 0, "away": 0}),
        "minute": minute,
        "is_match_day": match_dt.date() == now.date() and status != "postponed",
        "countdown": _countdown(total_seconds, status, time_known),
        "seconds_until_match": max(0, total_seconds),
        "time_known": time_known,
        "source": sources[0] if sources else "cache",
        "sources": sources,
        "logos": match.get("logos") or {},
        "details": match.get("details"),
    }


def take_moments(team_key: str = "palmeiras", mark: tuple[str, ...] = ()) -> tuple[list[str], dict[str, Any]]:
    """Momentos do jogo ainda não anunciados ("half" = intervalo, "full" = fim). Cada um vale uma vez
    por jogo. `mark` registra momentos como já ditos sem anunciá-los (ex.: o JARVIS abriu depois)."""
    match = get_current_or_next_match(team_key)
    kinds: list[str] = []
    if match.get("source") == "espn":
        if match.get("status") == "live" and match.get("minute") == "Intervalo":
            kinds.append("half")
        if match.get("status") == "finished":
            kinds.append("full")
    with _lock:
        cache = load_fan_cache()
        seen = cache.setdefault("moments", {}).setdefault(match.get("id", ""), [])
        new = [k for k in kinds if k not in seen]
        extra = [k for k in mark if k not in seen and k not in new]
        if new or extra:
            seen.extend(new + extra)
            save_fan_cache(cache)
    return [k for k in new if k not in mark], match


def mark_shout_fired(match_id: str) -> None:
    with _lock:
        cache = load_fan_cache()
        cache.setdefault("shouts_fired", {})[match_id] = _now_sp().isoformat()
        save_fan_cache(cache)


def last_goal(match: dict[str, Any], side: str = "ours") -> Optional[dict[str, Any]]:
    events = ((match.get("details") or {}).get("events")) or []
    goals = [e for e in events if e.get("kind") in {"goal", "own_goal"} and e.get("side") == side]
    return goals[-1] if goals else None


def team_goals(match: dict[str, Any]) -> tuple[int, int]:
    """(gols do time, gols do adversário) a partir do placar mandante/visitante."""
    score = match.get("score") or {}
    home, away = int(score.get("home") or 0), int(score.get("away") or 0)
    return (home, away) if match.get("home_away", "home") == "home" else (away, home)


def detect_score_change(team_key: str = "palmeiras") -> Optional[dict[str, Any]]:
    """Compara o placar ao vivo com o último visto: devolve {"kind": "goal"|"conceded", ...} ou None."""
    match = get_current_or_next_match(team_key)
    if match.get("status") not in {"live", "finished"} or match.get("source") != "espn":
        return None
    ours, theirs = team_goals(match)
    with _lock:
        cache = load_fan_cache()
        seen = cache.setdefault("score_seen", {})
        last = seen.get(match["id"])
        seen[match["id"]] = [ours, theirs]
        if last != [ours, theirs]:
            save_fan_cache(cache)
    if last is None:
        return None  # primeira leitura (ex.: JARVIS aberto no meio do jogo): só registra
    if ours > last[0]:
        return {"kind": "goal", "ours": ours, "theirs": theirs, "match": match}
    if theirs > last[1]:
        return {"kind": "conceded", "ours": ours, "theirs": theirs, "match": match}
    return None


def should_trigger_shout(team_key: str = "palmeiras") -> bool:
    """Grito de torcida uma vez por jogo, quando a bola começa a rolar."""
    match_info = get_current_or_next_match(team_key)
    if match_info.get("status") != "live":
        return False
    with _lock:
        cache = load_fan_cache()
        shouts_fired = cache.get("shouts_fired", {})
        match_id = match_info.get("id", "")
        if shouts_fired.get(match_id):
            return False
        shouts_fired[match_id] = _now_sp().isoformat()
        cache["shouts_fired"] = shouts_fired
        save_fan_cache(cache)
    return True


# ---------------------------------------------------------------- auto Modo Torcedor
def auto_state() -> dict[str, Any]:
    return dict(load_fan_cache().get("auto") or {})


def set_auto_state(**values: Any) -> None:
    with _lock:
        cache = load_fan_cache()
        cache["auto"] = {**(cache.get("auto") or {}), **values}
        save_fan_cache(cache)


def record_manual_activation(enabled: bool, team_key: str = "palmeiras", match: Optional[dict[str, Any]] = None) -> None:
    """Registra a escolha manual e se a ativação aconteceu num dia de jogo."""
    match = match or (get_current_or_next_match(team_key) if enabled else {})
    set_auto_state(
        activated_on=_now_sp().date().isoformat(),
        by_auto=False,
        activated_on_match_day=bool(enabled and match.get("is_match_day")),
    )


# ---------------------------------------------------------------- agenda / lembretes
def _build_google_calendar_url(title: str, start_dt: datetime, end_dt: datetime, venue: str, details: str) -> str:
    """Gera link de adição universal do Google Calendar sem precisar de token de autenticação."""
    utc_start = start_dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    utc_end = end_dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base_url = "https://calendar.google.com/calendar/render?action=TEMPLATE"
    return f"{base_url}&text={quote(title)}&dates={utc_start}/{utc_end}&location={quote(venue)}&details={quote(details)}"


_WEEKDAYS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def get_schedule(team_key: str = "palmeiras") -> list[Dict[str, Any]]:
    """Próximos jogos (hoje em diante) com contagem regressiva e link do Google Agenda. Só cache."""
    now = _now_sp()
    team_name = _team(team_key)["name"]
    items = []
    for item in _matches(load_fan_cache(), team_key):
        m_dt = _parse_dt(item.get("date"))
        if not m_dt or m_dt.date() < now.date() or item.get("status") == "postponed":
            continue
        home, away = (team_name, item["opponent"]) if item.get("home_away") == "home" else (item["opponent"], team_name)
        title = f"{home} x {away} - {item['competition']}"
        cal_url = _build_google_calendar_url(
            title, m_dt, m_dt + timedelta(hours=2), item.get("venue", ""),
            f"Acompanhamento pelo JARVIS. Local: {item.get('venue', '')}.",
        )
        items.append({
            "id": item["id"],
            "team": team_key,
            "opponent": item["opponent"],
            "competition": item["competition"],
            "date": m_dt.isoformat(),
            "date_human": f"{m_dt:%d/%m} ({_WEEKDAYS[m_dt.weekday()]}) às {m_dt:%H:%M}",
            "venue": item.get("venue", ""),
            "home_away": item.get("home_away", "home"),
            "status": item.get("status", "scheduled"),
            "seconds_left": max(0, int((m_dt - now).total_seconds())),
            "google_calendar_url": cal_url,
        })
    return items


def create_match_reminder(match_id: Optional[str] = None, minutes_before: int = 30) -> Dict[str, Any]:
    """Cria lembrete no sistema e gera link do Google Calendar para a partida."""
    from modules import reminders

    now = _now_sp()
    team_key = "palmeiras"
    sched = [s for s in get_schedule(team_key) if s["status"] == "scheduled" and s["seconds_left"] > 0]
    selected = next((m for m in sched if m["id"] == match_id), None) if match_id else None
    selected = selected or (sched[0] if sched else None)
    if not selected:
        return {
            "status": "error",
            "match": {"opponent": "a definir"},
            "message": "Ainda não tenho a agenda dos próximos jogos. Tente de novo em alguns minutos.",
        }

    m_dt = _parse_dt(selected["date"]) or now + timedelta(days=1)
    reminder_time = m_dt - timedelta(minutes=minutes_before)
    if reminder_time <= now:
        reminder_time = now + timedelta(minutes=2)

    text = f"⚽ Jogo do Palmeiras contra o {selected['opponent']} às {m_dt:%H:%M}!"
    rem = reminders.add_reminder(text, reminder_time.replace(tzinfo=None))

    return {
        "status": "ok",
        "match": selected,
        "reminder": rem,
        "reminder_time": reminder_time.isoformat(),
        "google_calendar_url": selected["google_calendar_url"],
        "message": f"Lembrete agendado para {minutes_before} minutos antes do jogo contra o {selected['opponent']}!",
    }

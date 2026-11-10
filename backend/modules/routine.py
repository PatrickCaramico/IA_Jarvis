"""Sugestões pela rotina (4.2, funcionalidade 2 do backlog).

O JARVIS anota algumas ações que você pede (protocolos e "abre o ...") com data e hora. Quando a
mesma ação aparece em pelo menos 3 dias diferentes das últimas 2 semanas, mais ou menos no mesmo
horário, ele passa a OFERECER fazer isso perto daquele horário: "Senhor, costuma ativar o protocolo
trabalho por volta das 9h. Quer que eu ative?". Nada acontece sem um "sim".

- "não" dispensa a sugestão só por hoje; "não sugira mais isso" desliga aquela sugestão.
- Os dados ficam em data/rotina.json (no máximo 500 registros, só a ação e o horário).
- Pode ser desligado em Configurações > Automação.
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from config import settings

log = logging.getLogger("jarvis.routine")
# Fuso fixo de Brasília (UTC-3), como em water.py e sports_provider.py. ZoneInfo("America/Sao_Paulo")
# não funciona no Windows sem o pacote tzdata e derrubava o backend na inicialização.
SP_TZ = timezone(timedelta(hours=-3))

DATA_PATH = settings.DATA_DIR / "rotina.json"
MAX_EVENTS = 500
LOOKBACK_DAYS = 14
MIN_DAYS = 3
WINDOW_MIN = 30          # tolerância em torno do horário de costume
SUGGEST_BEFORE_MIN = 10  # oferece a partir de 10 min antes do horário de costume

_lock = threading.Lock()


def _load() -> dict[str, Any]:
    try:
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("events", [])
            data.setdefault("muted", [])
            data.setdefault("dismissed", {})
            data.setdefault("suggested", {})
            return data
    except (OSError, ValueError):
        pass
    return {"events": [], "muted": [], "dismissed": {}, "suggested": {}}


def _save(data: dict[str, Any]) -> None:
    try:
        DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError as exc:
        log.debug("Não foi possível salvar a rotina: %s", exc)


def record(key: str, label: str, kind: str, value: str, now: Optional[datetime] = None) -> None:
    """Anota uma ação feita a pedido do usuário (ex.: key="protocol:trabalho")."""
    now = now or datetime.now(SP_TZ)
    with _lock:
        data = _load()
        data["events"].append({"key": key, "label": label, "kind": kind, "value": value,
                               "ts": now.isoformat(timespec="minutes")})
        data["events"] = data["events"][-MAX_EVENTS:]
        _save(data)


def _minutes(dt: datetime) -> int:
    return dt.hour * 60 + dt.minute


def find_habits(events: list[dict], now: datetime) -> list[dict]:
    """Ações repetidas em >= MIN_DAYS dias diferentes, no mesmo horário (± WINDOW_MIN). Função pura."""
    since = now - timedelta(days=LOOKBACK_DAYS)
    by_key: dict[str, list[datetime]] = {}
    meta: dict[str, dict] = {}
    for ev in events:
        try:
            ts = datetime.fromisoformat(ev["ts"])
        except (KeyError, ValueError):
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=SP_TZ)
        if ts < since or ts.date() >= now.date():
            continue
        by_key.setdefault(ev["key"], []).append(ts)
        meta[ev["key"]] = ev
    habits = []
    for key, stamps in by_key.items():
        # primeira vez de cada dia
        per_day: dict = {}
        for ts in sorted(stamps):
            per_day.setdefault(ts.date(), ts)
        if len(per_day) < MIN_DAYS:
            continue
        mins = sorted(_minutes(t) for t in per_day.values())
        median = mins[len(mins) // 2]
        close = [m for m in mins if abs(m - median) <= WINDOW_MIN]
        if len(close) < MIN_DAYS:
            continue
        typical = sum(close) // len(close)
        ev = meta[key]
        habits.append({"key": key, "label": ev["label"], "kind": ev["kind"], "value": ev["value"],
                       "minute": typical, "days": len(close)})
    return sorted(habits, key=lambda h: h["minute"])


def due_suggestion(now: Optional[datetime] = None) -> Optional[dict]:
    """A sugestão para agora, se houver (marca como oferecida hoje para não repetir)."""
    now = now or datetime.now(SP_TZ)
    today = now.date().isoformat()
    with _lock:
        data = _load()
        habits = find_habits(data["events"], now)
        done_today = {ev["key"] for ev in data["events"] if ev.get("ts", "").startswith(today)}
        current = _minutes(now)
        for habit in habits:
            key = habit["key"]
            if key in data["muted"] or key in done_today:
                continue
            if data["dismissed"].get(key) == today or data["suggested"].get(key) == today:
                continue
            if not habit["minute"] - SUGGEST_BEFORE_MIN <= current <= habit["minute"] + WINDOW_MIN:
                continue
            data["suggested"][key] = today
            _save(data)
            return {**habit, "text": suggestion_text(habit)}
    return None


def suggestion_text(habit: dict) -> str:
    hour, minute = divmod(habit["minute"], 60)
    when = f"{hour}h" if minute < 8 else f"{hour}h{minute:02d}"
    if habit["kind"] == "protocol":
        return f"Senhor, o senhor costuma ativar o protocolo {habit['label']} por volta das {when}. Quer que eu ative?"
    return f"Senhor, o senhor costuma abrir {habit['label']} por volta das {when}. Quer que eu abra?"


def dismiss(key: str, forever: bool = False, now: Optional[datetime] = None) -> None:
    now = now or datetime.now(SP_TZ)
    with _lock:
        data = _load()
        if forever:
            if key not in data["muted"]:
                data["muted"].append(key)
        else:
            data["dismissed"][key] = now.date().isoformat()
        _save(data)


def unmute_all() -> None:
    with _lock:
        data = _load()
        data["muted"] = []
        _save(data)


def summary(now: Optional[datetime] = None) -> dict:
    """Hábitos encontrados e sugestões silenciadas (para a tela de Configurações)."""
    now = now or datetime.now(SP_TZ)
    data = _load()
    habits = find_habits(data["events"], now)
    return {"habits": [{**h, "text": suggestion_text(h), "muted": h["key"] in data["muted"]} for h in habits],
            "muted": data["muted"], "events": len(data["events"])}


async def execute(habit: dict) -> str:
    """Faz a ação sugerida depois do "sim"."""
    if habit["kind"] == "protocol":
        from modules import protocols

        return (await protocols.run(habit["value"]))["reply"]
    from modules import tools

    return await tools.run(f"abrir {habit['value']}") or f"Abrindo {habit['label']}, senhor."

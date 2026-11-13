"""Módulo de Hidratação e Lembretes de Água (Fase W) para o JARVIS v4.0.

Gerencia meta diária, registros de ingestão de água, contagem de progresso,
reset diário à meia-noite e lembretes periódicos com respeito ao modo silencioso.
Armazena histórico diário em data/water_log.json.
"""
from __future__ import annotations

import json
import logging
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from config import settings

log = logging.getLogger("jarvis.water")

DATA_FILE = settings.DATA_DIR / "water_log.json"
SP_TZ = timezone(timedelta(hours=-3))

DEFAULT_GOAL_ML = 2000
DEFAULT_REMINDER_INTERVAL_MIN = 120
REMINDER_INTERVALS = (0, 30, 60, 90, 120, 180, 240)  # 0 = lembrete desligado
DEFAULT_START_HOUR = 8
DEFAULT_END_HOUR = 22


def _now() -> datetime:
    return datetime.now(SP_TZ)


def _today_str() -> str:
    return _now().strftime("%Y-%m-%d")


def _load_data() -> Dict[str, Any]:
    if not DATA_FILE.exists():
        return {
            "goal_ml": DEFAULT_GOAL_ML,
            "reminder_interval_min": DEFAULT_REMINDER_INTERVAL_MIN,
            "start_hour": DEFAULT_START_HOUR,
            "end_hour": DEFAULT_END_HOUR,
            "days": {},
            "last_reminder_ts": None,
        }
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "goal_ml" not in data:
                data["goal_ml"] = DEFAULT_GOAL_ML
            if "reminder_interval_min" not in data:
                data["reminder_interval_min"] = DEFAULT_REMINDER_INTERVAL_MIN
            if "days" not in data:
                data["days"] = {}
            return data
    except Exception as exc:
        log.warning("Falha ao carregar water_log.json: %s", exc)
        return {
            "goal_ml": DEFAULT_GOAL_ML,
            "reminder_interval_min": DEFAULT_REMINDER_INTERVAL_MIN,
            "days": {},
        }


def _save_data(data: Dict[str, Any]) -> None:
    try:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.warning("Falha ao salvar water_log.json: %s", exc)


def streak(data: Optional[Dict[str, Any]] = None, now: Optional[datetime] = None) -> Dict[str, Any]:
    """V6.8: ofensiva da água: dias seguidos batendo a meta (como no Duolingo).

    base = dias seguidos até ONTEM; hoje soma 1 quando a meta é batida. Se ontem não bateu, a ofensiva
    recomeça (base 0). Usa a meta atual para todos os dias.
    """
    data = data or _load_data()
    now = now or _now()
    goal = data.get("goal_ml", DEFAULT_GOAL_ML) or DEFAULT_GOAL_ML
    days = data.get("days", {})

    def done(d: datetime) -> bool:
        return int(days.get(d.strftime("%Y-%m-%d"), {}).get("total_ml", 0)) >= goal

    base = 0
    day = now - timedelta(days=1)
    while base < 3650 and done(day):
        base += 1
        day -= timedelta(days=1)
    today_done = done(now)
    best = int(data.get("best_streak", 0))
    total = base + (1 if today_done else 0)
    return {"days": total, "base": base, "today_done": today_done, "best": max(best, total)}


def streak_sentence(s: Dict[str, Any], st: Optional[Dict[str, Any]] = None) -> str:
    if s["days"] == 0:
        return "Sua ofensiva de água está zerada, senhor. Bata a meta hoje para começar uma nova."
    days = f"{s['days']} {'dia' if s['days'] == 1 else 'dias'}"
    if s["today_done"]:
        text = f"Sua ofensiva de água está em {days}, com a meta de hoje já batida."
    else:
        left = max(0, (st or get_status())["goal_ml"] - (st or get_status())["total_ml"])
        text = f"Sua ofensiva de água está em {days}. Faltam {left} ml hoje para manter."
    if s["best"] > s["days"]:
        text += f" Seu recorde é de {s['best']} dias."
    return text


def get_status() -> Dict[str, Any]:
    """Retorna o progresso hídrico de hoje."""
    data = _load_data()
    today = _today_str()
    day_entry = data["days"].get(today, {"total_ml": 0, "logs": []})
    total_ml = day_entry.get("total_ml", 0)
    goal_ml = data.get("goal_ml", DEFAULT_GOAL_ML)
    pct = min(100, int((total_ml / goal_ml) * 100)) if goal_ml > 0 else 0

    return {
        "date": today,
        "total_ml": total_ml,
        "goal_ml": goal_ml,
        "percentage": pct,
        "goal_reached": total_ml >= goal_ml,
        "logs": day_entry.get("logs", []),
        "last": (day_entry.get("logs") or [None])[-1],
        "reminder_interval_min": data.get("reminder_interval_min", DEFAULT_REMINDER_INTERVAL_MIN),
        "start_hour": data.get("start_hour", DEFAULT_START_HOUR),
        "end_hour": data.get("end_hour", DEFAULT_END_HOUR),
        # V6.8: ofensiva (dias seguidos batendo a meta)
        **{f"streak{'' if k == 'days' else '_' + k}": v for k, v in streak(data).items()},
    }


def status_sentence(st: Dict[str, Any]) -> str:
    """Frase única usada no texto da resposta (o frontend gera a mesma frase ao atualizar o cartão)."""
    return f"Hoje você já consumiu {st['total_ml']} ml de água ({st['percentage']}% da sua meta de {st['goal_ml']} ml)."


def get_day_total(days_ago: int = 1) -> Dict[str, Any]:
    """Total de um dia anterior (usado no resumo do dia: "total de ontem")."""
    data = _load_data()
    day = (_now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
    entry = data.get("days", {}).get(day, {"total_ml": 0})
    goal = data.get("goal_ml", DEFAULT_GOAL_ML)
    return {"date": day, "total_ml": int(entry.get("total_ml", 0)), "goal_ml": goal}


def undo_last() -> Dict[str, Any]:
    """Desfaz o último registro de hoje (sem efeito se não houver registros)."""
    data = _load_data()
    today = _today_str()
    day_entry = data["days"].get(today)
    if day_entry and day_entry.get("logs"):
        last = day_entry["logs"].pop()
        day_entry["total_ml"] = max(0, int(day_entry.get("total_ml", 0)) - int(last.get("ml", 0)))
        _save_data(data)
    return get_status()


def add_intake(ml: int, note: str = "copo de água") -> Dict[str, Any]:
    """Registra uma quantidade ingerida de água em ml."""
    if ml <= 0:
        raise ValueError("Quantidade de água deve ser maior que zero.")

    data = _load_data()
    today = _today_str()
    day_entry = data["days"].setdefault(today, {"total_ml": 0, "logs": []})

    now_iso = _now().strftime("%H:%M")
    day_entry["total_ml"] = day_entry.get("total_ml", 0) + ml
    day_entry["logs"].append({"time": now_iso, "ml": ml, "note": note})
    data["last_intake_ts"] = _now().isoformat()
    s = streak(data)  # V6.8: guarda o recorde da ofensiva
    if s["days"] > int(data.get("best_streak", 0)):
        data["best_streak"] = s["days"]

    _save_data(data)
    return get_status()


def set_goal(goal_ml: int) -> Dict[str, Any]:
    """Atualiza a meta diária de água."""
    if goal_ml < 500 or goal_ml > 10000:
        raise ValueError("A meta diária de água deve estar entre 500ml e 10.000ml.")
    data = _load_data()
    data["goal_ml"] = goal_ml
    _save_data(data)
    return get_status()


def reset_today() -> Dict[str, Any]:
    """Zera o consumo de hoje."""
    data = _load_data()
    today = _today_str()
    data["days"][today] = {"total_ml": 0, "logs": []}
    _save_data(data)
    return get_status()


def parse_water_command(message: str) -> Optional[tuple[str, int]]:
    """Identifica se a mensagem é um comando de beber água e extrai a quantidade em ml.

    Exemplos:
    - 'bebi 300ml de água' -> ('add', 300)
    - 'tomei um copo d água' -> ('add', 250)
    - 'bebi uma garrafinha' -> ('add', 500)
    - 'quanto de agua eu ja bebi' -> ('query', 0)
    - 'meta de agua 2500ml' -> ('set_goal', 2500)
    """
    norm = unicodedata.normalize("NFKD", message.lower().strip()).encode("ASCII", "ignore").decode("utf-8")
    norm_clean = re.sub(r"[^\w\s]", " ", norm)

    # Consulta
    query_phrases = (
        "quanto de agua", "quanta agua", "consumo de agua", "minha agua hoje",
        "nivel de agua", "quanto ja bebi", "indice de agua", "ver agua",
        "mostrar agua", "painel de agua", "status da agua", "relatorio de agua",
        "como esta a agua", "hidratacao", "nivel de hidratacao", "como esta minha hidratacao",
        "agua de hoje", "bebi agua hoje"
    )
    # V6.8: "qual minha ofensiva de água?" / "como está minha sequência de água?"
    if re.search(r"\bofensiva\b", norm_clean) or re.search(r"\bsequencia\b.*\bagua\b", norm_clean):
        return ("streak", 0)

    if any(q in norm_clean for q in query_phrases):
        return ("query", 0)

    # Ajuste de meta
    goal_match = re.search(r"(?:meta de agua|meta de hidratação|mudar meta de agua)\s*(?:para|pra)?\s*(\d+)\s*(?:ml|litros|l)?", norm_clean)
    if goal_match:
        val = int(goal_match.group(1))
        if "litro" in norm_clean or "l" in norm_clean and val <= 10:
            val = val * 1000
        return ("set_goal", val)

    # Ingestão explícita com ml
    ml_match = re.search(r"(?:bebi|tomei|beber|tomar|adicionei|registre|anote|mais)?\s*(\d+)\s*(?:ml|mili)?\s*(?:de agua|dagua|de água)?", norm_clean)
    if ml_match and any(k in norm_clean for k in ["bebi", "tomei", "agua", "água", "ml"]):
        val = int(ml_match.group(1))
        if 20 <= val <= 3000:
            return ("add", val)

    # Litros
    liter_match = re.search(r"(?:bebi|tomei|registre)?\s*(\d+(?:[.,]\d+)?)\s*(?:litro|litros|l)\s*(?:de agua|dagua)?", norm_clean)
    if liter_match:
        val_f = float(liter_match.group(1).replace(",", "."))
        return ("add", int(val_f * 1000))

    # Copos ou garrafas sem número explícito
    if any(k in norm_clean for k in ["bebi um copo", "tomei um copo", "mais um copo", "copo de agua", "copo dagua"]):
        return ("add", 250)
    if any(k in norm_clean for k in ["bebi dois copos", "tomei 2 copos", "dois copos de agua"]):
        return ("add", 500)
    if any(k in norm_clean for k in ["bebi uma garrafa", "tomei uma garrafa", "garrafa de agua", "garrafinha"]):
        return ("add", 500)

    return None


def should_remind_water() -> bool:
    """Verifica se já passou o tempo para lembrar o usuário de beber água."""
    now = _now()
    data = _load_data()

    start_h = data.get("start_hour", DEFAULT_START_HOUR)
    end_h = data.get("end_hour", DEFAULT_END_HOUR)

    # Não lembra de madrugada
    if now.hour < start_h or now.hour >= end_h:
        return False

    status = get_status()
    if status["goal_reached"]:
        return False

    interval_min = data.get("reminder_interval_min", DEFAULT_REMINDER_INTERVAL_MIN)
    if not interval_min:
        return False  # lembrete desligado

    # Conta a partir do que aconteceu por último: o último gole OU o último lembrete.
    # (Antes valia só a última ingestão; se ela fosse antiga, o JARVIS lembrava a cada 2 minutos.)
    last_dt = None
    for key in ("last_intake_ts", "last_reminder_ts"):
        try:
            dt = datetime.fromisoformat(data.get(key) or "")
        except (TypeError, ValueError):
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=SP_TZ)
        last_dt = dt if last_dt is None or dt > last_dt else last_dt
    if last_dt is not None and (now - last_dt).total_seconds() / 60 < interval_min:
        return False

    # Registra o lembrete
    data["last_reminder_ts"] = now.isoformat()
    _save_data(data)
    return True


def set_reminder(interval_min: Optional[int] = None, start_hour: Optional[int] = None,
                 end_hour: Optional[int] = None) -> Dict[str, Any]:
    """Ajusta o lembrete de água: intervalo (0 = desligado) e janela de horário."""
    data = _load_data()
    if interval_min is not None:
        if interval_min not in REMINDER_INTERVALS:
            raise ValueError(f"Intervalo inválido. Use {list(REMINDER_INTERVALS)} minutos (0 desliga).")
        data["reminder_interval_min"] = interval_min
    start = data.get("start_hour", DEFAULT_START_HOUR) if start_hour is None else start_hour
    end = data.get("end_hour", DEFAULT_END_HOUR) if end_hour is None else end_hour
    if not (0 <= start < end <= 24):
        raise ValueError("Janela de horário inválida (início deve ser antes do fim, entre 0 e 24 h).")
    data["start_hour"], data["end_hour"] = start, end
    _save_data(data)
    return get_status()

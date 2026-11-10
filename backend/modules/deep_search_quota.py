"""Controle de cota diária de pesquisas profundas (Gemini + Web Grounding)."""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from config import settings
from modules import prefs

log = logging.getLogger("jarvis.deep_search_quota")

_QUOTA_FILE: Path = settings.DATA_DIR / "deep_search_usage.json"


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _load_data() -> dict[str, Any]:
    today = _today_str()
    if not _QUOTA_FILE.exists():
        initial = {"date": today, "count": 0}
        _save_data(initial)
        return initial
    try:
        data = json.loads(_QUOTA_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("date") != today:
            reset = {"date": today, "count": 0}
            _save_data(reset)
            return reset
        return data
    except Exception as exc:
        log.warning("Falha ao ler deep_search_usage.json (%s); reiniciando cota diária.", exc)
        reset = {"date": today, "count": 0}
        _save_data(reset)
        return reset


def _save_data(data: dict[str, Any]) -> None:
    try:
        _QUOTA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        log.exception("Falha ao salvar deep_search_usage.json: %s", exc)


def get_status() -> dict[str, Any]:
    """Retorna o status atual da cota diária de pesquisa profunda."""
    data = _load_data()
    all_prefs = prefs.get_all()
    limit = int(all_prefs.get("deep_search_daily_limit", 5))
    allowed = bool(all_prefs.get("deep_search_allowed", False))
    count = int(data.get("count", 0))
    remaining = max(0, limit - count)
    return {
        "date": data.get("date", _today_str()),
        "count": count,
        "limit": limit,
        "allowed": allowed,
        "remaining": remaining,
    }


def can_consume() -> tuple[bool, str]:
    """Verifica se há cota disponível no dia de hoje."""
    status = get_status()
    if status["count"] >= status["limit"]:
        return False, "O limite de pesquisas profundas de hoje acabou, senhor."
    return True, ""


def consume() -> bool:
    """Registra o uso de uma pesquisa profunda e decrementa a cota diária."""
    data = _load_data()
    data["count"] = int(data.get("count", 0)) + 1
    _save_data(data)
    log.info("Pesquisa profunda realizada. Uso diário: %d", data["count"])
    return True


def refund() -> bool:
    """Ressarce a cota diária caso ocorra falha na API durante a pesquisa profunda."""
    data = _load_data()
    curr = int(data.get("count", 0))
    if curr > 0:
        data["count"] = curr - 1
        _save_data(data)
        log.info("Cota de pesquisa profunda reembolsada. Uso diário: %d", data["count"])
        return True
    return False

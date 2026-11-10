"""Gatilhos condicionais (4.2, funcionalidade 4 do backlog).

Avisos que o JARVIS dá sozinho quando uma condição acontece:
- chuva amanhã (uma vez por dia, à noite);
- jogo do time começando em breve (com o Modo Torcedor ligado);
- processador alto por alguns minutos seguidos;
- água atrasada em relação ao ritmo do dia (desligado por padrão: já existe o lembrete fixo).

As regras são funções puras sobre os dados de entrada (testáveis sem rede); `check_all()` busca os
dados, aplica as regras e devolve os avisos novos. Cada aviso tem uma chave e só é dado uma vez
por período (dia ou intervalo mínimo), então reiniciar o laço não repete avisos.
O laço que chama `check_all()` fica em core/watchers.py e roda tudo fora do servidor (to_thread).
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from config import settings

log = logging.getLogger("jarvis.triggers")
# Fuso fixo de Brasília (UTC-3), como em water.py e sports_provider.py. ZoneInfo("America/Sao_Paulo")
# não funciona no Windows sem o pacote tzdata e derrubava o backend na inicialização.
SP_TZ = timezone(timedelta(hours=-3))

DEFAULTS: dict[str, dict[str, Any]] = {
    "rain_tomorrow": {"enabled": True, "hour": 20, "min_probability": 60},
    "match_soon": {"enabled": True, "minutes": 30},
    "cpu_high": {"enabled": True, "threshold": 90, "minutes": 3},
    "water_behind": {"enabled": False, "deficit_ml": 500, "after_hour": 14},
}
LIMITS = {
    ("rain_tomorrow", "hour"): (6, 23),
    ("rain_tomorrow", "min_probability"): (10, 100),
    ("match_soon", "minutes"): (5, 180),
    ("cpu_high", "threshold"): (50, 100),
    ("cpu_high", "minutes"): (1, 30),
    ("water_behind", "deficit_ml"): (100, 3000),
    ("water_behind", "after_hour"): (8, 21),
}
QUIET_START, QUIET_END = 22, 7  # sem voz nesse intervalo (o aviso ainda aparece na tela)
CPU_COOLDOWN_S = 30 * 60

_lock = threading.Lock()
_fired: dict[str, str] = {}      # chave -> marca do período em que já avisou
_cpu_high_since: Optional[float] = None
_cpu_last_alert: Optional[float] = None


def merged_config(user: Optional[dict]) -> dict[str, dict[str, Any]]:
    """Padrões + o que o usuário salvou (chaves desconhecidas são ignoradas)."""
    out = {k: dict(v) for k, v in DEFAULTS.items()}
    for key, values in (user or {}).items():
        if key in out and isinstance(values, dict):
            out[key].update({k: v for k, v in values.items() if k in out[key]})
    return out


def validate(value: Any) -> Optional[str]:
    """Valida o patch de preferências `triggers`. Devolve a mensagem de erro ou None."""
    if not isinstance(value, dict):
        return "triggers deve ser um objeto."
    for key, values in value.items():
        if key not in DEFAULTS:
            return f"Gatilho desconhecido: {key}."
        if not isinstance(values, dict):
            return f"triggers.{key} deve ser um objeto."
        for field, v in values.items():
            if field not in DEFAULTS[key]:
                return f"Campo desconhecido em {key}: {field}."
            if field == "enabled":
                if not isinstance(v, bool):
                    return f"triggers.{key}.enabled deve ser verdadeiro ou falso."
                continue
            lo, hi = LIMITS[(key, field)]
            if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
                return f"triggers.{key}.{field} deve ser um número de {lo} a {hi}."
    return None


def is_quiet(now: datetime) -> bool:
    return now.hour >= QUIET_START or now.hour < QUIET_END


# ------------------------------------------------------------------ regras puras
def rule_rain_tomorrow(cfg: dict, now: datetime, forecast: Optional[dict], place: str) -> Optional[tuple[str, str]]:
    if not cfg["enabled"] or now.hour < cfg["hour"] or not forecast:
        return None
    probs = (forecast.get("daily") or {}).get("precipitation_probability_max") or []
    if len(probs) < 2 or probs[1] is None or probs[1] < cfg["min_probability"]:
        return None
    return (f"rain:{now.date()}",
            f"Previsão de chuva amanhã em {place}: {round(probs[1])}% de chance. Vale separar o guarda-chuva, senhor.")


def rule_match_soon(cfg: dict, match: Optional[dict], team_name: str) -> Optional[tuple[str, str]]:
    if not cfg["enabled"] or not match or match.get("status") != "scheduled":
        return None
    if match.get("time_known") is False:  # V4.4: jogo só confirmado pelo Google Notícias, sem horário
        return None
    seconds = match.get("seconds_until_match") or 0
    if not 0 < seconds <= cfg["minutes"] * 60:
        return None
    minutes = max(1, round(seconds / 60))
    opponent = match.get("opponent", "o adversário")
    return (f"match:{match.get('id')}:{match.get('date')}",
            f"O jogo do {team_name} contra {opponent} começa em {minutes} minutos.")


def rule_cpu_high(cfg: dict, cpu: Optional[float], now_mono: float) -> Optional[tuple[str, str]]:
    """Processador acima do limite por `minutes` seguidos; no máximo um aviso a cada 30 min."""
    global _cpu_high_since, _cpu_last_alert
    if not cfg["enabled"] or cpu is None:
        _cpu_high_since = None
        return None
    if cpu < cfg["threshold"]:
        _cpu_high_since = None
        return None
    if _cpu_high_since is None:
        _cpu_high_since = now_mono
    if now_mono - _cpu_high_since < cfg["minutes"] * 60 or (
        _cpu_last_alert is not None and now_mono - _cpu_last_alert < CPU_COOLDOWN_S
    ):
        return None
    _cpu_last_alert = now_mono
    return (f"cpu:{int(now_mono)}",
            f"Processador acima de {cfg['threshold']}% há {cfg['minutes']} minutos (agora em {round(cpu)}%). "
            "Pode haver algum programa travado, senhor.")


def rule_water_behind(cfg: dict, now: datetime, water: Optional[dict]) -> Optional[tuple[str, str]]:
    if not cfg["enabled"] or not water or water.get("goal_reached") or now.hour < cfg["after_hour"]:
        return None
    start, end = water.get("start_hour", 8), water.get("end_hour", 22)
    if not start <= now.hour < end or end <= start:
        return None
    elapsed = (now.hour + now.minute / 60 - start) / (end - start)
    expected = water.get("goal_ml", 2000) * max(0.0, min(1.0, elapsed))
    behind = expected - water.get("total_ml", 0)
    if behind < cfg["deficit_ml"]:
        return None
    return (f"water:{now.date()}",
            f"Você está cerca de {int(round(behind, -1))} ml abaixo do ritmo de água de hoje. Um copo agora ajuda, senhor.")


# ------------------------------------------------------------------ coleta + disparo
def _new(key_and_text: Optional[tuple[str, str]], kind: str) -> Optional[dict]:
    if not key_and_text:
        return None
    key, text = key_and_text
    with _lock:
        if _fired.get(kind) == key:
            return None
        _fired[kind] = key
    return {"kind": kind, "text": text}


def check_all(user_cfg: Optional[dict], fan_enabled: bool, team_id: str,
              now: Optional[datetime] = None) -> list[dict]:
    """Busca os dados necessários (rede só quando a regra está ligada) e devolve os avisos novos."""
    from modules import fan_mode, sports_provider, system_monitor, tools, water

    cfg = merged_config(user_cfg)
    now = now or datetime.now(SP_TZ)
    alerts: list[dict] = []

    if cfg["rain_tomorrow"]["enabled"] and now.hour >= cfg["rain_tomorrow"]["hour"] \
            and _fired.get("rain_tomorrow") != f"rain:{now.date()}":
        try:
            result = tools._fetch_weather(settings.WEATHER_CITY)
            if result:
                alerts.append(_new(rule_rain_tomorrow(cfg["rain_tomorrow"], now, result["data"], result["place"]),
                                   "rain_tomorrow"))
        except Exception as exc:  # noqa: BLE001 - sem internet: tenta no próximo ciclo
            log.debug("Gatilho de chuva sem previsão: %s", exc)

    if fan_enabled and cfg["match_soon"]["enabled"]:
        try:
            match = sports_provider.get_current_or_next_match(team_id)
            team = (fan_mode.get_team_info(team_id) or {}).get("name", team_id.capitalize())
            alerts.append(_new(rule_match_soon(cfg["match_soon"], match, team), "match_soon"))
        except Exception as exc:  # noqa: BLE001
            log.debug("Gatilho de jogo sem dados: %s", exc)

    if cfg["cpu_high"]["enabled"]:
        cpu = system_monitor.snapshot().get("cpu_percent")
        alerts.append(_new(rule_cpu_high(cfg["cpu_high"], cpu, time.monotonic()), "cpu_high"))

    if cfg["water_behind"]["enabled"]:
        alerts.append(_new(rule_water_behind(cfg["water_behind"], now, water.get_status()), "water_behind"))

    return [a for a in alerts if a]


def reset_for_tests() -> None:
    global _cpu_high_since, _cpu_last_alert
    with _lock:
        _fired.clear()
    _cpu_high_since = None
    _cpu_last_alert = None


def demo_now(hour: int, minute: int = 0) -> datetime:
    """Ajuda dos testes: hoje em São Paulo no horário pedido."""
    base = datetime.now(SP_TZ).replace(hour=hour, minute=minute, second=0, microsecond=0)
    return base if base.tzinfo else base.replace(tzinfo=SP_TZ)


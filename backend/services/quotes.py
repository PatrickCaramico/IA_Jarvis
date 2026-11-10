"""Cotações de moedas (AwesomeAPI, sem chave) num só lugar (refatoração 4.2).

Antes havia três buscas separadas (resposta por voz, cartão reativo e widget de finanças).
Agora todas usam `fetch_rates()`, com cache de 60 s: perguntas seguidas não repetem a consulta.
"""

from __future__ import annotations

from services import http_client

API_URL = "https://economia.awesomeapi.com.br/json/last/"
DEFAULT_PAIRS = ("USD-BRL", "EUR-BRL", "BTC-BRL")
CACHE_SECONDS = 60


def fetch_rates(pairs: tuple[str, ...] = DEFAULT_PAIRS, timeout: float = 6) -> dict:
    """Resposta bruta da AwesomeAPI: {"USDBRL": {"bid": "5.4", "name": ..., ...}, ...}."""
    return http_client.get_json(API_URL + ",".join(pairs), timeout=timeout, ttl=CACHE_SECONDS)


def get_rate(key: str) -> float:
    """Valor de compra (bid) de um par, ex.: get_rate("USDBRL")."""
    pair = f"{key[:3]}-{key[3:]}"
    pairs = DEFAULT_PAIRS if pair in DEFAULT_PAIRS else (pair,)
    return float(fetch_rates(pairs)[key]["bid"])


def summarize(raw: dict) -> list[dict]:
    """Lista normalizada usada pelos cartões e pelo widget (números já convertidos)."""
    rates = []
    for pair, info in raw.items():
        rates.append(
            {
                "pair": pair,
                "code": info.get("code"),
                "name": info.get("name"),
                "bid": float(info.get("bid", 0)),
                "pctChange": float(info.get("pctChange", 0)),
                "high": float(info.get("high", 0)),
                "low": float(info.get("low", 0)),
            }
        )
    return rates

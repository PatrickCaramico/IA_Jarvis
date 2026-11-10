"""V4.5: finanças pessoais sem banco (só o que você conta para o JARVIS), guardadas neste PC.

- "gastei 45 reais no mercado" / "paguei 120 de luz" / "recebi 3000 de salário"
- "quanto eu gastei hoje / essa semana / esse mês?" / "meu saldo do mês"
- "apaga o último gasto"

Nenhuma conta bancária é conectada. Categoria pelo que você disser (mercado, luz, uber...).
"""
from __future__ import annotations

import json
import re
import threading
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from config import settings

DATA_PATH: Path = settings.DATA_DIR / "financas.json"
SP_TZ = timezone(timedelta(hours=-3))
_lock = threading.Lock()

_CATEGORIES = {
    "mercado": "Mercado", "supermercado": "Mercado", "feira": "Mercado", "padaria": "Mercado",
    "luz": "Contas", "agua": "Contas", "internet": "Contas", "aluguel": "Moradia", "condominio": "Moradia",
    "gasolina": "Transporte", "combustivel": "Transporte", "uber": "Transporte", "onibus": "Transporte", "metro": "Transporte",
    "ifood": "Comida", "restaurante": "Comida", "lanche": "Comida", "almoco": "Comida", "jantar": "Comida",
    "farmacia": "Saúde", "remedio": "Saúde", "academia": "Saúde", "medico": "Saúde",
    "cinema": "Lazer", "jogo": "Lazer", "ingresso": "Lazer", "spotify": "Assinaturas", "netflix": "Assinaturas",
    "roupa": "Compras", "presente": "Compras",
}

_AMOUNT = r"(?:r\$\s*)?(\d+(?:[.,]\d{1,2})?)\s*(?:reais|real|conto|contos|pila)?"
_SPEND_RE = re.compile(rf"^(?:jarvis\s+)?(?:eu\s+)?(?:gastei|paguei|comprei|torrei)\s+{_AMOUNT}\s*(?:(?:no|na|nos|nas|em|de|com|do|da|pra|para)\s+(.+))?$")
_EARN_RE = re.compile(rf"^(?:jarvis\s+)?(?:eu\s+)?(?:recebi|ganhei|entrou|caiu)\s+{_AMOUNT}\s*(?:(?:de|do|da|no|na|com)\s+(.+))?$")
_QUERY_RE = re.compile(r"^(?:jarvis\s+)?(?:quanto (?:eu )?(?:ja )?gastei|meus gastos|(?:meu )?saldo|resumo (?:dos gastos|financeiro))"
                       r"\s*(?:de |d[oa] )?(hoje|ontem|(?:essa|esta|nessa|nesta) semana|(?:esse|este|nesse|neste) mes|do mes|da semana)?\??$")
_UNDO_RE = re.compile(r"^(?:jarvis\s+)?(?:apaga|apague|remove|remova|desfaz|desfaca)\s+(?:o\s+)?ultimo\s+(?:gasto|lancamento|registro)$")


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", text).strip()


def _load() -> list[dict[str, Any]]:
    try:
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _save(items: list[dict[str, Any]]) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(items[-2000:], ensure_ascii=False, indent=2), encoding="utf-8")


def _money(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _category(desc: str) -> str:
    for word in _norm(desc).split():
        if word in _CATEGORIES:
            return _CATEGORIES[word]
    return "Outros"


def add(kind: str, amount: float, desc: str, now: Optional[datetime] = None) -> dict[str, Any]:
    now = now or datetime.now(SP_TZ)
    item = {"kind": kind, "amount": round(amount, 2), "desc": desc.strip() or ("Entrada" if kind == "in" else "Gasto"),
            "category": "Entrada" if kind == "in" else _category(desc), "at": now.isoformat(timespec="seconds")}
    with _lock:
        items = _load()
        items.append(item)
        _save(items)
    return item


def summary(period: str = "month", now: Optional[datetime] = None) -> dict[str, Any]:
    now = now or datetime.now(SP_TZ)
    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "yesterday":
        start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        now = start + timedelta(days=1)
    elif period == "week":
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    spent, earned, by_cat, rows = 0.0, 0.0, {}, []
    for it in _load():
        try:
            at = datetime.fromisoformat(it["at"])
        except (KeyError, ValueError):
            continue
        if not start <= at < now + timedelta(seconds=1):
            continue
        rows.append(it)
        if it["kind"] == "in":
            earned += it["amount"]
        else:
            spent += it["amount"]
            by_cat[it["category"]] = by_cat.get(it["category"], 0) + it["amount"]
    return {"period": period, "spent": round(spent, 2), "earned": round(earned, 2), "balance": round(earned - spent, 2),
            "by_category": dict(sorted(by_cat.items(), key=lambda kv: -kv[1])), "items": rows[-30:]}


def handle_voice(norm: str) -> Optional[str]:
    m = _SPEND_RE.match(norm)
    if m:
        item = add("out", float(m.group(1).replace(",", ".")), m.group(2) or "")
        month = summary("month")
        return (f"Anotado, senhor: {_money(item['amount'])} em {item['category'].lower()}"
                f"{' (' + item['desc'] + ')' if item['desc'] and item['category'] == 'Outros' else ''}. "
                f"No mês, {_money(month['spent'])} em gastos.")
    m = _EARN_RE.match(norm)
    if m:
        item = add("in", float(m.group(1).replace(",", ".")), m.group(2) or "")
        return f"Entrada de {_money(item['amount'])} anotada, senhor."
    if _UNDO_RE.match(norm):
        with _lock:
            items = _load()
            if not items:
                return "Não há lançamentos para apagar, senhor."
            last = items.pop()
            _save(items)
        return f"Apaguei o último lançamento: {_money(last['amount'])} ({last['desc']})."
    m = _QUERY_RE.match(norm)
    if m:
        word = m.group(1) or "mes"
        period = "today" if "hoje" in word else "yesterday" if "ontem" in word else "week" if "semana" in word else "month"
        s = summary(period)
        label = {"today": "hoje", "yesterday": "ontem", "week": "nesta semana", "month": "neste mês"}[period]
        if not s["items"]:
            return f"Nenhum lançamento {label}, senhor. Diga, por exemplo: gastei 30 reais no mercado."
        top = ", ".join(f"{c.lower()} {_money(v)}" for c, v in list(s["by_category"].items())[:3])
        tail = f" Saldo {label}: {_money(s['balance'])}." if s["earned"] else ""
        return f"Você gastou {_money(s['spent'])} {label}, senhor{': ' + top if top else ''}.{tail}"
    return None

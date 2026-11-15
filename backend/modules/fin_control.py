"""V7.10: CONTROLE FINANCEIRO do agente 💰 @financas (ideia 3.1 do documento de atualização).

Guarda SÓ no PC (data/financas_controle.json):
- dívidas e parcelamentos (credor, saldo, parcela, 7 de 12, juros ao mês, dia do vencimento, histórico);
- contas fixas do mês (valor, vencimento, "paga" por mês);
- cartões (fechamento, vencimento, limite) e compras à vista/parceladas, que caem nas faturas certas;
- orçamento por categoria (as mesmas categorias dos gastos do modules/finances.py) e metas;
- plano para quitar: compara "menor dívida primeiro" x "maior juros primeiro" (meses e juros) e recomenda;
- avisos 3 dias antes e no dia (dívidas, contas e faturas) e de orçamento a 80%/100%.
Os gastos do dia a dia continuam no modules/finances.py (o orçamento lê de lá).
"""
from __future__ import annotations

import calendar
import json
import re
import secrets
import threading
import unicodedata
from datetime import date, datetime, timedelta
from typing import Optional

from config import settings

_PATH = settings.DATA_DIR / "financas_controle.json"
_lock = threading.RLock()
BIG_VALUE = 1000.0  # pagamento acima disso pede CONFIRMAR
EMPTY = {"dividas": [], "contas": [], "cartoes": [], "orcamentos": {}, "metas": [], "avisos": {}}


# --------------------------------------------------------------------------- base
def money(v: float) -> str:
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return re.sub(r"\s+", " ", "".join(c for c in t if unicodedata.category(c) != "Mn")).strip()


def _num(v) -> Optional[float]:
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    t = str(v).replace("R$", "").replace("%", "").strip()
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def _load() -> dict:
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8")) if _PATH.exists() else {}
    except (OSError, ValueError):
        data = {}
    for k, v in EMPTY.items():
        data.setdefault(k, type(v)())
    return data


def _save(data: dict) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _id() -> str:
    return secrets.token_hex(4)


def _find(items: list[dict], ref: str, field: str = "nome") -> Optional[dict]:
    """Acha pelo id ou pelo nome (parecido): "carro" acha "Financiamento do carro"."""
    if not ref:
        return None
    n = _norm(ref)
    for it in items:
        if it.get("id") == ref:
            return it
    exact = [it for it in items if _norm(it.get(field, "")) == n]
    if exact:
        return exact[0]
    part = [it for it in items if n in _norm(it.get(field, "")) or _norm(it.get(field, "")) in n]
    return part[0] if len(part) == 1 else (part[0] if part else None)


def _due(day: int, ref: date) -> date:
    """Dia `day` do mês de `ref` (ajustado para meses curtos)."""
    last = calendar.monthrange(ref.year, ref.month)[1]
    return date(ref.year, ref.month, min(max(1, int(day)), last))


def _add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def _ym(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


# --------------------------------------------------------------------------- dívidas
def divida_add(credor: str, saldo: float, parcela: float = 0, total_parcelas: int = 0, pagas: int = 0,
               juros_mes: float = 0, dia: int = 10, descricao: str = "") -> dict:
    with _lock:
        data = _load()
        d = {"id": _id(), "nome": credor.strip()[:60], "descricao": descricao.strip()[:80], "saldo": round(saldo, 2),
             "saldo_inicial": round(saldo, 2), "parcela": round(parcela or 0, 2), "total_parcelas": int(total_parcelas or 0),
             "pagas": int(pagas or 0), "juros_mes": round(juros_mes or 0, 3), "dia": int(dia or 10), "quitada": False,
             "pagamentos": [], "criada": datetime.now().isoformat(timespec="seconds")}
        data["dividas"].append(d)
        _save(data)
        return d


def divida_pagar(ref: str, valor: Optional[float] = None, now: Optional[datetime] = None) -> dict:
    now = now or datetime.now()
    with _lock:
        data = _load()
        d = _find([x for x in data["dividas"] if not x["quitada"]], ref)
        if not d:
            raise ValueError(f"Não achei a dívida \"{ref}\".")
        v = round(valor if valor else (d["parcela"] or d["saldo"]), 2)
        d["saldo"] = round(max(0.0, d["saldo"] - v), 2)
        if d["parcela"] and v >= d["parcela"] * 0.99:
            d["pagas"] = min(d["pagas"] + 1, d["total_parcelas"] or d["pagas"] + 1)
        d["pagamentos"].append({"data": now.isoformat(timespec="seconds"), "valor": v, "mes": _ym(now.date())})
        d["pagamentos"] = d["pagamentos"][-120:]
        if d["saldo"] <= 0.009 or (d["total_parcelas"] and d["pagas"] >= d["total_parcelas"]):
            d["quitada"], d["saldo"] = True, 0.0
        _save(data)
        return d


def divida_quitar(ref: str) -> dict:
    with _lock:
        data = _load()
        d = _find([x for x in data["dividas"] if not x["quitada"]], ref)
        if not d:
            raise ValueError(f"Não achei a dívida \"{ref}\".")
        d["pagamentos"].append({"data": datetime.now().isoformat(timespec="seconds"), "valor": d["saldo"], "quitacao": True,
                                "mes": _ym(date.today())})
        d["saldo"], d["quitada"] = 0.0, True
        _save(data)
        return d


def divida_editar(ref: str, **fields) -> dict:
    with _lock:
        data = _load()
        d = _find(data["dividas"], ref)
        if not d:
            raise ValueError(f"Não achei a dívida \"{ref}\".")
        for k in ("saldo", "parcela", "juros_mes"):
            if fields.get(k) is not None:
                d[k] = round(float(fields[k]), 3 if k == "juros_mes" else 2)
        for k in ("total_parcelas", "pagas", "dia"):
            if fields.get(k) is not None:
                d[k] = int(fields[k])
        _save(data)
        return d


def remover(kind: str, ref: str) -> str:
    with _lock:
        data = _load()
        lst = data[{"divida": "dividas", "conta": "contas", "cartao": "cartoes", "meta": "metas"}[kind]]
        it = _find(lst, ref)
        if not it:
            raise ValueError(f"Não achei \"{ref}\".")
        lst.remove(it)
        _save(data)
        return it["nome"]


# --------------------------------------------------------------------------- contas fixas
def conta_add(nome: str, valor: float, dia: int, categoria: str = "Contas") -> dict:
    with _lock:
        data = _load()
        c = {"id": _id(), "nome": nome.strip()[:60], "valor": round(valor, 2), "dia": int(dia), "categoria": categoria[:30],
             "pagas": {}}
        data["contas"].append(c)
        _save(data)
        return c


def conta_pagar(ref: str, valor: Optional[float] = None, now: Optional[datetime] = None) -> dict:
    now = now or datetime.now()
    with _lock:
        data = _load()
        c = _find(data["contas"], ref)
        if not c:
            raise ValueError(f"Não achei a conta \"{ref}\".")
        c["pagas"][_ym(now.date())] = {"data": now.isoformat(timespec="seconds"), "valor": round(valor or c["valor"], 2)}
        _save(data)
        return c


# --------------------------------------------------------------------------- cartões
def cartao_add(nome: str, fechamento: int, vencimento: int, limite: float = 0) -> dict:
    with _lock:
        data = _load()
        k = {"id": _id(), "nome": nome.strip()[:40], "fechamento": int(fechamento), "vencimento": int(vencimento),
             "limite": round(limite or 0, 2), "compras": [], "pagas": {}}
        data["cartoes"].append(k)
        _save(data)
        return k


def _first_invoice(card: dict, when: date) -> date:
    """Data de vencimento da fatura onde cai uma compra feita em `when`."""
    closing = _due(card["fechamento"], when)
    if when.day > card["fechamento"]:  # depois do fechamento: vai para a próxima
        closing = _due(card["fechamento"], _add_months(when.replace(day=1), 1))
    due = _due(card["vencimento"], closing)
    if card["vencimento"] <= card["fechamento"]:
        due = _due(card["vencimento"], _add_months(closing.replace(day=1), 1))
    return due


def cartao_compra(ref: str, valor: float, descricao: str = "", parcelas: int = 1, now: Optional[datetime] = None) -> dict:
    now = now or datetime.now()
    with _lock:
        data = _load()
        k = _find(data["cartoes"], ref) or (data["cartoes"][0] if len(data["cartoes"]) == 1 and not ref else None)
        if not k:
            raise ValueError("Não achei esse cartão. Cadastre o cartão primeiro (nome, fechamento e vencimento).")
        compra = {"id": _id(), "data": now.date().isoformat(), "descricao": descricao.strip()[:80] or "Compra",
                  "valor": round(valor, 2), "parcelas": max(1, int(parcelas or 1)),
                  "primeira": _first_invoice(k, now.date()).isoformat()}
        k["compras"].append(compra)
        k["compras"] = k["compras"][-400:]
        _save(data)
        return {"cartao": k["nome"], **compra}


def faturas(card: dict, months: int = 3, today: Optional[date] = None) -> list[dict]:
    """Próximas faturas (a atual e as seguintes) com o valor de cada uma."""
    today = today or date.today()
    current = _first_invoice(card, today)
    out = []
    for i in range(months):
        due = _due(card["vencimento"], _add_months(current.replace(day=1), i))
        total = 0.0
        for c in card["compras"]:
            first = date.fromisoformat(c["primeira"])
            n = (due.year - first.year) * 12 + (due.month - first.month)
            if 0 <= n < c["parcelas"]:
                total += c["valor"] / c["parcelas"]
        out.append({"vencimento": due.isoformat(), "valor": round(total, 2), "paga": _ym(due) in card.get("pagas", {})})
    return out


def fatura_pagar(ref: str, now: Optional[datetime] = None) -> dict:
    now = now or datetime.now()
    with _lock:
        data = _load()
        k = _find(data["cartoes"], ref) or (data["cartoes"][0] if len(data["cartoes"]) == 1 else None)
        if not k:
            raise ValueError(f"Não achei o cartão \"{ref}\".")
        f = next((x for x in faturas(k, 3, now.date()) if not x["paga"]), None)
        if not f:
            raise ValueError("Não há fatura em aberto.")
        k.setdefault("pagas", {})[f["vencimento"][:7]] = {"data": now.isoformat(timespec="seconds"), "valor": f["valor"]}
        _save(data)
        return {"cartao": k["nome"], **f}


# --------------------------------------------------------------------------- orçamento e metas
def orcamento_set(categoria: str, limite: float) -> dict:
    with _lock:
        data = _load()
        data["orcamentos"][categoria.strip()[:30].capitalize()] = round(limite, 2)
        _save(data)
        return data["orcamentos"]


def orcamento_status(now: Optional[datetime] = None) -> list[dict]:
    from modules import finances

    spent = finances.summary("month").get("by_category", {})
    out = []
    for cat, lim in _load()["orcamentos"].items():
        used = round(next((v for k, v in spent.items() if _norm(k) == _norm(cat)), 0.0), 2)
        out.append({"categoria": cat, "limite": lim, "gasto": used, "pct": round(100 * used / lim) if lim else 0})
    return sorted(out, key=lambda x: -x["pct"])


def meta_add(nome: str, alvo: float, prazo: str = "") -> dict:
    with _lock:
        data = _load()
        m = {"id": _id(), "nome": nome.strip()[:60], "alvo": round(alvo, 2), "guardado": 0.0, "prazo": prazo[:10]}
        data["metas"].append(m)
        _save(data)
        return m


def meta_guardar(ref: str, valor: float) -> dict:
    with _lock:
        data = _load()
        m = _find(data["metas"], ref)
        if not m:
            raise ValueError(f"Não achei a meta \"{ref}\".")
        m["guardado"] = round(m["guardado"] + valor, 2)
        _save(data)
        return m


# --------------------------------------------------------------------------- vencimentos, resumo e plano
def vencimentos(days: int = 30, today: Optional[date] = None) -> list[dict]:
    today = today or date.today()
    end = today + timedelta(days=days)
    data = _load()
    out = []
    for d in data["dividas"]:
        if d["quitada"]:
            continue
        for i in range(0, 2):
            due = _due(d["dia"], _add_months(today.replace(day=1), i))
            paid = any(p.get("mes") == _ym(due) for p in d["pagamentos"])
            if today <= due <= end or (due < today and i == 0 and not paid):
                out.append({"tipo": "divida", "id": d["id"], "nome": d["nome"], "valor": d["parcela"] or d["saldo"],
                            "data": due.isoformat(), "pago": paid, "atrasada": due < today and not paid})
    for c in data["contas"]:
        for i in range(0, 2):
            due = _due(c["dia"], _add_months(today.replace(day=1), i))
            paid = _ym(due) in c["pagas"]
            if today <= due <= end or (due < today and i == 0 and not paid):
                out.append({"tipo": "conta", "id": c["id"], "nome": c["nome"], "valor": c["valor"], "data": due.isoformat(),
                            "pago": paid, "atrasada": due < today and not paid})
    for k in data["cartoes"]:
        for f in faturas(k, 2, today):
            due = date.fromisoformat(f["vencimento"])
            if f["valor"] > 0 and due <= end:
                out.append({"tipo": "fatura", "id": k["id"], "nome": f"Fatura {k['nome']}", "valor": f["valor"],
                            "data": f["vencimento"], "pago": f["paga"], "atrasada": due < today and not f["paga"]})
    return sorted(out, key=lambda x: x["data"])


def plano(extra: float = 0.0, max_months: int = 600) -> dict:
    """Simula as duas estratégias com as dívidas em aberto (parcela mínima + extra no alvo)."""
    debts = [d for d in _load()["dividas"] if not d["quitada"] and d["saldo"] > 0]
    if not debts:
        return {"tem_dividas": False}

    def simulate(order_key) -> dict:
        ds = [{"nome": d["nome"], "saldo": d["saldo"], "taxa": (d["juros_mes"] or 0) / 100,
               "min": d["parcela"] or max(d["saldo"] * 0.05, 50)} for d in debts]
        budget = sum(x["min"] for x in ds) + max(extra, 0)
        months, interest, order = 0, 0.0, []
        while any(x["saldo"] > 0.01 for x in ds) and months < max_months:
            months += 1
            for x in ds:
                if x["saldo"] > 0:
                    j = x["saldo"] * x["taxa"]
                    x["saldo"] += j
                    interest += j
            money_left = budget
            alive = [x for x in ds if x["saldo"] > 0.01]
            for x in alive:
                pay = min(x["min"], x["saldo"], money_left)
                x["saldo"] -= pay
                money_left -= pay
            for x in sorted([x for x in ds if x["saldo"] > 0.01], key=order_key):
                pay = min(x["saldo"], money_left)
                x["saldo"] -= pay
                money_left -= pay
                if money_left <= 0:
                    break
            for x in ds:
                if x["saldo"] <= 0.01 and x["nome"] not in order:
                    order.append(x["nome"])
        foco = [x["nome"] for x in sorted(
            [{"nome": d["nome"], "saldo": d["saldo"], "taxa": (d["juros_mes"] or 0) / 100} for d in debts], key=order_key)]
        return {"meses": months, "juros": round(interest, 2), "ordem": order, "foco": foco, "completo": months < max_months}

    snow = simulate(lambda x: x["saldo"])
    aval = simulate(lambda x: -x["taxa"])
    saving = round(snow["juros"] - aval["juros"], 2)
    pick = "avalanche" if saving > max(100, snow["juros"] * 0.05) else "bola_de_neve"
    why = (f"Pagar primeiro a de maior juros economiza {money(saving)} em juros." if pick == "avalanche"
           else "A diferença de juros é pequena: começar pela menor dívida dá motivação vendo as dívidas sumirem.")
    return {"tem_dividas": True, "extra": round(extra, 2), "bola_de_neve": snow, "avalanche": aval,
            "recomendado": pick, "motivo": why, "orcamento_mensal": round(sum((d["parcela"] or 0) for d in debts) + extra, 2)}


def resumo(today: Optional[date] = None) -> dict:
    today = today or date.today()
    data = _load()
    abertas = [d for d in data["dividas"] if not d["quitada"]]
    venc = vencimentos(31, today)
    mes = [v for v in venc if v["data"][:7] == _ym(today)]
    cartoes = [{"id": k["id"], "nome": k["nome"], "limite": k["limite"], "fechamento": k["fechamento"],
                "vencimento": k["vencimento"], "faturas": faturas(k, 3, today)} for k in data["cartoes"]]
    return {
        "total_devido": round(sum(d["saldo"] for d in abertas), 2),
        "parcelas_mes": round(sum(d["parcela"] for d in abertas), 2),
        "a_pagar_mes": round(sum(v["valor"] for v in mes if not v["pago"]), 2),
        "pago_mes": round(sum(v["valor"] for v in mes if v["pago"]), 2),
        "atrasados": [v for v in venc if v["atrasada"]],
        "proximos": [v for v in venc if not v["pago"]][:12],
        "dividas": [{k: d[k] for k in ("id", "nome", "descricao", "saldo", "saldo_inicial", "parcela", "total_parcelas", "pagas",
                                       "juros_mes", "dia", "quitada")} for d in data["dividas"]],
        "contas": [{"id": c["id"], "nome": c["nome"], "valor": c["valor"], "dia": c["dia"],
                    "paga_mes": _ym(today) in c["pagas"]} for c in data["contas"]],
        "cartoes": cartoes,
        "orcamento": orcamento_status(),
        "metas": [{**m, "pct": round(100 * m["guardado"] / m["alvo"]) if m["alvo"] else 0} for m in data["metas"]],
    }


def resumo_texto(today: Optional[date] = None) -> str:
    r = resumo(today)
    dv = "; ".join(f"{d['nome']}: saldo {money(d['saldo'])}, parcela {money(d['parcela'])}"
                   + (f" ({d['pagas']} de {d['total_parcelas']})" if d["total_parcelas"] else "")
                   + (f", juros {d['juros_mes']}% a.m." if d["juros_mes"] else "") + f", vence dia {d['dia']}"
                   for d in r["dividas"] if not d["quitada"]) or "nenhuma"
    ct = "; ".join(f"{c['nome']} {money(c['valor'])} dia {c['dia']} ({'paga' if c['paga_mes'] else 'a pagar'})" for c in r["contas"]) or "nenhuma"
    cc = "; ".join(f"{k['nome']} (fecha dia {k['fechamento']}, vence dia {k['vencimento']}): faturas "
                   + ", ".join(f"{f['vencimento'][8:10]}/{f['vencimento'][5:7]} {money(f['valor'])}{' paga' if f['paga'] else ''}" for f in k["faturas"])
                   for k in r["cartoes"]) or "nenhum"
    orc = "; ".join(f"{o['categoria']}: {money(o['gasto'])} de {money(o['limite'])} ({o['pct']}%)" for o in r["orcamento"]) or "nenhum"
    mt = "; ".join(f"{m['nome']}: {money(m['guardado'])} de {money(m['alvo'])}" for m in r["metas"]) or "nenhuma"
    prox = "; ".join(f"{v['data'][8:10]}/{v['data'][5:7]} {v['nome']} {money(v['valor'])}{' (ATRASADA)' if v['atrasada'] else ''}"
                     for v in r["proximos"][:8]) or "nada"
    return (f"Total devido: {money(r['total_devido'])}. Parcelas por mês: {money(r['parcelas_mes'])}. "
            f"Ainda a pagar neste mês: {money(r['a_pagar_mes'])}. Dívidas: {dv}. Contas fixas: {ct}. Cartões: {cc}. "
            f"Orçamento: {orc}. Metas: {mt}. Próximos vencimentos: {prox}.")


# --------------------------------------------------------------------------- avisos (3 dias antes e no dia)
def due_alerts(today: Optional[date] = None) -> list[str]:
    """Avisos novos de hoje (cada um sai uma vez só). Dívidas, contas, faturas e orçamento."""
    today = today or date.today()
    out = []
    with _lock:
        data = _load()
        sent = data["avisos"]
        for v in vencimentos(3, today):
            if v["pago"]:
                continue
            days = (date.fromisoformat(v["data"]) - today).days
            when = "hoje" if days == 0 else ("está atrasada desde " + v["data"][8:10] + "/" + v["data"][5:7]) if days < 0 else (
                f"em {days} dias" if days == 3 else None)
            if not when:
                continue
            key = f"{v['tipo']}:{v['id']}:{v['data']}:{'0' if days <= 0 else '3'}"
            if key in sent:
                continue
            sent[key] = today.isoformat()
            what = {"divida": "a parcela de", "conta": "a conta de", "fatura": "a"}[v["tipo"]]
            out.append(f"Senhor, {'vence ' + when if days >= 0 else ''}{what} {v['nome']}, {money(v['valor'])}."
                       if days >= 0 else f"Senhor, {what} {v['nome']} ({money(v['valor'])}) {when}.")
        for o in orcamento_status():
            level = 100 if o["pct"] >= 100 else 80 if o["pct"] >= 80 else 0
            key = f"orc:{o['categoria']}:{_ym(today)}:{level}"
            if level and key not in sent:
                sent[key] = today.isoformat()
                out.append(f"Senhor, o orçamento de {o['categoria']} chegou a {o['pct']}%: {money(o['gasto'])} de {money(o['limite'])}.")
        cutoff = (today - timedelta(days=60)).isoformat()
        data["avisos"] = {k: v for k, v in sent.items() if v >= cutoff}
        _save(data)
    return out


# --------------------------------------------------------------------------- ações do agente
ACTIONS = ("divida_add", "divida_pagar", "divida_quitar", "divida_editar", "divida_remover", "conta_add", "conta_pagar",
           "conta_remover", "cartao_add", "cartao_compra", "fatura_pagar", "orcamento_set", "meta_add", "meta_guardar", "plano")
ALWAYS_CONFIRM = {"divida_quitar", "divida_editar", "divida_remover", "conta_remover"}


def _s(v, n: int) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def clean_action(a: dict) -> Optional[dict]:
    t = a.get("tipo") if isinstance(a, dict) else None
    if t not in ACTIONS:
        return None
    nome = _s(a.get("nome") or a.get("credor") or a.get("cartao") or a.get("categoria"), 60)
    valor = _num(a.get("valor"))
    if t == "divida_add":
        saldo = _num(a.get("saldo")) or valor
        if not nome or not saldo or saldo <= 0:
            return None
        return {"tipo": t, "nome": nome, "saldo": round(saldo, 2), "parcela": round(_num(a.get("parcela")) or 0, 2),
                "total_parcelas": int(_num(a.get("total_parcelas")) or 0), "pagas": int(_num(a.get("pagas")) or 0),
                "juros_mes": round(_num(a.get("juros_mes")) or 0, 3), "dia": int(min(31, max(1, _num(a.get("dia")) or 10))),
                "descricao": _s(a.get("descricao"), 80)}
    if t in ("divida_pagar", "conta_pagar"):
        return {"tipo": t, "nome": nome, "valor": round(valor, 2) if valor and valor > 0 else None} if nome else None
    if t in ("divida_quitar", "divida_remover", "conta_remover", "fatura_pagar"):
        return {"tipo": t, "nome": nome} if (nome or t == "fatura_pagar") else None
    if t == "divida_editar":
        fields = {k: _num(a.get(k)) for k in ("saldo", "parcela", "juros_mes", "total_parcelas", "pagas", "dia") if _num(a.get(k)) is not None}
        return {"tipo": t, "nome": nome, **fields} if nome and fields else None
    if t == "conta_add":
        dia = _num(a.get("dia"))
        return {"tipo": t, "nome": nome, "valor": round(valor, 2), "dia": int(min(31, max(1, dia))),
                "categoria": _s(a.get("categoria"), 30) or "Contas"} if nome and valor and dia else None
    if t == "cartao_add":
        f, v = _num(a.get("fechamento")), _num(a.get("vencimento"))
        return {"tipo": t, "nome": nome, "fechamento": int(f), "vencimento": int(v), "limite": round(_num(a.get("limite")) or 0, 2)} \
            if nome and f and v and 1 <= f <= 31 and 1 <= v <= 31 else None
    if t == "cartao_compra":
        return {"tipo": t, "nome": _s(a.get("cartao") or a.get("nome"), 40), "valor": round(valor, 2),
                "descricao": _s(a.get("descricao"), 80), "parcelas": int(min(48, max(1, _num(a.get("parcelas")) or 1)))} \
            if valor and valor > 0 else None
    if t == "orcamento_set":
        return {"tipo": t, "nome": nome, "valor": round(valor, 2)} if nome and valor and valor > 0 else None
    if t == "meta_add":
        return {"tipo": t, "nome": nome, "valor": round(valor, 2), "prazo": _s(a.get("prazo"), 10)} if nome and valor else None
    if t == "meta_guardar":
        return {"tipo": t, "nome": nome, "valor": round(valor, 2)} if nome and valor else None
    if t == "plano":
        return {"tipo": t, "valor": round(valor or 0, 2)}
    return None


def needs_confirm(a: dict) -> bool:
    return a["tipo"] in ALWAYS_CONFIRM or (a.get("valor") or 0) > BIG_VALUE and a["tipo"] in (
        "divida_pagar", "conta_pagar", "cartao_compra", "meta_guardar")


def describe(a: dict) -> str:
    t, n = a["tipo"], a.get("nome", "")
    v = money(a["valor"]) if a.get("valor") else ""
    return {
        "divida_add": lambda: f"Cadastrar dívida: {n}, saldo {money(a['saldo'])}" + (f", parcela {money(a['parcela'])}" if a["parcela"] else "")
        + (f" ({a['pagas']} de {a['total_parcelas']})" if a["total_parcelas"] else "") + f", vence dia {a['dia']}",
        "divida_pagar": lambda: f"Pagar {v or 'a parcela'} da dívida {n}",
        "divida_quitar": lambda: f"Quitar a dívida {n}",
        "divida_editar": lambda: f"Alterar a dívida {n}: " + ", ".join(f"{k} = {a[k]}" for k in a if k not in ("tipo", "nome")),
        "divida_remover": lambda: f"Apagar a dívida {n}",
        "conta_add": lambda: f"Cadastrar conta fixa: {n}, {v}, vence dia {a['dia']}",
        "conta_pagar": lambda: f"Marcar como paga a conta {n}" + (f" ({v})" if v else ""),
        "conta_remover": lambda: f"Apagar a conta fixa {n}",
        "cartao_add": lambda: f"Cadastrar cartão {n}: fecha dia {a['fechamento']}, vence dia {a['vencimento']}",
        "cartao_compra": lambda: f"Compra no cartão {n or ''}: {v}" + (f" em {a['parcelas']}x" if a["parcelas"] > 1 else "")
        + (f" ({a['descricao']})" if a["descricao"] else ""),
        "fatura_pagar": lambda: f"Marcar como paga a fatura do cartão {n}".strip(),
        "orcamento_set": lambda: f"Orçamento de {n}: {v} por mês",
        "meta_add": lambda: f"Nova meta: {n}, {v}",
        "meta_guardar": lambda: f"Guardar {v} na meta {n}",
        "plano": lambda: "Montar o plano para quitar as dívidas" + (f" com {v} a mais por mês" if v else ""),
    }[t]()


def run(a: dict) -> str:
    t = a["tipo"]
    if t == "divida_add":
        d = divida_add(a["nome"], a["saldo"], a["parcela"], a["total_parcelas"], a["pagas"], a["juros_mes"], a["dia"], a["descricao"])
        return f"✓ Dívida cadastrada: {d['nome']} ({money(d['saldo'])})"
    if t == "divida_pagar":
        d = divida_pagar(a["nome"], a.get("valor"))
        tail = "QUITADA! 🎉" if d["quitada"] else f"saldo agora {money(d['saldo'])}" + (
            f" ({d['pagas']} de {d['total_parcelas']})" if d["total_parcelas"] else "")
        return f"✓ Pagamento na dívida {d['nome']}: {tail}"
    if t == "divida_quitar":
        return f"✓ Dívida {divida_quitar(a['nome'])['nome']} QUITADA 🎉"
    if t == "divida_editar":
        d = divida_editar(a["nome"], **{k: v for k, v in a.items() if k not in ("tipo", "nome")})
        return f"✓ Dívida {d['nome']} atualizada"
    if t in ("divida_remover", "conta_remover"):
        return f"✓ Apagado: {remover('divida' if t == 'divida_remover' else 'conta', a['nome'])}"
    if t == "conta_add":
        c = conta_add(a["nome"], a["valor"], a["dia"], a["categoria"])
        return f"✓ Conta fixa cadastrada: {c['nome']} ({money(c['valor'])}, dia {c['dia']})"
    if t == "conta_pagar":
        c = conta_pagar(a["nome"], a.get("valor"))
        return f"✓ Conta {c['nome']} paga neste mês"
    if t == "cartao_add":
        k = cartao_add(a["nome"], a["fechamento"], a["vencimento"], a["limite"])
        return f"✓ Cartão {k['nome']} cadastrado"
    if t == "cartao_compra":
        c = cartao_compra(a["nome"], a["valor"], a["descricao"], a["parcelas"])
        return f"✓ Compra no {c['cartao']}: {money(c['valor'])}" + (f" em {c['parcelas']}x" if c["parcelas"] > 1 else "") + \
            f" (1ª fatura {c['primeira'][8:10]}/{c['primeira'][5:7]})"
    if t == "fatura_pagar":
        f = fatura_pagar(a.get("nome", ""))
        return f"✓ Fatura {f['cartao']} de {f['vencimento'][8:10]}/{f['vencimento'][5:7]} paga ({money(f['valor'])})"
    if t == "orcamento_set":
        orcamento_set(a["nome"], a["valor"])
        return f"✓ Orçamento de {a['nome']}: {money(a['valor'])} por mês"
    if t == "meta_add":
        m = meta_add(a["nome"], a["valor"], a.get("prazo", ""))
        return f"✓ Meta criada: {m['nome']} ({money(m['alvo'])})"
    if t == "meta_guardar":
        m = meta_guardar(a["nome"], a["valor"])
        return f"✓ Guardado na meta {m['nome']}: {money(m['guardado'])} de {money(m['alvo'])}"
    if t == "plano":
        p = plano(a.get("valor") or 0)
        return plano_texto(p)
    raise ValueError("Ação desconhecida.")


def plano_texto(p: dict) -> str:
    if not p.get("tem_dividas"):
        return "Nenhuma dívida em aberto. 🎉"

    def line(name, r):
        return f"{name}: {r['meses']} meses, {money(r['juros'])} de juros" + (" (não quita em 50 anos com esse valor)" if not r["completo"] else "")
    best = "maior juros primeiro" if p["recomendado"] == "avalanche" else "menor dívida primeiro"
    order = p[p["recomendado"]]["foco"]
    return (f"📊 Plano ({money(p['orcamento_mensal'])}/mês"
            + (f", com {money(p['extra'])} a mais" if p["extra"] else "") + f"): {line('Menor dívida primeiro', p['bola_de_neve'])}. "
            f"{line('Maior juros primeiro', p['avalanche'])}. Recomendo: {best}. {p['motivo']}"
            + (f" Ordem de ataque (o valor extra vai para a primeira): {' → '.join(order)}." if order else ""))


# --------------------------------------------------------------------------- avisos automáticos e nuvem
async def alerts_loop(interval: float = 900) -> None:
    """De 8h às 22h, a cada 15 min: avisos de vencimento (3 dias antes e no dia) e de orçamento."""
    import asyncio
    import logging

    from core import speech

    log = logging.getLogger("jarvis.fin_control")
    await asyncio.sleep(30)
    while True:
        try:
            if 8 <= datetime.now().hour < 22:
                for text in await asyncio.to_thread(due_alerts):
                    await speech.announce(text)
        except Exception:  # noqa: BLE001 - um aviso ruim não para os próximos
            log.exception("Avisos financeiros falharam")
        await asyncio.sleep(interval)


def cloud_summary() -> dict:
    """O que vai para a nuvem (escolha do Patrick: anotar e ver o RESUMO; os detalhes ficam só no PC)."""
    r = resumo()
    return {
        "total_devido": r["total_devido"], "parcelas_mes": r["parcelas_mes"], "a_pagar_mes": r["a_pagar_mes"],
        "pago_mes": r["pago_mes"], "atrasados": len(r["atrasados"]),
        "proximos": [{k: v[k] for k in ("tipo", "nome", "valor", "data", "atrasada")} for v in r["proximos"][:8]],
        "orcamento": [{k: o[k] for k in ("categoria", "pct")} for o in r["orcamento"]],
        "metas": [{"nome": m["nome"], "pct": m["pct"]} for m in r["metas"]],
        # só os NOMES, para "paguei a parcela do carro" funcionar fora de casa
        "dividas": [d["nome"] for d in r["dividas"] if not d["quitada"]],
        "contas": [c["nome"] for c in r["contas"]],
        "cartoes": [k["nome"] for k in r["cartoes"]],
    }

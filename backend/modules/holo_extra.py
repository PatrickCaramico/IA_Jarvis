"""V7.14: HOLOGRAMA, parte 2 da ideia 5.

- perguntar no meio da apresentação ("espera, o que é horizonte de eventos?"): resposta curta, no contexto da cena;
- quiz no final: 3 perguntas de múltipla escolha sobre o que foi mostrado;
- salvar e rever: até 30 apresentações/receitas guardadas no PC (rever não gasta IA); vão para a nuvem na sincronização;
- cartão animado para perguntas rápidas ("quanto está o dólar?", "quem ganhou o jogo?").
"""
from __future__ import annotations

import json
import re
import threading
import time
import uuid

from config import settings
from modules.holo import _loads, _number, _short

_PATH = settings.DATA_DIR / "holo_salvos.json"
_lock = threading.RLock()
MAX_SAVED = 30
_GUARD = "Responda em português do Brasil, como o J.A.R.V.I.S., tratando o usuário por senhor. Não invente dados: sem certeza, diga."


# --------------------------------------------------------------------------- perguntar no meio
def ask_prompt(titulo: str, cena: str, pergunta: str) -> str:
    return (
        f'Você está apresentando um holograma sobre "{_short(titulo, 80)}". A cena atual diz: "{_short(cena, 400)}".\n'
        f'O usuário interrompeu e perguntou: "{_short(pergunta, 240)}".\n'
        f"{_GUARD} Responda em 1 a 3 frases curtas (vai ser falado) e termine pronto para continuar a apresentação. "
        "Só o texto da resposta, sem listas."
    )


def parse_ask(raw: str) -> str:
    text = re.sub(r"\s+", " ", str(raw or "")).strip().strip('"')
    if not text:
        raise ValueError("A IA não respondeu.")
    return text[:500]


# --------------------------------------------------------------------------- quiz
def quiz_prompt(titulo: str, falas: list[str]) -> str:
    resumo = " ".join(_short(f, 400) for f in falas[:7])
    return (
        f'Crie um QUIZ de 3 perguntas sobre a apresentação "{_short(titulo, 80)}", usando SÓ o que foi dito nela:\n'
        f'"{resumo[:2400]}"\n'
        "Responda SOMENTE com um JSON: "
        '{"perguntas": [{"pergunta": "curta", "opcoes": ["A", "B", "C", "D"], "certa": 0, '
        '"explicacao": "1 frase dizendo por quê"}]}. '
        "4 opções por pergunta, uma certa (índice 0 a 3, varie a posição), as erradas plausíveis. Português do Brasil."
    )


def parse_quiz(raw: str) -> list[dict]:
    data = _loads(raw)
    out = []
    for q in (data or {}).get("perguntas") or []:
        if not isinstance(q, dict):
            continue
        opts = [_short(o, 90) for o in q.get("opcoes") or [] if isinstance(o, (str, int, float)) and _short(o, 90)]
        certa = _number(q.get("certa"))
        if len(opts) != 4 or certa is None or not 0 <= int(certa) <= 3 or not _short(q.get("pergunta"), 200):
            continue
        out.append({"pergunta": _short(q.get("pergunta"), 200), "opcoes": opts, "certa": int(certa),
                    "explicacao": _short(q.get("explicacao"), 240)})
    if not out:
        raise ValueError("O quiz veio vazio.")
    return out[:3]


# --------------------------------------------------------------------------- salvar e rever
def _load() -> list[dict]:
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8")) if _PATH.exists() else []
    except (OSError, ValueError):
        data = []
    return [d for d in data if isinstance(d, dict) and d.get("id") and isinstance(d.get("data"), dict)]


def _save(items: list[dict]) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(items[:MAX_SAVED], ensure_ascii=False), encoding="utf-8")


def _valid(data: dict) -> dict:
    """Confere de novo (o que chega do aparelho passa pelo mesmo filtro da IA) antes de guardar."""
    from modules import holo

    if not isinstance(data, dict) or data.get("tipo") not in holo.KINDS:
        raise ValueError("Apresentação inválida.")
    return holo.parse(json.dumps(data), data["tipo"])


def save(data: dict, query: str = "", item_id: str | None = None) -> dict:
    clean = _valid(data)
    with _lock:
        items = _load()
        same = next((i for i in items if i["titulo"] == clean["titulo"]), None)  # salvar de novo não duplica
        item = {"id": item_id or (same["id"] if same else uuid.uuid4().hex[:12]), "titulo": clean["titulo"], "tipo": clean["tipo"],
                "pergunta": _short(query, 240), "salvo_em": time.strftime("%Y-%m-%d %H:%M"), "data": clean}
        items = [i for i in items if i["id"] != item["id"] and i["titulo"] != item["titulo"]]
        items.insert(0, item)
        _save(items)
        return {k: v for k, v in item.items() if k != "data"}


def listing() -> list[dict]:
    return [{k: v for k, v in i.items() if k != "data"} for i in _load()]


def get(item_id: str) -> dict | None:
    return next((i for i in _load() if i["id"] == item_id), None)


def delete(item_id: str) -> bool:
    with _lock:
        items = _load()
        rest = [i for i in items if i["id"] != item_id]
        if len(rest) == len(items):
            return False
        _save(rest)
        return True


def cloud_list(limit: int = 20) -> list[dict]:
    """O que vai para a nuvem: as mais recentes, completas (para rever no celular sem gastar IA)."""
    return _load()[:limit]


# --------------------------------------------------------------------------- cartão rápido
_QUICK = re.compile(
    r"\b(quanto (esta|está|custa|vale|mede|pesa)|qual (e|é|a|o) (altura|tamanho|populacao|população|capital|distancia|distância|"
    r"cotacao|cotação|temperatura|idade)|quem ganhou|quem venceu|placar|resultado do jogo|cotacao|cotação|"
    r"(dolar|dólar|euro|bitcoin) (hoje|agora)|quantos (habitantes|anos|metros|km|quilometros))\b", re.I)
CURRENCY = {"dolar": "USD", "dólar": "USD", "euro": "EUR", "bitcoin": "BTC", "libra": "GBP"}


def is_quick(question: str) -> bool:
    q = question or ""
    return len(q.split()) <= 14 and bool(_QUICK.search(q) or any(c in q.lower() for c in CURRENCY))


def currency_of(question: str) -> str | None:
    q = (question or "").lower()
    return next((code for word, code in CURRENCY.items() if re.search(rf"\b{word}\b", q)), None)


def currency_card(code: str) -> dict:
    """Cotação com a série dos últimos dias (AwesomeAPI, pública)."""
    from services import http_client

    data = http_client.get_json(f"https://economia.awesomeapi.com.br/json/daily/{code}-BRL/7", timeout=8, ttl=600)
    days = [d for d in data if isinstance(d, dict) and _number(d.get("bid")) is not None]
    if not days:
        raise ValueError("sem cotação")
    serie = [{"rotulo": time.strftime("%d/%m", time.localtime(int(_number(d.get("timestamp")) or 0))), "valor": round(_number(d["bid"]), 2)}
             for d in reversed(days)]
    now, first = serie[-1]["valor"], serie[0]["valor"]
    name = {"USD": "Dólar", "EUR": "Euro", "BTC": "Bitcoin", "GBP": "Libra"}[code]
    return {"tipo": "numero", "titulo": f"{name} hoje", "valor": now, "prefixo": "R$", "unidade": "",
            "rotulo": f"{'subiu' if now >= first else 'caiu'} {abs((now - first) / first * 100):.1f}% na semana".replace(".", ","),
            "serie": serie, "fonte": "AwesomeAPI"}


def card_prompt(question: str, answer: str) -> str:
    return (
        f'O usuário perguntou: "{_short(question, 200)}" e o JARVIS respondeu: "{_short(answer, 600)}".\n'
        "Monte um CARTÃO visual pequeno com essa resposta. Responda SOMENTE com um JSON, um destes formatos:\n"
        '{"tipo": "numero", "titulo": "curto", "valor": 8848, "prefixo": "", "unidade": "m", "rotulo": "o que é"}\n'
        '{"tipo": "placar", "titulo": "campeonato", "time1": "Nome", "gols1": 2, "time2": "Nome", "gols2": 1, "rotulo": "quando/onde"}\n'
        '{"tipo": "foto", "titulo": "assunto", "wiki": "título do artigo da Wikipédia", "fato": "1 frase"}\n'
        '{"tipo": "lista", "titulo": "curto", "itens": ["até 5 itens curtos"]}\n'
        'Use SÓ dados que estão na resposta. Se a resposta não tiver dado concreto, responda {"tipo": null}.'
    )


def parse_card(raw: str) -> dict | None:
    try:
        d = _loads(raw)
    except ValueError:
        return None
    if not isinstance(d, dict):
        return None
    t = d.get("tipo")
    titulo = _short(d.get("titulo"), 60)
    if t == "numero":
        v = _number(d.get("valor"))
        return {"tipo": t, "titulo": titulo, "valor": v, "prefixo": _short(d.get("prefixo"), 6), "unidade": _short(d.get("unidade"), 20),
                "rotulo": _short(d.get("rotulo"), 80)} if v is not None else None
    if t == "placar":
        g1, g2 = _number(d.get("gols1")), _number(d.get("gols2"))
        if g1 is None or g2 is None or not _short(d.get("time1"), 30) or not _short(d.get("time2"), 30):
            return None
        return {"tipo": t, "titulo": titulo, "time1": _short(d.get("time1"), 30), "gols1": int(g1), "time2": _short(d.get("time2"), 30),
                "gols2": int(g2), "rotulo": _short(d.get("rotulo"), 80)}
    if t == "foto" and _short(d.get("wiki"), 80):
        return {"tipo": t, "titulo": titulo, "wiki": _short(d.get("wiki"), 80), "fato": _short(d.get("fato"), 200)}
    if t == "lista":
        itens = [_short(i, 80) for i in d.get("itens") or [] if isinstance(i, str) and i.strip()][:5]
        return {"tipo": t, "titulo": titulo, "itens": itens} if itens else None
    return None

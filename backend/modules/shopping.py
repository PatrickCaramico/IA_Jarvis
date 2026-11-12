"""V6.0: lista de compras por voz, com caixinhas no celular e na central.

"Jarvis, coloca leite na lista"             -> adiciona (vários de uma vez: "leite, pão e ovos")
"Jarvis, adiciona café na lista de compras"
"Jarvis, comprei o leite"                   -> marca como comprado
"Jarvis, tira o pão da lista"               -> remove
"Jarvis, o que tem na lista de compras?"    -> lê o que falta comprar
"Jarvis, limpa a lista de compras"          -> apaga o que já foi comprado (ou tudo: "limpa a lista inteira")

Um arquivo por pessoa (modules/profiles.py). As telas recebem o evento "shopping" quando a lista muda.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Optional

from config import settings
from modules.quick_replies import _norm

log = logging.getLogger("jarvis.shopping")
_PATH = settings.DATA_DIR / "compras.json"
MAX_ITEMS = 80

_broadcast = None  # injetado em core/speech.py (avisa as telas)


def configure(broadcast=None) -> None:
    global _broadcast
    _broadcast = broadcast


def _load() -> list[dict]:
    if not _PATH.exists():
        return []
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _save(items: list[dict]) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def list_items() -> list[dict]:
    """Primeiro o que falta comprar (na ordem em que entrou), depois o que já foi comprado."""
    items = _load()
    return sorted(items, key=lambda i: (bool(i.get("comprado")), i.get("id", 0)))


def _clean(text: str) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip(" .,!?;:"))
    return text[:60]


def add(texts: list[str]) -> list[dict]:
    items = _load()
    added = []
    pending_norms = {_norm(i["texto"]) for i in items if not i.get("comprado")}
    for raw in texts:
        text = _clean(raw)
        if not text or _norm(text) in pending_norms:
            continue
        # se já estava comprado, volta para a lista
        again = next((i for i in items if _norm(i["texto"]) == _norm(text)), None)
        if again:
            again["comprado"] = False
            added.append(again)
        else:
            if len(items) >= MAX_ITEMS:
                break
            new = {"id": max((i.get("id", 0) for i in items), default=0) + 1, "texto": text[:1].upper() + text[1:],
                   "comprado": False, "criado_em": datetime.now().strftime("%Y-%m-%d %H:%M")}
            items.append(new)
            added.append(new)
        pending_norms.add(_norm(text))
    _save(items)
    return added


def _find(items: list[dict], text: str) -> Optional[dict]:
    want = _norm(_clean(text))
    if not want:
        return None
    exact = next((i for i in items if _norm(i["texto"]) == want), None)
    return exact or next((i for i in items if want in _norm(i["texto"]) or _norm(i["texto"]) in want), None)


def set_bought(item_id: int, bought: bool = True) -> Optional[dict]:
    items = _load()
    for i in items:
        if i.get("id") == item_id:
            i["comprado"] = bool(bought)
            _save(items)
            return i
    return None


def remove(item_id: int) -> bool:
    items = _load()
    left = [i for i in items if i.get("id") != item_id]
    if len(left) == len(items):
        return False
    _save(left)
    return True


def clear(only_bought: bool = True) -> int:
    items = _load()
    left = [i for i in items if not i.get("comprado")] if only_bought else []
    _save(left)
    return len(items) - len(left)


async def announce() -> None:
    if _broadcast:
        try:
            await _broadcast({"type": "shopping", "items": list_items()})
        except Exception as exc:  # noqa: BLE001
            log.debug("Não consegui avisar as telas da lista: %s", exc)


def _split(text: str) -> list[str]:
    """ "leite, pão e ovos" -> ["leite", "pão", "ovos"] """
    parts = re.split(r",|\s+e\s+", text)
    return [p for p in (_clean(re.sub(r"^(?:o|a|os|as|um|uma|uns|umas|de|do|da)\s+", "", p.strip())) for p in parts) if p]


def _spoken(items: list[dict]) -> str:
    names = [i["texto"].lower() for i in items]
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " e " + names[-1]


async def handle_voice(message: str) -> Optional[str]:
    t = _norm(message)  # sem acento e sem pontuação: para reconhecer o pedido
    t = re.sub(r"^(?:jarvis|ei jarvis)[,\s]+", "", t)
    # o texto original (com acento e vírgula) é de onde saem os nomes dos itens
    low = re.sub(r"^\s*(?:ei\s+)?jarvis[,\s]+", "", (message or "").lower()).strip(" .!?")
    if "lista" not in t and not re.match(r"^(?:ja\s+)?comprei\b", t):
        return None
    if "lista de tarefa" in t:
        return None  # é a lista de tarefas (modules/tasks.py)

    # o que tem na lista?
    if re.search(r"\b(?:o que|oque|que)\s+(?:tem|falta|ta|esta)\b.*\blista\b|\b(?:le|ler|mostra|mostrar|ver)\s+(?:a\s+)?lista de compras\b|^lista de compras\??$", t):
        pending = [i for i in list_items() if not i.get("comprado")]
        if not pending:
            return "A lista de compras está vazia, senhor."
        return f"Na lista de compras: {_spoken(pending)}."

    # limpar
    m = re.search(r"\b(?:limpa|limpe|apaga|apague|zera|zere)\s+(?:a\s+)?lista(?: de compras)?(\s+inteira| toda|\s+tudo)?\b", t)
    if m:
        n = clear(only_bought=not m.group(1))
        await announce()
        return (f"Pronto: tirei {n} {'item' if n == 1 else 'itens'} da lista." if n
                else "Não havia nada comprado para tirar da lista.")

    # comprei X
    m = re.match(r"^(?:j[aá]\s+)?comprei\s+(.+)$", low)
    if m:
        items = _load()
        done = []
        for name in _split(m.group(1)):
            it = _find([i for i in items if not i.get("comprado")], name)
            if it:
                it["comprado"] = True
                done.append(it)
        if not done:
            return None if "lista" not in t else "Não achei isso na lista de compras."
        _save(items)
        await announce()
        return f"Marquei {_spoken(done)} como comprado."

    # tira X da lista
    m = re.search(r"\b(?:tira|tire|remove|remova|apaga|apague)\s+(.+?)\s+da\s+lista(?: de compras)?\b", low)
    if m:
        items = _load()
        gone = []
        for name in _split(m.group(1)):
            it = _find(items, name)
            if it:
                items = [i for i in items if i is not it]
                gone.append(it)
        if not gone:
            return "Não achei isso na lista de compras."
        _save(items)
        await announce()
        return f"Tirei {_spoken(gone)} da lista."

    # coloca X na lista (de compras)
    m = re.search(r"\b(?:coloca|coloque|bota|bote|p[oõ]e|ponha|adiciona|adicione|inclui|inclua|anota|anote)\s+(.+?)\s+(?:na|à|a)\s+lista(?: de compras| do mercado)?\s*$", low) \
        or re.search(r"^lista de compras[:,]?\s+(.+)$", low)
    if m:
        names = _split(m.group(1))
        if not names:
            return None
        added = add(names)
        await announce()
        if not added:
            return f"{_spoken([{'texto': n} for n in names]).capitalize()} já está na lista."
        return f"Coloquei {_spoken(added)} na lista de compras."
    return None

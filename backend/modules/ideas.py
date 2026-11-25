"""V9.5.6: BLOCO DE IDEIAS — rascunhos de ideias e projetos (CONTROLES › 💡 BLOCO DE IDEIAS e por voz).

Cada ideia tem título, texto e se é um projeto em andamento (os projetos entram no briefing do dia: "seus projetos").
Fica em data/ideias.json (safe_io: gravação atômica, sobrevive a queda de energia). Puro, testado em
tests/test_ideias_956.py.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from config import settings
from core import safe_io

log = logging.getLogger("jarvis.ideas")

_PATH = settings.DATA_DIR / "ideias.json"
MAX_IDEAS = 300
MAX_TITLE = 80
MAX_TEXT = 4000


def _load() -> list[dict]:
    try:
        data = safe_io.read_json(_PATH)
    except FileNotFoundError:
        return []
    except (OSError, ValueError):
        log.exception("Não consegui ler o bloco de ideias")
        return []
    return data if isinstance(data, list) else []


def _save(items: list[dict]) -> None:
    safe_io.write_json(_PATH, items[-MAX_IDEAS:])


def _clean_title(title: str, text: str) -> str:
    t = " ".join(str(title or "").split())[:MAX_TITLE]
    if t:
        return t
    first = " ".join(str(text or "").split())
    return (first[:MAX_TITLE - 1] + "…") if len(first) > MAX_TITLE else (first or "Ideia sem título")


def list_ideas() -> list[dict]:
    """Da mais recente para a mais antiga (fixadas primeiro)."""
    items = _load()
    return sorted(items, key=lambda i: (not i.get("projeto"), -float(i.get("atualizado") or 0)))


def add_idea(text: str, title: str = "", project: bool = False, now: Optional[float] = None) -> dict:
    text = str(text or "").strip()[:MAX_TEXT]
    if not text and not str(title or "").strip():
        raise ValueError("A ideia está vazia.")
    items = _load()
    stamp = now if now is not None else time.time()
    idea = {
        "id": (max((int(i.get("id") or 0) for i in items), default=0)) + 1,
        "titulo": _clean_title(title, text),
        "texto": text,
        "projeto": bool(project),
        "criado": stamp,
        "atualizado": stamp,
    }
    items.append(idea)
    _save(items)
    return idea


def update_idea(idea_id: int, *, text: Optional[str] = None, title: Optional[str] = None, project: Optional[bool] = None,
                now: Optional[float] = None) -> Optional[dict]:
    items = _load()
    idea = next((i for i in items if i.get("id") == idea_id), None)
    if idea is None:
        return None
    if text is not None:
        idea["texto"] = str(text).strip()[:MAX_TEXT]
    if title is not None:
        idea["titulo"] = _clean_title(title, idea.get("texto", ""))
    if project is not None:
        idea["projeto"] = bool(project)
    idea["atualizado"] = now if now is not None else time.time()
    _save(items)
    return idea


def delete_idea(idea_id: int) -> bool:
    items = _load()
    kept = [i for i in items if i.get("id") != idea_id]
    if len(kept) == len(items):
        return False
    _save(kept)
    return True


def projects(limit: int = 5) -> list[dict]:
    """Os projetos em andamento (para o briefing); sem projetos marcados, as ideias mais recentes."""
    items = list_ideas()
    marked = [i for i in items if i.get("projeto")]
    return (marked or items)[:limit]


def briefing_speech(items: list[dict]) -> str:
    """A fala do briefing: os títulos dos projetos, curta."""
    if not items:
        return ""
    titles = [i.get("titulo") or "sem título" for i in items]
    if len(titles) == 1:
        return f"No seu bloco de ideias, o projeto do momento é {titles[0]}."
    lista = ", ".join(titles[:-1]) + f" e {titles[-1]}"
    return f"No seu bloco de ideias, {len(titles)} projetos em andamento: {lista}."

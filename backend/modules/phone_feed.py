"""V6.5.4: a fila de avisos do celular fica em disco.

Antes ficava só na memória: cada reinício do JARVIS (toda atualização publicada reinicia) apagava os
avisos que o celular ainda não tinha buscado — e as notícias já marcadas como avisadas nunca chegavam.
"""
from __future__ import annotations

import json
import logging

from config import settings

log = logging.getLogger("jarvis.phone_feed")

_PATH = settings.DATA_DIR / "avisos_celular.json"
KEEP = 50


def load() -> list[dict]:
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8"))
        return [d for d in data if isinstance(d, dict) and isinstance(d.get("id"), int)][-KEEP:]
    except (OSError, ValueError, TypeError):
        return []


def save(items) -> None:
    try:
        _PATH.parent.mkdir(parents=True, exist_ok=True)
        _PATH.write_text(json.dumps(list(items)[-KEEP:], ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        log.warning("Não consegui guardar os avisos do celular: %s", exc)

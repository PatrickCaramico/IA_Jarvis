"""V6.0: entrar com a digital no app do celular.

Depois de entrar uma vez pelo PIN no app, o celular pode pedir uma "chave do aparelho" (256 bits
aleatórios). O PC guarda só o hash dela (SHA-256) em data/chaves_aparelho.json; o app guarda a chave e só
a usa depois que a digital (ou o rosto) do próprio Android confirma quem é. A chave libera a central como o
PIN libera (método "device"), vale só para o perfil principal e pode ser revogada.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import threading
from datetime import datetime
from typing import Optional

from config import settings

log = logging.getLogger("jarvis.device_keys")
_PATH = settings.DATA_DIR / "chaves_aparelho.json"
MAX_KEYS = 5
_lock = threading.Lock()


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


def _hash(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def enroll(name: str = "Celular") -> dict:
    """Cria a chave de um aparelho. Devolve {id, secret} (o segredo só sai aqui, uma vez)."""
    secret = secrets.token_urlsafe(32)
    with _lock:
        items = _load()
        name = (name or "Celular").strip()[:40] or "Celular"
        items = [i for i in items if i.get("name") != name]  # o mesmo aparelho troca a chave
        items.append({
            "id": secrets.token_hex(4),
            "name": name,
            "hash": _hash(secret),
            "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "last_used": None,
        })
        items = items[-MAX_KEYS:]
        _save(items)
        new_id = items[-1]["id"]
    return {"id": new_id, "secret": secret}


def verify(secret: str) -> Optional[dict]:
    """A chave confere? Devolve o registro (sem o hash) ou None."""
    if not secret or len(secret) > 200:
        return None
    digest = _hash(secret)
    with _lock:
        items = _load()
        for item in items:
            if hmac.compare_digest(item.get("hash", ""), digest):
                item["last_used"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                _save(items)
                return {k: v for k, v in item.items() if k != "hash"}
    return None


def list_keys() -> list[dict]:
    return [{k: v for k, v in i.items() if k != "hash"} for i in _load()]


def revoke(key_id: Optional[str] = None) -> int:
    with _lock:
        items = _load()
        left = [i for i in items if key_id is not None and i.get("id") != key_id]
        _save(left)
        return len(items) - len(left)

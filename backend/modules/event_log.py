"""Histórico local de comandos, eventos e erros do JARVIS."""
from datetime import datetime

from config import settings
from core import safe_io

_PATH = settings.DATA_DIR / "eventos.json"


def add(kind: str, message: str, detail: str = "") -> None:
    try:
        events = safe_io.read_json(_PATH) if _PATH.exists() else []  # V8.11: cache + gravação atômica
        if not isinstance(events, list):
            events = []
        events.append({"kind": kind, "message": message, "detail": detail, "at": datetime.now().isoformat(timespec="seconds")})
        safe_io.write_json(_PATH, events[-200:])
    except (OSError, ValueError):
        pass


def list_events(limit: int = 50) -> list[dict]:
    if not _PATH.exists():
        return []
    try:
        data = safe_io.read_json(_PATH)
        return list(reversed(data[-max(1, min(limit, 200)):]))
    except (OSError, ValueError):
        return []

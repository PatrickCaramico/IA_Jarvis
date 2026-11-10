"""Histórico local de comandos, eventos e erros do JARVIS."""
import json
from datetime import datetime

from config import settings

_PATH = settings.DATA_DIR / "eventos.json"


def add(kind: str, message: str, detail: str = "") -> None:
    try:
        events = json.loads(_PATH.read_text(encoding="utf-8")) if _PATH.exists() else []
        events.append({"kind": kind, "message": message, "detail": detail, "at": datetime.now().isoformat(timespec="seconds")})
        _PATH.write_text(json.dumps(events[-200:], ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, ValueError):
        pass


def list_events(limit: int = 50) -> list[dict]:
    if not _PATH.exists():
        return []
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8"))
        return list(reversed(data[-max(1, min(limit, 200)):]))
    except (OSError, ValueError):
        return []

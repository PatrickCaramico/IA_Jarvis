"""Registro de tentativas de acesso da tela de bloqueio (seção 17.2).

- data/lock_log.json guarda as últimas 200 entradas: horário, método (face, pin, clap,
  wake, guest), resultado (ok, fail, locked_out, enter, exit) e similaridade, se houver.
- Nunca guarda imagens. A única exceção é opcional e fica desligada por padrão
  (`lock_save_failed_photo`): uma miniatura do rosto não reconhecido em data/intruders/,
  com no máximo 20 arquivos e exclusão automática após 30 dias.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from config import settings

log = logging.getLogger("jarvis.lock_log")

LOG_PATH: Path = settings.DATA_DIR / "lock_log.json"
INTRUDERS_DIR: Path = settings.DATA_DIR / "intruders"
MAX_ENTRIES = 200
MAX_INTRUDER_FILES = 20
INTRUDER_MAX_AGE_S = 30 * 24 * 3600

METHODS = {"face", "pin", "clap", "wake", "guest", "auto", "voice"}
RESULTS = {"ok", "fail", "locked_out", "enter", "exit", "lock"}

_io_lock = threading.Lock()


def _load() -> list[dict[str, Any]]:
    if not LOG_PATH.exists():
        return []
    try:
        data = json.loads(LOG_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _save(entries: list[dict[str, Any]]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(json.dumps(entries[-MAX_ENTRIES:], ensure_ascii=False, indent=2), encoding="utf-8")


def add(method: str, result: str, score: Optional[float] = None, mode: Optional[str] = None) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "at": datetime.now().isoformat(timespec="seconds"),
        "method": method if method in METHODS else "face",
        "result": result if result in RESULTS else "fail",
    }
    if score is not None and score >= 0:
        entry["score"] = round(float(score), 3)
    if mode:
        entry["mode"] = mode
    with _io_lock:
        entries = _load()
        entries.append(entry)
        _save(entries)
    return entry


def failures_before_last_success() -> int:
    """Quantas falhas houve entre o penúltimo e o último acesso bem-sucedido.

    Chamado logo depois de registrar um sucesso: responde "houve N tentativas não
    reconhecidas desde o último acesso".
    """
    entries = _load()
    if not entries:
        return 0
    idx = len(entries) - 1
    if entries[idx].get("result") == "ok":
        idx -= 1
    count = 0
    while idx >= 0:
        e = entries[idx]
        if e.get("result") == "ok":
            break
        if e.get("result") in {"fail", "locked_out"}:
            count += 1
        idx -= 1
    return count


def list_entries(limit: int = 50) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), MAX_ENTRIES))
    return list(reversed(_load()[-limit:]))


def clear() -> None:
    with _io_lock:
        _save([])


# ------------------------------------------------------------------ miniatura opcional
def prune_intruders(now: Optional[float] = None) -> int:
    now = time.time() if now is None else now
    if not INTRUDERS_DIR.exists():
        return 0
    removed = 0
    files = sorted(INTRUDERS_DIR.glob("*.jpg"), key=lambda p: p.stat().st_mtime)
    for f in files:
        if now - f.stat().st_mtime > INTRUDER_MAX_AGE_S:
            f.unlink(missing_ok=True)
            removed += 1
    files = sorted(INTRUDERS_DIR.glob("*.jpg"), key=lambda p: p.stat().st_mtime)
    while len(files) > MAX_INTRUDER_FILES:
        files.pop(0).unlink(missing_ok=True)
        removed += 1
    return removed


def save_intruder(jpeg_bytes: bytes) -> Optional[Path]:
    """Salva a miniatura (já reduzida pelo chamador) e aplica os limites."""
    if not jpeg_bytes:
        return None
    try:
        INTRUDERS_DIR.mkdir(parents=True, exist_ok=True)
        path = INTRUDERS_DIR / f"tentativa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        path.write_bytes(jpeg_bytes)
        prune_intruders()
        return path
    except OSError:
        log.warning("Não consegui salvar a miniatura da tentativa.")
        return None


def clear_intruders() -> int:
    if not INTRUDERS_DIR.exists():
        return 0
    n = 0
    for f in INTRUDERS_DIR.glob("*.jpg"):
        f.unlink(missing_ok=True)
        n += 1
    return n

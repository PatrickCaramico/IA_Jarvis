"""PIN de reserva da tela de bloqueio (seção 17.1).

- Guarda em data/lock_pin.json apenas o hash scrypt com sal (nunca o PIN).
- Compara com hmac.compare_digest.
- 5 erros seguidos bloqueiam por 5 min; cada novo bloqueio dobra o tempo, até 30 min.
  O estado de bloqueio fica no arquivo, então sobrevive a reinícios.
- Nada aqui registra o PIN em log ou em mensagens de erro.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import secrets
import threading
import time
from pathlib import Path
from typing import Any, Optional

from config import settings

log = logging.getLogger("jarvis.lock_pin")

PIN_PATH: Path = settings.DATA_DIR / "lock_pin.json"
MAX_ATTEMPTS = 5
BASE_LOCKOUT_S = 5 * 60
MAX_LOCKOUT_S = 30 * 60
_SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1, "dklen": 32}
_WEAK = {"0000", "1111", "1234", "4321", "1212", "123456", "000000", "111111", "654321", "12345678"}

_io_lock = threading.Lock()


class PinError(ValueError):
    """Erro de validação do PIN (mensagem segura para mostrar ao usuário)."""


def _load() -> dict[str, Any]:
    if not PIN_PATH.exists():
        return {}
    try:
        data = json.loads(PIN_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        log.warning("lock_pin.json ilegível; tratando como sem PIN.")
        return {}


def _save(data: dict[str, Any]) -> None:
    PIN_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = PIN_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(PIN_PATH)


def _hash(pin: str, salt: bytes, params: dict[str, int]) -> bytes:
    return hashlib.scrypt(pin.encode("utf-8"), salt=salt, n=params["n"], r=params["r"], p=params["p"],
                          dklen=params["dklen"], maxmem=64 * 1024 * 1024)


def validate_format(pin: str) -> None:
    if not isinstance(pin, str) or not re.fullmatch(r"\d{4,8}", pin or ""):
        raise PinError("O PIN deve ter de 4 a 8 dígitos numéricos.")


def is_weak(pin: str) -> bool:
    return pin in _WEAK or len(set(pin)) == 1


def has_pin() -> bool:
    data = _load()
    return bool(data.get("hash") and data.get("salt"))


def status(now: Optional[float] = None) -> dict[str, Any]:
    now = time.time() if now is None else now
    data = _load()
    locked_until = float(data.get("locked_until") or 0)
    return {
        "has_pin": bool(data.get("hash")),
        "locked_until": locked_until if locked_until > now else None,
        "remaining_attempts": max(0, MAX_ATTEMPTS - int(data.get("failures", 0))),
    }


def set_pin(new_pin: str, current_pin: Optional[str] = None) -> dict[str, Any]:
    """Cria ou troca o PIN. Trocar exige o PIN atual."""
    validate_format(new_pin)
    with _io_lock:
        data = _load()
        if data.get("hash"):
            if not current_pin or not _check(data, current_pin):
                raise PinError("PIN atual incorreto.")
        salt = secrets.token_bytes(16)
        params = dict(_SCRYPT)
        data = {
            "algo": "scrypt",
            "salt": salt.hex(),
            "params": params,
            "hash": _hash(new_pin, salt, params).hex(),
            "failures": 0,
            "lockouts": 0,
            "locked_until": 0,
            "updated_at": time.time(),
        }
        _save(data)
    return status()


def clear_pin(current_pin: str) -> dict[str, Any]:
    with _io_lock:
        data = _load()
        if not data.get("hash"):
            return status()
        if not _check(data, current_pin):
            raise PinError("PIN atual incorreto.")
        PIN_PATH.unlink(missing_ok=True)
    return status()


def _check(data: dict[str, Any], pin: str) -> bool:
    try:
        salt = bytes.fromhex(data["salt"])
        expected = bytes.fromhex(data["hash"])
        params = {**_SCRYPT, **(data.get("params") or {})}
    except (KeyError, ValueError, TypeError):
        return False
    if not isinstance(pin, str) or not re.fullmatch(r"\d{4,8}", pin or ""):
        return False
    return hmac.compare_digest(_hash(pin, salt, params), expected)


def verify(pin: str, now: Optional[float] = None) -> dict[str, Any]:
    """Confere o PIN aplicando o limite de tentativas. Nunca lança com o PIN na mensagem."""
    now = time.time() if now is None else now
    with _io_lock:
        data = _load()
        if not data.get("hash"):
            return {"verified": False, "reason": "no_pin", "remaining_attempts": 0, "locked_until": None}
        locked_until = float(data.get("locked_until") or 0)
        if locked_until > now:
            return {"verified": False, "reason": "locked_out", "remaining_attempts": 0, "locked_until": locked_until}
        if _check(data, pin):
            data["failures"] = 0
            data["lockouts"] = 0
            data["locked_until"] = 0
            _save(data)
            return {"verified": True, "reason": "ok", "remaining_attempts": MAX_ATTEMPTS, "locked_until": None}
        data["failures"] = int(data.get("failures", 0)) + 1
        result_locked = None
        if data["failures"] >= MAX_ATTEMPTS:
            lockouts = int(data.get("lockouts", 0))
            duration = min(MAX_LOCKOUT_S, BASE_LOCKOUT_S * (2 ** lockouts))
            data["lockouts"] = lockouts + 1
            data["failures"] = 0
            data["locked_until"] = now + duration
            result_locked = data["locked_until"]
        _save(data)
        return {
            "verified": False,
            "reason": "locked_out" if result_locked else "wrong",
            "remaining_attempts": 0 if result_locked else MAX_ATTEMPTS - data["failures"],
            "locked_until": result_locked,
        }

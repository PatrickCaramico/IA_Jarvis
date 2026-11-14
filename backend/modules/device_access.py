"""V7.6: SEGURANÇA. Uma chave por aparelho, aprovação de aparelho novo no PC e bloqueio de tentativas.

Antes: uma chave única (a do QR code) valia para todos os aparelhos e para sempre.
Agora:
- a chave do QR vira a CHAVE DE PAREAMENTO: serve para um aparelho pedir a PRÓPRIA chave (e para o
  pouco que o app Android usa sem a central aberta: avisos, "o PC está no ar?", baixar o app);
- cada aparelho aprovado ganha a sua chave (guardada aqui só como hash) e aparece em
  Configurações > Segurança, de onde pode ser REMOVIDO;
- aparelho novo fica "aguardando aprovação" até alguém tocar PERMITIR na tela do PC;
- migração: nos primeiros MIGRATION_DAYS depois da atualização, os aparelhos que já tinham a chave antiga
  ganham a própria chave sozinhos (sem escanear o QR de novo nem aprovar);
- 5 tentativas com chave errada em 10 min bloqueiam o endereço por 15 min (o tempo dobra a cada vez),
  com aviso por voz no PC, notificação no celular e registro no Diagnóstico.
"""
from __future__ import annotations

import hashlib
import json
import logging
import secrets
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

from config import settings

log = logging.getLogger("jarvis.device_access")

MIGRATION_DAYS = 14
PENDING_TTL = 120  # segundos para aprovar um aparelho novo
FAIL_LIMIT = 5
FAIL_WINDOW = 10 * 60
BLOCK_BASE = 15 * 60
BLOCK_MAX = 24 * 3600
TOUCH_EVERY = 60
EVENT_KEEP = 200

# o que a chave de pareamento (a do QR) ainda pode fazer depois da migração
PAIRING_ROUTES = {
    ("GET", "/api/health"),
    ("GET", "/api/mobile/info"),
    ("GET", "/api/mobile/notifications"),
    ("GET", "/api/mobile/app.apk"),
    ("GET", "/api/mobile/pair"),
    ("POST", "/api/security/claim"),
    ("GET", "/api/security/claim"),
}

_lock = threading.RLock()
_state: Optional[dict] = None
_fails: dict[str, list[float]] = {}
_blocks: dict[str, dict] = {}


_PATH = settings.DATA_DIR / "aparelhos.json"


def _path():
    return _PATH


def _now() -> float:
    return time.time()


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _load() -> dict:
    global _state
    if _state is not None:
        return _state
    data = {}
    try:
        if _path().exists():
            data = json.loads(_path().read_text(encoding="utf-8")) or {}
    except (OSError, ValueError):
        log.warning("aparelhos.json ilegível; começando do zero")
        data = {}
    data.setdefault("devices", {})
    data.setdefault("pending", {})
    data.setdefault("events", [])
    if not data.get("migration_until"):
        data["migration_until"] = (datetime.now() + timedelta(days=MIGRATION_DAYS)).isoformat(timespec="seconds")
    _state = data
    _save()
    return _state


def _save() -> None:
    try:
        _path().write_text(json.dumps(_state, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        log.exception("Não consegui salvar aparelhos.json")


def reset_for_tests() -> None:
    global _state
    with _lock:
        _state = None
        _fails.clear()
        _blocks.clear()
        _last_alert.clear()
        _rate.clear()


def migration_active(now: Optional[datetime] = None) -> bool:
    st = _load()
    try:
        return (now or datetime.now()) < datetime.fromisoformat(st["migration_until"])
    except (ValueError, KeyError):
        return False


def end_migration() -> None:
    with _lock:
        _load()["migration_until"] = datetime.now().isoformat(timespec="seconds")
        _save()


# --------------------------------------------------------------------------- chaves
def pairing_key() -> str:
    from core import runtime

    return runtime.ACCESS_TOKEN


def classify(token: str) -> tuple[str, Optional[dict]]:
    """("device", aparelho) | ("pairing", None) | ("revoked", aparelho) | ("invalid", None) | ("none", None)"""
    if not token:
        return "none", None
    h = _hash(token)
    with _lock:
        for dev in _load()["devices"].values():
            if secrets.compare_digest(dev.get("hash", ""), h):
                return ("revoked", dev) if dev.get("revoked") else ("device", dev)
    if secrets.compare_digest(token, pairing_key()):
        return "pairing", None
    return "invalid", None


def pairing_allowed(method: str, path: str) -> bool:
    path = path.rstrip("/") or "/"
    return migration_active() or (method.upper(), path) in PAIRING_ROUTES


def touch(dev: dict, ip: str) -> None:
    now = _now()
    if now - dev.get("seen_ts", 0) < TOUCH_EVERY and dev.get("ip") == ip:
        return
    with _lock:
        dev["seen_ts"] = now
        dev["last_seen"] = datetime.now().isoformat(timespec="seconds")
        dev["ip"] = ip
        _save()


def _new_device(name: str, kind: str, ip: str) -> tuple[dict, str]:
    token = secrets.token_urlsafe(32)
    dev_id = secrets.token_hex(6)
    dev = {
        "id": dev_id, "name": (name or "Aparelho")[:60], "kind": kind if kind in KINDS else "outro",
        "hash": _hash(token), "created": datetime.now().isoformat(timespec="seconds"),
        "last_seen": datetime.now().isoformat(timespec="seconds"), "seen_ts": _now(), "ip": ip, "revoked": False,
    }
    _load()["devices"][dev_id] = dev
    _save()
    return dev, token


KINDS = {"celular", "tablet", "tv", "pc", "outro"}


def claim(name: str, kind: str, ip: str) -> dict:
    """Pedido de chave própria (feito com a chave de pareamento). Na migração já sai aprovado."""
    with _lock:
        if migration_active():
            dev, token = _new_device(name, kind, ip)
            add_event("info", f"Aparelho conectado (migração automática): {dev['name']}", ip)
            return {"status": "approved", "token": token, "device": public(dev)}
        _expire_pending()
        req_id = secrets.token_hex(6)
        secret = secrets.token_urlsafe(16)
        _load()["pending"][req_id] = {
            "id": req_id, "secret_hash": _hash(secret), "name": (name or "Aparelho")[:60],
            "kind": kind if kind in KINDS else "outro", "ip": ip, "at": _now(), "status": "pending",
        }
        _save()
        add_event("info", f"Aparelho novo pediu para se conectar: {name or 'Aparelho'}", ip)
        return {"status": "pending", "request_id": req_id, "secret": secret, "expires_in": PENDING_TTL}


def claim_status(req_id: str, secret: str) -> dict:
    with _lock:
        _expire_pending()
        req = _load()["pending"].get(req_id)
        if not req or not secrets.compare_digest(req["secret_hash"], _hash(secret or "")):
            return {"status": "unknown"}
        if req["status"] == "approved" and req.get("token"):
            token = req.pop("token")  # entregue uma vez só
            req["status"] = "delivered"
            _save()
            return {"status": "approved", "token": token}
        return {"status": req["status"]}


def _expire_pending() -> None:
    pending = _load()["pending"]
    now = _now()
    changed = False
    for key in list(pending):
        req = pending[key]
        if req["status"] == "pending" and now - req["at"] > PENDING_TTL:
            req["status"] = "expired"
            changed = True
        if now - req["at"] > 3600:
            del pending[key]
            changed = True
    if changed:
        _save()


def pending_requests() -> list[dict]:
    with _lock:
        _expire_pending()
        return [{k: r[k] for k in ("id", "name", "kind", "ip")} | {"seconds_left": max(0, int(PENDING_TTL - (_now() - r["at"])))}
                for r in _load()["pending"].values() if r["status"] == "pending"]


def decide(req_id: str, approve: bool) -> bool:
    with _lock:
        _expire_pending()
        req = _load()["pending"].get(req_id)
        if not req or req["status"] != "pending":
            return False
        if approve:
            dev, token = _new_device(req["name"], req["kind"], req["ip"])
            req["status"] = "approved"
            req["token"] = token
            add_event("info", f"Aparelho aprovado: {dev['name']}", req["ip"])
        else:
            req["status"] = "refused"
            add_event("warn", f"Aparelho recusado: {req['name']}", req["ip"])
        _save()
        return True


def public(dev: dict) -> dict:
    return {k: dev.get(k) for k in ("id", "name", "kind", "created", "last_seen", "ip")}


def list_devices() -> list[dict]:
    with _lock:
        devs = [public(d) for d in _load()["devices"].values() if not d.get("revoked")]
    return sorted(devs, key=lambda d: d.get("last_seen") or "", reverse=True)


def remove(dev_id: str) -> bool:
    with _lock:
        dev = _load()["devices"].get(dev_id)
        if not dev or dev.get("revoked"):
            return False
        dev["revoked"] = True
        add_event("warn", f"Aparelho removido: {dev['name']}", dev.get("ip", ""))
        _save()
        return True


def remove_all() -> int:
    """Desconecta todos os aparelhos e troca a chave de pareamento (QR antigo deixa de valer)."""
    from core import runtime

    with _lock:
        count = 0
        for dev in _load()["devices"].values():
            if not dev.get("revoked"):
                dev["revoked"] = True
                count += 1
        _load()["pending"].clear()
        new_key = secrets.token_urlsafe(32)
        runtime.ACCESS_TOKEN = new_key
        try:
            settings.ACCESS_TOKEN_FILE.write_text(new_key, encoding="utf-8")
        except OSError:
            log.exception("Não consegui salvar a nova chave de pareamento")
        _load()["migration_until"] = datetime.now().isoformat(timespec="seconds")
        add_event("warn", f"Todos os aparelhos desconectados ({count}) e QR code trocado.", "")
        _save()
        return count


# --------------------------------------------------------------------------- limite de uso
_rate: dict[str, float] = {}


def rate_ok(key: str, seconds: float) -> bool:
    """True se a ação `key` pode rodar agora (no máximo 1 vez a cada `seconds`)."""
    now = _now()
    if now - _rate.get(key, 0) < seconds:
        return False
    _rate[key] = now
    return True


# --------------------------------------------------------------------------- tentativas suspeitas
def add_event(level: str, message: str, ip: str = "") -> None:
    with _lock:
        events = _load()["events"]
        events.append({"at": datetime.now().isoformat(timespec="seconds"), "level": level, "message": message, "ip": ip})
        del events[:-EVENT_KEEP]
        _save()


def recent_events(hours: int = 24, levels: tuple = ("warn", "alert")) -> list[dict]:
    since = datetime.now() - timedelta(hours=hours)
    out = []
    for e in reversed(_load()["events"]):
        try:
            if e["level"] in levels and datetime.fromisoformat(e["at"]) >= since:
                out.append(e)
        except (ValueError, KeyError):
            continue
    return out


def blocked_for(ip: str) -> int:
    b = _blocks.get(ip)
    if not b:
        return 0
    left = int(b["until"] - _now())
    return max(0, left)


def record_failure(ip: str, reason: str) -> Optional[int]:
    """Conta uma tentativa errada. Se passou do limite, bloqueia e devolve os segundos de bloqueio."""
    now = _now()
    hits = [t for t in _fails.get(ip, []) if now - t < FAIL_WINDOW] + [now]
    _fails[ip] = hits
    if len(hits) < FAIL_LIMIT:
        return None
    prev = _blocks.get(ip, {}).get("strikes", 0)
    seconds = min(BLOCK_MAX, BLOCK_BASE * (2 ** prev))
    _blocks[ip] = {"until": now + seconds, "strikes": prev + 1}
    _fails[ip] = []
    alert(f"Tentativas suspeitas de acesso ({reason}). O aparelho {ip} foi bloqueado por {seconds // 60} min.", ip)
    return seconds


_last_alert: dict[str, float] = {}
ALERT_DEDUP = 120


def alert(message: str, ip: str = "") -> None:
    """Aviso de segurança: registro, notificação no celular e voz no PC (o mesmo aviso no máximo a cada 2 min)."""
    now = _now()
    if now - _last_alert.get(message, 0) < ALERT_DEDUP:
        return
    _last_alert[message] = now
    add_event("alert", message, ip)
    log.warning("SEGURANÇA: %s", message)
    try:
        from core import runtime, speech

        runtime.notify("security", "Alerta de segurança do JARVIS", message)
        loop = None
        try:
            import asyncio

            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop:
            runtime.track(speech.say_quietly("Senhor, alerta de segurança: houve tentativas suspeitas de acesso ao JARVIS."))
    except Exception:  # noqa: BLE001
        log.debug("Aviso de segurança sem voz/notificação", exc_info=True)

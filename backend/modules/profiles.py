"""V4.5: perfis locais por pessoa (rosto + PIN), guardados só neste PC.

- O perfil principal ("dono") é o de sempre: usa os arquivos da raiz de data/ (nada é migrado).
- Cada pessoa nova ganha data/perfis/<id>/ com os PRÓPRIOS arquivos pessoais: preferências,
  rosto, PIN, memória, tarefas, lembretes, rotina, notas, atalhos, "sobre mim", tokens do Google e
  do Spotify, eventos, água e saúde. Uma pessoa não vê os dados da outra.
- Continuam do PC (comuns): registro de bloqueio, token de acesso, cache do futebol e as chaves de IA.
- Quem entra (rosto ou PIN) vira o perfil ativo; ao bloquear, o PC volta para o perfil principal.
- Criar perfil novo pede o PIN do dono (se o dono tiver PIN) ou a central do dono liberada.

Troca de perfil = apontar os caminhos dos módulos para a pasta da pessoa (os módulos leem os
caminhos a cada chamada). É um PC de uso pessoal: um perfil ativo por vez.
"""
from __future__ import annotations

import importlib
import json
import logging
import re
import threading
import time
import unicodedata
from pathlib import Path
from typing import Any, Optional

from config import settings

log = logging.getLogger("jarvis.profiles")

OWNER_ID = "dono"
REGISTRY_PATH: Path = settings.DATA_DIR / "perfis.json"
PROFILES_DIR: Path = settings.DATA_DIR / "perfis"
MAX_PROFILES = 8

# (módulo, atributo, arquivo): tudo o que é pessoal e muda de pessoa para pessoa
PERSONAL_FILES: tuple[tuple[str, str, str], ...] = (
    ("prefs", "_SETTINGS_PATH", "jarvis_settings.json"),
    ("face", "PHOTO_PATH", "profile.jpg"),
    ("face", "META_PATH", "profile.json"),
    ("lock_pin", "PIN_PATH", "lock_pin.json"),
    ("memory", "_PATH", "memoria.json"),
    ("tasks", "_TASKS_PATH", "tarefas.json"),
    ("reminders", "_REMINDERS_PATH", "lembretes.json"),
    ("alarms", "_PATH", "alarmes.json"),
    ("routine", "DATA_PATH", "rotina.json"),
    ("tools", "_NOTES_PATH", "anotacoes.json"),
    ("tools", "_SHORTCUTS_PATH", "atalhos.json"),
    ("about", "PATH", "sobre_mim.txt"),
    ("google_calendar", "_TOKEN_PATH", "google_calendar_token.json"),
    ("spotify", "_TOKEN_PATH", "spotify_token.json"),
    ("event_log", "_PATH", "eventos.json"),
    ("water", "DATA_FILE", "water_log.json"),
    ("health", "HEALTH_FILE", "health_telemetry.json"),
    ("files", "UNDO_PATH", "organizacao_ultima.json"),
    ("quick_replies", "CUSTOM_PATH", "respostas.json"),
    ("whatsapp", "CONTACTS_PATH", "contatos.json"),  # V4.5
    ("finances", "DATA_PATH", "financas.json"),       # V4.5
    ("shopping", "_PATH", "compras.json"),            # V6.0: lista de compras
    ("wellbeing", "_PATH", "humor.json"),             # V6.7: registro de humor
    ("agents", "_PATH", "lugares.json"),              # V6.8: lugares do agente de rotas
)

_lock = threading.RLock()
_active = OWNER_ID


def _base(profile_id: str) -> Path:
    return settings.DATA_DIR if profile_id == OWNER_ID else PROFILES_DIR / profile_id


def _load() -> dict[str, Any]:
    try:
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("profiles"), dict):
            data["profiles"].setdefault(OWNER_ID, {"name": "", "created": ""})
            return data
    except (OSError, ValueError):
        pass
    return {"profiles": {OWNER_ID: {"name": "", "created": ""}}}


def _save(data: dict[str, Any]) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = REGISTRY_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(REGISTRY_PATH)


def _point_modules_to(profile_id: str) -> None:
    base = _base(profile_id)
    for module_name, attr, filename in PERSONAL_FILES:
        try:
            module = importlib.import_module(f"modules.{module_name}")
        except Exception:  # noqa: BLE001 - módulo opcional (ex.: sem dependência instalada)
            continue
        if hasattr(module, attr):
            setattr(module, attr, base / filename)


def active_id() -> str:
    return _active


def is_owner_active() -> bool:
    return _active == OWNER_ID


def activate(profile_id: str) -> str:
    """Torna `profile_id` o perfil ativo (desconhecido -> dono). Devolve o id ativo."""
    global _active
    with _lock:
        if profile_id not in _load()["profiles"]:
            profile_id = OWNER_ID
        if profile_id != _active:
            _point_modules_to(profile_id)
            _active = profile_id
            log.info("Perfil ativo: %s", profile_id)
        return _active


def activate_owner() -> None:
    activate(OWNER_ID)


def _has(profile_id: str, filename: str) -> bool:
    p = _base(profile_id) / filename
    return p.exists() and p.stat().st_size > 0


def _name(profile_id: str, meta: dict[str, Any]) -> str:
    try:
        n = json.loads((_base(profile_id) / "profile.json").read_text(encoding="utf-8")).get("name", "")
    except (OSError, ValueError):
        n = ""
    return (n or meta.get("name") or ("Principal" if profile_id == OWNER_ID else "Pessoa")).strip()


def list_profiles() -> list[dict[str, Any]]:
    """Todos os perfis (uso interno e da central liberada; não vai para a tela de bloqueio)."""
    out = []
    for pid, meta in _load()["profiles"].items():
        out.append({
            "id": pid,
            "name": _name(pid, meta),
            "is_owner": pid == OWNER_ID,
            "has_photo": _has(pid, "profile.jpg"),
            "has_pin": _has(pid, "lock_pin.json"),
            "created": meta.get("created", ""),
            "active": pid == _active,
        })
    out.sort(key=lambda p: (not p["is_owner"], p["created"]))
    return out


def count() -> int:
    return len(_load()["profiles"])


def face_refs() -> list[tuple[str, Path]]:
    """Fotos de referência de todos os perfis que têm rosto cadastrado."""
    return [(p["id"], _base(p["id"]) / "profile.jpg") for p in list_profiles() if p["has_photo"]]


def pin_paths() -> list[tuple[str, Path]]:
    return [(p["id"], _base(p["id"]) / "lock_pin.json") for p in list_profiles() if p["has_pin"]]


def _slug(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:24] or "pessoa"
    return s


def create(name: str) -> str:
    """Cria a pasta e o registro de um perfil novo. Devolve o id (ainda sem foto nem PIN)."""
    name = (name or "").strip()
    if not name:
        raise ValueError("Diga o nome da pessoa.")
    with _lock:
        data = _load()
        if len(data["profiles"]) >= MAX_PROFILES:
            raise ValueError(f"Limite de {MAX_PROFILES} perfis neste PC.")
        base_id = _slug(name)
        pid, n = base_id, 2
        while pid in data["profiles"] or pid == OWNER_ID:
            pid, n = f"{base_id}-{n}", n + 1
        (PROFILES_DIR / pid).mkdir(parents=True, exist_ok=True)
        data["profiles"][pid] = {"name": name, "created": time.strftime("%Y-%m-%dT%H:%M:%S")}
        _save(data)
        return pid


def delete(profile_id: str) -> None:
    """Remove um perfil (nunca o principal). Apaga a pasta dele."""
    import shutil

    if profile_id == OWNER_ID:
        raise ValueError("O perfil principal não pode ser removido.")
    with _lock:
        data = _load()
        if profile_id not in data["profiles"]:
            raise ValueError("Perfil não encontrado.")
        if _active == profile_id:
            activate_owner()
        data["profiles"].pop(profile_id)
        _save(data)
        folder = PROFILES_DIR / profile_id
        if folder.exists() and folder.resolve().parent == PROFILES_DIR.resolve():
            shutil.rmtree(folder, ignore_errors=True)


def owner_pin_ok(pin: Optional[str]) -> bool:
    """Confere o PIN do dono sem mudar o perfil ativo nem as tentativas de quem estiver ativo."""
    from modules import lock_pin

    owner_pin_path = _base(OWNER_ID) / "lock_pin.json"
    if not owner_pin_path.exists():
        return True  # dono sem PIN: não há o que conferir
    if not pin:
        return False
    with _lock:
        previous = lock_pin.PIN_PATH
        try:
            lock_pin.PIN_PATH = owner_pin_path
            return bool(lock_pin.verify(pin).get("verified"))
        finally:
            lock_pin.PIN_PATH = previous


def match_pin(pin: str) -> Optional[str]:
    """Descobre de quem é o PIN, sem gastar tentativas de ninguém (só leitura)."""
    from modules import lock_pin

    for pid, path in pin_paths():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if float(data.get("locked_until") or 0) > time.time():
            continue
        try:
            if lock_pin._check(data, pin):  # noqa: SLF001 - comparação constante, sem efeito colateral
                return pid
        except Exception:  # noqa: BLE001
            continue
    return None

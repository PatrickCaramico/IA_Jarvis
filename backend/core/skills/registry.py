"""V8.11: catálogo das Skills, com auto-discovery da pasta backend/skills/.

- Cada arquivo (ou pasta com __init__.py) em backend/skills/ que não começa com "_" é importado na primeira
  vez que o catálogo é usado. Um arquivo com erro fica de fora e o motivo aparece em /api/skills (as outras
  skills continuam funcionando).
- Ligar/desligar uma skill: preferência "skills_disabled" (lista de nomes), pela rota /api/skills/{nome}/toggle.
- Disjuntor: 3 falhas seguidas deixam a skill de lado por 5 minutos (ela não trava o JARVIS repetindo o erro).
"""
from __future__ import annotations

import importlib
import logging
import pkgutil
import threading
import time
from dataclasses import dataclass
from typing import Optional

from core.skills import base
from core.skills.base import Skill

log = logging.getLogger("jarvis.skills")

PACKAGE = "skills"
BREAKER_FAILURES = 3
BREAKER_PAUSE_S = 300


@dataclass
class Stats:
    calls: int = 0
    failures: int = 0
    consecutive_failures: int = 0
    paused_until: float = 0.0
    last_ms: int = 0
    last_error: str = ""


_skills: dict[str, Skill] = {}
_stats: dict[str, Stats] = {}
_errors: list[str] = []
_loaded = False
_lock = threading.RLock()


def _import_package_modules(package: str) -> list[str]:
    """Importa os módulos do pacote (ignora os que começam com "_"). Devolve os erros de importação."""
    errors: list[str] = []
    try:
        pkg = importlib.import_module(package)
    except Exception as exc:  # noqa: BLE001
        return [f"{package}: {exc}"]
    for info in pkgutil.iter_modules(getattr(pkg, "__path__", [])):
        if info.name.startswith("_"):
            continue
        full = f"{package}.{info.name}"
        try:
            importlib.import_module(full)
        except Exception as exc:  # noqa: BLE001 - uma skill quebrada não derruba as outras
            log.exception("Skill %s não carregou", full)
            errors.append(f"{full}: {type(exc).__name__}: {exc}")
    return errors


def _collect() -> None:
    """Move as skills declaradas pelo decorador para o catálogo (recusando nomes repetidos)."""
    while base._declared:
        sk = base._declared.pop(0)
        if sk.name in _skills and _skills[sk.name].module != sk.module:
            _errors.append(f"{sk.module}: o nome {sk.name} já é usado por {_skills[sk.name].module}.")
            continue
        _skills[sk.name] = sk
        _stats.setdefault(sk.name, Stats())
    while base._declared_errors:
        _errors.append(base._declared_errors.pop(0))


def load(package: str = PACKAGE, force: bool = False) -> None:
    global _loaded
    with _lock:
        if _loaded and not force:
            return
        _loaded = True
        _errors.extend(_import_package_modules(package))
        _collect()
        if _skills or _errors:
            log.info("Skills carregadas: %s%s", ", ".join(sorted(_skills)) or "nenhuma",
                     f" ({len(_errors)} com erro)" if _errors else "")


def register(sk: Skill) -> None:
    """Registra uma skill montada à mão (testes, ou um módulo do core que quer virar skill)."""
    with _lock:
        _skills[sk.name] = sk
        _stats.setdefault(sk.name, Stats())


def reset_for_tests() -> None:
    global _loaded
    with _lock:
        _skills.clear()
        _stats.clear()
        _errors.clear()
        base._declared.clear()
        base._declared_errors.clear()
        base._services.clear()
        _loaded = True  # testes registram à mão; não importa a pasta real


def errors() -> list[str]:
    load()
    return list(_errors)


def get(name: str) -> Optional[Skill]:
    load()
    return _skills.get(name)


def stats(name: str) -> Stats:
    with _lock:
        return _stats.setdefault(name, Stats())


def _disabled() -> set[str]:
    try:
        from modules import prefs

        return set(prefs.get_all().get("skills_disabled") or [])
    except Exception:  # noqa: BLE001
        return set()


def is_enabled(name: str) -> bool:
    return name not in _disabled()


def set_enabled(name: str, enabled: bool) -> bool:
    if get(name) is None:
        return False
    from modules import prefs

    current = _disabled()
    current.discard(name) if enabled else current.add(name)
    prefs.update(skills_disabled=sorted(current))
    return True


def paused_for(name: str, now: Optional[float] = None) -> int:
    st = stats(name)
    return max(0, int(st.paused_until - (now or time.time())))


def available(public_only: bool = False) -> list[Skill]:
    """Skills ligadas e fora do disjuntor (public_only: só as que valem com a central bloqueada)."""
    load()
    off = _disabled()
    now = time.time()
    return [s for n, s in sorted(_skills.items())
            if n not in off and not paused_for(n, now) and (s.public or not public_only)]


def all_skills() -> list[Skill]:
    load()
    return [s for _, s in sorted(_skills.items())]


def llm_skills() -> list[Skill]:
    return [s for s in available() if s.llm]


def record(name: str, ok: bool, ms: int, error: str = "") -> None:
    with _lock:
        st = _stats.setdefault(name, Stats())
        st.calls += 1
        st.last_ms = ms
        if ok:
            st.consecutive_failures = 0
            return
        st.failures += 1
        st.consecutive_failures += 1
        st.last_error = error[:300]
        if st.consecutive_failures >= BREAKER_FAILURES:
            st.paused_until = time.time() + BREAKER_PAUSE_S
            st.consecutive_failures = 0
            log.warning("Skill %s falhou %d vezes seguidas; fica de lado por %d min.", name, BREAKER_FAILURES,
                        BREAKER_PAUSE_S // 60)


def match(norm: str, message: str, public_only: bool = False) -> Optional[tuple[Skill, dict]]:
    """Caminho rápido (sem IA): a primeira skill cujo gatilho (ou parse) reconhece a frase."""
    for sk in available(public_only=public_only):
        args: Optional[dict] = None
        if sk.parse is not None:
            try:
                args = sk.parse(norm, message)
            except Exception:  # noqa: BLE001
                log.exception("parse da skill %s falhou", sk.name)
                args = None
        else:
            for rx in sk.triggers:
                m = rx.search(norm)
                if m:
                    args = {k: v.strip() for k, v in m.groupdict().items() if v is not None}
                    break
        if args is None:
            continue
        missing = [k for k in sk.params.get("required", []) or [] if k not in args]
        if missing:
            continue  # a frase não trouxe tudo: deixa a IA (ou outra função) cuidar
        return sk, args
    return None


def start_services(track) -> int:
    """Liga as tarefas de fundo declaradas com @service. `track` = runtime.track_service."""
    load()
    started = 0
    while base._services:
        name, fn = base._services.pop(0)
        try:
            track(_guarded(name, fn))
            started += 1
        except Exception:  # noqa: BLE001
            log.exception("Serviço de skill %s não ligou", name)
    return started


async def _guarded(name: str, fn) -> None:
    import asyncio

    delay = 5.0
    while True:
        started = time.monotonic()
        try:
            await fn()
            return  # terminou de propósito
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            log.exception("Serviço de skill %s caiu; religando em %.0f s.", name, delay)
        delay = 5.0 if time.monotonic() - started > 300 else min(300.0, delay * 2)
        await asyncio.sleep(delay)


def catalog() -> list[dict]:
    """Para a tela (Central de Agentes) e para /api/skills."""
    off = _disabled()
    out = []
    for sk in all_skills():
        st = stats(sk.name)
        out.append({**sk.describe(), "enabled": sk.name not in off, "paused_s": paused_for(sk.name),
                    "calls": st.calls, "failures": st.failures, "last_ms": st.last_ms, "last_error": st.last_error})
    return out

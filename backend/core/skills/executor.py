"""V8.11: executa as Skills com as regras do JARVIS (permissão, "sim" nas críticas, prazo, log e disjuntor).

Toda execução passa por aqui, venha do caminho rápido (gatilho), da IA (function calling), da rota de teste
ou de outra skill (ctx.call). A IA nunca contorna estas regras: ela só PEDE a chamada.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from core.skills import registry
from core.skills.base import Permission, Skill, SkillContext, SkillResult

log = logging.getLogger("jarvis.skills")

MAX_DEPTH = 3
_COERCE = {"integer": int, "number": float}


class ArgumentError(ValueError):
    pass


def validate_args(sk: Skill, args: Optional[dict]) -> dict:
    """Confere os parâmetros contra o schema da skill (tipos, enum, obrigatórios) e converte números ditos
    como texto ("10" -> 10). Parâmetros que a skill não declarou são descartados."""
    args = dict(args or {})
    props: dict = sk.params.get("properties", {}) or {}
    out: dict[str, Any] = {}
    for key, spec in props.items():
        if key not in args or args[key] is None:
            continue
        value, kind = args[key], spec.get("type")
        if kind in _COERCE and isinstance(value, str):
            try:
                value = _COERCE[kind](value.replace(",", "."))
            except ValueError as exc:
                raise ArgumentError(f'"{key}" precisa ser um número.') from exc
        if kind == "integer" and isinstance(value, float) and value.is_integer():
            value = int(value)
        if kind == "boolean" and isinstance(value, str):
            value = value.strip().lower() in {"true", "sim", "1", "yes"}
        expected = {"string": str, "integer": int, "number": (int, float), "boolean": bool,
                    "array": list, "object": dict}[kind]
        if not isinstance(value, expected) or (kind in ("integer", "number") and isinstance(value, bool)):
            raise ArgumentError(f'"{key}" precisa ser do tipo {kind}.')
        if "enum" in spec and value not in spec["enum"]:
            raise ArgumentError(f'"{key}" precisa ser um de: {", ".join(map(str, spec["enum"]))}.')
        out[key] = value
    missing = [k for k in sk.params.get("required", []) or [] if k not in out]
    if missing:
        raise ArgumentError(f"Faltou: {', '.join(missing)}.")
    return out


def _restricted() -> bool:
    try:
        from modules import access

        return access.is_restricted()
    except Exception:  # noqa: BLE001
        return True  # na dúvida, trata como bloqueado


async def _open_on_device(url: str) -> None:
    from modules import agents

    await agents._open(url)  # noqa: SLF001 - mesmo comportamento dos agentes (abre no aparelho que pediu)


async def execute(name: str, args: Optional[dict], ctx: Optional[SkillContext] = None) -> SkillResult:
    ctx = ctx or SkillContext()
    sk = registry.get(name)
    if sk is None:
        return SkillResult(ok=False, speech="Não conheço essa habilidade, senhor.")
    title = sk.title or sk.name.replace("_", " ")
    if ctx.depth > MAX_DEPTH:
        return SkillResult(ok=False, speech="Essa sequência de ações ficou longa demais; parei por segurança.")
    if not registry.is_enabled(name):
        return SkillResult(ok=False, speech=f"A habilidade {title} está desligada, senhor.")
    wait = registry.paused_for(name)
    if wait:
        return SkillResult(ok=False, speech=f"A habilidade {title} falhou várias vezes e está em pausa por mais "
                                             f"{max(1, wait // 60)} minuto(s), senhor.")
    if _restricted() and not sk.public:
        return SkillResult(ok=False, speech="Para isso, preciso que a central esteja liberada, senhor.")
    if ctx.remote and not sk.allow_remote:
        return SkillResult(ok=False, speech=f"Por segurança, {title} só pode ser pedido no próprio computador.")
    try:
        clean = validate_args(sk, args)
    except ArgumentError as exc:
        log.info("skill=%s origin=%s status=args_invalid detail=%s", name, ctx.origin, exc)
        return SkillResult(ok=False, speech=f"Não entendi os detalhes para {title}: {exc}")

    if sk.permission is Permission.CRITICAL and not ctx.confirmed:
        from core import confirm

        confirm.offer("skill", {"name": name, "args": clean, "message": ctx.message, "origin": ctx.origin,
                                "remote": ctx.remote})
        log.info("skill=%s origin=%s status=awaiting_confirmation", name, ctx.origin)
        return SkillResult(speech=sk.ask_confirmation(clean), pending=True)

    started = time.monotonic()
    if ctx.depth == 0:  # V9.1.2: a central mostra a habilidade que está rodando
        from core import runtime

        await runtime.doing(title)
    try:
        if sk.is_async:
            coro = sk.handler(ctx, **clean)
        else:
            coro = asyncio.to_thread(sk.handler, ctx, **clean)
        result = await asyncio.wait_for(coro, timeout=sk.timeout)
        if isinstance(result, str):
            result = SkillResult(speech=result)
        elif not isinstance(result, SkillResult):
            raise TypeError(f"a skill devolveu {type(result).__name__} (esperado SkillResult ou texto)")
    except asyncio.TimeoutError:
        ms = int((time.monotonic() - started) * 1000)
        registry.record(name, False, ms, f"passou de {sk.timeout:.0f} s")
        log.warning("skill=%s origin=%s status=timeout ms=%d", name, ctx.origin, ms)
        _log_event("Habilidade demorou demais", f"{name}: passou de {sk.timeout:.0f} s")
        return SkillResult(ok=False, speech=f"{title.capitalize()} demorou demais e eu interrompi, senhor.")
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001
        ms = int((time.monotonic() - started) * 1000)
        registry.record(name, False, ms, f"{type(exc).__name__}: {exc}")
        log.exception("skill=%s origin=%s status=error ms=%d", name, ctx.origin, ms)
        _log_event("Falha em uma habilidade", f"{name}: {type(exc).__name__}: {exc}")
        return SkillResult(ok=False, speech=f"Não consegui concluir {title} agora, senhor. O detalhe ficou no log.")

    ms = int((time.monotonic() - started) * 1000)
    registry.record(name, True, ms)
    log.info("skill=%s origin=%s permission=%s status=ok ms=%d", name, ctx.origin, sk.permission.value, ms)
    if result.url:
        try:
            await _open_on_device(result.url)
        except Exception:  # noqa: BLE001
            log.exception("skill=%s não conseguiu abrir %s", name, result.url)
    return result


def _log_event(title: str, detail: str) -> None:
    try:
        from modules import event_log

        event_log.add("error", title, detail)
    except Exception:  # noqa: BLE001
        pass


async def run_confirmed(data: dict) -> str:
    """O usuário disse "sim" para uma ação crítica pendente (chamado por core/confirm.py)."""
    ctx = SkillContext(message=data.get("message", ""), origin="confirm", confirmed=True,
                       remote=bool(data.get("remote")))
    result = await execute(data.get("name", ""), data.get("args") or {}, ctx)
    return result.speech or ("Feito, senhor." if result.ok else "Não consegui concluir, senhor.")


def run_from_thread(loop: asyncio.AbstractEventLoop, name: str, args: dict, ctx: SkillContext) -> SkillResult:
    """A IA roda numa thread (asyncio.to_thread): executa a skill no laço principal e espera o resultado."""
    sk = registry.get(name)
    limit = (sk.timeout if sk else 10.0) + 5.0
    future = asyncio.run_coroutine_threadsafe(execute(name, args, ctx), loop)
    try:
        return future.result(timeout=limit)
    except Exception as exc:  # noqa: BLE001
        future.cancel()
        log.warning("skill=%s origin=llm status=thread_error detail=%s", name, exc)
        return SkillResult(ok=False, speech="Não consegui concluir essa ação agora, senhor.")

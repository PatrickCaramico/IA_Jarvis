"""V8.11: contrato das Skills (habilidades plug-and-play) do JARVIS.

Uma skill é uma função `async` (ou comum) decorada com `@skill(...)` dentro de um arquivo em `backend/skills/`.
O motor (core/skills/registry.py) acha o arquivo sozinho; ninguém precisa mexer no core para plugar.

    from core.skills import Permission, SkillContext, SkillResult, skill

    @skill(
        name="ola_mundo",
        description="Cumprimenta o usuário pelo nome.",     # a IA lê isto para decidir quando chamar
        permission=Permission.READ,
        triggers=[r"^(?:jarvis\\s+)?diga ola para (?P<nome>.+)$"],   # caminho rápido, sem IA (opcional)
        params={"type": "object", "properties": {"nome": {"type": "string"}}, "required": ["nome"]},
    )
    async def ola_mundo(ctx: SkillContext, nome: str) -> SkillResult:
        return SkillResult(speech=f"Olá, {nome}.")

Níveis de permissão (o executor aplica; a IA nunca decide sozinha):
- READ: só lê/consulta, sem efeito colateral. Executa direto.
- ACTION: efeito local reversível (abrir, mover janela, tocar música). Executa e registra no log.
- CRITICAL: irreversível ou sensível (apagar, fechar processo, enviar mensagem). SEMPRE pergunta antes
  ("sim" por voz, via core/confirm.py) e, por padrão, só vale para pedidos feitos no próprio PC.
"""
from __future__ import annotations

import inspect
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Optional

NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,47}$")  # serve como nome de função no Gemini e na OpenAI/Groq
MAX_TIMEOUT_S = 120.0
_TYPES = {"string", "integer", "number", "boolean", "array", "object"}


class Permission(str, Enum):
    READ = "read"
    ACTION = "action"
    CRITICAL = "critical"


@dataclass
class SkillResult:
    """O que a skill devolve.

    speech: o que o JARVIS fala (curto, sem markdown). Vazio = a IA monta a frase a partir de `data`.
    cards: cartões para a tela (mesmo formato dos cartões reativos).
    data: dados para a IA explicar (quando a skill foi chamada pela IA e não deu `speech`).
    url: aberto no aparelho que fez o pedido (celular ou navegador do PC).
    """

    speech: str = ""
    cards: list[dict] = field(default_factory=list)
    data: Optional[dict] = None
    url: str = ""
    ok: bool = True
    pending: bool = False  # esperando o "sim" do usuário (ação crítica)


@dataclass
class SkillContext:
    """O que a skill recebe além dos parâmetros."""

    message: str = ""  # frase original do usuário
    norm: str = ""  # frase normalizada (minúsculas, sem acentos)
    origin: str = "voice"  # voice (caminho rápido) | llm (a IA chamou) | api (rota de teste) | skill | confirm
    user_name: str = ""
    device: Optional[str] = None  # aparelho que fez o pedido (None = o próprio PC)
    remote: bool = False  # o pedido veio de outro aparelho da rede
    confirmed: bool = False  # o usuário já disse "sim" (ações críticas)
    depth: int = 0  # skills chamando skills (ctx.call): limite contra laço infinito

    async def broadcast(self, event: dict) -> None:
        from core import runtime

        await runtime.manager.broadcast(event)

    async def call(self, name: str, **args: Any) -> SkillResult:
        """Compõe skills: chama outra skill com as mesmas regras de permissão (inclusive o "sim")."""
        from core.skills import executor

        sub = SkillContext(message=self.message, norm=self.norm, origin="skill", user_name=self.user_name,
                           device=self.device, remote=self.remote, confirmed=False, depth=self.depth + 1)
        return await executor.execute(name, args, sub)


Handler = Callable[..., Any]
Parser = Callable[[str, str], Optional[dict]]


@dataclass
class Skill:
    name: str
    description: str
    handler: Handler
    permission: Permission = Permission.READ
    params: dict = field(default_factory=lambda: {"type": "object", "properties": {}})
    timeout: float = 10.0
    triggers: list[re.Pattern] = field(default_factory=list)
    parse: Optional[Parser] = None
    public: bool = False  # vale com a central bloqueada (Sentinela) e no modo visitante
    llm: bool = True  # oferecida à IA como função (function calling)
    allow_remote: bool = True
    confirm_text: Optional[Callable[[dict], str]] = None  # pergunta das ações críticas
    title: str = ""
    examples: list[str] = field(default_factory=list)
    module: str = ""

    @property
    def is_async(self) -> bool:
        return inspect.iscoroutinefunction(self.handler)

    def ask_confirmation(self, args: dict) -> str:
        if self.confirm_text:
            try:
                return self.confirm_text(args)
            except Exception:  # noqa: BLE001
                pass
        return f"Confirma {self.title or self.name.replace('_', ' ')}, senhor? Diga sim para continuar."

    def describe(self) -> dict:
        return {"name": self.name, "title": self.title or self.name.replace("_", " "), "description": self.description,
                "permission": self.permission.value, "public": self.public, "llm": self.llm,
                "examples": list(self.examples), "module": self.module}


class SkillDefinitionError(ValueError):
    """A declaração da skill está errada (o motor recusa e registra o motivo, sem derrubar as outras)."""


def validate_schema(params: dict) -> None:
    if not isinstance(params, dict) or params.get("type") != "object":
        raise SkillDefinitionError('params precisa ser um JSON Schema com "type": "object".')
    props = params.get("properties", {})
    if not isinstance(props, dict):
        raise SkillDefinitionError("params.properties precisa ser um objeto.")
    for key, spec in props.items():
        if not isinstance(spec, dict) or spec.get("type") not in _TYPES:
            raise SkillDefinitionError(f'O parâmetro "{key}" precisa de um "type" válido ({", ".join(sorted(_TYPES))}).')
    for key in params.get("required", []) or []:
        if key not in props:
            raise SkillDefinitionError(f'O parâmetro obrigatório "{key}" não está em properties.')


def build_skill(handler: Handler, *, name: str, description: str, permission: Permission | str = Permission.READ,
                params: Optional[dict] = None, timeout: float = 10.0, triggers: Optional[list[str]] = None,
                parse: Optional[Parser] = None, public: bool = False, llm: bool = True,
                allow_remote: Optional[bool] = None, confirm_text: Optional[Callable[[dict], str]] = None,
                title: str = "", examples: Optional[list[str]] = None) -> Skill:
    if not NAME_RE.match(name or ""):
        raise SkillDefinitionError(f'Nome inválido "{name}": use minúsculas, números e _ (2 a 48 letras).')
    if not (description or "").strip():
        raise SkillDefinitionError(f'A skill "{name}" precisa de uma descrição (a IA usa para decidir quando chamar).')
    try:
        permission = Permission(permission)
    except ValueError as exc:
        raise SkillDefinitionError(f'Permissão inválida em "{name}": {permission}.') from exc
    params = params or {"type": "object", "properties": {}}
    validate_schema(params)
    if not (0 < float(timeout) <= MAX_TIMEOUT_S):
        raise SkillDefinitionError(f'Timeout de "{name}" precisa estar entre 0 e {MAX_TIMEOUT_S:.0f} s.')
    if public and permission is Permission.CRITICAL:
        raise SkillDefinitionError(f'"{name}": ação crítica não pode ser pública (Sentinela/visitante).')
    try:
        compiled = [re.compile(t) for t in (triggers or [])]
    except re.error as exc:
        raise SkillDefinitionError(f'Gatilho (regex) inválido em "{name}": {exc}') from exc
    sig = inspect.signature(handler)
    if not sig.parameters or list(sig.parameters)[0] != "ctx":
        raise SkillDefinitionError(f'A função de "{name}" precisa receber ctx como primeiro parâmetro.')
    return Skill(
        name=name, description=description.strip(), handler=handler, permission=permission, params=params,
        timeout=float(timeout), triggers=compiled, parse=parse, public=public, llm=llm,
        allow_remote=(permission is not Permission.CRITICAL) if allow_remote is None else allow_remote,
        confirm_text=confirm_text, title=title, examples=list(examples or []),
        module=getattr(handler, "__module__", ""),
    )


# Skills declaradas pelo decorador enquanto um arquivo é importado (o registry recolhe e valida)
_declared: list[Skill] = []
_declared_errors: list[str] = []
# Tarefas de fundo das skills (ex.: vigiar a CPU): o registry liga junto com o JARVIS
_services: list[tuple[str, Callable[[], Awaitable[None]]]] = []


def skill(**options: Any) -> Callable[[Handler], Handler]:
    """Decorador que declara uma skill. Veja o exemplo no topo deste arquivo e skills/_template.py."""

    def wrap(handler: Handler) -> Handler:
        try:
            _declared.append(build_skill(handler, **options))
        except (SkillDefinitionError, TypeError) as exc:
            _declared_errors.append(f"{getattr(handler, '__module__', '?')}: {exc}")
        return handler

    return wrap


def service(name: str) -> Callable[[Callable[[], Awaitable[None]]], Callable[[], Awaitable[None]]]:
    """Tarefa de fundo de uma skill (laço infinito com `await asyncio.sleep(...)`). Ligada no início do JARVIS."""

    def wrap(fn: Callable[[], Awaitable[None]]) -> Callable[[], Awaitable[None]]:
        if not inspect.iscoroutinefunction(fn):
            _declared_errors.append(f"{getattr(fn, '__module__', '?')}: o serviço {name} precisa ser async.")
        else:
            _services.append((name, fn))
        return fn

    return wrap

"""V8.11: as Skills viram "funções" para a IA (function calling) no formato de cada provedor.

O schema da skill (JSON Schema) é o mesmo para todos; aqui só muda o embrulho:
- Gemini (google-genai): types.Tool(function_declarations=[FunctionDeclaration(...)]);
- OpenAI e Groq (API no formato da OpenAI): [{"type": "function", "function": {...}}].
"""
from __future__ import annotations

import copy
from typing import Any

from core.skills.base import Skill

TOOL_GUIDE = (
    "Você TEM funções do sistema local disponíveis nesta conversa. Quando o pedido do usuário for uma ação ou "
    "consulta que uma função resolve, CHAME a função em vez de responder com texto. Nunca diga que fez algo sem "
    "ter chamado a função. Se nenhuma função servir, responda normalmente."
)


def _schema(sk: Skill) -> dict:
    params = copy.deepcopy(sk.params) or {"type": "object", "properties": {}}
    params.setdefault("properties", {})
    return params


def to_openai(skills: list[Skill]) -> list[dict]:
    return [{"type": "function", "function": {"name": s.name, "description": s.description,
                                              "parameters": _schema(s)}} for s in skills]


_GEMINI_TYPES = {"string": "STRING", "integer": "INTEGER", "number": "NUMBER", "boolean": "BOOLEAN",
                 "array": "ARRAY", "object": "OBJECT"}


def _gemini_schema(spec: dict) -> dict:
    """JSON Schema -> Schema do Gemini (tipos em maiúsculas; só as chaves que ele aceita)."""
    out: dict[str, Any] = {"type": _GEMINI_TYPES.get(spec.get("type", "string"), "STRING")}
    for key in ("description", "enum", "format"):
        if key in spec:
            out[key] = spec[key]
    if spec.get("type") == "object":
        out["properties"] = {k: _gemini_schema(v) for k, v in (spec.get("properties") or {}).items()}
        if spec.get("required"):
            out["required"] = list(spec["required"])
    if spec.get("type") == "array" and isinstance(spec.get("items"), dict):
        out["items"] = _gemini_schema(spec["items"])
    return out


def to_gemini(skills: list[Skill]):
    from google.genai import types

    decls = []
    for s in skills:
        schema = _schema(s)
        kwargs: dict[str, Any] = {"name": s.name, "description": s.description}
        if schema.get("properties"):  # o Gemini recusa objeto vazio como parâmetros
            kwargs["parameters"] = types.Schema(**_gemini_schema(schema))
        decls.append(types.FunctionDeclaration(**kwargs))
    return types.Tool(function_declarations=decls)

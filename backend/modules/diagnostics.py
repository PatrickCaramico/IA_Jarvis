"""Diagnóstico para copiar e colar (V4.2.2): o estado do JARVIS sem segredos e sem dados pessoais.

O que entra: versão, sistema, provedor de IA escolhido, quais integrações estão configuradas
(só sim/não), algumas preferências de funcionamento e os últimos eventos (tipo, hora e título).
O que NÃO entra: chaves de API, tokens, PIN, o texto dos seus comandos, memórias e o "Sobre mim".
Os detalhes de erro passam por `redact()`, que mascara qualquer coisa com cara de chave ou token.
"""
from __future__ import annotations

import platform
import re
import sys
from datetime import datetime
from typing import Any

from config import settings
from version import VERSION

# Padrões com cara de segredo: chaves conhecidas, "key=...", "token: ...", "Bearer ...", e-mails
_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),                       # OpenAI / Anthropic
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),                     # Google / Gemini
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]+"),
    re.compile(r"(?i)\b(api[_-]?key|key|token|secret|password|senha|pin)\s*[=:]\s*[^\s&\"',;]+"),
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),                    # e-mails
]
# Linhas com o texto do comando (ex.: "Comando: abre meu e-mail") ficam de fora
_COMMAND_LINE = re.compile(r"(?im)^\s*comando:.*$\n?")

SAFE_PREFS = (
    "llm_provider", "personality_mode", "search_mode", "silent_mode", "sentinel_enabled",
    "clap_wake_enabled", "clap_scope", "lock_backend_enforce", "lock_auto_relock_minutes",
    "fan_mode_enabled", "screen_assist_enabled", "routine_suggestions_enabled",
    "notifications_enabled", "sfx_mode", "sfx_volume",
)
DETAIL_KINDS = {"error", "warning"}
MAX_EVENTS = 25


def redact(text: str) -> str:
    text = _COMMAND_LINE.sub("", text or "")
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[oculto]", text)
    return text.strip()[:300]


def _configured(*values: str) -> bool:
    return all(bool(v) for v in values)


def build(events: list[dict], prefs_data: dict[str, Any], runtime_info: dict[str, Any]) -> dict[str, Any]:
    """Monta o diagnóstico. Função pura sobre os dados recebidos (testada sem rede)."""
    recent = []
    for ev in events[:MAX_EVENTS]:
        kind = ev.get("kind", "?")
        item = {"at": ev.get("at", ""), "kind": kind}
        if kind == "command":
            item["title"] = "comando (texto omitido)"
        elif kind == "memory":
            item["title"] = "memória adicionada (texto omitido)"
        else:
            item["title"] = redact(str(ev.get("message", "")))
        if kind in DETAIL_KINDS and ev.get("detail"):
            item["detail"] = redact(str(ev["detail"]))
        recent.append(item)
    return {
        "jarvis": VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "system": {
            "python": sys.version.split()[0],
            "os": f"{platform.system()} {platform.release()}",
        },
        "ai_keys_configured": {
            "openai": _configured(settings.OPENAI_API_KEY),
            "anthropic": _configured(settings.ANTHROPIC_API_KEY),
            "gemini": _configured(settings.GEMINI_API_KEY),
        },
        "integrations_configured": {
            "spotify": _configured(getattr(settings, "SPOTIFY_CLIENT_ID", ""), getattr(settings, "SPOTIFY_CLIENT_SECRET", "")),
            "google_calendar": _configured(getattr(settings, "GOOGLE_CLIENT_ID", ""), getattr(settings, "GOOGLE_CLIENT_SECRET", "")),
        },
        "runtime": runtime_info,
        "prefs": {k: prefs_data.get(k) for k in SAFE_PREFS if k in prefs_data},
        "recent_events": recent,
    }


def as_text(diag: dict[str, Any]) -> str:
    """Versão em texto para colar numa mensagem."""
    lines = [f"Diagnóstico JARVIS v{diag['jarvis']} · {diag['generated_at']}",
             f"Sistema: {diag['system']['os']} · Python {diag['system']['python']}"]
    yes = lambda d: ", ".join(f"{k} {'sim' if v else 'não'}" for k, v in d.items())  # noqa: E731
    lines.append(f"Chaves de IA configuradas: {yes(diag['ai_keys_configured'])}")
    lines.append(f"Integrações configuradas: {yes(diag['integrations_configured'])}")
    lines.append("Execução: " + ", ".join(f"{k}={v}" for k, v in diag["runtime"].items()))
    lines.append("Preferências: " + ", ".join(f"{k}={v}" for k, v in diag["prefs"].items()))
    lines.append(f"Últimos eventos ({len(diag['recent_events'])}):")
    for ev in diag["recent_events"]:
        extra = f" — {ev['detail']}" if ev.get("detail") else ""
        lines.append(f"  {ev['at']} [{ev['kind']}] {ev['title']}{extra}".replace("\n", " "))
    return "\n".join(lines)

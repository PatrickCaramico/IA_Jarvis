"""V8.2: Cérebro (IA) › Conectar as IAs grátis. A chave colada no app é salva SÓ no .env deste PC.

Nunca devolve a chave (só "conectada"), nunca escreve a chave no log e não vai para a nuvem.
"""
from __future__ import annotations

import re
import threading

from config import settings

PROVIDERS = {
    "groq": {"env": "GROQ_API_KEY", "attr": "GROQ_API_KEY", "nome": "Groq", "papel": "A principal: muito rápida.",
             "link": "https://console.groq.com/keys", "formato": re.compile(r"^gsk_[A-Za-z0-9]{20,120}$")},
    "gemini": {"env": "GEMINI_API_KEY", "attr": "GEMINI_API_KEY", "nome": "Gemini", "papel": "A reserva: entra quando a Groq chega no limite do dia (e pesquisa no Google).",
               "link": "https://aistudio.google.com/apikey", "formato": re.compile(r"^AIza[A-Za-z0-9_-]{30,60}$")},
}
_lock = threading.Lock()


def _write_env(name: str, value: str) -> None:
    path = settings.ENV_FILE
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    out, done = [], False
    for line in lines:
        if re.match(rf"^\s*{name}\s*=", line):
            if value and not done:
                out.append(f"{name}={value}")
                done = True
            continue
        out.append(line)
    if value and not done:
        out.append(f"{name}={value}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def _drop_client(provider: str) -> None:
    try:
        from services import llm_orchestrator

        with llm_orchestrator._clients_lock:
            for k in [k for k in llm_orchestrator._clients if k[0] == provider]:
                llm_orchestrator._clients.pop(k, None)
        llm_orchestrator._provider_rest.pop(provider, None)
    except Exception:  # noqa: BLE001
        pass


def save_key(provider: str, key: str) -> dict:
    """Valida o formato, grava no .env e já passa a usar (sem reiniciar)."""
    info = PROVIDERS.get(provider)
    if not info:
        raise KeyError(provider)
    key = (key or "").strip().strip('"').strip("'")
    if not info["formato"].match(key):
        exemplo = "gsk_…" if provider == "groq" else "AIza…"
        raise ValueError(f"Essa não parece uma chave da {info['nome']} (ela começa com {exemplo}).")
    with _lock:
        _write_env(info["env"], key)
        setattr(settings, info["attr"], key)
    _drop_client(provider)
    return status()


def remove_key(provider: str) -> dict:
    info = PROVIDERS.get(provider)
    if not info:
        raise KeyError(provider)
    with _lock:
        _write_env(info["env"], "")
        setattr(settings, info["attr"], "")
    _drop_client(provider)
    return status()


def status() -> dict:
    from modules import prefs
    from services import llm_orchestrator

    chosen = str(prefs._load().get("llm_provider") or "auto")
    keys = llm_orchestrator.provider_keys()
    itens = []
    for pid, info in PROVIDERS.items():
        rest = llm_orchestrator.provider_rest(pid)
        itens.append({"id": pid, "nome": info["nome"], "papel": info["papel"], "link": info["link"],
                      "conectada": keys[pid], "descansando": rest})
    auto_ok = chosen == "auto" and (keys["groq"] or keys["gemini"])
    return {"modo": chosen, "automatico": auto_ok, "ativa": llm_orchestrator.last_provider(), "provedores": itens,
            "outras": {k: v for k, v in keys.items() if k not in PROVIDERS}}

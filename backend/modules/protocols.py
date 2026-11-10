"""Protocolos (4.2, funcionalidade 3 do backlog): um comando dispara várias ações.

"Jarvis, protocolo gravação" executa, em ordem, os passos salvos para "gravação".
Os protocolos ficam em prefs["protocols"] (editáveis em Configurações > Protocolos); se o usuário
ainda não criou nenhum, valem os exemplos de DEFAULT_PROTOCOLS.

Só existem ações seguras e reversíveis (nada apaga arquivos nem envia mensagens):
  open       abre um programa ou site (mesma regra do "abre o ..." por voz)
  focus      inicia o modo foco por N minutos
  focus_stop encerra o modo foco
  silent     liga/desliga o modo silencioso do JARVIS
  volume     ajusta o volume do Windows (0 a 100)
  playlist   toca uma playlist do Spotify (link ou URI)
  say        frase dita ao terminar
"""
from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from typing import Any, Optional

log = logging.getLogger("jarvis.protocols")

ACTIONS = ("open", "focus", "focus_stop", "silent", "volume", "playlist", "say")
MAX_PROTOCOLS = 12
MAX_STEPS = 10

DEFAULT_PROTOCOLS: dict[str, dict[str, Any]] = {
    "trabalho": {
        "label": "Trabalho",
        "steps": [
            {"action": "volume", "value": 30},
            {"action": "focus", "value": 50},
            {"action": "say", "value": "Protocolo trabalho ativo: volume em 30% e foco de 50 minutos."},
        ],
    },
    "gravacao": {
        "label": "Gravação",
        "steps": [
            {"action": "open", "value": "obs"},
            {"action": "volume", "value": 40},
            {"action": "say", "value": "Protocolo gravação ativo. Vou ficar em silêncio até o senhor desligar o modo silencioso."},
            {"action": "silent", "value": True},
        ],
    },
    "descanso": {
        "label": "Descanso",
        "steps": [
            {"action": "focus_stop", "value": None},
            {"action": "silent", "value": False},
            {"action": "volume", "value": 50},
            {"action": "say", "value": "Protocolo descanso ativo. Bom descanso, senhor."},
        ],
    },
}


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def validate(value: Any) -> Optional[str]:
    """Valida prefs["protocols"]. Devolve a mensagem de erro ou None."""
    if not isinstance(value, dict):
        return "protocols deve ser um objeto."
    if len(value) > MAX_PROTOCOLS:
        return f"No máximo {MAX_PROTOCOLS} protocolos."
    for key, proto in value.items():
        if not isinstance(key, str) or not slug(key) or len(key) > 40:
            return "Cada protocolo precisa de um nome curto."
        if not isinstance(proto, dict) or not isinstance(proto.get("steps"), list):
            return f"Protocolo {key}: informe a lista de passos."
        label = proto.get("label", key)
        if not isinstance(label, str) or len(label) > 40:
            return f"Protocolo {key}: nome muito longo."
        steps = proto["steps"]
        if not 1 <= len(steps) <= MAX_STEPS:
            return f"Protocolo {key}: de 1 a {MAX_STEPS} passos."
        for step in steps:
            err = _validate_step(step)
            if err:
                return f"Protocolo {label}: {err}"
    return None


def _validate_step(step: Any) -> Optional[str]:
    if not isinstance(step, dict) or step.get("action") not in ACTIONS:
        return f"ação inválida (use {', '.join(ACTIONS)})."
    action, value = step["action"], step.get("value")
    if action in ("open", "playlist", "say"):
        if not isinstance(value, str) or not value.strip() or len(value) > 200:
            return f"'{action}' precisa de um texto curto."
        if action == "playlist" and not (value.startswith("spotify:playlist:") or "open.spotify.com/playlist/" in value):
            return "'playlist' precisa de um link ou URI de playlist do Spotify."
    elif action == "focus":
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 180:
            return "'focus' precisa de 1 a 180 minutos."
    elif action == "volume":
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
            return "'volume' precisa de 0 a 100."
    elif action == "silent":
        if not isinstance(value, bool):
            return "'silent' precisa de verdadeiro ou falso."
    return None


def all_protocols(user: Optional[dict] = None) -> dict[str, dict[str, Any]]:
    """Protocolos do usuário; sem nenhum salvo, os exemplos padrão."""
    if user is None:
        from modules import prefs

        user = prefs.get_all().get("protocols") or {}
    return user or DEFAULT_PROTOCOLS


def find(name: str, protos: dict[str, dict[str, Any]]) -> Optional[tuple[str, dict[str, Any]]]:
    wanted = slug(name)
    for key, proto in protos.items():
        if wanted in (slug(key), slug(proto.get("label", key))):
            return key, proto
    for key, proto in protos.items():  # começo do nome ("protocolo grava")
        if len(wanted) >= 3 and (slug(key).startswith(wanted) or slug(proto.get("label", key)).startswith(wanted)):
            return key, proto
    return None


async def _run_step(step: dict) -> Optional[str]:
    """Executa um passo. Devolve um problema (texto) ou None se deu certo."""
    from modules import focus, prefs, spotify, system_control, tools

    action, value = step["action"], step.get("value")
    try:
        if action == "open":
            reply = await tools.run(f"abrir {value}")
            if reply and reply.startswith(("Não encontrei", "Não consegui")):
                return f"não abri {value}"
        elif action == "focus":
            await asyncio.to_thread(focus.start_focus, int(value))
        elif action == "focus_stop":
            await asyncio.to_thread(focus.stop_focus)
        elif action == "silent":
            await asyncio.to_thread(prefs.set_silent_mode, bool(value))
        elif action == "volume":
            await asyncio.to_thread(system_control._set_volume, int(value))
        elif action == "playlist":
            await asyncio.to_thread(spotify.play_playlist, str(value), True)
    except Exception as exc:  # noqa: BLE001 - um passo com problema não impede os outros
        log.warning("Passo %s do protocolo falhou: %s", action, exc)
        labels = {"open": f"não abri {value}", "playlist": "a playlist não tocou", "volume": "o volume não mudou",
                  "focus": "o foco não iniciou", "focus_stop": "o foco não parou", "silent": "o modo silencioso não mudou"}
        return labels.get(action, f"{action} falhou")
    return None


async def run(name: str, user: Optional[dict] = None, record: bool = True) -> dict[str, Any]:
    """Executa o protocolo. Devolve {"ok", "label", "reply", "problems"}.

    record=False (botão "testar" das Configurações) não conta para as sugestões pela rotina.
    """
    protos = all_protocols(user)
    hit = find(name, protos)
    if hit is None:
        names = ", ".join(p.get("label", k) for k, p in protos.items())
        return {"ok": False, "label": name, "problems": [],
                "reply": f"Não encontrei o protocolo {name}, senhor. Disponíveis: {names}."}
    key, proto = hit
    label = proto.get("label", key)
    problems: list[str] = []
    say_parts: list[str] = []
    silence_after = False
    for step in proto["steps"]:
        if step["action"] == "say":
            say_parts.append(str(step["value"]))
            continue
        if step["action"] == "silent" and step.get("value") is True:
            silence_after = True  # liga depois da fala, senão a confirmação não seria ouvida
            continue
        problem = await _run_step(step)
        if problem:
            problems.append(problem)
    reply = " ".join(say_parts) or f"Protocolo {label} executado, senhor."
    if problems:
        reply += " Atenção: " + "; ".join(problems) + "."
    if silence_after:
        asyncio.get_running_loop().create_task(_silence_later(min(15.0, 2.0 + len(reply) / 14)))
    from modules import event_log, routine

    event_log.add("protocol", f"Protocolo {label}", "; ".join(problems) or "ok")
    if record:
        routine.record(f"protocol:{key}", label, "protocol", key)
    return {"ok": not problems, "label": label, "reply": reply, "problems": problems}


async def _silence_later(delay: float) -> None:
    from modules import prefs

    await asyncio.sleep(delay)
    await asyncio.to_thread(prefs.set_silent_mode, True)


_RUN_RE = re.compile(r"^(?:jarvis\s+)?(?:(?:ativar|ativa|ative|iniciar|inicia|inicie|executar|executa|execute|rodar|roda)\s+)?(?:o\s+)?protocolo\s+(.+)$")
_LIST_RE = re.compile(r"^(?:jarvis\s+)?(?:quais|que|lista(?:r)?|mostra(?:r)?)\s+(?:sao\s+)?(?:os\s+)?(?:meus\s+)?protocolos")


async def handle_voice(norm: str) -> Optional[str]:
    """Comando de voz já normalizado (sem acentos, minúsculo). Devolve a resposta ou None."""
    if _LIST_RE.match(norm):
        protos = all_protocols()
        names = ", ".join(p.get("label", k) for k, p in protos.items())
        return f"Protocolos disponíveis: {names}. Diga 'protocolo' e o nome para ativar."
    m = _RUN_RE.match(norm)
    if not m:
        return None
    result = await run(m.group(1).strip())
    return result["reply"]

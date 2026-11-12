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
V6.0 (rotinas em 1 comando):
  pause_music  pausa o Spotify
  lock_pc      bloqueia a tela do Windows (Win+L)
  tomorrow     fala o despertador, o clima e o primeiro compromisso de amanhã
  weather_now  fala o clima de agora
  shopping     lê o que falta na lista de compras
Também valem frases naturais: "modo dormir", "vou dormir", "estou saindo" (campo "aliases").
"""
from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from typing import Any, Optional

log = logging.getLogger("jarvis.protocols")

ACTIONS = ("open", "focus", "focus_stop", "silent", "volume", "playlist", "say",
           "pause_music", "lock_pc", "tomorrow", "weather_now", "shopping")
# Ações que só falam algo (o texto entra na resposta, na ordem)
SPEAKING_ACTIONS = ("tomorrow", "weather_now", "shopping")
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
    "dormir": {
        "label": "Dormir",
        "aliases": ["vou dormir", "hora de dormir", "boa noite jarvis vou dormir"],
        "steps": [
            {"action": "pause_music", "value": None},
            {"action": "focus_stop", "value": None},
            {"action": "volume", "value": 15},
            {"action": "tomorrow", "value": None},
            {"action": "say", "value": "Bom descanso, senhor."},
        ],
    },
    "saindo": {
        "label": "Saindo de casa",
        "aliases": ["estou saindo", "to saindo", "vou sair", "saindo de casa"],
        "steps": [
            {"action": "weather_now", "value": None},
            {"action": "shopping", "value": None},
            {"action": "pause_music", "value": None},
            {"action": "lock_pc", "value": None},
            {"action": "say", "value": "Bloqueei o computador. Até mais, senhor."},
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
    return None  # pause_music, lock_pc, tomorrow, weather_now, shopping: sem valor


def all_protocols(user: Optional[dict] = None) -> dict[str, dict[str, Any]]:
    """Protocolos do usuário; sem nenhum salvo, os exemplos padrão."""
    if user is None:
        from modules import prefs

        user = prefs.get_all().get("protocols") or {}
    return user or DEFAULT_PROTOCOLS


def find(name: str, protos: dict[str, dict[str, Any]]) -> Optional[tuple[str, dict[str, Any]]]:
    wanted = slug(name)
    for key, proto in protos.items():
        if wanted in (slug(key), slug(proto.get("label", key))) or wanted in {slug(a) for a in proto.get("aliases", [])}:
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
        elif action == "pause_music":
            if spotify.connected():
                await asyncio.to_thread(spotify.pause)
        elif action == "lock_pc":
            await asyncio.to_thread(system_control._lock_screen)
    except Exception as exc:  # noqa: BLE001 - um passo com problema não impede os outros
        log.warning("Passo %s do protocolo falhou: %s", action, exc)
        labels = {"open": f"não abri {value}", "playlist": "a playlist não tocou", "volume": "o volume não mudou",
                  "pause_music": "a música não pausou", "lock_pc": "o computador não bloqueou",
                  "focus": "o foco não iniciou", "focus_stop": "o foco não parou", "silent": "o modo silencioso não mudou"}
        return labels.get(action, f"{action} falhou")
    return None


async def _speak_step(action: str) -> str:
    """V6.0: passos que viram fala (amanhã, clima agora, lista de compras). Falha vira texto vazio."""
    from datetime import datetime, timedelta

    try:
        if action == "shopping":
            from modules import shopping

            pending = [i["texto"].lower() for i in shopping.list_items() if not i.get("comprado")]
            if not pending:
                return ""
            return "Na lista de compras: " + (pending[0] if len(pending) == 1 else ", ".join(pending[:-1]) + " e " + pending[-1]) + "."
        if action == "weather_now":
            from config import settings
            from modules import tools

            res = await asyncio.to_thread(tools._fetch_weather, settings.WEATHER_CITY)
            if not res:
                return ""
            from modules.briefing import weather_tip

            cur, daily = res["data"].get("current", {}), res["data"].get("daily", {})
            desc = tools._WMO.get(cur.get("weather_code"), "tempo variável")
            rain = (daily.get("precipitation_probability_max") or [None])[0]
            tip = weather_tip((daily.get("temperature_2m_min") or [None])[0], (daily.get("temperature_2m_max") or [None])[0], rain, cur.get("weather_code"))
            return f"Lá fora, {round(cur.get('temperature_2m', 0))} graus e {desc}." + (f" {tip}" if tip else "")
        if action == "tomorrow":
            from config import settings
            from modules import alarms, calendar_hub, reminders, tools

            tomorrow = datetime.now() + timedelta(days=1)
            day = tomorrow.strftime("%Y-%m-%d")
            parts = []
            alarm = next((a for a in alarms.list_alarms() if a.get("proximo", "").startswith(day)), None)
            parts.append(f"Seu despertador toca às {alarm['hora']}." if alarm else "Não há despertador para amanhã.")
            first = None
            try:
                evs = [e for e in calendar_hub.upcoming_events(days=2, limit=15) if (e.get("start") or "").startswith(day)] if calendar_hub.connected() else []
                if evs:
                    first = (evs[0].get("start", "")[11:16] or "dia todo", evs[0].get("title", "compromisso"))
            except Exception:  # noqa: BLE001
                first = None
            if not first:
                rs = [r for r in reminders.get_reminders(only_pending=True) if r.get("data_hora", "").startswith(day)]
                if rs:
                    rs.sort(key=lambda r: r["data_hora"])
                    first = (rs[0]["data_hora"][11:16], rs[0].get("texto", "lembrete"))
            if first:
                parts.append(f"O primeiro compromisso é {first[1]}, às {first[0]}.")
            res = await asyncio.to_thread(tools._fetch_weather, settings.WEATHER_CITY)
            if res:
                daily = res["data"].get("daily", {})
                try:
                    tmin, tmax = round(daily["temperature_2m_min"][1]), round(daily["temperature_2m_max"][1])
                    desc = tools._WMO.get((daily.get("weather_code") or [None, None])[1], "tempo variável")
                    parts.append(f"Amanhã: {desc}, entre {tmin} e {tmax} graus.")
                except (KeyError, IndexError, TypeError):
                    pass
            return " ".join(parts)
    except Exception as exc:  # noqa: BLE001
        log.warning("Passo %s da rotina falhou: %s", action, exc)
    return ""


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
        if step["action"] in SPEAKING_ACTIONS:
            text = await _speak_step(step["action"])
            if text:
                say_parts.append(text)
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


_MODE_RE = re.compile(r"^(?:jarvis\s+)?(?:(?:ativar|ativa|ative|liga|ligar)\s+(?:o\s+)?)?(?:modo|rotina)\s+(.+)$")


async def handle_natural(norm: str) -> Optional[str]:
    """V6.0: "modo dormir", "rotina saindo", "vou dormir", "estou saindo" (só se bater com um protocolo)."""
    text = re.sub(r"^(?:ei\s+)?jarvis\s+", "", norm).strip()
    protos = all_protocols()
    m = _MODE_RE.match(text)
    candidate = m.group(1).strip() if m else text
    hit = find(candidate, protos) if m else None
    if hit is None:
        for key, proto in protos.items():
            if text in {slug(a) for a in proto.get("aliases", [])}:
                hit = (key, proto)
                break
    if hit is None:
        return None
    result = await run(hit[0])
    return result["reply"]


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

"""Alarmes do JARVIS (V5.1), no jeito da Alexa.

Voz: "Jarvis, me acorda às 7", "alarme de segunda a sexta às 6 e meia", "quais são meus alarmes?",
"cancela o alarme das 7", "apaga todos os alarmes". Tocando: "parar" ou "soneca" / "mais 5 minutos".

Guardados em data/alarmes.json (sobrevivem ao reinício). Na hora, toca um bipe em loop pelo PC (canal de
som separado da voz) e, a cada 25 s, fala a hora. PARAR desliga; SONECA adia 9 minutos; sem resposta,
desliga sozinho depois de 10 minutos. Alarme que repete (dias da semana) já se reagenda ao tocar.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Awaitable, Callable, Optional

from config import settings
from modules import when

log = logging.getLogger("jarvis.alarms")

_PATH = settings.DATA_DIR / "alarmes.json"
SNOOZE_MINUTES = 9
RING_LIMIT_SECONDS = 10 * 60
SPEAK_EVERY_SECONDS = 25
MAX_ALARMS = 30

_broadcast: Optional[Callable[[dict], Awaitable[None]]] = None
_speak: Optional[Callable[[str], Awaitable[None]]] = None
_is_restricted: Callable[[], bool] = lambda: False

_ringing: Optional[dict] = None
_ring_task: Optional[asyncio.Task] = None
_pending_create: float = 0.0  # "me acorda" sem horário: espera a hora na próxima frase (30 s)


def configure(broadcast=None, speak=None, is_restricted=None) -> None:
    global _broadcast, _speak, _is_restricted
    if broadcast:
        _broadcast = broadcast
    if speak:
        _speak = speak
    if is_restricted:
        _is_restricted = is_restricted


# ------------------------------------------------------------------ dados
def _load() -> list[dict]:
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _save(items: list[dict]) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def _when(a: dict) -> datetime:
    return datetime.strptime(a["proximo"], "%Y-%m-%d %H:%M")


def list_alarms() -> list[dict]:
    return sorted(_load(), key=_when)


def add_alarm(at: datetime, days: Optional[list[int]] = None, label: str = "") -> dict:
    items = _load()
    if len(items) >= MAX_ALARMS:
        raise ValueError("Já tenho alarmes demais. Apague alguns antes.")
    new = {
        "id": max((a.get("id", 0) for a in items), default=0) + 1,
        "hora": at.strftime("%H:%M"),
        "dias": sorted(days) if days else [],
        "rotulo": label.strip()[:60],
        "proximo": at.strftime("%Y-%m-%d %H:%M"),
        "criado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    items.append(new)
    _save(items)
    return new


def delete_alarm(alarm_id: int) -> bool:
    items = _load()
    left = [a for a in items if a.get("id") != alarm_id]
    if len(left) == len(items):
        return False
    _save(left)
    return True


def clear_alarms() -> int:
    n = len(_load())
    _save([])
    return n


def describe(a: dict, now: Optional[datetime] = None) -> str:
    return when.describe(_when(a), a.get("dias") or None, now)


# ------------------------------------------------------------------ tocar
def is_ringing() -> bool:
    return _ringing is not None


def ringing_info() -> Optional[dict]:
    if not _ringing:
        return None
    return {k: _ringing[k] for k in ("id", "hora", "rotulo")}


def spoken_time(hm: str) -> str:
    """"07:00" -> "são 7 horas"; "06:30" -> "são 6 e meia"; "01:15" -> "é 1 e 15"; "12:00" -> "é meio-dia"."""
    h, mi = (int(x) for x in hm.split(":"))
    if h == 12 and mi == 0:
        return "é meio-dia"
    if h == 0 and mi == 0:
        return "é meia-noite"
    hour = 12 if h == 0 else (h if h <= 12 else h - 12)
    verb = "é" if hour == 1 else "são"
    if mi == 0:
        return f"{verb} {hour} {'hora' if hour == 1 else 'horas'}"
    return f"{verb} {hour} e {'meia' if mi == 30 else mi}"


def _public_label(a: dict) -> str:
    # Com a central bloqueada, o rótulo (pode ser pessoal) não aparece nem é falado
    return "" if _is_restricted() else a.get("rotulo", "")


_tone = None


_tone_device = None  # V6.5.8: caixa em que o bipe foi criado


def _play_tone() -> None:
    """Três bipes curtos num canal próprio (não interrompe a voz). Sem som disponível, segue mudo."""
    global _tone
    try:
        import numpy as np
        import pygame

        from modules import tts

        global _tone_device
        tts._ensure_mixer()  # noqa: SLF001 - V6.5.8: o alarme toca na mesma caixa escolhida para a voz
        if tts._mixer_device != _tone_device:  # noqa: SLF001 - o som foi reaberto em outra caixa: refaz o bipe
            _tone = None
            _tone_device = tts._mixer_device  # noqa: SLF001
        if _tone is None:
            freq, _fmt, channels = pygame.mixer.get_init()
            beep_t = np.linspace(0, 0.14, int(freq * 0.14), endpoint=False)
            beep = (np.sin(2 * np.pi * 880 * beep_t) * 0.45 * 32767).astype(np.int16)
            fade = np.linspace(1, 0, len(beep) // 6)
            beep[-len(fade):] = (beep[-len(fade):] * fade).astype(np.int16)
            gap = np.zeros(int(freq * 0.09), dtype=np.int16)
            mono = np.concatenate([beep, gap, beep, gap, beep])
            arr = np.column_stack([mono] * channels) if channels > 1 else mono
            _tone = pygame.sndarray.make_sound(np.ascontiguousarray(arr))
        _tone.play()
    except Exception:  # noqa: BLE001
        log.debug("Sem som para o alarme", exc_info=True)


player: Callable[[], None] = _play_tone  # os testes trocam por um silencioso


async def _send(event: dict) -> None:
    if _broadcast:
        try:
            await _broadcast(event)
        except Exception:  # noqa: BLE001
            log.debug("Falha ao avisar a tela do alarme", exc_info=True)


async def _say(text: str) -> None:
    if _speak:
        try:
            await _speak(text)
        except Exception:  # noqa: BLE001
            log.debug("Falha ao falar o alarme", exc_info=True)


async def _ring_loop(a: dict) -> None:
    started = time.monotonic()
    last_speech = -float(SPEAK_EVERY_SECONDS)  # fala a hora logo depois dos primeiros bipes
    label = _public_label(a)
    phrase = f"Senhor, {spoken_time(a['hora'])}." + (f" Alarme: {label}." if label else "")
    try:
        while _ringing is not None and _ringing.get("id") == a["id"]:
            elapsed = time.monotonic() - started
            if elapsed > RING_LIMIT_SECONDS:
                log.info("Alarme %s desligado sozinho depois de %s s.", a["id"], RING_LIMIT_SECONDS)
                await _finish("timeout")
                return
            player()
            if elapsed - last_speech >= SPEAK_EVERY_SECONDS:
                last_speech = elapsed
                await _say(phrase)
            await asyncio.sleep(1.4)
    except asyncio.CancelledError:
        pass


async def ring(a: dict) -> None:
    global _ringing, _ring_task
    if _ringing is not None:
        return
    _ringing = {"id": a["id"], "hora": a["hora"], "rotulo": a.get("rotulo", ""), "since": time.time()}
    log.info("Alarme tocando: %s %s", a["hora"], a.get("rotulo", ""))
    await _send({"type": "alarm", "state": "ringing", "id": a["id"], "hora": a["hora"], "rotulo": _public_label(a),
                 "snooze_minutes": SNOOZE_MINUTES})
    _ring_task = asyncio.create_task(_ring_loop(a))


async def _finish(reason: str) -> None:
    global _ringing, _ring_task
    _ringing = None
    task, _ring_task = _ring_task, None
    if task and not task.done() and task is not asyncio.current_task():
        task.cancel()
    try:
        import pygame

        if pygame.mixer.get_init() and _tone is not None:
            _tone.stop()
    except Exception:  # noqa: BLE001
        pass
    await _send({"type": "alarm", "state": "stopped", "reason": reason})


async def stop() -> Optional[dict]:
    """PARAR: desliga o alarme que está tocando. Devolve o alarme parado (ou None)."""
    if _ringing is None:
        return None
    info = dict(_ringing)
    await _finish("stopped")
    return info


async def snooze(minutes: int = SNOOZE_MINUTES) -> Optional[datetime]:
    """SONECA: desliga agora e toca de novo daqui a `minutes` (como alarme único)."""
    if _ringing is None:
        return None
    info = dict(_ringing)
    await _finish("snoozed")
    minutes = max(1, min(int(minutes), 60))
    at = (datetime.now() + timedelta(minutes=minutes)).replace(second=0, microsecond=0)
    add_alarm(at, None, info.get("rotulo") or "")
    return at


async def check_due(now: Optional[datetime] = None) -> None:
    """Toca o alarme vencido mais antigo; reagenda os que repetem e apaga os de uma vez só."""
    now = now or datetime.now()
    items = _load()
    due = [a for a in items if _when(a) <= now]
    if not due or _ringing is not None:
        return
    a = min(due, key=_when)
    if (now - _when(a)) > timedelta(minutes=30):
        log.info("Alarme %s perdido (PC desligado na hora): não toca atrasado.", a["id"])
        ring_now = False
    else:
        ring_now = True
    if a.get("dias"):
        h, mi = (int(x) for x in a["hora"].split(":"))
        a["proximo"] = when.next_on_days(h, mi, a["dias"], max(now, _when(a))).strftime("%Y-%m-%d %H:%M")
    else:
        items = [x for x in items if x.get("id") != a["id"]]
    _save(items)
    if ring_now:
        await ring(a)


async def worker_loop() -> None:
    while True:
        try:
            await check_due()
        except asyncio.CancelledError:
            break
        except Exception:  # noqa: BLE001
            log.exception("Erro no loop de alarmes")
        await asyncio.sleep(2)


# ------------------------------------------------------------------ voz
_ALARM = re.compile(r"\b(?:alarmes?|despertador(?:es)?|me\s+acord[ae]|me\s+despert[ae]|acorde?\s+me)\b")
_STOP = re.compile(r"^(?:jarvis\s+)?(?:para|pare|parar|desliga|desligue|desligar|chega|ja\s+acordei|acordei|"
                   r"silencio|ok|cancela|cancelar|tudo\s+bem|beleza)(?:\s+(?:o\s+)?(?:alarme|despertador))?(?:\s+por\s+favor)?$")
_SNOOZE = re.compile(r"\b(?:soneca|adia|adiar|adie|mais\s+(?:\w+\s+)?minutos?|daqui\s+a\s+pouco|deixa\s+eu\s+dormir)\b")
_CANCEL = re.compile(r"\b(?:cancela|cancele|cancelar|desliga|desligue|desligar|apaga|apague|apagar|remove|remova|"
                     r"tira|tire|exclui|exclua|deleta|delete)\b")
_LIST = re.compile(r"\b(?:quais|qual|meus|tenho|lista|listar|ver|mostra|mostre|algum|quantos|proximo)\b")
_NOISE = re.compile(r"\b(?:jarvis|por\s+favor|coloca|coloque|cria|crie|criar|define|defina|programa|programe|"
                    r"poe|ponha|bota|bote|um|o|uma|novo|alarmes?|despertador(?:es)?|me\s+acord[ae]|"
                    r"me\s+despert[ae]|acorde?\s+me)\b")


def _label(rest: str) -> str:
    rest = _NOISE.sub(" ", rest)
    rest = re.sub(r"^\s*(?:para|pra|de|com\s+o\s+nome)\s+", " ", re.sub(r"\s+", " ", rest).strip() + " ")
    words = rest.split()
    while words and words[0] in {"para", "pra", "de", "e", "a", "o", "que"}:
        words.pop(0)
    return " ".join(words)


async def handle_ringing_voice(norm: str) -> Optional[str]:
    """Com o alarme tocando: "parar" ou "soneca" (vale até com a central bloqueada)."""
    if _ringing is None:
        return None
    if _SNOOZE.search(norm):
        m = re.search(r"\bmais\s+(\d{1,2}|\w+)\s+minutos?\b", norm)
        minutes = SNOOZE_MINUTES
        if m:
            minutes = int(m.group(1)) if m.group(1).isdigit() else (when._num(m.group(1)) or SNOOZE_MINUTES)
        at = await snooze(minutes)
        return f"Certo, senhor. Toco de novo às {at:%H:%M}."
    if _STOP.match(norm) or (_ALARM.search(norm) and _CANCEL.search(norm)):
        await stop()
        return "Alarme desligado, senhor."
    return None


def _list_reply(now: datetime) -> str:
    items = list_alarms()
    if not items:
        return "Você não tem nenhum alarme, senhor."
    parts = [describe(a, now) + (f" ({a['rotulo']})" if a.get("rotulo") else "") for a in items[:5]]
    head = "Você tem um alarme: " if len(items) == 1 else f"Você tem {len(items)} alarmes: "
    return head + "; ".join(parts) + "."


async def handle_voice(norm: str, now: Optional[datetime] = None) -> Optional[str]:
    global _pending_create
    now = now or datetime.now()
    ringing_reply = await handle_ringing_voice(norm)
    if ringing_reply:
        return ringing_reply

    asked_time = time.monotonic() < _pending_create
    if not _ALARM.search(norm) and not asked_time:
        return None
    if _ALARM.search(norm) and _CANCEL.search(norm):
        items = list_alarms()
        if not items:
            return "Você não tem nenhum alarme para cancelar."
        if re.search(r"\btod[oa]s?\b", norm):
            n = clear_alarms()
            return f"Pronto. Apaguei {'o alarme' if n == 1 else f'os {n} alarmes'}."
        target = when.parse(_CANCEL.sub(" ", norm), now)
        if target.at is not None:
            # "das 7" pode ser 07:00 ou 19:00: vale qualquer um dos dois
            h, mi = target.at.hour, target.at.minute
            options = {f"{h:02d}:{mi:02d}", f"{(h + 12) % 24:02d}:{mi:02d}"}
            match = [a for a in items if a["hora"] in options]
        else:
            match = items if len(items) == 1 else []
        if len(match) == 1:
            delete_alarm(match[0]["id"])
            return f"Alarme de {describe(match[0], now)} cancelado."
        if len(match) > 1:
            for a in match:
                delete_alarm(a["id"])
            return f"Cancelei os {len(match)} alarmes das {match[0]['hora']}."
        return "Qual deles, senhor? " + _list_reply(now)
    if _ALARM.search(norm) and _LIST.search(norm) and when.parse(norm, now).at is None:
        return _list_reply(now)

    parsed = when.parse(norm, now)
    if parsed.at is None:
        if asked_time:
            return None  # não era a resposta da hora: segue o fluxo normal
        _pending_create = time.monotonic() + 30
        return "Para que horas, senhor?"
    _pending_create = 0.0
    try:
        a = add_alarm(parsed.at, parsed.days, _label(parsed.rest))
    except ValueError as exc:
        return str(exc)
    text = f"Alarme definido para {describe(a, now)}"
    return text + (f": {a['rotulo']}." if a.get("rotulo") else ".")

"""V5.4: o que o JARVIS faz ao entrar na central, decidido NO PC (vale para site, PC e app juntos).

Antes, "já fiz o briefing hoje" ficava no navegador: o site, a central do PC e o app tinham cada um a sua
memória, então cada aparelho repetia o briefing inteiro, e toda reentrada perguntava de novo "quer que eu
repita?", junto com o "Em que posso ajudar?". Agora:

- 1ª entrada do dia (em qualquer aparelho): o briefing ("bom dia" ou, depois das 18h, "boa noite");
- 2ª entrada: pergunta UMA vez se repete o briefing ou pula;
- dali em diante: uma saudação curta, sempre diferente da última (ou nada no modo silencioso).
Pedir "bom dia" por voz também conta como briefing feito.
"""
from __future__ import annotations

import random
import time
from datetime import datetime
from typing import Optional

from modules import prefs

QUICK_WELCOMES = [
    "Bem-vindo de volta, senhor.",
    "De volta à central, senhor. Ao seu dispor.",
    "Sistemas prontos, senhor. Em que posso ajudar?",
    "Tudo em ordem por aqui, senhor.",
    "Pronto quando o senhor estiver.",
]
# V6.1: o desbloqueio (rosto/PIN) já cumprimentou; a pergunta vem sem um segundo "bem-vindo"
ASK_TEXT = "Quer que eu repita o briefing de hoje ou prefere pular?"

# V5.6.2: duas telas entrando juntas (aba antiga que reconectou + aba nova do Iniciar-JARVIS.bat, ou PC e
# celular) recebiam cada uma a sua fala: a primeira o briefing, a segunda "quer que eu repita?". Agora, uma
# entrada nos últimos SAME_ENTRY_SECONDS conta como a MESMA entrada: a segunda tela entra em silêncio.
SAME_ENTRY_SECONDS = 120
GREET_AFTER_UNLOCK = False  # V6.1: a saudação curta extra saiu (o desbloqueio já cumprimenta)
_last_decision_at = 0.0


def _today(now: datetime) -> str:
    return now.strftime("%Y-%m-%d")


def _state(now: datetime) -> dict:
    st = prefs._load().get("briefing_entry") or {}
    if st.get("date") != _today(now):
        st = {"date": _today(now), "briefed": False, "asked": False, "last_welcome": st.get("last_welcome", -1)}
    return st


def _save(st: dict) -> None:
    prefs.update(briefing_entry=st)


def briefing_command(now: datetime) -> str:
    if now.hour >= 18 or now.hour < 4:
        return "boa noite"
    return "boa tarde" if now.hour >= 12 else "bom dia"  # V6.5: resumo da tarde


def briefing_pending(now: Optional[datetime] = None) -> bool:
    """V6.1: a próxima entrada vai fazer o briefing? (aí o desbloqueio não diz "bom dia", o briefing diz)"""
    now = now or datetime.now()
    mode = prefs._load().get("lock_daily_summary") or "first_login"
    if mode == "off":
        return False
    return mode == "always" or not _state(now)["briefed"]


def mark_briefed(now: Optional[datetime] = None) -> None:
    """Chamado quando um briefing completo roda (pela entrada ou pedido por voz)."""
    now = now or datetime.now()
    st = _state(now)
    st["briefed"] = True
    _save(st)


def decide(now: Optional[datetime] = None, rng: Optional[random.Random] = None) -> dict:
    """{"action": "briefing"|"ask"|"greet"|"none", "command"?, "text"?} e já registra a decisão."""
    global _last_decision_at
    now = now or datetime.now()
    mode = prefs._load().get("lock_daily_summary") or "first_login"
    st = _state(now)
    command = briefing_command(now)

    tick = time.monotonic()
    if _last_decision_at and tick - _last_decision_at < SAME_ENTRY_SECONDS:
        return {"action": "none"}  # outra tela acabou de entrar: esta fica em silêncio
    _last_decision_at = tick

    if mode == "always" or (mode != "off" and not st["briefed"]):
        st["briefed"] = True
        _save(st)
        return {"action": "briefing", "command": command}
    if mode != "off" and not st["asked"]:
        st["asked"] = True
        _save(st)
        from modules import phrases

        return {"action": "ask", "command": command, "text": phrases.pick("ask_repeat")}  # V6.5.3: varia

    # V6.1: já fez o briefing e já perguntou hoje: o desbloqueio já cumprimentou, então a entrada fica em
    # silêncio (antes vinha "Bem-vindo de volta" logo depois do "Olá... tudo bem?": duas saudações)
    if not GREET_AFTER_UNLOCK:
        return {"action": "none"}
    rng = rng or random.Random()
    choices = [i for i in range(len(QUICK_WELCOMES)) if i != st.get("last_welcome", -1)]
    pick = rng.choice(choices)
    st["last_welcome"] = pick
    _save(st)
    return {"action": "greet", "text": QUICK_WELCOMES[pick]}


# --------------------------------------------------------------------------- V7.2: saudação "só às vezes"
# Antes, TODO desbloqueio (rosto, PIN, digital) falava "Boa tarde, Patrick. Tudo pronto por aqui".
# Agora, no padrão ("sometimes"), ele cumprimenta na 1ª entrada do dia e depois só se passou um tempo
# (GREET_GAP_HOURS); nas outras, entra em silêncio. O aviso de tentativas não reconhecidas continua sendo falado.
GREET_GAP_HOURS = 3


def unlock_speech(hello: str, confirm: str, note: str = "", now: Optional[datetime] = None) -> str:
    """O que falar ao desbloquear ("" = silêncio). hello/confirm já vêm sorteados das frases."""
    now = now or datetime.now()
    if briefing_pending(now):
        return confirm + note  # o briefing vem logo depois; aqui só confirma
    mode = prefs._load().get("lock_unlock_greeting") or "sometimes"
    if mode == "always":
        return hello + note
    if mode == "off":
        return note.strip()
    st = prefs._load().get("unlock_greeting") or {}
    last = st.get("at")
    try:
        gap = (now - datetime.fromisoformat(last)).total_seconds() / 3600 if last else None
    except ValueError:
        gap = None
    if gap is None or gap >= GREET_GAP_HOURS or datetime.fromisoformat(last).date() != now.date():
        prefs.update(unlock_greeting={"at": now.isoformat(timespec="seconds")})
        return hello + note
    return note.strip()

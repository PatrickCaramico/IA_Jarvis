"""Modo Sentinela e modo visitante: o que o JARVIS pode responder sem acesso liberado.

`classify_and_answer` recebe a frase e o estado (locked | guest) e devolve:
    {"reply": str, "public": bool, "requires_unlock": bool, "action": str | None}

Pedidos públicos (nível 1): cumprimentos, "tá acordado?", hora, data, clima, quem é o
JARVIS, contas simples, timers, foco/Pomodoro e status do sistema. No modo visitante,
também os controles de música. Todo o resto é protegido: o JARVIS não executa e só
avisa que precisa liberar a central (ou recusa, no modo visitante).

As funções locais reaproveitadas (tools._h_*) recebem nome vazio para não revelar dados.
"""
from __future__ import annotations

import asyncio
import logging
import random
import re
from typing import Any, Optional

from modules import quick_replies, tools

log = logging.getLogger("jarvis.sentinel")

UNLOCK_REPLY = "Para te mostrar isso, preciso liberar a central, senhor. Vou ativar a câmera para o escaneamento."
GUEST_REFUSAL = "Desculpe, no modo visitante não posso acessar isso. O proprietário precisa liberar a central."
AWAKE_REPLIES = ("Estou aqui, senhor.", "Sempre, senhor.", "Às suas ordens, senhor.")

_AWAKE = re.compile(r"^(?:(?:ei|oi|ola|e ai)\s+)?(?:jarvis\s*)?(?:(?:voce\s+)?(?:ta|esta)\s+(?:acordado|ai|on|online|me ouvindo)|acorda|ta ai)?$")
_LOCK_CMD = re.compile(r"\b(?:bloquear|bloqueie|bloqueia|trancar|tranque|tranca)\b(?:\s+(?:a\s+)?(?:tela|central|sistema|jarvis))?")
_NEWS = re.compile(r"\b(?:noticias?|manchetes?|novidades)\b")
_SUMMARY = re.compile(r"\b(?:resumo|o que (?:eu )?tenho (?:pra |para )?hoje|como esta (?:o )?meu dia|meu dia)\b")
_MUSIC = re.compile(r"\b(?:pausar|pause|pausa|parar a musica|proxima|seguinte|anterior|voltar a musica|continuar|retomar|tocando|musica atual|tocar|play)\b")
_MUSIC_CONTEXT = re.compile(r"\b(?:musica|spotify|faixa|som)\b")
_SYSTEM_STATUS = re.compile(r"^(?:jarvis\s+)?(?:status|diagnostico)(?:\s+do\s+sistema|\s+dos\s+sistemas)?$")
_IDENTITY_WORDS = ("quem e voce", "quem desenvolveu", "quem criou", "quem te criou", "quem fez voce",
                   "o que voce faz", "o que voce sabe fazer", "qual e o seu nome", "como voce se chama",
                   "se apresente", "para que voce serve", "pra que voce serve")
_SENSITIVE_HINTS = ("meu nome", "minha", "meu ", "meus", "minhas", "senha", "agenda", "tarefa", "lembrete",
                    "memoria", "financ", "email", "e-mail", "saude", "remedio")


def _norm(text: str) -> str:
    return quick_replies._norm(text)


def strip_wake_words(norm: str, wake_words: list[str]) -> str:
    """Remove a palavra de ativação do começo da frase ("jarvis, que horas são" -> "que horas sao")."""
    for w in sorted((_norm(x) for x in wake_words if x), key=len, reverse=True):
        if w and (norm == w or norm.startswith(w + " ")):
            return norm[len(w):].strip()
    return norm


def _quick_public(message: str, norm: str) -> Optional[str]:
    """Respostas instantâneas sem dados pessoais: cumprimentos, hora, data e identidade."""
    if any(h in norm for h in _SENSITIVE_HINTS) and not any(i in norm for i in _IDENTITY_WORDS):
        return None
    reply = quick_replies.match(message, "")
    if not reply:
        return None
    return reply.replace("por você,", "pelo meu operador,").replace(", você", "")


async def _local(handler, message: str, norm: str) -> Optional[str]:
    try:
        return await handler(message, norm, len(norm.split()), "")
    except Exception:  # noqa: BLE001
        log.exception("Falha na função pública %s", getattr(handler, "__name__", handler))
        return None


def _counts_summary() -> str:
    """Resumo SEM detalhes (só números) para o modo bloqueado."""
    try:
        from modules import reminders, tasks
        pending = [t for t in tasks.get_tasks(include_completed=False) if not t.get("concluida")]
        rems = reminders.get_reminders(only_pending=True)
    except Exception:  # noqa: BLE001
        return UNLOCK_REPLY
    t, r = len(pending), len(rems)
    parts = [f"{t} tarefa{'s' if t != 1 else ''} pendente{'s' if t != 1 else ''}",
             f"{r} lembrete{'s' if r != 1 else ''} agendado{'s' if r != 1 else ''}"]
    return f"Você tem {parts[0]} e {parts[1]}. Quer ver? Preciso liberar a central."


# V4.2.2: frases só de liberar a central ("abrir central", "liberar"): escaneia sem pedido pendente.
# Mesma regra de frontend/src/utils/wakeWords.js (isUnlockPhrase); tests/test_v422.py confere.
_UNLOCK_ONLY = re.compile(
    r"^(?:(?:pode|por favor|quero)\s+)?(?:(?:abrir|abre|abra|liberar|libera|libere|desbloquear|desbloqueia|desbloqueie|"
    r"destravar|destrava|destrave)(?:\s+(?:a|o))?(?:\s+(?:central|jarvis|sistema|tela))?|entrar|me deixa entrar|deixa eu entrar)"
    r"(?:\s+por favor)?$"
)
UNLOCK_ONLY_REPLY = "Escaneando, senhor."


def is_unlock_only(norm: str) -> bool:
    return bool(norm) and not re.fullmatch(r"abrir|abre|abra", norm) and bool(_UNLOCK_ONLY.fullmatch(norm))


async def classify_and_answer(message: str, state: str, wake_words: Optional[list[str]] = None) -> dict[str, Any]:
    wake_words = wake_words or ["jarvis", "ei jarvis", "ta acordado"]
    raw_norm = _norm(message)
    norm = strip_wake_words(raw_norm, wake_words)
    guest = state == "guest"

    def public(reply: str, action: Optional[str] = None) -> dict[str, Any]:
        return {"reply": reply, "public": True, "requires_unlock": False, "action": action}

    def protected(reply: Optional[str] = None) -> dict[str, Any]:
        if guest:
            return {"reply": GUEST_REFUSAL, "public": False, "requires_unlock": False, "action": None}
        return {"reply": reply or UNLOCK_REPLY, "public": False, "requires_unlock": True, "action": "unlock"}

    if not norm or _AWAKE.fullmatch(norm) or raw_norm in {_norm(w) for w in wake_words}:
        return public(random.choice(AWAKE_REPLIES), "awake")

    if is_unlock_only(norm):
        if guest:
            return {"reply": GUEST_REFUSAL, "public": False, "requires_unlock": False, "action": None}
        return {"reply": UNLOCK_ONLY_REPLY, "public": False, "requires_unlock": True, "action": "unlock_only"}

    if _LOCK_CMD.search(norm) and len(norm.split()) <= 4:
        return public("Já estou em modo bloqueio, senhor." if not guest else "Modo visitante ativo.", "lock")

    if _SYSTEM_STATUS.fullmatch(norm):
        try:
            from modules import system_monitor
            snap = await asyncio.to_thread(system_monitor.snapshot)
            cpu = snap.get("cpu_percent")
            mem = snap.get("ram_percent")
            extra = []
            if isinstance(cpu, (int, float)):
                extra.append(f"processador em {round(cpu)} por cento")
            if isinstance(mem, (int, float)):
                extra.append(f"memória em {round(mem)} por cento")
            detail = (", " + " e ".join(extra)) if extra else ""
            return public(f"Sistemas operacionais, senhor{detail}.")
        except Exception:  # noqa: BLE001
            return public("Sistemas operacionais, senhor.")

    if guest and (_MUSIC.search(norm) and (_MUSIC_CONTEXT.search(norm) or len(norm.split()) <= 3)):
        music_norm = norm if "spotify" in norm else f"{norm} spotify"
        reply = await _local(tools._h_spotify, message, music_norm)
        if reply and not re.search(r"\b(?:abrir|abra|abre)\b", norm):
            return public(reply)

    for handler in (tools._h_timer, tools._h_calc, tools._h_weather, tools._h_focus):
        reply = await _local(handler, message, norm)
        if reply:
            return public(reply)

    quick = _quick_public(message, norm)
    if quick:
        return public(quick)

    if _NEWS.search(norm):
        return protected("Há novidades no radar, senhor. Para ler as manchetes, preciso liberar a central.")

    if _SUMMARY.search(norm) and not guest:
        return protected(_counts_summary())

    return protected()

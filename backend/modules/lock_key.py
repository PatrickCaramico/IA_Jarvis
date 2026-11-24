"""V9.4: TECLA DE ACESSO da tela de bloqueio.

Antes: a barra de espaço, um clique, duas palmas ou "abrir central" já ligavam a câmera, e o rosto reconhecido
abria a central. Qualquer pessoa podia começar a verificação (e, com o senhor passando atrás, ela abria).

Agora, com a tecla de acesso ligada (Configurações > Bloqueio), a verificação do rosto só começa quando a tecla
escolhida é apertada no teclado do PC. São dois passos: saber a tecla e ter o rosto. Espaço, clique, palmas e voz
não abrem mais a câmera; o PIN continua como reserva. Quem aperta outras teclas várias vezes vira uma "tentativa"
no relatório de segurança (com a foto, se a câmera vir alguém que não é de casa).

A tecla fica só no PC (data/tecla_acesso.json) e nunca é mostrada na tela bloqueada: as rotas públicas dizem apenas
se ela está ligada. Guardamos o código físico da tecla (KeyboardEvent.code, por exemplo "F8" ou "KeyJ").
"""
from __future__ import annotations

import hmac
import re
import time
from pathlib import Path
from typing import Optional

from config import settings
from core import safe_io

_PATH: Path = settings.DATA_DIR / "tecla_acesso.json"

# Códigos aceitos: letras, números, F1-F24 e algumas teclas de navegação. Espaço, Enter e Esc ficam de fora:
# todo mundo aperta essas sem querer (e o Esc fecha janelas). O P também: no bloqueio ele liga e desliga o microfone.
_CODE_RE = re.compile(r"^(?:Key[A-OQ-Z]|Digit[0-9]|Numpad[0-9]|F(?:[1-9]|1[0-9]|2[0-4])|Insert|Home|End|PageUp|PageDown|"
                      r"Pause|ScrollLock|Backquote|Minus|Equal|BracketLeft|BracketRight|Backslash|Semicolon|Quote|"
                      r"Comma|Period|Slash|IntlBackslash|IntlRo)$")
WRONG_LIMIT = 6        # teclas erradas seguidas para virar "tentativa"
WRONG_WINDOW_S = 60    # ... dentro deste tempo
ATTEMPT_COOLDOWN_S = 120  # depois de uma tentativa, a tecla fica 2 min sem valer (contra tentar tecla por tecla)

_wrong: list[float] = []
_last_attempt = 0.0


class LockKeyError(ValueError):
    """Tecla inválida (mensagem segura para a tela)."""


def label(code: str) -> str:
    """Nome amigável da tecla ("KeyJ" -> "J", "Digit7" -> "7", "F8" -> "F8")."""
    if code.startswith("Key") and len(code) == 4:
        return code[3]
    if code.startswith("Digit"):
        return code[5:]
    if code.startswith("Numpad"):
        return f"{code[6:]} (teclado numérico)"
    return code


def valid(code: str) -> bool:
    return bool(_CODE_RE.match(code or ""))


def _load() -> dict:
    try:
        data = safe_io.read_json(_PATH) if _PATH.exists() else {}
    except (OSError, ValueError):
        data = {}
    return data if isinstance(data, dict) else {}


def current() -> str:
    code = str(_load().get("code") or "")
    return code if valid(code) else ""


def enabled() -> bool:
    return bool(current())


def status(full: bool = False) -> dict:
    """full=True (central liberada): diz qual é a tecla; senão, só se está ligada."""
    code = current()
    out = {"enabled": bool(code)}
    if full and code:
        out.update(code=code, label=label(code))
    return out


def set_key(code: str) -> dict:
    code = (code or "").strip()
    if not valid(code):
        raise LockKeyError("Escolha uma letra, um número ou uma tecla F (F1 a F12). Espaço, Enter e Esc não valem.")
    safe_io.write_json(_PATH, {"code": code, "at": time.strftime("%Y-%m-%dT%H:%M:%S")})
    reset_wrong()
    return status(full=True)


def clear() -> dict:
    safe_io.write_json(_PATH, {})
    reset_wrong()
    return status()


def matches(code: Optional[str]) -> bool:
    """A tecla apertada é a de acesso? (sem tecla configurada, qualquer pedido vale)."""
    expected = current()
    if not expected:
        return True
    return hmac.compare_digest(str(code or "").encode(), expected.encode())


def reset_wrong() -> None:
    _wrong.clear()


def wrong_key(now: Optional[float] = None) -> bool:
    """Registra uma tecla errada. True = passou do limite (vira uma tentativa no relatório; no máximo 1 a cada 2 min)."""
    global _last_attempt
    now = time.time() if now is None else now
    _wrong[:] = [t for t in _wrong if now - t <= WRONG_WINDOW_S] + [now]
    if len(_wrong) < WRONG_LIMIT or now - _last_attempt < ATTEMPT_COOLDOWN_S:
        return False
    _last_attempt = now
    _wrong.clear()
    return True


def blocked(now: Optional[float] = None) -> int:
    """Segundos que faltam do bloqueio depois de muitas teclas erradas (0 = liberada). O PIN continua valendo."""
    now = time.time() if now is None else now
    if not _last_attempt:
        return 0
    return max(0, int(_last_attempt + ATTEMPT_COOLDOWN_S - now))


def check(code: Optional[str], now: Optional[float] = None) -> dict:
    """A tela bloqueada pergunta se a tecla apertada é a de acesso (antes de ligar a câmera).

    {"ok": é a tecla (e não está bloqueada), "attempt": esta tecla errada virou tentativa, "blocked": segundos}."""
    now = time.time() if now is None else now
    wait = blocked(now)
    if wait:
        return {"ok": False, "attempt": False, "blocked": wait}
    if matches(code):
        reset_wrong()
        return {"ok": True, "attempt": False, "blocked": 0}
    attempt = wrong_key(now)
    return {"ok": False, "attempt": attempt, "blocked": blocked(now)}


def reset_for_tests() -> None:
    global _last_attempt
    _last_attempt = 0.0
    _wrong.clear()

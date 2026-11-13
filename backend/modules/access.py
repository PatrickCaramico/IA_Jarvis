"""Estado de acesso do JARVIS: bloqueado, liberado ou modo visitante.

A tela de bloqueio deixa de ser só visual: enquanto o estado não for "unlocked",
as rotas pessoais respondem 403 (veja `is_allowed`). O estado vive na memória do
backend; ao reiniciar, o JARVIS volta bloqueado (como a própria tela de bloqueio).

Regras:
- Sem foto de perfil e sem PIN não há como liberar, então nada é bloqueado
  (exceto o modo visitante, que sempre restringe).
- A preferência `lock_backend_enforce` (padrão: ligada) permite voltar ao bloqueio
  só de interface. O modo visitante continua restrito mesmo com ela desligada.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

log = logging.getLogger("jarvis.access")

LOCKED, UNLOCKED, GUEST = "locked", "unlocked", "guest"

_lock = threading.Lock()
_state = LOCKED
_since = time.time()
_method: Optional[str] = None


def _has_credentials() -> bool:
    from modules import face, lock_pin
    try:
        return face.has_profile() or lock_pin.has_pin()
    except Exception:  # noqa: BLE001
        return face.has_profile()


def enforcement_active() -> bool:
    from modules import prefs
    try:
        enforce = bool(prefs._load().get("lock_backend_enforce", True))
    except Exception:  # noqa: BLE001
        enforce = True
    return enforce and _has_credentials()


def get_state() -> str:
    return _state


def effective_state() -> str:
    """Estado que vale para as regras: sem credenciais (ou sem bloqueio real), conta como liberado."""
    if _state == GUEST:
        return GUEST
    if _state == LOCKED and not enforcement_active():
        return UNLOCKED
    return _state


def is_restricted() -> bool:
    return effective_state() != UNLOCKED


def snapshot() -> dict:
    return {
        "state": _state,
        "effective": effective_state(),
        "since": _since,
        "method": _method,
        "enforced": enforcement_active(),
    }


def _set(state: str, method: Optional[str] = None) -> dict:
    global _state, _since, _method
    with _lock:
        _state = state
        _since = time.time()
        _method = method
    log.info("Estado de acesso: %s (%s)", state, method or "-")
    if state != UNLOCKED:
        # V4.5: bloqueado (ou visitante), o PC volta para o perfil principal (o dono).
        try:
            from modules import profiles

            profiles.activate_owner()
        except Exception:  # noqa: BLE001
            log.debug("Não foi possível voltar ao perfil principal", exc_info=True)
    return snapshot()


def unlock(method: str) -> dict:
    return _set(UNLOCKED, method)


def lock(reason: str = "manual") -> dict:
    return _set(LOCKED, reason)


def enter_guest() -> dict:
    return _set(GUEST, "guest")


def exit_guest() -> dict:
    # Sair do modo visitante volta para o bloqueio: liberar exige rosto ou PIN.
    return _set(LOCKED, "guest_exit")


def reset_for_tests(state: str = LOCKED) -> None:
    _set(state, "test")


# ------------------------------------------------------------------ política de rotas
# Rotas liberadas em QUALQUER estado (tela de bloqueio, sentinela e visitante).
# Tudo o que começa com /api e não está aqui exige acesso liberado (negação por padrão).
_PUBLIC_EXACT = {
    ("GET", "/api/health"),
    ("GET", "/api/system/update/status"),  # V6.7.2: bolinha de atualização no botão ATUALIZAR do bloqueio
    ("POST", "/api/system/optimize"),  # V7.2: ⚡ OTIMIZAR na tela de bloqueio (só limpa sobras de áudio)
    ("GET", "/api/integrations/spotify/track"),  # V4.2.2: a rota confere se o cartão está ligado no bloqueio
    ("GET", "/api/presence"),
    ("GET", "/api/profile"),          # devolve só has_photo quando restrito (sem nome)
    ("GET", "/api/prefs"),            # devolve só as chaves públicas quando restrito
    ("GET", "/api/access"),
    ("POST", "/api/access/lock"),
    ("GET", "/api/auth/token"),       # já é restrita ao computador local
    ("POST", "/api/auth/verify"),
    ("GET", "/api/auth/pin/status"),
    ("POST", "/api/auth/pin"),
    ("POST", "/api/auth/device/unlock"),  # V6.0: entrar com a digital no app (chave do aparelho)
    ("POST", "/api/guest/enter"),
    ("POST", "/api/guest/exit"),
    ("POST", "/api/chat"),            # quando restrito, só responde pedidos públicos (modules/sentinel.py)
    ("POST", "/api/cancel"),
    ("POST", "/api/speak"),
    ("GET", "/api/weather"),
    ("GET", "/api/timers"),
    ("GET", "/api/fan/match"),
    ("POST", "/api/fan/toggle"),      # V4.4: botão do Modo Torcedor no bloqueio (só o visual do clube)
    ("POST", "/api/background"),      # V5.9.1: botão de fundo no bloqueio (só o visual)
    ("POST", "/api/lock/mic"),        # V6.5.20: microfone do bloqueio lembra se ficou ligado (só esse ajuste)
    ("GET", "/api/audio"),            # V6.5.8: botão de áudio do bloqueio (caixa de som e microfone do PC)
    ("POST", "/api/audio"),
    ("POST", "/api/audio/test"),
    ("GET", "/api/mobile"),           # V4.5: página de download do app Android (sem token, sem dados)
    ("GET", "/api/mobile/app.apk"),
    ("GET", "/api/mobile/info"),      # QR de download da Sentinela
    ("GET", "/api/mobile/notifications"),  # avisos do celular pareado (a rota exige a chave sempre)
    ("POST", "/api/mobile/pair-pin"),  # parear o app com o PIN do dono (limite de tentativas do PIN)
    ("GET", "/api/profiles/lock-info"),  # V4.5: só se dá para criar perfil e se pede PIN (sem nomes)
    ("POST", "/api/profiles"),        # criar pessoa nova pelo bloqueio (exige o PIN do dono, se houver)
    ("GET", "/api/water"),            # cartão "água de hoje" da tela de bloqueio
    ("GET", "/api/lock/status"),      # V5.6.1: cartão de sistemas do bloqueio (sem nada pessoal)
    ("GET", "/api/lock/public-info"),  # V5.8: cotações e manchete do bloqueio (informação pública)
    ("POST", "/api/health/biometrics"),  # recebimento do relógio (Android Sync) não pode quebrar
    ("POST", "/api/system/update"),   # botão ATUALIZAR do bloqueio (a rota aceita só o próprio PC)
    ("GET", "/api/alarms/ringing"),   # V5.1: alarme tocando (sem o rótulo)
    ("POST", "/api/alarms/stop"),     # PARAR e SONECA funcionam com a central bloqueada
    ("POST", "/api/alarms/snooze"),
}
_PUBLIC_PREFIX = (
    ("GET", "/api/integrations/google-calendar/callback"),  # o estado OAuth já protege
    ("GET", "/api/integrations/spotify/callback"),
)
# Extras do modo visitante: controles de música.
_GUEST_EXTRA = {
    ("GET", "/api/integrations/spotify/status"),
    ("GET", "/api/integrations/spotify/now-playing"),
    ("POST", "/api/integrations/spotify/control"),
}
# Exceção: trocar a foto bloqueado só vale quando NÃO há PIN (senão vira atalho para burlar o rosto).
_PROFILE_WRITE = ("POST", "/api/profile")


def is_allowed(method: str, path: str, state: Optional[str] = None) -> bool:
    """Diz se a rota pode ser usada no estado informado (padrão: estado efetivo atual)."""
    state = state or effective_state()
    method = method.upper()
    if not path.startswith("/api"):
        return True
    if state == UNLOCKED:
        return True
    key = (method, path.rstrip("/") or "/")
    if method == "GET" and path.startswith("/api/fan/logo"):
        return True
    if key in _PUBLIC_EXACT:
        return True
    if any(method == m and path.startswith(p) for m, p in _PUBLIC_PREFIX):
        return True
    if state == GUEST and key in _GUEST_EXTRA:
        return True
    if key == _PROFILE_WRITE and state == LOCKED:
        from modules import lock_pin
        return not lock_pin.has_pin()
    return False


def denial_detail(state: Optional[str] = None) -> dict:
    state = state or effective_state()
    if state == GUEST:
        return {"detail": "Recurso indisponível no modo visitante.", "code": "guest"}
    return {"detail": "Central bloqueada. Faça o escaneamento facial ou use o PIN.", "code": "locked"}

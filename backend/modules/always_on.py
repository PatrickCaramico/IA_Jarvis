"""V8.12.3: SEMPRE LIGADO — o JARVIS fica no ar sem o usuário precisar lembrar de ligar.

Antes, ligar junto com o Windows era opcional (desligado até alguém marcar) e nada impedia o PC de dormir: o site
abria em "RECONECTANDO AO SEU JARVIS" toda vez que o notebook suspendia ou reiniciava. Agora, com "always_on"
(padrão ligado):
  - o atalho da Inicialização do Windows é criado sozinho ao ligar o backend (modules/autostart.py);
  - se o guardião (scripts/guardiao.py) não está dando sinal de vida, o backend liga um de novo;
  - com "keep_awake" (padrão ligado), o PC não entra em suspensão por inatividade enquanto está NA TOMADA
    (a tela ainda apaga normalmente; na bateria nada muda, para não descarregar o notebook).
Desligar "ligar junto com o Windows" (configurações, voz ou rota) desliga o "always_on" também, e ele não volta sozinho.
"""
from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from modules import autostart, prefs

log = logging.getLogger("jarvis.always_on")

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
LOGS = ROOT / "logs"
BEAT_PATH = LOGS / "guardiao.beat"
STARTING_FLAG = LOGS / "iniciando.flag"
BEAT_STALE_S = 120          # o guardião escreve o sinal a cada 10 s
STARTING_GRACE_S = 300      # o Iniciar-JARVIS.bat ainda está ligando/atualizando
GUARDIAN_FIRST_CHECK_S = 180  # o Iniciar liga o guardião logo depois do backend: dá tempo antes de conferir
TICK_S = 60                 # a suspensão do Windows conta minutos: avisar a cada 1 min basta

# SetThreadExecutionState: ES_SYSTEM_REQUIRED zera o contador de inatividade da suspensão (não segura a tela).
ES_SYSTEM_REQUIRED = 0x00000001


def _is_windows() -> bool:
    return os.name == "nt"


def enabled() -> bool:
    return bool(prefs.get_all().get("always_on", True))


def keep_awake_enabled() -> bool:
    data = prefs.get_all()
    return bool(data.get("always_on", True) and data.get("keep_awake", True))


# ------------------------------------------------------------------ ligar junto com o Windows
def ensure_autostart() -> dict:
    """Cria o atalho da Inicialização se o "sempre ligado" está ativo e ele ainda não existe."""
    st = autostart.status()
    if not enabled() or not st["available"] or st["enabled"]:
        return {**st, "changed": False}
    res = autostart.enable()
    if res.get("ok"):
        log.info("Sempre ligado: atalho da Inicialização do Windows criado.")
    else:
        log.warning("Sempre ligado: não consegui criar o atalho da Inicialização (%s).", res.get("message"))
    return {**res, "changed": bool(res.get("ok"))}


def set_autostart(on: bool) -> dict:
    """Liga/desliga junto com o Windows pela escolha do usuário. Desligar também desliga o "sempre ligado",
    senão o backend recriaria o atalho no próximo início (o usuário pediu para não ligar sozinho)."""
    res = autostart.enable() if on else autostart.disable()
    if res.get("ok"):
        prefs.update(always_on=bool(on))
    return res


# ------------------------------------------------------------------ PC acordado (na tomada)
def on_ac_power() -> bool:
    """Na tomada? PC de mesa (sem bateria) conta como tomada. Sem como saber: considera bateria (não segura)."""
    try:
        import psutil

        battery = psutil.sensors_battery()
    except Exception:  # noqa: BLE001 - sensor indisponível: não arrisca descarregar o notebook
        log.debug("Não consegui ler a bateria", exc_info=True)
        return False
    return battery is None or bool(battery.power_plugged)


def keep_awake_tick() -> bool:
    """Avisa o Windows que o sistema está em uso (só zera a contagem da suspensão). Devolve se avisou."""
    if not _is_windows() or not keep_awake_enabled() or not on_ac_power():
        return False
    try:
        import ctypes

        ok = bool(ctypes.windll.kernel32.SetThreadExecutionState(ES_SYSTEM_REQUIRED))
    except (OSError, AttributeError):
        log.exception("Não consegui segurar a suspensão do Windows")
        return False
    return ok


# ------------------------------------------------------------------ guardião
def _age(path: Path, now: float) -> Optional[float]:
    try:
        return now - path.stat().st_mtime
    except OSError:
        return None


def guardian_alive(now: Optional[float] = None) -> bool:
    age = _age(BEAT_PATH, now or time.time())
    return age is not None and age < BEAT_STALE_S


def ensure_guardian(now: Optional[float] = None) -> bool:
    """Liga o guardião se ele não dá sinal de vida (caiu sozinho). Devolve se ligou."""
    now = now or time.time()
    if not _is_windows() or not enabled() or guardian_alive(now):
        return False
    starting = _age(STARTING_FLAG, now)
    if starting is not None and starting < STARTING_GRACE_S:
        return False  # o Iniciar-JARVIS.bat está trabalhando e liga o guardião no fim
    pyw = autostart.pythonw()
    script = SCRIPTS / "guardiao.py"
    if pyw is None or not script.is_file():
        return False
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    try:
        subprocess.Popen([str(pyw), str(script)], cwd=str(SCRIPTS), creationflags=flags,  # noqa: S603
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
    except OSError:
        log.exception("Não consegui ligar o guardião")
        return False
    log.warning("Sempre ligado: o guardião não dava sinal de vida; liguei de novo.")
    return True


def status() -> dict:
    data = prefs.get_all()
    return {
        "always_on": bool(data.get("always_on", True)),
        "keep_awake": bool(data.get("keep_awake", True)),
        "autostart": autostart.status(),
        "guardian": guardian_alive(),
        "on_ac": on_ac_power(),
        "windows": _is_windows(),
    }


async def always_on_loop() -> None:
    """Serviço de fundo: atalho no início, PC acordado a cada minuto e guardião conferido depois de 3 min."""
    try:
        await asyncio.to_thread(ensure_autostart)
    except Exception:  # noqa: BLE001 - não derruba o serviço; tenta de novo no próximo início
        log.exception("Sempre ligado: falha ao conferir o atalho da Inicialização")
    started = time.monotonic()
    while True:
        try:
            await asyncio.to_thread(keep_awake_tick)
            if time.monotonic() - started >= GUARDIAN_FIRST_CHECK_S:
                await asyncio.to_thread(ensure_guardian)
        except Exception:  # noqa: BLE001
            log.exception("Sempre ligado: falha no laço")
        await asyncio.sleep(TICK_S)

"""V9.4.1: quanto tempo o JARVIS levou para ligar, por etapa (para achar a demora em vez de adivinhar).

Antes não havia como saber se o minuto de "RECONECTANDO AO SEU JARVIS" vinha do Windows (entrada, atalho da
Inicialização), do Iniciar-JARVIS.bat ou do próprio backend. Agora, ao ficar pronto, o backend registra no log e
devolve em /api/health (campo "startup"):
  - windows_to_process_s: do Windows ligar até o processo do backend nascer (atalho, espera, .bat, PowerShell);
  - process_to_ready_s: do processo nascer até responder (importações, inicialização);
  - ready_at: a hora em que ficou pronto.
Só números e horas: nada pessoal.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Optional

log = logging.getLogger("jarvis.startup")

_info: dict = {}


def measure(now: Optional[float] = None, process_start: Optional[float] = None, boot: Optional[float] = None) -> dict:
    """Parte pura: os tempos a partir das horas (segundos desde 1970)."""
    now = time.time() if now is None else now
    out: dict = {"ready_at": datetime.fromtimestamp(now).strftime("%H:%M:%S")}
    if process_start:
        out["process_to_ready_s"] = round(max(0.0, now - process_start), 1)
        if boot and process_start >= boot:
            gap = process_start - boot
            # só faz sentido logo depois de ligar o PC (senão é o tempo desde o último boot, horas ou dias)
            if gap <= 30 * 60:
                out["windows_to_process_s"] = round(gap, 1)
    return out


def mark_ready() -> dict:
    global _info
    process_start = boot = None
    try:
        import os

        import psutil

        process_start = psutil.Process(os.getpid()).create_time()
        boot = psutil.boot_time()
    except Exception:  # noqa: BLE001 - sem psutil: registra só a hora
        log.debug("Sem psutil para medir a subida", exc_info=True)
    _info = measure(process_start=process_start, boot=boot)
    parts = [f"pronto às {_info['ready_at']}"]
    if "process_to_ready_s" in _info:
        parts.append(f"{_info['process_to_ready_s']:.1f} s desde que o processo começou")
    if "windows_to_process_s" in _info:
        parts.append(f"o processo começou {_info['windows_to_process_s']:.0f} s depois de o Windows ligar")
    log.info("Subida do backend: %s.", "; ".join(parts))
    return _info


def info() -> dict:
    return dict(_info)

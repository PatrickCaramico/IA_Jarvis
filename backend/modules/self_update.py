"""Atualizar e reiniciar o JARVIS pelo botão ATUALIZAR da tela de bloqueio.

1. Baixa a versão mais nova do GitHub (git pull --ff-only: nunca mistura nem apaga mudanças locais).
2. Reinicia pelo Iniciar-JARVIS.bat no modo "site": ele encerra este processo, refaz a interface local
   se ela mudou e sobe tudo de novo, sem abrir aba nova (a central aberta reconecta sozinha).

BOOT_ID muda a cada início do backend: a central usa isso para saber que a versão nova já subiu.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from pathlib import Path

log = logging.getLogger("jarvis.update")

ROOT = Path(__file__).resolve().parents[2]
START_BAT = ROOT / "Iniciar-JARVIS.bat"
BOOT_ID = str(int(time.time() * 1000))
GIT_TIMEOUT = 90


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=GIT_TIMEOUT,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def pull() -> dict:
    """Baixa a atualização. Retorna {ok, changed, before, after, message}. Roda fora do loop (to_thread)."""
    if not shutil.which("git") or not (ROOT / ".git").exists():
        return {"ok": True, "changed": False, "before": "", "after": "",
                "message": "Sem Git nesta pasta: só reinicio os sistemas."}
    try:
        before = _git("rev-parse", "--short", "HEAD").stdout.strip()
        result = _git("pull", "--ff-only")
        after = _git("rev-parse", "--short", "HEAD").stdout.strip()
    except subprocess.TimeoutExpired:
        return {"ok": False, "changed": False, "before": "", "after": "",
                "message": "O GitHub demorou demais para responder. Confira a internet e tente de novo."}
    except OSError as exc:
        return {"ok": False, "changed": False, "before": "", "after": "", "message": f"Não consegui rodar o Git: {exc}"}
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        log.warning("git pull falhou: %s", " | ".join(detail[-3:]))
        return {"ok": False, "changed": False, "before": before, "after": after,
                "message": "Não consegui baixar a atualização (há mudanças locais nesta pasta ou o GitHub recusou). "
                           "Nada foi alterado."}
    changed = bool(before and after and before != after)
    log.info("Atualização: %s -> %s", before, after)
    return {"ok": True, "changed": changed, "before": before, "after": after,
            "message": f"Atualizado de {before} para {after}." if changed else "Já estava na versão mais nova."}


def restart() -> bool:
    """Chama o Iniciar-JARVIS.bat em segundo plano (ele encerra este backend e sobe o novo)."""
    if os.name != "nt" or not START_BAT.exists():
        log.error("Reinício automático só existe no Windows, com o Iniciar-JARVIS.bat.")
        return False
    # Console escondido (não DETACHED_PROCESS: sem console, cada PowerShell do .bat abriria uma janela).
    # Grupo próprio: o .bat continua vivo quando encerra este backend.
    flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(  # noqa: S603 - comando fixo, sem nada vindo do pedido
        ["cmd.exe", "/c", str(START_BAT), "site"],
        cwd=str(ROOT),
        creationflags=flags,
        close_fds=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    log.info("Reiniciando o JARVIS pelo Iniciar-JARVIS.bat (modo site).")
    return True

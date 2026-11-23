"""V8.11: liga o JARVIS em segundo plano, sem janela (usado pelo atalho da Inicialização do Windows).

    pythonw scripts/ligar_jarvis.py --logon   # ao entrar no Windows (espera o Windows assentar)
    pythonw scripts/ligar_jarvis.py           # agora

Se o JARVIS já está no ar, não faz nada. Senão roda o Iniciar-JARVIS.bat no modo "site" (liga tudo, não abre aba)
com o console escondido. Registro em logs/ligar.log.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BAT = ROOT / "Iniciar-JARVIS.bat"
HEALTH = "http://127.0.0.1:8000/api/health"
LOGON_DELAY_S = 20  # deixa o Windows terminar de abrir (rede, área de trabalho) antes de ligar

log = logging.getLogger("jarvis.ligar")


def backend_up(timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(HEALTH, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:  # noqa: BLE001
        return False


def start_command(bat: Path = BAT) -> list[str]:
    return ["cmd.exe", "/c", str(bat), "site"]


def start_hidden(bat: Path = BAT) -> bool:
    """Roda o Iniciar-JARVIS.bat sem mostrar o console (e num grupo próprio: sobrevive a quem chamou)."""
    if not bat.is_file():
        log.error("Iniciar-JARVIS.bat não encontrado em %s", bat)
        return False
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    info = None
    if hasattr(subprocess, "STARTUPINFO"):
        info = subprocess.STARTUPINFO()
        info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        info.wShowWindow = 0  # SW_HIDE
    subprocess.Popen(start_command(bat), cwd=str(bat.parent), creationflags=flags, startupinfo=info,  # noqa: S603
                     close_fds=True)
    return True


def main(argv: list[str]) -> int:
    (ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(filename=ROOT / "logs" / "ligar.log", level=logging.INFO, encoding="utf-8",
                        format="%(asctime)s %(message)s")
    if "--logon" in argv:
        time.sleep(LOGON_DELAY_S)
    if backend_up():
        log.info("O JARVIS já estava ligado.")
        return 0
    log.info("Ligando o JARVIS%s.", " (entrada no Windows)" if "--logon" in argv else "")
    return 0 if start_hidden() else 1


if __name__ == "__main__":
    if os.name != "nt":
        print("Só no Windows.")
        sys.exit(1)
    sys.exit(main(sys.argv[1:]))

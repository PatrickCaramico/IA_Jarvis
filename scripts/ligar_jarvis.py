"""V8.11: liga o JARVIS em segundo plano, sem janela (usado pelo atalho da Inicialização do Windows).

    pythonw scripts/ligar_jarvis.py --logon   # ao entrar no Windows (espera o Windows assentar)
    pythonw scripts/ligar_jarvis.py           # agora
    pythonw scripts/ligar_jarvis.py --url jarvis://atualizar   # V9.5.3: atalho do site (atualiza e liga)

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
# V9.4: eram 20 s fixos ao entrar no Windows, somados à inicialização (a central ficava "procurando" o PC por ~1 min).
# 5 s bastam para a área de trabalho assentar; o backend não depende da rede para subir.
LOGON_DELAY_S = 5

log = logging.getLogger("jarvis.ligar")


def backend_up(timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(HEALTH, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:  # noqa: BLE001
        return False


def start_command(bat: Path = BAT, mode: str = "site") -> list[str]:
    return ["cmd.exe", "/c", str(bat), mode if mode in MODES else "site"]


# V9.5.3: o atalho jarvis:// agora passa o endereço para cá. Só duas coisas são aceitas: ligar (qualquer endereço) ou
# atualizar e ligar (jarvis://atualizar). O endereço nunca vira comando: só escolhe uma das duas opções fixas.
MODES = ("site", "atualizar")


def mode_from_url(url: str) -> str:
    u = (url or "").strip().lower()
    return "atualizar" if u.startswith("jarvis://atualizar") else "site"


def start_hidden(bat: Path = BAT, mode: str = "site") -> bool:
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
    subprocess.Popen(start_command(bat, mode), cwd=str(bat.parent), creationflags=flags, startupinfo=info,  # noqa: S603
                     close_fds=True)
    return True


def main(argv: list[str]) -> int:
    (ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(filename=ROOT / "logs" / "ligar.log", level=logging.INFO, encoding="utf-8",
                        format="%(asctime)s %(message)s")
    if "--logon" in argv:
        time.sleep(LOGON_DELAY_S)
    mode = mode_from_url(argv[argv.index("--url") + 1]) if "--url" in argv and argv.index("--url") + 1 < len(argv) else "site"
    if mode == "atualizar":  # V9.5.3: botão ⟳ ATUALIZAR E LIGAR da central
        log.info("Atualizando e ligando o JARVIS (botão da central).")
        return 0 if start_hidden(mode="atualizar") else 1
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

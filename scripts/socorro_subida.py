"""V9.5.2: SOCORRO DA SUBIDA — o Iniciar-JARVIS.bat chama quando o backend não respondeu a tempo.

Antes, se o JARVIS caía ao ligar (uma atualização trouxe uma biblioteca nova que não estava instalada, a porta ficou
presa), ele ficava fora do ar em silêncio: a central passava minutos "procurando o PC" e nada dizia o porquê.
Agora este script:
  1. espera mais um pouco, se o JARVIS só está demorando (PC pesado logo depois de ligar);
  2. lê o motivo da queda em logs/backend-erro.log (o run_server.py grava lá);
  3. faltando biblioteca: instala o requirements.txt e liga o backend de novo (uma vez);
  4. registra tudo em logs/ligar.log.

    python scripts/socorro_subida.py 0.0.0.0 true
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
LOGS = ROOT / "logs"
CRASH_LOG = LOGS / "backend-erro.log"
HEALTH = "http://127.0.0.1:8000/api/health"
EXTRA_WAIT_S = 45  # ainda pode estar só demorando
RECENT_S = 10 * 60  # o erro registrado vale se for desta subida
PIP_TIMEOUT_S = 15 * 60

log = logging.getLogger("jarvis.socorro")


def backend_up(timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(HEALTH, timeout=timeout) as resp:  # noqa: S310 - endereço fixo local
            return resp.status == 200
    except Exception:  # noqa: BLE001
        return False


def wait_up(seconds: float, sleep=time.sleep, up=backend_up) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if up():
            return True
        sleep(1.0)
    return up()


def last_crash(path: Path = CRASH_LOG, now: Optional[float] = None) -> str:
    """O último registro de queda, se for recente (desta subida); senão ""."""
    try:
        if (now or time.time()) - path.stat().st_mtime > RECENT_S:
            return ""
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    marker = text.rfind("=====")
    start = text.rfind("\n=====", 0, marker) if marker > 0 else -1
    return text[start + 1:] if start >= 0 else text[-4000:]


def diagnose(text: str) -> Optional[str]:
    """Por que caiu: "deps" (biblioteca faltando), "port" (porta ocupada), "other" ou None (sem registro)."""
    if not text.strip():
        return None
    if "ModuleNotFoundError" in text or "ImportError" in text or "No module named" in text:
        return "deps"
    if "10048" in text or "address already in use" in text.lower() or "porta 8000 ocupada" in text:
        return "port"
    return "other"


def install_requirements(python: Path) -> bool:
    log.info("Faltava biblioteca: instalando o requirements.txt.")
    try:
        done = subprocess.run(  # noqa: S603 - comando fixo
            [str(python), "-m", "pip", "install", "--disable-pip-version-check", "-q", "-r",
             str(BACKEND / "requirements.txt")],
            cwd=str(BACKEND), timeout=PIP_TIMEOUT_S, capture_output=True, text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.error("A instalação das bibliotecas falhou: %s", exc)
        return False
    if done.returncode != 0:
        log.error("A instalação das bibliotecas falhou:\n%s", (done.stderr or done.stdout)[-2000:])
        return False
    return True


def start_backend(python: Path, host: str, netmode: str) -> None:
    env = {**os.environ, "JARVIS_NETWORK_MODE": netmode}
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen(  # noqa: S603 - comando fixo
        [str(python), "run_server.py", "--host", host, "--port", "8000"],
        cwd=str(BACKEND), env=env, creationflags=flags, close_fds=True,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def rescue(host: str = "0.0.0.0", netmode: str = "true", *, up=backend_up, wait=wait_up, crash=last_crash,  # noqa: S104
           install=install_requirements, start=start_backend, python: Optional[Path] = None) -> str:
    """Devolve o que aconteceu: "ok", "slow-ok", "fixed", "failed-deps", "port", "other" ou "down"."""
    if up():
        return "ok"
    if wait(EXTRA_WAIT_S):
        log.info("O JARVIS só estava demorando: respondeu.")
        return "slow-ok"
    reason = diagnose(crash())
    python = python or BACKEND / "venv" / "Scripts" / "python.exe"
    if reason == "deps":
        if not install(python):
            return "failed-deps"
        start(python, host, netmode)
        if wait(90):
            log.info("Bibliotecas instaladas: o JARVIS ligou.")
            return "fixed"
        return "failed-deps"
    if reason == "port":
        log.error("A porta 8000 estava ocupada por outro programa. Rode o Parar-JARVIS.bat e ligue de novo.")
        return "port"
    if reason == "other":
        log.error("O JARVIS caiu ao ligar. O motivo está em logs/backend-erro.log.")
        return "other"
    log.error("O JARVIS não respondeu e não deixou motivo registrado (o guardião tenta religar em 2 min).")
    return "down"


def main(argv: list[str]) -> int:
    LOGS.mkdir(exist_ok=True)
    logging.basicConfig(filename=LOGS / "ligar.log", level=logging.INFO, encoding="utf-8",
                        format="%(asctime)s %(message)s")
    host = argv[0] if argv else "0.0.0.0"  # noqa: S104 - o mesmo do Iniciar (rede de casa)
    netmode = argv[1] if len(argv) > 1 else "true"
    result = rescue(host, netmode)
    log.info("Socorro da subida: %s", result)
    return 0 if result in {"ok", "slow-ok", "fixed"} else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

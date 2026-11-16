"""V8.2.3: monta a interface nova (npm run build) em SEGUNDO PLANO, com o JARVIS já ligado.

O Iniciar-JARVIS.bat chama isto quando a interface pronta do site não serviu: o JARVIS liga na hora com a
interface atual e esta monta a nova sem segurar nada. Registro em logs/build.log. Não roda dois ao mesmo tempo.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
LOGS = ROOT / "logs"
LOCK = LOGS / "build.running"
MAX_AGE = 20 * 60


def main() -> int:
    LOGS.mkdir(exist_ok=True)
    if LOCK.exists() and time.time() - LOCK.stat().st_mtime < MAX_AGE:
        return 0  # já tem uma montagem rodando
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm:
        return 1
    LOCK.write_text(str(os.getpid()))
    try:
        with open(LOGS / "build.log", "w", encoding="utf-8", errors="replace") as out:
            out.write(f"Montando a interface nova em segundo plano ({time.strftime('%d/%m %H:%M:%S')})\n")
            out.flush()
            started = time.time()
            code = subprocess.call([npm, "run", "build"], cwd=str(FRONTEND), stdout=out, stderr=subprocess.STDOUT,  # noqa: S603
                                   stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            out.write(f"\nFim: código {code} em {time.time() - started:.0f} s\n")
        return code
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())

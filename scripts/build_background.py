"""V8.2.3: monta a interface nova (npm run build) em SEGUNDO PLANO, com o JARVIS já ligado.

O Iniciar-JARVIS.bat chama isto quando a interface pronta do site não serviu: o JARVIS liga na hora com a
interface atual e esta monta a nova sem segurar nada. Registro em logs/build.log. Não roda dois ao mesmo tempo.

V8.3.1: antes de montar no PC (que no PC do Patrick leva mais de 10 minutos), tenta de novo a interface PRONTA do
site por até 10 minutos: logo depois de uma versão nova o site ainda está montando, e o .bat só esperava 20 s.
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
PREBUILT_WAIT = 10 * 60


def try_prebuilt(out, wait_s: float = PREBUILT_WAIT) -> bool:
    """A interface pronta do site (scripts/prebuilt.py), esperando o site terminar de montar."""
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("jarvis_prebuilt", ROOT / "scripts" / "prebuilt.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        def log(msg: str) -> None:
            out.write(msg.strip() + "\n")
            out.flush()
        return bool(mod.fetch(FRONTEND, log=log, wait_s=wait_s))
    except Exception as exc:  # noqa: BLE001
        out.write(f"Interface pronta indisponível: {exc}\n")
        return False


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
            if try_prebuilt(out):
                out.write(f"\nFim: interface pronta do site instalada em {time.time() - started:.0f} s (sem montar no PC)\n")
                return 0
            out.write("Montando aqui no PC (npm run build)...\n")
            out.flush()
            code = subprocess.call([npm, "run", "build"], cwd=str(FRONTEND), stdout=out, stderr=subprocess.STDOUT,  # noqa: S603
                                   stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            out.write(f"\nFim: código {code} em {time.time() - started:.0f} s\n")
        return code
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())

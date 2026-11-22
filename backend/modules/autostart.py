"""V8.11: ligar o JARVIS junto com o Windows (sem janela e sem abrir aba).

Cria (ou apaga) o atalho "JARVIS.lnk" na pasta Inicializar do usuário (sem administrador). Ao entrar no Windows,
o atalho roda o scripts/ligar_jarvis.py com o pythonw (sem console): ele espera o Windows assentar e chama o
Iniciar-JARVIS.bat no modo "site" (liga tudo em segundo plano, sem abrir aba nova). O guardião (scripts/guardiao.py)
mantém o JARVIS no ar depois disso.

Liga/desliga: Configurações › Diagnóstico & Backup › Inicialização, "liga o JARVIS junto com o Windows" (skill) ou
Instalar-JARVIS-no-Windows.bat / Remover-JARVIS-do-Windows.bat.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

log = logging.getLogger("jarvis.autostart")

ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "scripts" / "ligar_jarvis.py"
SHORTCUT_NAME = "JARVIS.lnk"
PS_TIMEOUT_S = 20


def _is_windows() -> bool:
    return os.name == "nt"


def startup_dir() -> Optional[Path]:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def shortcut_path() -> Optional[Path]:
    folder = startup_dir()
    return folder / SHORTCUT_NAME if folder else None


def pythonw() -> Optional[Path]:
    """O pythonw.exe do ambiente do JARVIS (roda sem abrir janela de console)."""
    for cand in (ROOT / "backend" / "venv" / "Scripts" / "pythonw.exe", Path(sys.executable).with_name("pythonw.exe")):
        if cand.is_file():
            return cand
    return None


def status() -> dict:
    path = shortcut_path()
    available = _is_windows() and path is not None and pythonw() is not None
    return {"available": available, "enabled": bool(path and path.is_file()),
            "message": "" if available else "Ligar junto com o Windows só funciona no PC com Windows."}


def enable() -> dict:
    """Cria o atalho na Inicialização. Os caminhos vão por variável de ambiente (nada é montado como comando)."""
    st = status()
    if not st["available"]:
        return {**st, "ok": False}
    path, pyw = shortcut_path(), pythonw()
    path.parent.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "JARVIS_LNK": str(path), "JARVIS_PYW": str(pyw), "JARVIS_ARGS": f'"{LAUNCHER}" --logon',
           "JARVIS_DIR": str(ROOT)}
    script = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:JARVIS_LNK); $s.TargetPath=$env:JARVIS_PYW; "
              "$s.Arguments=$env:JARVIS_ARGS; $s.WorkingDirectory=$env:JARVIS_DIR; $s.WindowStyle=7; "
              "$s.Description='JARVIS - liga junto com o Windows'; $s.Save()")
    try:
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], env=env, capture_output=True,
                       timeout=PS_TIMEOUT_S, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False)
    except (OSError, subprocess.SubprocessError):
        log.exception("Não consegui criar o atalho da Inicialização")
    ok = path.is_file()
    if ok:
        log.info("JARVIS vai ligar junto com o Windows (%s).", path)
    return {**status(), "ok": ok, "message": "" if ok else "Não consegui criar o atalho na Inicialização do Windows."}


def disable() -> dict:
    path = shortcut_path()
    try:
        if path and path.is_file():
            path.unlink()
            log.info("JARVIS não liga mais junto com o Windows.")
    except OSError:
        log.exception("Não consegui apagar o atalho da Inicialização")
        return {**status(), "ok": False, "message": "Não consegui apagar o atalho da Inicialização."}
    return {**status(), "ok": True}


if __name__ == "__main__":  # Instalar-JARVIS-no-Windows.bat / Remover-JARVIS-do-Windows.bat
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    result = enable() if action == "instalar" else disable() if action == "remover" else status()
    print("OK" if result.get("ok", result.get("enabled")) else "ERRO", result.get("message", ""))
    sys.exit(0 if result.get("ok", True) else 1)

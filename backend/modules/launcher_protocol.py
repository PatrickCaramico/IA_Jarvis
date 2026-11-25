"""V9.5.3: o atalho jarvis:// (botão LIGAR O JARVIS da central do site) entende "atualizar e ligar".

Até a 9.5.2 o atalho rodava o Iniciar-JARVIS.bat direto e ignorava o endereço. Agora ele chama o
scripts/ligar_jarvis.py com o endereço, que aceita só duas opções fixas (ligar, ou jarvis://atualizar = baixar a
versão nova e ligar). Quem já tinha instalado o atalho (Instalar-Botao-Ligar.bat) não precisa rodar de novo: ao ligar,
o JARVIS troca o comando antigo pelo novo. Só mexe no atalho que já existe (nunca cria sem o usuário pedir), só no
usuário atual (HKCU, sem administrador) e só no Windows.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from modules import autostart

log = logging.getLogger("jarvis.launcher")

ROOT = Path(__file__).resolve().parents[2]
KEY = r"Software\Classes\jarvis\shell\open\command"


def wanted_command(pythonw: Path, root: Path = ROOT) -> str:
    return f'"{pythonw}" "{root / "scripts" / "ligar_jarvis.py"}" --url "%1"'


def needs_update(current: Optional[str], wanted: str) -> bool:
    """Troca só o comando do JARVIS (o antigo, que roda o Iniciar-JARVIS.bat, ou de outra pasta)."""
    if not current or current == wanted:
        return False
    low = current.lower()
    return "iniciar-jarvis.bat" in low or "ligar_jarvis.py" in low


def _is_windows() -> bool:
    return os.name == "nt"


def refresh() -> str:
    """"updated", "ok", "absent" (atalho não instalado) ou "skip" (fora do Windows/sem pythonw)."""
    if not _is_windows():
        return "skip"
    pyw = autostart.pythonw()
    if not pyw:
        return "skip"
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            current, _ = winreg.QueryValueEx(key, "")
            wanted = wanted_command(pyw)
            if not needs_update(current, wanted):
                return "ok"
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, wanted)
    except FileNotFoundError:
        return "absent"
    log.info("Atalho jarvis:// atualizado: o botão ATUALIZAR E LIGAR da central já funciona.")
    return "updated"

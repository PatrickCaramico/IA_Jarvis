"""Q8 (V8.11): abrir um programa DESCONHECIDO só depois do "sim".

Antes, "abre o X" que não estava nos atalhos, em Meus Sites nem no Menu Iniciar procurava X no PATH e, se não
achasse, mandava o PowerShell rodar `Start-Process X`: qualquer executável ("abre o cmd", "abre o regedit")
abria na hora, inclusive pedido de um celular pareado. Agora:
  - atalhos, Meus Sites, sites conhecidos e o Menu Iniciar continuam abrindo direto (são os seus programas);
  - programa só achado no PATH ou no registro do Windows (App Paths): o JARVIS pergunta "Abro o X? Diga sim";
  - terminais, PowerShell, Registro e afins pedem o "sim" sempre, mesmo vindo do Menu Iniciar;
  - pedido de outro aparelho da rede para um desses: recusado (só no próprio PC).
O PowerShell saiu desse caminho (ele levava 1 a 3 s só para ligar).

Esta skill não tem frase nem é oferecida à IA: quem a usa é o "abrir" de modules/tools.py (via confirm.offer).
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from core.skills import Permission, SkillContext, SkillResult, skill

log = logging.getLogger("jarvis.skills.abrir_programa")

# Programas que mexem no sistema ou executam comandos: pedem "sim" mesmo vindo do Menu Iniciar
DANGEROUS = {
    "cmd", "command", "prompt de comando", "powershell", "pwsh", "windows powershell", "powershell ise", "terminal",
    "windows terminal", "wt", "regedit", "regedt32", "editor do registro", "registry editor", "wscript", "cscript",
    "mshta", "rundll32", "regsvr32", "diskpart", "format", "bcdedit", "shutdown", "taskkill", "reg", "schtasks",
    "net", "sc", "wmic", "msiexec", "certutil", "bitsadmin", "gpedit", "secpol", "netsh", "vssadmin", "cipher",
    "takeown", "icacls", "mmc", "compmgmt", "diskmgmt", "services", "msconfig", "bash", "wsl",
}
RUNNABLE = {".exe", ".com", ".lnk", ".msc", ".appref-ms", ".url"}


def _norm(text: str) -> str:
    import unicodedata

    t = unicodedata.normalize("NFKD", (text or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip()


def _file_name(path: str) -> str:
    """Nome do arquivo em caminho do Windows ou do Linux (C:\\...\\cmd.exe -> cmd.exe)."""
    return re.split(r"[\\/]", path or "")[-1]


def is_dangerous(name: str, path: str = "") -> bool:
    """O nome falado, o nome do atalho ou o arquivo é um terminal/ferramenta do sistema?"""
    cands = {_norm(name), _norm(re.sub(r"\.[a-z-]+$", "", _file_name(path), flags=re.I)) if path else ""}
    return any(c and (c in DANGEROUS or c.replace(" ", "") in DANGEROUS) for c in cands)


def _app_paths(exe: str) -> Optional[str]:
    """Registro do Windows (App Paths): onde o Windows acha programas como winword.exe, chrome.exe."""
    if os.name != "nt":
        return None
    import winreg

    sub = rf"Software\Microsoft\Windows\CurrentVersion\App Paths\{exe}"
    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(root, sub) as key:
                value = str(winreg.QueryValueEx(key, "")[0]).strip().strip('"')
                if value and os.path.isfile(os.path.expandvars(value)):
                    return os.path.expandvars(value)
        except OSError:
            continue
    return None


def resolve(name: str) -> Optional[str]:
    """Caminho do programa com esse nome (PATH ou App Paths), sem executar nada. None = não existe."""
    clean = _norm(name)
    if not clean or re.search(r"[;&|`$<>\"'\n\r%^]", clean) or ".." in clean or "/" in clean or "\\" in clean:
        return None
    for cand in dict.fromkeys([clean, clean.replace(" ", "")]):
        found = shutil.which(cand)
        if found:
            return found
        found = _app_paths(cand if cand.endswith(".exe") else f"{cand}.exe")
        if found:
            return found
    return None


def offer(label: str, path: str, remote: bool) -> str:
    """Guarda a pergunta (vale 3 min) e devolve o que o JARVIS fala. Pedido remoto: recusa."""
    from core import confirm

    if remote:
        return f"Por segurança, só abro o {label} com o pedido feito no próprio computador, senhor."
    confirm.offer("skill", {"name": "abrir_programa", "args": {"caminho": path, "nome": label}, "message": "",
                            "origin": "abrir", "remote": False})
    if is_dangerous(label, path):
        return f"O {label} executa comandos no sistema. Abro mesmo assim, senhor? Diga sim para confirmar."
    return f"O {label} não está nos seus atalhos. Abro o programa {_file_name(path)}, senhor? Diga sim para confirmar."


@skill(
    name="abrir_programa",
    title="abrir o programa",
    description="Abre um programa do computador que não está nos atalhos (só depois do sim do usuário).",
    permission=Permission.CRITICAL,
    llm=False,  # só pelo "abrir" com confirmação; a IA não chama
    timeout=10,
    params={"type": "object", "required": ["caminho"], "properties": {
        "caminho": {"type": "string"}, "nome": {"type": "string"}}},
    confirm_text=lambda a: f"Abro o {a.get('nome') or Path(a.get('caminho', '')).name}, senhor? Diga sim para confirmar.",
)
def abrir_programa(ctx: SkillContext, caminho: str, nome: str = "") -> SkillResult:
    path = Path(caminho)
    label = nome or path.stem
    if path.suffix.lower() not in RUNNABLE or not path.is_file():
        return SkillResult(ok=False, speech=f"Não encontrei mais o {label} neste computador, senhor.")
    try:
        if os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]  # sem shell: abre o arquivo como o Explorador
        else:
            subprocess.Popen([str(path)], close_fds=True)  # noqa: S603 - caminho resolvido e confirmado
    except OSError:
        log.exception("Não consegui abrir %s", path)
        return SkillResult(ok=False, speech=f"Não consegui abrir o {label}, senhor. O detalhe ficou no log.")
    log.info("Programa aberto depois do sim: %s", path)
    return SkillResult(speech=f"Iniciando {label}, senhor.")

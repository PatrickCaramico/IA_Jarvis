"""Atualizar e reiniciar o JARVIS pelo botão ATUALIZAR da tela de bloqueio.

1. Baixa a versão mais nova do GitHub (git pull --ff-only: nunca mistura nem apaga mudanças locais).
2. Reinicia pelo Iniciar-JARVIS.bat no modo "site": ele encerra este processo, refaz a interface local
   se ela mudou e sobe tudo de novo, sem abrir aba nova (a central aberta reconecta sozinha).

BOOT_ID muda a cada início do backend: a central usa isso para saber que a versão nova já subiu.

V8.1.7: mais rápido e com o andamento de verdade (PROGRESS, lido pela tela em /api/system/update/progress):
- a interface nova é compilada AQUI, com o JARVIS ainda ligado (antes era depois de desligar, no .bat);
- o aviso por voz não segura mais o reinício (antes esperava a fala inteira, e a voz falhando atrasava tudo).
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


# ------------------------------------------------------------------ V8.1.7: andamento
FRONTEND = ROOT / "frontend"
BUILD_TIMEOUT = 240  # V8.2.1: era 600; passou disso, o .bat refaz a interface do jeito antigo
PROGRESS: dict = {"etapa": "", "detalhe": "", "inicio": 0.0, "antes": "", "depois": "", "notas": []}


def set_progress(etapa: str, detalhe: str = "", **extra) -> None:
    PROGRESS.update(etapa=etapa, detalhe=detalhe, **extra)
    if etapa == "baixando":
        PROGRESS["inicio"] = time.time()


def progress() -> dict:
    out = dict(PROGRESS)
    out["segundos"] = round(time.time() - out["inicio"]) if out.get("inicio") else 0
    return out


def frontend_stale() -> bool:
    """A interface compilada (frontend/dist) está atrás do código? (a mesma conta do serve_frontend.py --stale)"""
    index = FRONTEND / "dist" / "index.html"
    if not index.exists():
        return True
    built = index.stat().st_mtime
    for name in ("src", "public", "index.html", "package.json", "vite.config.js", "tailwind.config.js", "postcss.config.js"):
        path = FRONTEND / name
        files = [path] if path.is_file() else list(path.rglob("*")) if path.is_dir() else []
        if any(f.is_file() and f.stat().st_mtime > built for f in files):
            return True
    return False


def fetch_prebuilt() -> bool:
    """V8.2.2: baixa a interface pronta do site (scripts/prebuilt.py); False se não deu (aí monta no PC)."""
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("jarvis_prebuilt", ROOT / "scripts" / "prebuilt.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return bool(mod.fetch(FRONTEND, log=lambda m: log.info(m.strip()), wait_s=150))
    except Exception as exc:  # noqa: BLE001
        log.warning("Interface pronta indisponível: %s", exc)
        return False


def build_frontend() -> bool:
    """Compila a interface nova antes de reiniciar (o .bat vê que está em dia e pula essa parte).

    V8.2.1: a saída vai para logs/build.log (antes era capturada por "tubo": no Windows um processo auxiliar
    do build herdava o tubo e o JARVIS ficava esperando ele fechar, até 10 minutos). Agora espera só o build
    terminar e, se passar do tempo, encerra o build inteiro e deixa o .bat fazer.
    """
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm or not (FRONTEND / "node_modules").exists():
        return False
    logs = ROOT / "logs"
    logs.mkdir(exist_ok=True)
    started = time.time()
    try:
        with open(logs / "build.log", "w", encoding="utf-8", errors="replace") as out:
            proc = subprocess.Popen(  # noqa: S603 - comando fixo
                [npm, "run", "build"], cwd=str(FRONTEND), stdout=out, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            try:
                code = proc.wait(timeout=BUILD_TIMEOUT)
            except subprocess.TimeoutExpired:
                _kill_tree(proc.pid)
                log.warning("Build da interface passou de %s s: o .bat refaz no reinício.", BUILD_TIMEOUT)
                return False
    except OSError as exc:
        log.warning("Build da interface antes de reiniciar falhou: %s", exc)
        return False
    log.info("Build da interface em %.0f s (código %s).", time.time() - started, code)
    return code == 0


def _kill_tree(pid: int) -> None:
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, timeout=15,  # noqa: S603,S607
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        else:
            os.kill(pid, 9)
    except Exception:  # noqa: BLE001
        pass


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


# ------------------------------------------------------------------ V6.7.2: tem atualização?
import re as _re  # noqa: E402

_CHECK_TTL = 15 * 60
_last_check: dict = {"at": 0.0, "result": None}
_VERSION_RE = _re.compile(r'^VERSION\s*=\s*"([^"]+)"', _re.M)
_RELEASE_RE = _re.compile(r"^JARVIS (\d+\.\d+\.\d+)\b")


def _current_version() -> str:
    try:
        return _VERSION_RE.search((ROOT / "backend" / "version.py").read_text(encoding="utf-8")).group(1)
    except (OSError, AttributeError):
        return ""


def check(force: bool = False) -> dict:
    """Quantas versões novas há na branch que o ATUALIZAR baixa (git fetch + comparação). Guarda por 15 min.

    Retorna {available, count, current, latest, notes, message}. Roda fora do loop (to_thread).
    """
    now = time.time()
    if not force and _last_check["result"] and now - _last_check["at"] < _CHECK_TTL:
        return _last_check["result"]
    current = _current_version()
    base = {"available": False, "count": 0, "current": current, "latest": current, "notes": [], "message": ""}
    if not shutil.which("git") or not (ROOT / ".git").exists():
        return {**base, "message": "Sem Git nesta pasta."}
    try:
        fetched = _git("fetch", "--quiet")
        if fetched.returncode != 0:
            return {**base, "message": "Não consegui falar com o GitHub agora."}
        upstream = _git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}").stdout.strip() or "origin/main"
        behind = int((_git("rev-list", "--count", f"HEAD..{upstream}").stdout or "0").strip() or 0)
        subjects = [s for s in _git("log", "--no-merges", "--format=%s", f"HEAD..{upstream}").stdout.splitlines() if s.strip()]
        latest_src = _git("show", f"{upstream}:backend/version.py").stdout
    except (subprocess.TimeoutExpired, OSError, ValueError) as exc:
        return {**base, "message": f"Não consegui conferir: {exc}"}
    m = _VERSION_RE.search(latest_src or "")
    latest = m.group(1) if m else current
    releases = [s for s in subjects if _RELEASE_RE.match(s)]
    count = len(releases) or (1 if behind else 0)
    result = {**base, "available": behind > 0, "count": count, "latest": latest,
              "notes": [s for s in (releases or subjects)][:5],
              "message": f"Versão {latest} disponível." if behind else "Você já está na versão mais nova."}
    _last_check.update(at=now, result=result)
    return result

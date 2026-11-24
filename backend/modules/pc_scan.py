"""V8.10.0 (ideia 13): VARREDURA QUANDO O PC ESTÁ LENTO ("meu note está lento", "o PC está travando").

Mede o que deixa o PC lento (CPU, memória, disco, programas pesados, tempo ligado, inicialização, temporários,
lixeira e bateria), diz a causa principal numa frase curta e oferece correções. NADA é corrigido sem o "pode"
do usuário: as correções são rotas separadas, chamadas pelos botões do cartão.
- fechar programas: só os que o usuário escolheu, nunca os do Windows nem o próprio JARVIS;
- limpar temporários: a pasta TEMP do usuário, só arquivos com mais de 1 dia (os em uso são pulados);
- esvaziar a lixeira (Windows).
Tudo roda só no PC; nada vai para a nuvem.
"""
from __future__ import annotations

import logging
import os
import platform
import re
import shutil
import tempfile
import time
import unicodedata
from pathlib import Path

log = logging.getLogger("jarvis.pc_scan")

TEMP_MIN_AGE_S = 24 * 3600
TOP_N = 6
BIG_RECYCLE_BYTES = 1024 ** 3  # 1 GB: a partir daí a lixeira "ocupa bastante"
BIG_TEMP_BYTES = 500 * 1024 ** 2
LONG_UPTIME_DAYS = 3
MANY_STARTUP = 8

# Programas que NUNCA são fechados (Windows, antivírus, drivers e o próprio JARVIS)
PROTECTED = {
    "system", "system idle process", "registry", "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe",
    "services.exe", "lsass.exe", "svchost.exe", "explorer.exe", "dwm.exe", "fontdrvhost.exe", "sihost.exe",
    "taskhostw.exe", "ctfmon.exe", "runtimebroker.exe", "searchhost.exe", "searchindexer.exe", "startmenuexperiencehost.exe",
    "shellexperiencehost.exe", "textinputhost.exe", "audiodg.exe", "spoolsv.exe", "memory compression", "conhost.exe",
    "msmpeng.exe", "nissrv.exe", "securityhealthservice.exe", "securityhealthsystray.exe", "smartscreen.exe",
    "mcshield.exe", "mfemms.exe", "mfevtps.exe", "modulecoreservice.exe", "mcapexe.exe", "pefservice.exe",
    "lsaiso.exe", "wudfhost.exe", "dashost.exe", "igfxem.exe", "nvcontainer.exe", "nvdisplay.container.exe",
    "python.exe", "pythonw.exe", "node.exe", "jarvis.exe", "msedgewebview2.exe", "cmd.exe", "powershell.exe",
    "windowsterminal.exe", "openconsole.exe", "taskmgr.exe", "systemsettings.exe", "applicationframehost.exe",
}

_SLOW = re.compile(
    r"\b(?:(?:meu|o|a|esse|este)\s+)?(?:note|notebook|pc|computador|maquina|windows|laptop)\b.{0,30}?"
    r"\b(?:lent[oa]|travando|trava(?:ndo)?|pesad[oa]|devagar|engasgando|demorando|carregando devagar|ruim)\b"
    r"|\b(?:lent[oa]|travando|pesad[oa]|devagar)\b.{0,20}\b(?:note|notebook|pc|computador|maquina|windows)\b"
    r"|\b(?:roda|rode|rodar|faz|faca|fazer)\s+(?:uma\s+)?varredura\b"
    r"|\b(?:otimiza|otimize|otimizar|acelera|acelere|acelerar|limpa|limpe|limpar)\s+(?:o\s+|meu\s+)?(?:pc|note|notebook|computador|maquina)\b"
)


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def is_slow_request(message: str) -> bool:
    """O usuário está reclamando que o PC está lento (ou pediu a varredura)?"""
    norm = _norm(message)
    if not norm or len(norm.split()) > 18:
        return False
    if re.search(r"\b(jarvis|site|central|app|aplicativo)\b", norm) and not re.search(r"\b(note|notebook|pc|computador|maquina|windows)\b", norm):
        return False  # "o JARVIS está lento" é outra coisa (o otimizador do próprio app)
    return bool(_SLOW.search(norm))


def _gb(n: float) -> float:
    return round(n / 1024 ** 3, 1)


def _dir_size(path: Path, min_age_s: float = 0, now: float | None = None) -> tuple[int, int]:
    """(bytes, arquivos) dos arquivos da pasta (com idade mínima). Erros de permissão são pulados."""
    now = now or time.time()
    total = count = 0
    for root, _dirs, files in os.walk(path, onerror=lambda _e: None):
        for f in files:
            try:
                st = os.stat(os.path.join(root, f))
            except OSError:
                continue
            if now - st.st_mtime >= min_age_s:
                total += st.st_size
                count += 1
    return total, count


def temp_dir() -> Path:
    return Path(os.environ.get("TEMP") or tempfile.gettempdir())


def recycle_bin_bytes() -> int | None:
    """Tamanho da lixeira (só Windows). None quando não dá para saber."""
    if platform.system() != "Windows":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class SHQUERYRBINFO(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.DWORD), ("i64Size", ctypes.c_longlong), ("i64NumItems", ctypes.c_longlong)]

        info = SHQUERYRBINFO()
        info.cbSize = ctypes.sizeof(SHQUERYRBINFO)
        if ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(info)) != 0:
            return None
        return int(info.i64Size)
    except Exception:  # noqa: BLE001
        return None


def startup_count() -> int | None:
    """Quantos programas abrem junto com o Windows (registro Run + pasta Inicializar). Só Windows."""
    if platform.system() != "Windows":
        return None
    total = 0
    try:
        import winreg

        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(hive, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
                    total += winreg.QueryInfoKey(key)[1]
            except OSError:
                pass
    except ImportError:
        return None
    folder = Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs/Startup"
    try:
        total += sum(1 for p in folder.iterdir() if p.suffix.lower() in {".lnk", ".exe", ".bat", ".url"})
    except OSError:
        pass
    return total


TASKLIST_TIMEOUT_S = 8
CPU_TOP_GROUPS = 12  # o processador só é medido nos programas que mais gastam memória
_K_RE = re.compile(r"\D")


def parse_tasklist(text: str) -> list[tuple[str, int, int]]:
    """Saída do "tasklist /fo csv /nh" -> [(nome, pid, memória em bytes)]. A memória vem como "123.456 K" (o
    separador de milhar muda com o idioma do Windows: só os dígitos importam)."""
    import csv
    import io

    out = []
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 5:
            continue
        try:
            pid = int(row[1])
            kb = int(_K_RE.sub("", row[4]) or 0)
        except ValueError:
            continue
        out.append((row[0].strip(), pid, kb * 1024))
    return out


def _tasklist() -> list[tuple[str, int, int]]:
    import subprocess

    res = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, timeout=TASKLIST_TIMEOUT_S,  # noqa: S603,S607
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False)
    if res.returncode != 0:
        raise RuntimeError(f"tasklist saiu com {res.returncode}")
    # o tasklist escreve na página de código do console (cp850 no Windows em português)
    return parse_tasklist(res.stdout.decode("cp850", errors="replace"))


def group(rows: list[tuple[str, int, int]], me: int) -> dict[str, dict]:
    groups: dict[str, dict] = {}
    for name, pid, mem in rows:
        if not name or pid in (0, 4, me):
            continue
        g = groups.setdefault(name.lower(), {"name": name, "mem": 0, "cpu": 0.0, "count": 0, "pids": []})
        g["mem"] += mem
        g["count"] += 1
        g["pids"].append(pid)
    return groups


def _cpu_for(psutil, groups: list[dict], cores: int, wait: float = 0.5) -> None:
    """Processador (%) só dos grupos pedidos: duas leituras com uma pausa. Processo sem acesso fica de fora."""
    procs = []
    for g in groups:
        for pid in g["pids"]:
            try:
                p = psutil.Process(pid)
                p.cpu_percent(None)
                procs.append((g, p))
            except Exception:  # noqa: BLE001 - fechou ou é protegido
                continue
    time.sleep(wait)
    for g, p in procs:
        try:
            g["cpu"] += p.cpu_percent(None) / cores
        except Exception:  # noqa: BLE001
            continue


def _as_list(groups: dict[str, dict], total_mem: int) -> list[dict]:
    out = []
    for key, g in groups.items():
        out.append({"name": g["name"], "label": friendly(g["name"]), "count": g["count"],
                    "mem_mb": round(g["mem"] / 1024 ** 2), "mem_percent": round(g["mem"] * 100 / (total_mem or 1), 1),
                    "cpu_percent": round(g["cpu"], 1), "protected": key in PROTECTED})
    return out


def _processes(psutil) -> list[dict]:
    """Os programas mais pesados, somando as janelas/abas do mesmo programa (ex.: chrome.exe).

    V9.4.2: no Windows, a lista vem do "tasklist" numa leitura só. Antes era o psutil processo por processo: para
    cada processo protegido do sistema (que ele não consegue abrir) o psutil refaz a foto de TODOS os processos,
    então o custo crescia ao quadrado e, com a memória alta, passava de 12 s (a auto-análise e "o que está pesando"
    estouravam o prazo). O processador é medido só nos programas que mais gastam memória."""
    cores = psutil.cpu_count() or 1
    me = os.getpid()
    total_mem = psutil.virtual_memory().total or 1
    if os.name == "nt":
        try:
            groups = group(_tasklist(), me)
            top = sorted(groups.values(), key=lambda g: g["mem"], reverse=True)[:CPU_TOP_GROUPS]
            _cpu_for(psutil, top, cores)
            return _as_list(groups, total_mem)
        except Exception:  # noqa: BLE001 - sem tasklist: o caminho antigo, pelo psutil
            log.warning("tasklist falhou; lendo os programas pelo psutil", exc_info=True)
    rows = []
    for p in psutil.process_iter(["name", "memory_info"]):
        mi = p.info.get("memory_info")
        rows.append((p.info.get("name") or "", p.pid, mi.rss if mi else 0))
    groups = group(rows, me)
    _cpu_for(psutil, list(groups.values()), cores)
    return _as_list(groups, total_mem)


_FRIENDLY = {"chrome.exe": "Google Chrome", "msedge.exe": "Microsoft Edge", "firefox.exe": "Firefox", "opera.exe": "Opera",
             "brave.exe": "Brave", "discord.exe": "Discord", "spotify.exe": "Spotify", "teams.exe": "Teams", "ms-teams.exe": "Teams",
             "whatsapp.exe": "WhatsApp", "steam.exe": "Steam", "steamwebhelper.exe": "Steam", "code.exe": "VS Code",
             "onedrive.exe": "OneDrive", "epicgameslauncher.exe": "Epic Games", "outlook.exe": "Outlook", "excel.exe": "Excel",
             "winword.exe": "Word", "powerpnt.exe": "PowerPoint", "zoom.exe": "Zoom", "obs64.exe": "OBS", "telegram.exe": "Telegram"}


def friendly(name: str) -> str:
    n = (name or "").lower()
    return _FRIENDLY.get(n, re.sub(r"\.exe$", "", name or "", flags=re.I))


def scan() -> dict:
    """A varredura completa (leva ~1 s). Funciona mesmo sem psutil (só com o que der para medir)."""
    data: dict = {"at": time.strftime("%H:%M"), "cpu_percent": None, "ram_percent": None, "ram_total_gb": None,
                  "ram_used_gb": None, "disk_percent": None, "disk_free_gb": None, "uptime_days": None, "battery": None,
                  "top": [], "startup": startup_count(), "recycle_bytes": recycle_bin_bytes()}
    try:
        import psutil

        data["cpu_percent"] = psutil.cpu_percent(interval=0.4)
        vm = psutil.virtual_memory()
        data.update(ram_percent=round(vm.percent), ram_total_gb=_gb(vm.total), ram_used_gb=_gb(vm.total - vm.available))
        data["uptime_days"] = round((time.time() - psutil.boot_time()) / 86400, 1)
        try:
            bat = psutil.sensors_battery()
            if bat is not None:
                data["battery"] = {"percent": round(bat.percent), "plugged": bool(bat.power_plugged)}
        except Exception:  # noqa: BLE001
            pass
        procs = _processes(psutil)
        data["top"] = sorted([p for p in procs if not p["protected"]], key=lambda p: p["mem_mb"] + p["cpu_percent"] * 40, reverse=True)[:TOP_N]
    except ImportError:
        log.info("psutil não instalado: varredura parcial")
    try:
        root = os.path.splitdrive(os.path.abspath(os.sep))[0] + os.sep if platform.system() == "Windows" else "/"
        du = shutil.disk_usage(root)
        data.update(disk_percent=round(du.used * 100 / du.total), disk_free_gb=_gb(du.free))
    except OSError:
        pass
    temp_bytes, temp_files = _dir_size(temp_dir(), TEMP_MIN_AGE_S)
    data.update(temp_bytes=temp_bytes, temp_files=temp_files)
    data.update(diagnose(data))
    return data


def _mb(n: int | None) -> str:
    n = n or 0
    return f"{n / 1024 ** 3:.1f} GB".replace(".", ",") if n >= 1024 ** 3 else f"{round(n / 1024 ** 2)} MB"


def diagnose(d: dict) -> dict:
    """Função pura: os achados (do mais grave ao mais leve), as correções oferecidas e a frase falada."""
    findings: list[dict] = []
    fixes: list[str] = []
    top = d.get("top") or []
    heavy = top[0] if top else None
    ram, cpu, disk = d.get("ram_percent"), d.get("cpu_percent"), d.get("disk_percent")
    if ram is not None and ram >= 85:
        who = f" O que mais gasta é o {heavy['label']} ({heavy['mem_percent']:.0f}%)." if heavy and heavy["mem_percent"] >= 10 else ""
        findings.append({"level": "fail", "id": "ram", "text": f"A memória está quase cheia: {ram}% em uso.{who}"})
    elif ram is not None and ram >= 70:
        findings.append({"level": "warn", "id": "ram", "text": f"A memória está bem usada: {ram}%."})
    if cpu is not None and cpu >= 80:
        hog = max(top, key=lambda p: p["cpu_percent"]) if top else None
        who = f" O {hog['label']} está usando {hog['cpu_percent']:.0f}%." if hog and hog["cpu_percent"] >= 15 else ""
        findings.append({"level": "fail", "id": "cpu", "text": f"O processador está no limite: {cpu:.0f}%.{who}"})
    elif cpu is not None and cpu >= 55:
        findings.append({"level": "warn", "id": "cpu", "text": f"O processador está ocupado: {cpu:.0f}%."})
    if top and ((ram is not None and ram >= 70) or (cpu is not None and cpu >= 55)):
        fixes.append("fechar")
    if disk is not None and disk >= 90:
        findings.append({"level": "fail", "id": "disco", "text": f"O disco está quase cheio: só {str(d.get('disk_free_gb')).replace('.', ',')} GB livres."})
    elif disk is not None and disk >= 80:
        findings.append({"level": "warn", "id": "disco", "text": f"O disco está com {disk}% ocupado."})
    if (d.get("temp_bytes") or 0) >= BIG_TEMP_BYTES or (disk is not None and disk >= 80 and (d.get("temp_bytes") or 0) >= 50 * 1024 ** 2):
        findings.append({"level": "warn", "id": "temp", "text": f"Há {_mb(d.get('temp_bytes'))} de arquivos temporários antigos."})
    if (d.get("temp_bytes") or 0) >= 20 * 1024 ** 2:
        fixes.append("temporarios")
    if (d.get("recycle_bytes") or 0) >= BIG_RECYCLE_BYTES:
        findings.append({"level": "warn", "id": "lixeira", "text": f"A lixeira está ocupando {_mb(d.get('recycle_bytes'))}."})
        fixes.append("lixeira")
    up = d.get("uptime_days")
    if up is not None and up >= LONG_UPTIME_DAYS:
        findings.append({"level": "warn", "id": "ligado", "text": f"O PC está ligado há {int(up)} dias sem reiniciar. Reiniciar costuma deixar tudo mais leve."})
    st = d.get("startup")
    if st is not None and st >= MANY_STARTUP:
        findings.append({"level": "warn", "id": "inicializacao", "text": f"{st} programas abrem junto com o Windows. Dá para desligar os que não usa em Gerenciador de Tarefas › Aplicativos de inicialização."})
    bat = d.get("battery")
    if bat and not bat.get("plugged") and bat.get("percent", 100) <= 30:
        findings.append({"level": "warn", "id": "bateria", "text": f"O note está na bateria ({bat['percent']}%): o Windows reduz o desempenho para economizar. Ligue na tomada."})
    order = {"fail": 0, "warn": 1}
    findings.sort(key=lambda f: order.get(f["level"], 2))
    if findings:
        speech = findings[0]["text"]
        extra = len(findings) - 1
        if extra:
            speech += f" Encontrei mais {extra} {'ponto' if extra == 1 else 'pontos'}; está tudo no cartão."
        if fixes:
            speech += " Posso arrumar pelos botões, é só confirmar."
        verdict = "fail" if findings[0]["level"] == "fail" else "warn"
    else:
        speech = "Varredura feita: memória, processador e disco estão tranquilos agora. Se a lentidão voltar, me chame de novo na hora."
        verdict = "ok"
    return {"findings": findings, "fixes": fixes, "speech": speech, "verdict": verdict}


# ------------------------------------------------------------------ correções (só com confirmação, pelos botões)
def close_programs(names: list[str]) -> dict:
    """Fecha os programas escolhidos (todas as janelas do mesmo nome). Nunca os protegidos."""
    wanted = {n.strip().lower() for n in names or [] if n and n.strip()}
    blocked = sorted(n for n in wanted if n in PROTECTED)
    wanted -= PROTECTED
    closed: dict[str, int] = {}
    if not wanted:
        return {"closed": [], "blocked": blocked}
    import psutil

    me = os.getpid()
    victims = []
    for p in psutil.process_iter(["name"]):
        try:
            if p.pid != me and (p.info.get("name") or "").lower() in wanted:
                p.terminate()
                victims.append(p)
                closed[p.info["name"]] = closed.get(p.info["name"], 0) + 1
        except Exception:  # noqa: BLE001
            continue
    _gone, alive = psutil.wait_procs(victims, timeout=3)
    for p in alive:
        try:
            p.kill()
        except Exception:  # noqa: BLE001
            pass
    log.info("Varredura: programas fechados a pedido: %s", ", ".join(closed))
    return {"closed": [{"name": n, "label": friendly(n), "count": c} for n, c in closed.items()], "blocked": blocked}


def clean_temp(folder: Path | None = None, min_age_s: float = TEMP_MIN_AGE_S, now: float | None = None) -> dict:
    """Apaga da pasta TEMP do usuário só os arquivos com mais de 1 dia; pula os que estão em uso."""
    folder = folder or temp_dir()
    now = now or time.time()
    freed = removed = skipped = 0
    for root, dirs, files in os.walk(folder, topdown=False, onerror=lambda _e: None):
        for f in files:
            path = os.path.join(root, f)
            try:
                st = os.lstat(path)
                if now - st.st_mtime < min_age_s:
                    continue
                os.remove(path)
                freed += st.st_size
                removed += 1
            except OSError:
                skipped += 1
        for d in dirs:  # pastas que ficaram vazias
            try:
                os.rmdir(os.path.join(root, d))
            except OSError:
                pass
    log.info("Varredura: temporários limpos: %d arquivos, %s", removed, _mb(freed))
    return {"freed_bytes": freed, "freed": _mb(freed), "removed": removed, "skipped": skipped}


def empty_recycle_bin() -> dict:
    if platform.system() != "Windows":
        return {"ok": False, "message": "A lixeira só pode ser esvaziada no Windows."}
    before = recycle_bin_bytes() or 0
    try:
        import ctypes

        # SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND (o usuário já confirmou no cartão)
        res = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x1 | 0x2 | 0x4)
    except Exception as exc:  # noqa: BLE001
        log.warning("Não deu para esvaziar a lixeira: %s", exc)
        return {"ok": False, "message": "Não consegui esvaziar a lixeira."}
    ok = res in (0, -2147418113)  # S_OK, ou E_UNEXPECTED quando ela já estava vazia
    return {"ok": ok, "freed": _mb(before), "message": f"Lixeira esvaziada: {_mb(before)} liberados." if ok else "Não consegui esvaziar a lixeira."}

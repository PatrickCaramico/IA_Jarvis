"""Tempo de tela e resumo da semana (V9.0), tudo no próprio PC.

Um serviço de fundo olha, a cada 10 s, qual PROGRAMA está em primeiro plano (só o nome do programa — nunca o título
da janela nem o conteúdo) e soma o tempo do dia. Se você está sem mexer no teclado/mouse há 5 min, não conta.
Guarda 60 dias em data/tempo_de_tela.json. Liga/desliga: preferência screen_time_enabled (ou "para de medir meu
tempo de tela" / "volta a medir meu tempo de tela").

Frases:
- "quanto tempo eu fiquei no Chrome hoje?", "quanto tempo passei no Discord ontem?", "… essa semana?"
- "meu tempo de tela hoje", "quais programas eu mais usei essa semana?"
- "resumo da semana", "como foi minha semana?"  -> tarefas feitas, água, ofensiva, XP e os programas mais usados
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from datetime import date, datetime, timedelta
from typing import Optional

from config import settings
from core import safe_io
from core.skills import Permission, SkillContext, SkillResult, service, skill

log = logging.getLogger("jarvis.skills.tempo_de_tela")

_PATH = settings.DATA_DIR / "tempo_de_tela.json"
SAMPLE_S = 10
FLUSH_S = 60
IDLE_LIMIT_S = 300
KEEP_DAYS = 60

# nome do executável -> nome falado
NAMES = {
    "chrome": "Chrome", "msedge": "Edge", "firefox": "Firefox", "opera": "Opera", "brave": "Brave",
    "code": "VS Code", "devenv": "Visual Studio", "pycharm64": "PyCharm", "idea64": "IntelliJ",
    "spotify": "Spotify", "discord": "Discord", "whatsapp": "WhatsApp", "telegram": "Telegram", "slack": "Slack",
    "teams": "Teams", "ms-teams": "Teams", "zoom": "Zoom", "explorer": "Explorador de Arquivos",
    "winword": "Word", "excel": "Excel", "powerpnt": "PowerPoint", "outlook": "Outlook", "onenote": "OneNote",
    "notepad": "Bloco de Notas", "windowsterminal": "Terminal", "cmd": "Prompt de Comando", "powershell": "PowerShell",
    "steam": "Steam", "epicgameslauncher": "Epic Games", "obs64": "OBS", "vlc": "VLC", "photoshop": "Photoshop",
    "figma": "Figma", "notion": "Notion", "obsidian": "Obsidian", "jarvis": "JARVIS",
}
_IGNORE = {"lockapp", "searchhost", "shellexperiencehost", "startmenuexperiencehost", "applicationframehost", "idle", ""}


def on_windows() -> bool:
    return os.name == "nt"


def friendly(exe: str) -> str:
    base = re.sub(r"\.exe$", "", (exe or "").strip(), flags=re.I)
    return NAMES.get(base.lower(), base[:1].upper() + base[1:] if base else "")


# ------------------------------------------------------------------ Windows (só nomes, nunca títulos)
def foreground_exe() -> str:
    """O executável da janela em primeiro plano ("" fora do Windows ou sem janela)."""
    if os.name != "nt":
        return ""
    import ctypes
    from ctypes import wintypes

    import psutil

    hwnd = ctypes.windll.user32.GetForegroundWindow()
    if not hwnd:
        return ""
    pid = wintypes.DWORD()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    try:
        return psutil.Process(pid.value).name()
    except (psutil.Error, ValueError):
        return ""


def idle_seconds() -> float:
    """Há quantos segundos ninguém mexe no teclado/mouse (0 fora do Windows)."""
    if os.name != "nt":
        return 0.0
    import ctypes

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(info)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0
    return max(0.0, (ctypes.windll.kernel32.GetTickCount() - info.dwTime) / 1000.0)


# ------------------------------------------------------------------ dados
def _load() -> dict:
    data = safe_io.read_json(_PATH) if _PATH.exists() else {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("dias", {})
    data.setdefault("xp", {})
    return data


def enabled() -> bool:
    from modules import prefs

    return bool(prefs.get_all().get("screen_time_enabled", True))


def add_seconds(counts: dict[str, float], day: Optional[str] = None) -> None:
    """Soma os segundos de cada programa no dia (e apaga o que passou de 60 dias)."""
    if not counts:
        return
    day = day or date.today().isoformat()
    data = _load()
    today = data["dias"].setdefault(day, {})
    for app, sec in counts.items():
        if app and sec > 0:
            today[app] = round(today.get(app, 0) + sec)
    cutoff = (date.fromisoformat(day) - timedelta(days=KEEP_DAYS)).isoformat()
    data["dias"] = {d: v for d, v in data["dias"].items() if d >= cutoff}
    data["xp"] = {d: v for d, v in data["xp"].items() if d >= cutoff}
    safe_io.write_json(_PATH, data)


def snapshot_xp(day: Optional[str] = None) -> None:
    """Guarda o XP total do dia (para a semana saber quanto XP você ganhou)."""
    from modules import desk

    day = day or date.today().isoformat()
    data = _load()
    data["xp"][day] = int(desk._load()["xp"]["total"])
    safe_io.write_json(_PATH, data)


def day_apps(day: str) -> dict[str, int]:
    return dict(_load()["dias"].get(day, {}))


def range_apps(days: list[str]) -> dict[str, int]:
    total: dict[str, int] = {}
    dias = _load()["dias"]
    for d in days:
        for app, sec in dias.get(d, {}).items():
            total[app] = total.get(app, 0) + sec
    return total


def fmt(seconds: float) -> str:
    """3725 -> "1 hora e 2 minutos"; 59 -> "menos de um minuto"."""
    m = int(seconds // 60)
    if m < 1:
        return "menos de um minuto"
    h, m = divmod(m, 60)
    parts = []
    if h:
        parts.append(f"{h} {'hora' if h == 1 else 'horas'}")
    if m:
        parts.append(f"{m} {'minuto' if m == 1 else 'minutos'}")
    return " e ".join(parts)


def top(apps: dict[str, int], n: int = 3) -> list[tuple[str, int]]:
    return sorted(((a, s) for a, s in apps.items() if s >= 60), key=lambda x: -x[1])[:n]


def find_app(apps: dict[str, int], wanted: str) -> Optional[str]:
    w = re.sub(r"[^a-z0-9]", "", wanted.lower())
    for app in apps:
        if re.sub(r"[^a-z0-9]", "", app.lower()) == w:
            return app
    for app in apps:
        a = re.sub(r"[^a-z0-9]", "", app.lower())
        if w and (w in a or a in w):
            return app
    return None


def period_days(periodo: str, today: Optional[date] = None) -> tuple[list[str], str]:
    today = today or date.today()
    if periodo == "ontem":
        return [(today - timedelta(days=1)).isoformat()], "ontem"
    if periodo == "semana":
        return [(today - timedelta(days=i)).isoformat() for i in range(7)], "nos últimos 7 dias"
    return [today.isoformat()], "hoje"


# ------------------------------------------------------------------ serviço
_pending: dict[str, float] = {}


@service("tempo_de_tela")
async def tempo_de_tela_loop() -> None:
    """A cada 10 s, soma o programa em primeiro plano (se você está mexendo no PC); grava a cada minuto."""
    if not on_windows():
        return
    last_flush = time.monotonic()
    while True:
        try:
            if enabled():
                exe, idle = await asyncio.to_thread(lambda: (foreground_exe(), idle_seconds()))
                name = friendly(exe)
                if name and exe.lower().removesuffix(".exe") not in _IGNORE and idle < IDLE_LIMIT_S:
                    _pending[name] = _pending.get(name, 0) + SAMPLE_S
            if time.monotonic() - last_flush >= FLUSH_S and _pending:
                counts = dict(_pending)
                _pending.clear()
                await asyncio.to_thread(add_seconds, counts)
                await asyncio.to_thread(snapshot_xp)
                last_flush = time.monotonic()
        except Exception:  # noqa: BLE001 - o motor religa o serviço; aqui só registra
            log.exception("Tempo de tela: falha ao medir")
        await asyncio.sleep(SAMPLE_S)


# ------------------------------------------------------------------ frases
_PERIOD = r"(?:\s+(?P<periodo>hoje|ontem|essa semana|esta semana|nessa semana|na semana|da semana))?"
_APP_Q = re.compile(r"\bquanto tempo (?:eu )?(?:fiquei|passei|usei|gastei|estive)\s+(?:no |na |nos |nas |com o |com a |em )?"
                    r"(?P<app>(?!o computador|o pc)[a-z0-9 .+-]{2,30}?)" + _PERIOD + r"\??$")
_TOTAL_Q = re.compile(r"\b(?:meu tempo de tela|quanto tempo (?:eu )?(?:fiquei|passei|usei) (?:no|o) (?:computador|pc)|"
                      r"quais (?:programas|apps|aplicativos) (?:eu )?mais usei)" + _PERIOD + r"\??$")
_SWITCH = re.compile(r"\b(?P<acao>para de|pare de|parar de|volta a|volte a|voltar a)\s+medir (?:o )?(?:meu )?tempo de tela\b")


def _periodo(word: Optional[str]) -> str:
    if not word:
        return "hoje"
    return "semana" if "semana" in word else word


def _parse(norm: str, _original: str) -> Optional[dict]:
    m = _SWITCH.search(norm)
    if m:
        return {"acao": "desligar" if m.group("acao").startswith("par") else "ligar"}
    m = _TOTAL_Q.search(norm)
    if m:
        return {"acao": "total", "periodo": _periodo(m.group("periodo"))}
    m = _APP_Q.search(norm)
    if m:
        return {"acao": "programa", "programa": m.group("app").strip(), "periodo": _periodo(m.group("periodo"))}
    return None


@skill(
    name="tempo_de_tela",
    title="ver o tempo de tela",
    description=("Tempo de uso do PC por programa (medido no próprio PC, só o nome do programa): quanto tempo num "
                 "programa (acao programa) ou o total e os mais usados (acao total), hoje, ontem ou na semana. "
                 "Também liga/desliga a medição (acao ligar|desligar)."),
    permission=Permission.READ,
    allow_remote=True,
    timeout=6,
    parse=_parse,
    params={"type": "object", "required": ["acao"], "properties": {
        "acao": {"type": "string", "enum": ["programa", "total", "ligar", "desligar"]},
        "programa": {"type": "string"},
        "periodo": {"type": "string", "enum": ["hoje", "ontem", "semana"]}}},
    examples=["quanto tempo eu fiquei no Chrome hoje?", "meu tempo de tela da semana"],
)
def tempo_de_tela(ctx: SkillContext, acao: str, programa: str = "", periodo: str = "hoje") -> SkillResult:
    from modules import prefs

    if acao in ("ligar", "desligar"):
        prefs.update(screen_time_enabled=acao == "ligar")
        return SkillResult(speech="Certo, senhor: voltei a medir o seu tempo de tela." if acao == "ligar"
                           else "Certo, senhor: parei de medir o seu tempo de tela. O que já estava medido continua guardado.")
    if not on_windows() and not _load()["dias"]:
        return SkillResult(ok=False, speech="O tempo de tela é medido no PC com Windows, senhor.")
    days, label = period_days(periodo if periodo in ("hoje", "ontem", "semana") else "hoje")
    apps = range_apps(days)
    if not apps:
        return SkillResult(speech=f"Ainda não tenho tempo de tela medido {label}, senhor."
                           + ("" if enabled() else " A medição está desligada."))
    if acao == "programa" and programa:
        app = find_app(apps, programa)
        if not app:
            return SkillResult(speech=f"Não vi o {programa} em uso {label}, senhor.", data={"apps": apps})
        return SkillResult(speech=f"{label[:1].upper() + label[1:]}, o senhor passou {fmt(apps[app])} no {app}.",
                           data={"programa": app, "segundos": apps[app]})
    total = sum(apps.values())
    best = top(apps, 5)
    rows = [{"label": a, "value": fmt(s)} for a, s in best]
    lead = ", ".join(f"{a} ({fmt(s)})" for a, s in best[:3])
    speech = f"{label[:1].upper() + label[1:]}, o senhor usou o PC por {fmt(total)}." + (f" Os mais usados: {lead}." if lead else "")
    return SkillResult(speech=speech, cards=[{"type": "skill", "data": {"tag": "TEMPO DE TELA", "source": f"{label} · total {fmt(total)}", "rows": rows}}],
                       data={"total": total, "apps": dict(best)})


# ------------------------------------------------------------------ resumo da semana
def week_summary(today: Optional[date] = None) -> dict:
    """Os números da semana (últimos 7 dias): tarefas feitas, dias com a meta de água, ofensiva, XP e programas."""
    from modules import desk_missions, tasks, water

    today = today or date.today()
    start = today - timedelta(days=6)
    done = 0
    for t in tasks.get_tasks(True):
        when = str(t.get("concluida_em") or "")
        try:
            d = datetime.strptime(when[:10], "%d/%m/%Y").date()
        except ValueError:
            continue
        if start <= d <= today:
            done += 1
    wdata = water._load_data()
    goal = wdata.get("goal_ml", water.DEFAULT_GOAL_ML) or 1
    water_days = sum(1 for i in range(7) if (wdata.get("days", {}).get((today - timedelta(days=i)).isoformat(), {}).get("total_ml", 0) >= goal))
    xp_map = _load()["xp"]
    xp_now = xp_map.get(today.isoformat())
    before = [v for d, v in xp_map.items() if d < start.isoformat()]
    xp_week = (xp_now - max(before)) if xp_now is not None and before else None
    try:
        streak = int(desk_missions.view().get("ofensiva", {}).get("atual", 0))
    except Exception:  # noqa: BLE001
        streak = 0
    apps = range_apps([(today - timedelta(days=i)).isoformat() for i in range(7)])
    return {"tarefas": done, "agua_dias": water_days, "ofensiva": streak, "xp": xp_week,
            "tela_total": sum(apps.values()), "apps": top(apps, 3)}


def week_speech(s: dict) -> str:
    parts = [f"Na semana, o senhor concluiu {s['tarefas']} {'tarefa' if s['tarefas'] == 1 else 'tarefas'}",
             f"bateu a meta de água em {s['agua_dias']} de 7 dias"]
    if s["xp"]:
        parts.append(f"ganhou {s['xp']} de XP")
    text = ", ".join(parts[:-1]) + " e " + parts[-1] + "."
    if s["ofensiva"]:
        text += f" A ofensiva está em {s['ofensiva']} {'dia' if s['ofensiva'] == 1 else 'dias'}."
    if s["tela_total"]:
        text += f" Tempo de tela: {fmt(s['tela_total'])}"
        text += f", mais no {s['apps'][0][0]}." if s["apps"] else "."
    return text


@skill(
    name="resumo_da_semana",
    title="resumir a semana",
    description="Resumo dos últimos 7 dias do usuário: tarefas concluídas, dias com a meta de água, ofensiva, XP e programas mais usados.",
    permission=Permission.READ,
    timeout=8,
    triggers=[r"\b(?:resumo|resuma|balanco)\s+(?:da|de|dessa|desta)\s+(?:minha\s+)?semana\b", r"\bcomo foi (?:a )?minha semana\b"],
    params={"type": "object", "properties": {}},
    examples=["resumo da semana", "como foi minha semana?"],
)
def resumo_da_semana(ctx: SkillContext) -> SkillResult:
    s = week_summary()
    rows = [{"label": "Tarefas concluídas", "value": str(s["tarefas"])},
            {"label": "Meta de água", "value": f"{s['agua_dias']} de 7 dias"},
            {"label": "Ofensiva", "value": f"{s['ofensiva']} dias"}]
    if s["xp"] is not None:
        rows.append({"label": "XP ganho", "value": f"+{s['xp']}"})
    if s["tela_total"]:
        rows.append({"label": "Tempo de tela", "value": fmt(s["tela_total"])})
        rows += [{"label": f"  {a}", "value": fmt(sec)} for a, sec in s["apps"]]
    return SkillResult(speech=week_speech(s), cards=[{"type": "skill", "data": {"tag": "SUA SEMANA", "source": "últimos 7 dias", "rows": rows}}],
                       data=s)

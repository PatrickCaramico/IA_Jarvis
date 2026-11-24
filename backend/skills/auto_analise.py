"""Auto-análise do PC (V9.2): o JARVIS olha o próprio computador e sugere o que fazer quando a memória ou o
processador estão altos.

Antes: o vigia do sistema (skills/system_guard.py) só avisava no limite (memória acima de 92% ou processador acima
de 90%) e só oferecia fechar o programa que mais gastava. Agora há um diagnóstico com sugestões concretas:
  - o navegador com muitas abas (cada aba é um processo; se o Chrome do JARVIS estiver aberto, conta as abas);
  - programas que ficam em segundo plano gastando memória (Teams, Discord, Steam, OneDrive…);
  - o próprio JARVIS gastando demais (reiniciar libera);
  - o PC ligado há dias sem reiniciar, o Windows usando o disco como memória, disco quase cheio;
  - e oferece fechar o programa mais pesado que é seguro fechar (pergunta antes: fechar_programa é crítica).

Frases: "faz uma auto análise", "analisa o meu PC", "por que a memória está alta?", "como liberar memória?".
A central mostra ANALISAR embaixo da memória/processador quando eles estão altos, e o vigia avisa (só na tela e
no celular) quando a memória passa de 85% por alguns minutos.
"""
from __future__ import annotations

import logging
import re
import time
from typing import Optional

from core.skills import Permission, SkillContext, SkillResult, skill

log = logging.getLogger("jarvis.skills.auto_analise")

BROWSERS = {"chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "brave.exe"}
BACKGROUND = {"teams.exe", "ms-teams.exe", "discord.exe", "steam.exe", "steamwebhelper.exe", "onedrive.exe",
              "epicgameslauncher.exe", "spotify.exe", "whatsapp.exe", "telegram.exe", "zoom.exe", "slack.exe",
              "obs64.exe", "battle.net.exe", "riotclientservices.exe", "dropbox.exe", "googledrivefs.exe"}
BROWSER_HEAVY_MB = 1200
BACKGROUND_MB = 300
OFFER_MB = 500
JARVIS_MB = 900
UPTIME_DAYS = 5


def _gb_or_mb(mb: float) -> str:
    return f"{mb / 1024:.1f} GB".replace(".", ",") if mb >= 1024 else f"{round(mb)} MB"


def level(pct: float) -> str:
    if pct >= 90:
        return "crítica"
    if pct >= 80:
        return "alta"
    if pct >= 70:
        return "moderada"
    return "tranquila"


def diagnose(snap: dict) -> dict:
    """Parte pura: a partir das medições, devolve {"findings": [...], "tips": [...], "offer": nome|None, "speech": str}.

    snap: cpu, ram, ram_total_gb, swap, procs (os do pc_scan), jarvis_mb, uptime_days, disk_free_pct, disk_free_gb,
    tabs (abas do Chrome do JARVIS ou None).
    """
    cpu, ram = float(snap.get("cpu") or 0), float(snap.get("ram") or 0)
    procs = [p for p in snap.get("procs") or [] if not p.get("protected")]
    findings: list[dict] = [
        {"label": "Memória", "value": f"{ram:.0f}% ({level(ram)}) de {snap.get('ram_total_gb', 0):.0f} GB".replace(".", ",")},
        {"label": "Processador", "value": f"{cpu:.0f}%"},
    ]
    tips: list[str] = []
    offer: Optional[dict] = None

    by_mem = sorted(procs, key=lambda p: p.get("mem_mb", 0), reverse=True)
    browsers = [p for p in by_mem if p["name"].lower() in BROWSERS]
    for b in browsers[:2]:
        findings.append({"label": b["label"], "value": f"{_gb_or_mb(b['mem_mb'])} em {b.get('count', 1)} processos"})
    heavy_browser = next((b for b in browsers if b["mem_mb"] >= BROWSER_HEAVY_MB or b.get("count", 1) >= 25), None)
    if heavy_browser:
        tabs = snap.get("tabs")
        extra = f" (o navegador do JARVIS está com {tabs} abas)" if tabs else ""
        tips.append(f"O {heavy_browser['label']} é o que mais pesa: {_gb_or_mb(heavy_browser['mem_mb'])}{extra}. "
                    "Cada aba é um processo: feche as que não está usando.")

    background = [p for p in by_mem if p["name"].lower() in BACKGROUND and p["mem_mb"] >= BACKGROUND_MB]
    if background:
        names = ", ".join(f"{p['label']} ({_gb_or_mb(p['mem_mb'])})" for p in background[:3])
        tips.append(f"Programas que ficam em segundo plano gastando memória: {names}. Feche os que não estiver usando.")

    if ram >= 80:
        candidate = next((p for p in by_mem if p["name"].lower() not in BROWSERS and p["mem_mb"] >= OFFER_MB), None)
        if candidate:
            offer = {"name": candidate["name"], "label": candidate["label"], "mem_mb": candidate["mem_mb"]}

    if cpu >= 80 and procs:
        hog = max(procs, key=lambda p: p.get("cpu_percent", 0))
        if hog.get("cpu_percent", 0) >= 15:
            findings.append({"label": "Mais processador", "value": f"{hog['label']} ({hog['cpu_percent']:.0f}%)"})
            tips.append(f"O processador está em {cpu:.0f}%, puxado pelo {hog['label']}.")

    jarvis_mb = float(snap.get("jarvis_mb") or 0)
    if jarvis_mb:
        findings.append({"label": "O próprio JARVIS", "value": _gb_or_mb(jarvis_mb)})
    if jarvis_mb >= JARVIS_MB:
        tips.append(f"Eu mesmo estou usando {_gb_or_mb(jarvis_mb)}; reiniciar o JARVIS libera essa memória.")

    uptime = float(snap.get("uptime_days") or 0)
    if uptime >= UPTIME_DAYS:
        tips.append(f"O PC está ligado há {uptime:.0f} dias sem reiniciar; reiniciar libera a memória que ficou presa.")
    if float(snap.get("swap") or 0) >= 50 and ram >= 80:
        tips.append("O Windows já está usando o disco como memória extra, o que deixa tudo mais lento.")
    if snap.get("ram_total_gb") and snap["ram_total_gb"] <= 8.5 and ram >= 75:
        tips.append("Com 8 GB de memória, isso é comum: o navegador é o que mais ajuda a aliviar.")
    if snap.get("disk_free_pct") is not None and snap["disk_free_pct"] < 10:
        tips.append(f"O disco está quase cheio ({snap.get('disk_free_gb', 0):.0f} GB livres). "
                    "Diga 'meu PC está lento' que eu faço a limpeza.")

    # fala: 1 a 3 frases (estado + a dica principal + a oferta)
    if ram < 70 and cpu < 70 and not tips:
        speech = f"Está tudo tranquilo, senhor: memória em {ram:.0f}% e processador em {cpu:.0f}%."
    else:
        speech = f"Memória em {ram:.0f}%, {level(ram)}, e processador em {cpu:.0f}%."
        if tips:
            speech += " " + tips[0]
        elif by_mem:
            top = by_mem[0]
            speech += f" O que mais gasta é o {top['label']}, com {_gb_or_mb(top['mem_mb'])}."
        if offer:
            speech += f" Quer que eu feche o {offer['label']}, que está com {_gb_or_mb(offer['mem_mb'])}? Diga sim."
    return {"findings": findings, "tips": tips, "offer": offer, "speech": speech}


def snapshot() -> dict:
    """As medições do PC agora (~0,5 s, por causa da leitura de processador de cada programa)."""
    import os
    import shutil

    import psutil

    from config import settings
    from skills.system_guard import processes

    vm = psutil.virtual_memory()
    snap = {
        "cpu": psutil.cpu_percent(interval=None),
        "ram": vm.percent,
        "ram_total_gb": vm.total / 1024 ** 3,
        "swap": psutil.swap_memory().percent,
        "procs": processes(),
        "jarvis_mb": psutil.Process(os.getpid()).memory_info().rss / 1024 ** 2,
        "uptime_days": (time.time() - psutil.boot_time()) / 86400,
        "tabs": None,
    }
    try:
        du = shutil.disk_usage(settings.BASE_DIR.anchor or "/")
        snap["disk_free_gb"] = du.free / 1024 ** 3
        snap["disk_free_pct"] = du.free * 100 / du.total
    except OSError:
        pass
    try:  # abas do navegador do JARVIS, se ele estiver aberto (consulta local, prazo curto)
        from skills.navegador import cdp

        if cdp.available():
            snap["tabs"] = len(cdp.tabs())
    except Exception:  # noqa: BLE001 - sem navegador do JARVIS: só não conta as abas
        log.debug("Abas do navegador indisponíveis", exc_info=True)
    return snap


def card(result: dict, snap: dict) -> dict:
    rows = list(result["findings"])
    rows += [{"label": "Sugestão", "value": t} for t in result["tips"][:4]]
    return {"type": "skill", "data": {"tag": "AUTO-ANÁLISE", "source": f"CPU {snap.get('cpu', 0):.0f}% · RAM {snap.get('ram', 0):.0f}%",
                                      "rows": rows}}


_PATTERNS = [
    re.compile(r"\bauto ?analise\b"),
    re.compile(r"\b(?:analisa|analise|diagnostica|diagnostique|faz (?:uma? )?(?:analise|diagnostico)(?: d[oa])?)\s+"
               r"(?:o |a |do |da |no )?(?:meu |minha |seu )?(?:pc|computador|sistema|desempenho|memoria)\b"),
    re.compile(r"\bpor ?que\s+(?:a |o )?(?:memoria|ram|processador|cpu)\s+(?:esta|ta)\s+(?:tao\s+)?"
               r"(?:alta|alto|cheia|cheio|no talo|no limite)\b"),
    re.compile(r"\bcomo\s+(?:eu\s+)?(?:posso\s+|faco pra\s+|faco para\s+|da pra\s+)?(?:liberar|libero|economizar|aliviar)\s+"
               r"(?:a\s+)?(?:memoria|ram)\b"),
    re.compile(r"\bcomo\s+(?:eu\s+)?(?:posso\s+|da pra\s+)?melhorar\s+o\s+desempenho\b"),
]


def _parse(norm: str, _original: str) -> Optional[dict]:
    return {} if any(rx.search(norm) for rx in _PATTERNS) else None


@skill(
    name="auto_analise",
    title="fazer a auto-análise do PC",
    description=("Examina o PC agora (memória, processador, navegador, programas em segundo plano, o próprio JARVIS, "
                 "tempo ligado e disco) e sugere o que fazer para aliviar; oferece fechar o programa mais pesado."),
    permission=Permission.READ,
    timeout=15,
    parse=_parse,
    params={"type": "object", "properties": {}},
    examples=["faz uma auto análise", "por que a memória está alta?", "como liberar memória?"],
)
def auto_analise(ctx: SkillContext) -> SkillResult:
    snap = snapshot()
    result = diagnose(snap)
    offer = result["offer"]
    if offer:
        from core import confirm

        if confirm.pending() is None:
            confirm.offer("skill", {"name": "fechar_programa", "args": {"programa": re.sub(r"\.exe$", "", offer["name"], flags=re.I)},
                                    "origin": "auto_analise", "message": ctx.message})
        else:  # já há uma pergunta esperando o "sim": não oferece outra por cima
            result["speech"] = result["speech"].split(" Quer que eu feche")[0] + f" Se quiser, peça para eu fechar o {offer['label']}."
    data = {"cpu": snap["cpu"], "memoria": snap["ram"], "sugestoes": result["tips"],
            "programas": [{"nome": p["label"], "memoria_mb": p["mem_mb"]} for p in
                          sorted([p for p in snap["procs"] if not p.get("protected")], key=lambda p: p["mem_mb"], reverse=True)[:5]]}
    return SkillResult(speech=result["speech"], cards=[card(result, snap)], data=data)

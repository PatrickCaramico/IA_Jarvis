"""Skill System Guard (V8.11): o que está pesando no PC, fechar programas e o vigia que avisa sozinho.

Frases (caminho rápido, sem IA) — a IA também pode chamar cada uma como função:
- "o que está pesando no PC?", "quais programas estão usando mais memória?"
- "como está o uso do processador?", "quanto de memória está usando?" (vale com a central bloqueada)
- "fecha o Discord", "encerra o Spotify", "mata o processo do Chrome" -> pergunta antes (ação crítica) e
  nunca fecha programas do Windows, o antivírus nem o próprio JARVIS (lista do modules/pc_scan.py)
- "desliga o vigia do sistema" / "liga o vigia do sistema"

Vigia: a cada 15 s mede processador e memória. Processador acima de 90% por 2 min, ou memória acima de 92% por
1 min, gera UM aviso (no máximo a cada 30 min por tipo) dizendo o programa que mais gasta e oferecendo fechar.
A varredura completa continua em "meu PC está lento" (modules/pc_scan.py).
"""
from __future__ import annotations

import asyncio
import collections
import logging
import re
import time
from typing import Optional

from config import settings
from core import safe_io
from core.skills import Permission, SkillContext, SkillResult, service, skill

log = logging.getLogger("jarvis.skills.system_guard")

_PATH = settings.DATA_DIR / "vigia_sistema.json"
SAMPLE_S = 15
CPU_LIMIT, CPU_WINDOW_S = 90.0, 120
RAM_LIMIT, RAM_WINDOW_S = 92.0, 60
COOLDOWN_S = 30 * 60
NAMES_TTL_S = 10


def _norm(text: str) -> str:
    from skills.workspace.layouts import norm

    return norm(text)


def _gb_or_mb(mb: float) -> str:
    return f"{mb / 1024:.1f} GB".replace(".", ",") if mb >= 1024 else f"{round(mb)} MB"


# ------------------------------------------------------------------ programas
def processes() -> list[dict]:
    """Programas agrupados por nome (mesma leitura da varredura: memória e processador de cada um)."""
    import psutil

    from modules import pc_scan

    return pc_scan._processes(psutil)  # noqa: SLF001 - leva ~0,5 s (duas leituras de CPU)


_names_cache: dict = {"at": 0.0, "names": []}


def running_names() -> list[str]:
    """Nomes dos processos abertos (só nomes: rápido), com cache curto para o reconhecimento da frase."""
    if time.monotonic() - _names_cache["at"] < NAMES_TTL_S:
        return list(_names_cache["names"])
    try:
        import psutil

        names = sorted({(p.info.get("name") or "") for p in psutil.process_iter(["name"]) if p.info.get("name")})
    except Exception:  # noqa: BLE001
        names = []
    _names_cache.update(at=time.monotonic(), names=names)
    return names


def match_process(wanted: str, names: list[str]) -> list[str]:
    """Processos que combinam com o nome dito ("chrome" -> chrome.exe; "vs code" -> Code.exe)."""
    from modules.pc_scan import friendly

    w = _norm(wanted)
    if len(w) < 2:
        return []
    compact = w.replace(" ", "")
    exact, partial = [], []
    for name in names:
        stem = _norm(re.sub(r"\.exe$", "", name, flags=re.I))
        label = _norm(friendly(name))
        cands = {stem, label, stem.replace(" ", ""), label.replace(" ", "")}
        if w in cands or compact in cands:
            exact.append(name)
        elif len(w) >= 4 and any(compact in c.replace(" ", "") for c in (stem, label)):
            partial.append(name)
    return exact or partial


def _is_protected(name: str) -> bool:
    from modules.pc_scan import PROTECTED

    return name.lower() in PROTECTED


def _label(name: str) -> str:
    from modules.pc_scan import friendly

    return friendly(name)


# ------------------------------------------------------------------ o que está pesando
@skill(
    name="programas_pesados",
    title="ver o que está pesando",
    description="Diz quais programas estão usando mais memória e processador agora, com o uso geral do PC.",
    permission=Permission.READ,
    timeout=10,
    triggers=[r"\b(?:o que|quem|qual programa|quais programas|que programa|que programas)\b.{0,25}?\b(?:pesando|pesa mais|"
              r"consumindo|gastando|usando mais|comendo|puxando)\b",
              r"\b(?:quais|que)\s+programas?\s+(?:estao\s+|esta\s+)?(?:usando|gastando|consumindo)\s+mais\b"],
    examples=["o que está pesando no PC?", "quais programas estão usando mais memória?"],
)
def programas_pesados(ctx: SkillContext) -> SkillResult:
    import psutil

    procs = [p for p in processes() if not p["protected"]]
    cpu, ram = psutil.cpu_percent(interval=None), psutil.virtual_memory().percent
    if not procs:
        return SkillResult(speech=f"Nada pesado aberto agora, senhor. Processador em {cpu:.0f}% e memória em {ram:.0f}%.")
    top = sorted(procs, key=lambda p: p["mem_mb"] + p["cpu_percent"] * 40, reverse=True)[:5]
    first = top[0]
    parts = [f"{first['label']} ({_gb_or_mb(first['mem_mb'])} de memória"
             + (f", {first['cpu_percent']:.0f}% do processador)" if first["cpu_percent"] >= 5 else ")")]
    parts += [f"{p['label']} ({_gb_or_mb(p['mem_mb'])})" for p in top[1:3]]
    from skills.workspace.layouts import spoken_list

    speech = (f"O que mais pesa agora: {spoken_list(parts)}. Processador em {cpu:.0f}% e memória em {ram:.0f}%.")
    rows = [{"label": p["label"], "value": f"{_gb_or_mb(p['mem_mb'])} · CPU {p['cpu_percent']:.0f}%"} for p in top]
    return SkillResult(speech=speech, data={"cpu": cpu, "memoria": ram, "programas": top},
                       cards=[{"type": "skill", "data": {"tag": "O QUE ESTÁ PESANDO", "source": f"CPU {cpu:.0f}% · RAM {ram:.0f}%",
                                                         "rows": rows}}])


@skill(
    name="recursos_do_pc",
    title="ver o uso do PC",
    description="Diz o uso atual do processador, da memória, do disco e a bateria (sem dados pessoais).",
    permission=Permission.READ,
    public=True,
    timeout=6,
    triggers=[r"\b(?:uso|consumo)\s+d[ao]\s+(?:cpu|processador|memoria|ram)\b",
              r"\bquanto\s+(?:de\s+)?(?:memoria|ram|cpu|processador)\s+(?:esta|ta)\s+(?:usando|em uso|livre)\b",
              r"\bcomo\s+(?:esta|ta)\s+(?:o\s+|a\s+)?(?:processador|memoria|cpu|ram)\b"],
    examples=["como está o uso do processador?"],
)
def recursos_do_pc(ctx: SkillContext) -> SkillResult:
    import shutil

    import psutil

    cpu = psutil.cpu_percent(interval=0.3)
    vm = psutil.virtual_memory()
    parts = [f"processador em {cpu:.0f}%", f"memória em {vm.percent:.0f}% ({vm.available / 1024 ** 3:.1f} GB livres)".replace(".", ",", 1)]
    try:
        du = shutil.disk_usage(settings.BASE_DIR.anchor or "/")
        parts.append(f"disco com {du.free / 1024 ** 3:.0f} GB livres")
    except OSError:
        pass
    try:
        bat = psutil.sensors_battery()
        if bat is not None:
            parts.append(f"bateria em {bat.percent:.0f}%" + (" na tomada" if bat.power_plugged else ""))
    except Exception:  # noqa: BLE001
        pass
    from skills.workspace.layouts import spoken_list

    return SkillResult(speech=f"Agora: {spoken_list(parts)}, senhor.", data={"cpu": cpu, "memoria": vm.percent})


# ------------------------------------------------------------------ fechar programa (crítica)
_CLOSE_RE = re.compile(r"^(?:jarvis\s+)?(?:por favor\s+)?(?:fecha|feche|fechar|encerra|encerre|encerrar|mata|mate|matar|"
                       r"finaliza|finalize|finalizar)\s+(?:o\s+|a\s+)?(?:programa\s+|processo\s+|aplicativo\s+|app\s+)?"
                       r"(?:d[oa]\s+)?(?P<app>[a-z0-9 .]{2,40})$")
_NOT_APPS = {"aba", "abas", "guia", "guias", "janela", "janelas", "timer", "timers", "alarme", "alarmes", "modo", "tela",
             "painel", "cartao", "lembrete", "lembretes", "foco", "pomodoro", "isso", "tudo", "porta", "olho", "olhos",
             "a boca", "boca", "reuniao", "o jarvis", "jarvis", "central", "navegador"}


def _parse_close(norm_text: str, _original: str) -> Optional[dict]:
    m = _CLOSE_RE.search(norm_text)
    if not m:
        return None
    app = m.group("app").strip()
    if app in _NOT_APPS or app.split()[0] in _NOT_APPS:
        return None
    # só assume o pedido se o programa estiver aberto (senão a frase segue para as outras funções)
    if not match_process(app, running_names()):
        return None
    return {"programa": app}


def _close_question(args: dict) -> str:
    hits = match_process(args.get("programa", ""), running_names())
    if hits and all(_is_protected(h) for h in hits):  # já avisa: o "sim" não vai fechar mesmo
        return f"Por segurança, não fecho o {_label(hits[0])}, senhor: ele é do Windows ou do próprio JARVIS."
    label = _label(hits[0]) if hits else args.get("programa", "esse programa")
    return f"Fecho o {label}, senhor? O que não estiver salvo nele pode se perder. Diga sim para confirmar."


@skill(
    name="fechar_programa",
    title="fechar o programa",
    description="Fecha um programa aberto no computador (todas as janelas dele). Pede confirmação antes.",
    permission=Permission.CRITICAL,
    timeout=15,
    parse=_parse_close,
    params={"type": "object", "required": ["programa"], "properties": {
        "programa": {"type": "string", "description": "Nome do programa (ex.: chrome, discord, spotify)."}}},
    confirm_text=_close_question,
    examples=["fecha o Discord", "encerra o Spotify"],
)
def fechar_programa(ctx: SkillContext, programa: str) -> SkillResult:
    from modules import pc_scan

    _names_cache["at"] = 0.0  # lê de novo: o programa pode ter fechado enquanto esperava o "sim"
    hits = match_process(programa, running_names())
    if not hits:
        return SkillResult(ok=False, speech=f"Não encontrei o {programa} aberto, senhor.")
    blocked = [h for h in hits if _is_protected(h)]
    allowed = [h for h in hits if not _is_protected(h)]
    if not allowed:
        return SkillResult(ok=False, speech=f"Por segurança, não fecho o {_label(blocked[0])}: ele é do Windows ou do próprio JARVIS.")
    result = pc_scan.close_programs(allowed)
    closed = result.get("closed") or []
    if not closed:
        return SkillResult(ok=False, speech=f"Não consegui fechar o {_label(allowed[0])}, senhor. Talvez precise de permissão de administrador.")
    names = ", ".join(c["label"] for c in closed)
    total = sum(int(c.get("count") or 1) for c in closed)
    tail = f" ({total} processos)" if total > 1 else ""
    return SkillResult(speech=f"Fechei o {names}{tail}, senhor.")


# ------------------------------------------------------------------ vigia
def _load() -> dict:
    try:
        data = safe_io.read_json(_PATH) if _PATH.exists() else {}
    except (OSError, ValueError):
        data = {}
    return {"enabled": True, **data} if isinstance(data, dict) else {"enabled": True}


def watch_enabled() -> bool:
    return bool(_load().get("enabled", True))


class Watch:
    """Parte pura do vigia: guarda as medições e diz quando avisar (limite sustentado + intervalo mínimo)."""

    def __init__(self) -> None:
        self.samples: collections.deque = collections.deque(maxlen=64)
        self.last_alert: dict[str, float] = {}

    def add(self, ts: float, cpu: float, ram: float) -> None:
        self.samples.append((ts, cpu, ram))

    def _sustained(self, idx: int, limit: float, window: float, now: float) -> bool:
        recent = [s for s in self.samples if now - s[0] <= window + SAMPLE_S / 2]
        need = max(2, int(window // SAMPLE_S))
        if len(recent) < need or now - recent[0][0] < window - SAMPLE_S:
            return False
        return all(s[idx] >= limit for s in recent)

    def check(self, now: float) -> list[str]:
        kinds = []
        if self._sustained(1, CPU_LIMIT, CPU_WINDOW_S, now):
            kinds.append("cpu")
        if self._sustained(2, RAM_LIMIT, RAM_WINDOW_S, now):
            kinds.append("ram")
        due = [k for k in kinds if now - self.last_alert.get(k, -1e12) >= COOLDOWN_S]
        for k in due:
            self.last_alert[k] = now
        return due


def alert_text(kind: str, top: list[dict], cpu: float, ram: float) -> tuple[str, Optional[str]]:
    """Frase do aviso e o processo que dá para fechar (None = nenhum que seja seguro fechar)."""
    if kind == "cpu":
        text = f"Senhor, o processador está acima de {CPU_LIMIT:.0f}% há {CPU_WINDOW_S // 60} minutos ({cpu:.0f}% agora)."
        hog = max(top, key=lambda p: p["cpu_percent"]) if top else None
        if hog and hog["cpu_percent"] >= 15:
            text += f" O que mais está usando é o {hog['label']}, com {hog['cpu_percent']:.0f}%."
    else:
        text = f"Senhor, a memória está quase cheia: {ram:.0f}% em uso."
        hog = max(top, key=lambda p: p["mem_mb"]) if top else None
        if hog and hog["mem_mb"] >= 300:
            text += f" O que mais gasta é o {hog['label']}, com {_gb_or_mb(hog['mem_mb'])}."
    if hog is None or (kind == "cpu" and hog["cpu_percent"] < 15) or (kind == "ram" and hog["mem_mb"] < 300):
        return text, None
    return text, hog["name"]


async def _alert(kind: str, cpu: float, ram: float) -> None:
    from core import confirm, runtime, session, speech
    from modules import access

    top = [p for p in await asyncio.to_thread(processes) if not p["protected"]]
    text, victim = alert_text(kind, top, cpu, ram)
    if victim and confirm.pending() is None and not session.busy:
        confirm.offer("skill", {"name": "fechar_programa", "args": {"programa": re.sub(r"\.exe$", "", victim, flags=re.I)},
                                "origin": "vigia", "message": ""})
        text += " Quer que eu feche? Diga sim para fechar."
    runtime.notify("system", "⚠️ PC sobrecarregado", text)
    await runtime.manager.broadcast({"type": "alert", "text": text})
    if not access.is_restricted() and not session.busy:
        runtime.track(speech.say_quietly(text))
    log.info("Vigia do sistema: %s", text)


_watch = Watch()


@service("vigia_sistema")
async def watch_loop() -> None:
    import psutil

    from core.skills import registry

    psutil.cpu_percent(interval=None)  # a primeira leitura só prepara a medição
    while True:
        await asyncio.sleep(SAMPLE_S)
        if not registry.is_enabled("vigia_do_sistema") or not await asyncio.to_thread(watch_enabled):
            _watch.samples.clear()
            continue
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        now = time.time()
        _watch.add(now, cpu, ram)
        for kind in _watch.check(now):
            try:
                await _alert(kind, cpu, ram)
            except Exception:  # noqa: BLE001
                log.exception("Vigia do sistema: o aviso falhou")


_TOGGLE_RE = re.compile(r"\b(?P<verb>liga|ligue|ativa|ative|desliga|desligue|desativa|desative|pausa|pause)\s+"
                        r"(?:o\s+|os\s+)?(?:vigia|alertas?|avisos?)\s+(?:do\s+sistema|do\s+pc|de\s+(?:cpu|processador|memoria))\b")


def _parse_toggle(norm_text: str, _original: str) -> Optional[dict]:
    m = _TOGGLE_RE.search(norm_text)
    if not m:
        return None
    return {"ativo": not m.group("verb").startswith(("desl", "desat", "paus"))}


@skill(
    name="vigia_do_sistema",
    title="ajustar o vigia do sistema",
    description="Liga ou desliga os avisos automáticos de processador ou memória sobrecarregados.",
    permission=Permission.ACTION,
    timeout=5,
    parse=_parse_toggle,
    params={"type": "object", "required": ["ativo"], "properties": {"ativo": {"type": "boolean"}}},
    examples=["desliga o vigia do sistema"],
)
def vigia_do_sistema(ctx: SkillContext, ativo: bool) -> SkillResult:
    data = _load()
    data["enabled"] = bool(ativo)
    safe_io.write_json(_PATH, data)
    if ativo:
        return SkillResult(speech="Vigia do sistema ligado: aviso se o processador ou a memória ficarem no limite, senhor.")
    return SkillResult(speech="Vigia do sistema desligado, senhor. Não aviso mais sobre processador e memória.")

"""Skill Workspace (V8.11): janelas e monitores por voz, e workspaces salvos.

Frases (caminho rápido, sem IA) — a IA também pode chamar cada uma como função:
- "quais janelas estão abertas?"
- "manda o Chrome pro monitor 2", "leva o Spotify para a outra tela", "manda isso pro monitor principal"
- "organiza as janelas" (grade em cada monitor), "organiza as janelas do monitor 2",
  "coloca o Chrome e o VS Code lado a lado", "deixa só o Word na tela"
- "salva esse layout como estudo", "abre o workspace estudo", "quais são meus workspaces?",
  "apaga o workspace estudo" (pede confirmação)

Só funciona no Windows (ctypes); nos outros sistemas responde que não dá.
Arquivos: layouts.py (cálculo puro, testado), desktop.py (Windows), este (as skills).
"""
from __future__ import annotations

import os
import re
import time
from typing import Optional

from config import settings
from core import safe_io
from core.skills import Permission, SkillContext, SkillResult, skill
from skills.workspace import desktop as _desktop
from skills.workspace.layouts import (OTHER, Monitor, Window, find_windows, fit_into, from_fractions, grid,
                                      monitor_number, norm, plan_restore, resolve_monitor, snapshot, spoken_list)

_PATH = settings.DATA_DIR / "workspaces.json"
MAX_WORKSPACES = 20
MAX_LAUNCH = 6
NOT_WINDOWS = "Organizar janelas só funciona no Windows, senhor."


def get_desktop():
    return _desktop.get_desktop()


# ------------------------------------------------------------------ armazenamento
def _load() -> dict:
    try:
        data = safe_io.read_json(_PATH) if _PATH.exists() else {}
    except (OSError, ValueError):
        data = {}
    return data if isinstance(data, dict) else {}


def _save(data: dict) -> None:
    safe_io.write_json(_PATH, data)


def _key(name: str) -> str:
    n = norm(name)
    n = re.sub(r"^(?:o|a|do|da|de|meu|minha)\s+", "", n)
    return n.strip()[:40]


# ------------------------------------------------------------------ ajudantes
def _card(tag: str, source: str, rows: list[dict]) -> dict:
    return {"type": "skill", "data": {"tag": tag, "source": source, "rows": rows}}


def _target(dk, windows: list[Window], app: str) -> Optional[Window]:
    if app:
        hits = find_windows(windows, app)
        return hits[0] if hits else None
    fg = dk.foreground()
    return next((w for w in windows if w.hwnd == fg), None) or next((w for w in windows if not w.minimized), None)


def _mon(monitors: list[Monitor], index: int) -> Monitor:
    return next((m for m in monitors if m.index == index), monitors[0])


_WHERE = r"(?:pro|pra|para o|para a|para|no|na|ao|a)"
_MON_WORD = r"(?:\d|um|uma|dois|duas|tres|quatro|principal|primeir[oa]|segund[oa]|terceir[oa])"
_MOVE_RE = re.compile(
    r"\b(?:manda|mande|mandar|move|mova|mover|leva|leve|levar|joga|jogue|passa|passe|coloca|coloque|bota|bote)\s+"
    r"(?:o\s+|a\s+)?(?P<app>.+?)\s+" + _WHERE + r"\s+(?:"
    r"(?:monitor|tela)\s+(?P<m1>" + _MON_WORD + r")|(?P<m2>outr[oa]|proxim[oa]|seguinte)\s+(?:monitor|tela)"
    r"|(?P<m3>segund[oa]|primeir[oa])\s+(?:monitor|tela))\b"
)
_THIS = {"isso", "essa", "esta", "isto", "essa janela", "esta janela", "a janela", "janela", "ela", "ele"}


def _clean_app(app: str) -> str:
    app = re.sub(r"^(?:janela\s+d[oa]s?\s+|o\s+|a\s+)", "", (app or "").strip())
    return "" if app in _THIS else app


def _parse_move(norm_text: str, _original: str) -> Optional[dict]:
    m = _MOVE_RE.search(norm_text)
    if not m:
        return None
    number = monitor_number(m.group("m1") or m.group("m2") or m.group("m3") or "")
    if number is None:
        return None
    return {"app": _clean_app(m.group("app")), "monitor": number}


# ------------------------------------------------------------------ janelas abertas
@skill(
    name="janelas_abertas",
    title="ver as janelas abertas",
    description="Lista as janelas de programas abertas no computador, separadas por monitor.",
    permission=Permission.READ,
    timeout=8,
    triggers=[r"\b(?:quais|que)\s+(?:janelas|programas)\s+(?:estao\s+|tem\s+|eu tenho\s+)?abert[oa]s\b",
              r"\b(?:lista|liste|mostra|mostre)\s+(?:as\s+)?janelas(?:\s+abertas)?\b"],
    examples=["quais janelas estão abertas?"],
)
def janelas_abertas(ctx: SkillContext) -> SkillResult:
    dk = get_desktop()
    if dk is None:
        return SkillResult(ok=False, speech=NOT_WINDOWS)
    windows, monitors = dk.windows(), dk.monitors()
    if not windows:
        return SkillResult(speech="Não há janelas de programas abertas agora, senhor.")
    parts, rows = [], []
    for mon in monitors:
        labels: list[str] = []
        for w in windows:
            if w.monitor == mon.index and w.label not in labels:
                labels.append(w.label)
            if w.monitor == mon.index:
                rows.append({"label": f"Monitor {mon.index}" if len(monitors) > 1 else "Aberta",
                             "value": f"{w.label} — {w.title[:60]}" + (" (minimizada)" if w.minimized else "")})
        if labels:
            parts.append((f"no monitor {mon.index}, " if len(monitors) > 1 else "") + spoken_list(labels[:6]))
    n = len(windows)
    speech = f"Há {n} {'janela aberta' if n == 1 else 'janelas abertas'}: " + "; ".join(parts) + "."
    return SkillResult(speech=speech, cards=[_card("JANELAS ABERTAS", f"{n} janela(s)", rows[:20])],
                       data={"janelas": [{"programa": w.label, "titulo": w.title, "monitor": w.monitor} for w in windows]})


# ------------------------------------------------------------------ mover para outro monitor
@skill(
    name="janela_para_monitor",
    title="mover a janela de monitor",
    description=("Move a janela de um programa para outro monitor. monitor: 1 = principal, 2, 3...; "
                 "0 = o outro monitor (o seguinte). Sem programa, move a janela da frente."),
    permission=Permission.ACTION,
    timeout=8,
    parse=_parse_move,
    params={"type": "object", "required": ["monitor"], "properties": {
        "app": {"type": "string", "description": "Nome do programa ou parte do título (ex.: chrome, spotify)."},
        "monitor": {"type": "integer", "description": "1 = principal; 0 = o outro monitor."}}},
    examples=["manda o Chrome pro monitor 2", "leva o Spotify para a outra tela"],
)
def janela_para_monitor(ctx: SkillContext, monitor: int, app: str = "") -> SkillResult:
    dk = get_desktop()
    if dk is None:
        return SkillResult(ok=False, speech=NOT_WINDOWS)
    windows, monitors = dk.windows(), dk.monitors()
    win = _target(dk, windows, app)
    if win is None:
        return SkillResult(ok=False, speech=f"Não encontrei uma janela do {app} aberta, senhor." if app
                           else "Não encontrei uma janela para mover, senhor.")
    if len(monitors) < 2:
        return SkillResult(ok=False, speech="Só encontrei um monitor ligado, senhor.")
    dst_index = resolve_monitor(monitor, win.monitor, len(monitors))
    if dst_index is None:
        return SkillResult(ok=False, speech=f"Não encontrei o monitor {monitor}; há {len(monitors)} ligados, senhor.")
    if dst_index == win.monitor and monitor != OTHER:
        return SkillResult(speech=f"O {win.label} já está no monitor {dst_index}, senhor.")
    src, dst = _mon(monitors, win.monitor), _mon(monitors, dst_index)
    was_max = win.maximized
    dk.move(win.hwnd, fit_into(win.rect, src, dst))
    if was_max:
        dk.maximize(win.hwnd)
    dk.focus(win.hwnd)
    return SkillResult(speech=f"{win.label} no monitor {dst_index}, senhor.")


# ------------------------------------------------------------------ organizar
_ORG_RE = re.compile(r"\b(?:organiza|organize|organizar|arruma|arrume|arrumar|ajeita|ajeite|distribui|distribua)\s+"
                     r"(?:as\s+|minhas\s+|essas\s+)?janelas\b(?P<rest>.*)$")
_PAIR_RE = re.compile(r"\b(?:coloca|coloque|poe|ponha|deixa|deixe|bota|bote|abre|abra)?\s*(?:o\s+|a\s+)?(?P<a>[a-z0-9 ]+?)"
                      r"\s+e\s+(?:o\s+|a\s+)?(?P<b>[a-z0-9 ]+?)\s+lado a lado\b")
_ONLY_RE = re.compile(r"\b(?:deixa|deixe)\s+(?:so|somente|apenas)\s+(?:o\s+|a\s+)?(?P<app>.+?)\s+"
                      r"(?:na tela|aberto|aberta|visivel|na frente)\b")
_MON_IN = re.compile(r"\b(?:do|no|da|na)\s+(?:monitor|tela)\s+(?P<m>" + _MON_WORD + r")\b")


def _parse_organize(norm_text: str, _original: str) -> Optional[dict]:
    m = _PAIR_RE.search(norm_text)
    if m and m.group("a").strip() and m.group("b").strip():
        return {"layout": "lado_a_lado", "apps": [m.group("a").strip(), m.group("b").strip()]}
    m = _ONLY_RE.search(norm_text)
    if m:
        return {"layout": "foco", "apps": [_clean_app(m.group("app"))]}
    m = _ORG_RE.search(norm_text)
    if not m:
        return None
    rest = m.group("rest")
    args: dict = {"layout": "lado_a_lado" if "lado a lado" in rest else "grade"}
    mm = _MON_IN.search(rest)
    if mm and monitor_number(mm.group("m")):
        args["monitor"] = monitor_number(mm.group("m"))
    return args


@skill(
    name="organizar_janelas",
    title="organizar as janelas",
    description=("Organiza as janelas abertas. layout: 'grade' (todas lado a lado em grade, em cada monitor), "
                 "'lado_a_lado' (duas janelas dividindo a tela; apps opcional com os dois programas) ou 'foco' "
                 "(maximiza um programa e minimiza as outras janelas daquele monitor)."),
    permission=Permission.ACTION,
    timeout=10,
    parse=_parse_organize,
    params={"type": "object", "required": ["layout"], "properties": {
        "layout": {"type": "string", "enum": ["grade", "lado_a_lado", "foco"]},
        "monitor": {"type": "integer", "description": "Só neste monitor (1 = principal)."},
        "apps": {"type": "array", "items": {"type": "string"}, "description": "Programas envolvidos."}}},
    examples=["organiza as janelas", "coloca o Chrome e o VS Code lado a lado", "deixa só o Word na tela"],
)
def organizar_janelas(ctx: SkillContext, layout: str, monitor: int = 0, apps: Optional[list] = None) -> SkillResult:
    dk = get_desktop()
    if dk is None:
        return SkillResult(ok=False, speech=NOT_WINDOWS)
    windows, monitors = dk.windows(), dk.monitors()
    visible = [w for w in windows if not w.minimized]
    apps = [str(a) for a in (apps or []) if str(a).strip()]
    if monitor and not any(m.index == monitor for m in monitors):
        return SkillResult(ok=False, speech=f"Não encontrei o monitor {monitor}, senhor.")

    if layout == "grade":
        placed, used = 0, 0
        for mon in monitors:
            if monitor and mon.index != monitor:
                continue
            mine = [w for w in visible if w.monitor == mon.index][:9]
            if not mine:
                continue
            used += 1
            for w, rect in zip(mine, grid(mon, len(mine))):
                dk.move(w.hwnd, rect)
                placed += 1
        if not placed:
            return SkillResult(speech="Não há janelas visíveis para organizar, senhor.")
        where = f"no monitor {monitor}" if monitor else ("nos monitores" if used > 1 else "na tela")
        return SkillResult(speech=f"Organizei {placed} {'janela' if placed == 1 else 'janelas'} {where}, senhor.")

    if layout == "lado_a_lado":
        chosen: list[Window] = []
        for app in apps[:2]:
            hit = next((w for w in find_windows(windows, app) if w not in chosen), None)
            if hit is None:
                return SkillResult(ok=False, speech=f"Não encontrei uma janela do {app} aberta, senhor.")
            chosen.append(hit)
        for w in visible:
            if len(chosen) >= 2:
                break
            if w not in chosen:
                chosen.append(w)
        if len(chosen) < 2:
            return SkillResult(ok=False, speech="Preciso de duas janelas abertas para deixar lado a lado, senhor.")
        mon = _mon(monitors, monitor or chosen[0].monitor)
        for w, rect in zip(chosen, grid(mon, 2)):
            dk.move(w.hwnd, rect)
        dk.focus(chosen[0].hwnd)
        return SkillResult(speech=f"{chosen[0].label} e {chosen[1].label} lado a lado, senhor.")

    # foco
    win = _target(dk, windows, apps[0] if apps else "")
    if win is None:
        return SkillResult(ok=False, speech=f"Não encontrei uma janela do {apps[0]} aberta, senhor." if apps
                           else "Não encontrei uma janela para focar, senhor.")
    mon_index = monitor or win.monitor
    if mon_index != win.monitor:
        dk.move(win.hwnd, fit_into(win.rect, _mon(monitors, win.monitor), _mon(monitors, mon_index)))
    dk.maximize(win.hwnd)
    others = [w for w in visible if w.monitor == mon_index and w.hwnd != win.hwnd]
    for w in others:
        dk.minimize(w.hwnd)
    dk.focus(win.hwnd)
    tail = f"; minimizei {len(others)} {'janela' if len(others) == 1 else 'janelas'}" if others else ""
    return SkillResult(speech=f"Só o {win.label} na tela{tail}, senhor.")


# ------------------------------------------------------------------ workspaces salvos
_LAYOUT_WORD = r"(?:layout|workspace|arranjo(?: das janelas)?|espaco de trabalho|area de trabalho)"


@skill(
    name="salvar_workspace",
    title="salvar o workspace",
    description="Salva com um nome a posição atual das janelas abertas (programa, monitor e tamanho) para remontar depois.",
    permission=Permission.ACTION,
    timeout=8,
    triggers=[r"\b(?:salva|salve|salvar|guarda|guarde|grava|grave)\s+(?:esse\s+|este\s+|o\s+|meu\s+)?" + _LAYOUT_WORD
              + r"(?:\s+atual|\s+das janelas)?\s+(?:como|com o nome(?: de)?)\s+(?P<nome>[a-z0-9 ]{2,40})$"],
    params={"type": "object", "required": ["nome"], "properties": {
        "nome": {"type": "string", "description": "Nome do workspace (ex.: estudo, trabalho, reunião)."}}},
    examples=["salva esse layout como estudo"],
)
def salvar_workspace(ctx: SkillContext, nome: str) -> SkillResult:
    dk = get_desktop()
    if dk is None:
        return SkillResult(ok=False, speech=NOT_WINDOWS)
    key = _key(nome)
    if not key:
        return SkillResult(ok=False, speech="Qual nome dou para esse workspace, senhor?")
    items = snapshot(dk.windows(), dk.monitors())
    if not items:
        return SkillResult(ok=False, speech="Não há janelas abertas para salvar, senhor.")
    data = _load()
    if key not in data and len(data) >= MAX_WORKSPACES:
        return SkillResult(ok=False, speech=f"Já há {MAX_WORKSPACES} workspaces salvos; apague um antes, senhor.")
    data[key] = {"windows": items, "saved_at": time.strftime("%Y-%m-%d %H:%M")}
    _save(data)
    labels = spoken_list(list(dict.fromkeys(Window(0, i["title"], i["process"]).label for i in items))[:5])
    return SkillResult(speech=f"Workspace {key} salvo com {len(items)} janelas: {labels}. "
                              f"Para remontar, diga: abre o workspace {key}.")


def _restore(dk, saved: list[dict]) -> tuple[int, int, list[str]]:
    monitors = dk.monitors()
    windows = dk.windows()
    placed = opened = 0
    failed: list[str] = []
    for item, win in plan_restore(saved, windows):
        label = Window(0, item.get("title", ""), item.get("process", "")).label
        if win is None:
            exe = item.get("exe") or ""
            if opened >= MAX_LAUNCH or not exe or not os.path.isfile(exe):
                failed.append(label)
                continue
            known = {w.hwnd for w in dk.windows()}
            dk.launch(exe)
            win = dk.wait_new_window(item.get("process", ""), known)
            if win is None:
                failed.append(label)
                continue
            opened += 1
        mon = _mon(monitors, int(item.get("monitor") or 1))
        dk.move(win.hwnd, from_fractions(item.get("frac") or [], mon))
        if item.get("maximized"):
            dk.maximize(win.hwnd)
        placed += 1
    return placed, opened, failed


@skill(
    name="abrir_workspace",
    title="montar o workspace",
    description="Remonta um workspace salvo: põe cada janela no monitor e na posição guardados e abre os programas que faltam.",
    permission=Permission.ACTION,
    timeout=45,
    triggers=[r"\b(?:abre|abra|abrir|restaura|restaure|monta|monte|carrega|carregue|ativa|ative|volta|volte)\s+"
              r"(?:o\s+|pro\s+|para o\s+|meu\s+)?" + _LAYOUT_WORD + r"\s+(?:d[eao]\s+)?(?P<nome>[a-z0-9 ]{2,40})$"],
    params={"type": "object", "required": ["nome"], "properties": {"nome": {"type": "string"}}},
    examples=["abre o workspace estudo"],
)
def abrir_workspace(ctx: SkillContext, nome: str) -> SkillResult:
    dk = get_desktop()
    if dk is None:
        return SkillResult(ok=False, speech=NOT_WINDOWS)
    data = _load()
    key = _key(nome)
    entry = data.get(key)
    if entry is None:
        names = spoken_list(sorted(data)) if data else ""
        extra = f" Os salvos são: {names}." if names else " Para criar, diga: salva esse layout como " + key + "."
        return SkillResult(ok=False, speech=f"Não tenho um workspace chamado {key}, senhor.{extra}")
    placed, opened, failed = _restore(dk, entry.get("windows") or [])
    speech = f"Workspace {key} montado: {placed} {'janela' if placed == 1 else 'janelas'} no lugar"
    if opened:
        speech += f", {opened} {'programa aberto' if opened == 1 else 'programas abertos'}"
    speech += "."
    if failed:
        speech += f" Não consegui abrir {spoken_list(failed[:3])}."
    return SkillResult(speech=speech + " Pronto, senhor." if not failed else speech, ok=placed > 0 or not failed)


def has_workspace(nome: str) -> bool:
    """Para outras skills (ex.: o modo reunião usa o workspace "reuniao" se ele existir)."""
    return _key(nome) in _load()


@skill(
    name="listar_workspaces",
    title="listar os workspaces",
    description="Diz quais workspaces (arranjos de janelas) estão salvos.",
    permission=Permission.READ,
    timeout=5,
    triggers=[r"\b(?:quais|meus|lista|liste|mostra)\s+(?:sao\s+)?(?:os\s+)?(?:meus\s+)?(?:layouts|workspaces)\b"],
    examples=["quais são meus workspaces?"],
)
def listar_workspaces(ctx: SkillContext) -> SkillResult:
    data = _load()
    if not data:
        return SkillResult(speech="Ainda não há workspaces salvos, senhor. Arrume as janelas e diga: salva esse layout como trabalho.")
    rows = [{"label": k, "value": f"{len(v.get('windows') or [])} janelas · {v.get('saved_at', '')}"} for k, v in sorted(data.items())]
    return SkillResult(speech=f"Workspaces salvos: {spoken_list(sorted(data))}.",
                       cards=[_card("WORKSPACES", f"{len(data)} salvo(s)", rows)])


@skill(
    name="apagar_workspace",
    title="apagar o workspace",
    description="Apaga um workspace salvo.",
    permission=Permission.CRITICAL,
    timeout=5,
    triggers=[r"\b(?:apaga|apague|exclui|exclua|remove|remova|esquece|esqueca|deleta|delete)\s+o\s+"
              r"(?:layout|workspace)\s+(?P<nome>[a-z0-9 ]{2,40})$"],
    params={"type": "object", "required": ["nome"], "properties": {"nome": {"type": "string"}}},
    confirm_text=lambda a: f"Apago o workspace {_key(a.get('nome', ''))}, senhor? Diga sim para confirmar.",
    examples=["apaga o workspace estudo"],
)
def apagar_workspace(ctx: SkillContext, nome: str) -> SkillResult:
    data = _load()
    key = _key(nome)
    if key not in data:
        return SkillResult(ok=False, speech=f"Não tenho um workspace chamado {key}, senhor.")
    del data[key]
    _save(data)
    return SkillResult(speech=f"Workspace {key} apagado, senhor.")

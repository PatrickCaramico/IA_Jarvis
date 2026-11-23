"""Workspace: partes puras (sem Windows), testadas em qualquer sistema.

Monitores e janelas chegam como dados (Monitor, Window); aqui só se calcula onde cada janela deve ficar.
"""
from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional

GAP = 8  # espaço entre as janelas lado a lado (px)
MAX_PER_MONITOR = 9


@dataclass
class Monitor:
    index: int  # 1 = principal; depois da esquerda para a direita
    left: int
    top: int
    right: int
    bottom: int  # área de trabalho (sem a barra de tarefas)
    primary: bool = False

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


@dataclass
class Window:
    hwnd: int
    title: str
    process: str  # ex.: chrome.exe
    exe: str = ""  # caminho completo (para reabrir num workspace salvo)
    monitor: int = 1
    rect: tuple[int, int, int, int] = (0, 0, 0, 0)  # left, top, right, bottom
    maximized: bool = False
    minimized: bool = False
    extra: dict = field(default_factory=dict)

    @property
    def label(self) -> str:
        from modules.pc_scan import friendly

        return friendly(self.process)


Rect = tuple[int, int, int, int]  # x, y, largura, altura


def norm(text: str) -> str:
    t = unicodedata.normalize("NFKD", (text or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", t)).strip()


def order_monitors(raw: list[Monitor]) -> list[Monitor]:
    """Numera: o principal é o 1; os outros seguem da esquerda para a direita (e de cima para baixo)."""
    ordered = sorted(raw, key=lambda m: (not m.primary, m.left, m.top))
    for i, m in enumerate(ordered, start=1):
        m.index = i
    return ordered


_NUM_WORDS = {"um": 1, "uma": 1, "primeiro": 1, "primeira": 1, "principal": 1, "dois": 2, "duas": 2, "segundo": 2,
              "segunda": 2, "tres": 3, "terceiro": 3, "terceira": 3, "quatro": 4, "quarto": 4, "quarta": 4}
OTHER = 0  # "a outra tela": o monitor seguinte ao da janela


def monitor_number(word: str) -> Optional[int]:
    w = norm(word)
    if w.isdigit():
        return int(w)
    if w in ("outro", "outra", "proximo", "proxima", "seguinte"):
        return OTHER
    return _NUM_WORDS.get(w)


def resolve_monitor(wanted: int, current: int, count: int) -> Optional[int]:
    """Número pedido -> monitor existente (OTHER = o seguinte, dando a volta). None = não existe."""
    if count <= 0:
        return None
    if wanted == OTHER:
        return 1 if count == 1 else (current % count) + 1
    return wanted if 1 <= wanted <= count else None


def _score(win: Window, wanted: str) -> int:
    w = norm(wanted)
    if not w:
        return 0
    compact = w.replace(" ", "")
    label, stem = norm(win.label), norm(re.sub(r"\.exe$", "", win.process, flags=re.I))
    for cand in (label, stem):
        if cand and (cand == w or cand.replace(" ", "") == compact):
            return 3
    for cand in (label, stem):
        if cand and len(w) >= 3 and (w in cand or cand in w or compact in cand.replace(" ", "")):
            return 2
    if len(w) >= 3 and w in norm(win.title):
        return 1
    return 0


def find_windows(windows: list[Window], wanted: str) -> list[Window]:
    """Janelas que combinam com o nome dito ("chrome", "vs code", "o documento do contrato").

    Mantém a ordem da tela (a de cima primeiro) entre as de mesma nota."""
    scored = [(s, i, w) for i, w in enumerate(windows) if (s := _score(w, wanted)) > 0]
    best = max((s for s, _, _ in scored), default=0)
    return [w for s, _, w in sorted(scored, key=lambda t: (-t[0], t[1])) if s == best]


def grid(mon: Monitor, n: int, gap: int = GAP) -> list[Rect]:
    """Retângulos para n janelas num monitor. 1 = tela toda; 2 = metades; 3 = metade + duas empilhadas;
    4+ = grade (colunas = teto da raiz)."""
    n = max(1, min(n, MAX_PER_MONITOR))
    x0, y0, W, H = mon.left + gap, mon.top + gap, mon.width - 2 * gap, mon.height - 2 * gap
    if n == 1:
        return [(x0, y0, W, H)]
    if n == 3:
        half = (W - gap) // 2
        hh = (H - gap) // 2
        return [(x0, y0, half, H), (x0 + half + gap, y0, W - half - gap, hh),
                (x0 + half + gap, y0 + hh + gap, W - half - gap, H - hh - gap)]
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    cw, rh = (W - gap * (cols - 1)) // cols, (H - gap * (rows - 1)) // rows
    out = []
    for i in range(n):
        r, c = divmod(i, cols)
        out.append((x0 + c * (cw + gap), y0 + r * (rh + gap), cw, rh))
    return out


def fit_into(rect: tuple[int, int, int, int], src: Monitor, dst: Monitor) -> Rect:
    """Leva a janela para outro monitor mantendo a posição e o tamanho proporcionais (sem sair da tela)."""
    left, top, right, bottom = rect
    fx = (left - src.left) / max(1, src.width)
    fy = (top - src.top) / max(1, src.height)
    fw = (right - left) / max(1, src.width)
    fh = (bottom - top) / max(1, src.height)
    w = max(320, min(dst.width, int(fw * dst.width)))
    h = max(240, min(dst.height, int(fh * dst.height)))
    x = dst.left + int(min(max(fx, 0.0), 1.0) * dst.width)
    y = dst.top + int(min(max(fy, 0.0), 1.0) * dst.height)
    x = min(max(x, dst.left), dst.right - w)
    y = min(max(y, dst.top), dst.bottom - h)
    return x, y, w, h


def to_fractions(rect: tuple[int, int, int, int], mon: Monitor) -> list[float]:
    left, top, right, bottom = rect
    return [round((left - mon.left) / max(1, mon.width), 4), round((top - mon.top) / max(1, mon.height), 4),
            round((right - left) / max(1, mon.width), 4), round((bottom - top) / max(1, mon.height), 4)]


def from_fractions(frac: list[float], mon: Monitor) -> Rect:
    fx, fy, fw, fh = (list(frac) + [0, 0, 0.5, 0.5])[:4]
    w = max(320, min(mon.width, int(fw * mon.width)))
    h = max(240, min(mon.height, int(fh * mon.height)))
    x = min(max(mon.left + int(fx * mon.width), mon.left), mon.right - w)
    y = min(max(mon.top + int(fy * mon.height), mon.top), mon.bottom - h)
    return x, y, w, h


def snapshot(windows: list[Window], monitors: list[Monitor], limit: int = 12) -> list[dict]:
    """O que guardar num workspace: programa, monitor e posição em frações (resiste a trocar a resolução)."""
    by_index = {m.index: m for m in monitors}
    out = []
    for w in windows:
        if w.minimized or not w.process:
            continue
        mon = by_index.get(w.monitor) or monitors[0]
        out.append({"process": w.process, "exe": w.exe, "title": w.title[:120], "monitor": mon.index,
                    "frac": to_fractions(w.rect, mon), "maximized": w.maximized})
        if len(out) >= limit:
            break
    return out


def plan_restore(saved: list[dict], windows: list[Window]) -> list[tuple[dict, Optional[Window]]]:
    """Casa cada item salvo com uma janela aberta do mesmo programa (cada janela usada uma vez).
    Sem janela aberta: (item, None) = precisa abrir o programa."""
    free = list(windows)
    plan: list[tuple[dict, Optional[Window]]] = []
    for item in saved:
        same = [w for w in free if w.process.lower() == str(item.get("process", "")).lower()]
        if same:
            title = norm(item.get("title", ""))
            same.sort(key=lambda w: 0 if title and norm(w.title) == title else 1)
            pick = same[0]
            free.remove(pick)
            plan.append((item, pick))
        else:
            plan.append((item, None))
    return plan


def spoken_list(names: list[str]) -> str:
    names = [n for n in names if n]
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " e " + names[-1]

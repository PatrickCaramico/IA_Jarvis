"""Arquivos por voz (4.2, funcionalidade 5 do backlog).

- "Acha o vídeo que gravei ontem" / "Cadê a planilha de gastos" / "Encontra o arquivo relatório":
  procura nas pastas pessoais (Área de Trabalho, Documentos, Downloads, Vídeos, Imagens, Músicas),
  mostra até 5 resultados e aceita "abre o primeiro" ou "mostra na pasta".
- "Organiza a pasta Downloads": monta um plano (separar por tipo em subpastas), diz o que vai fazer e
  só move depois do "sim". Nada é apagado, nenhum arquivo é sobrescrito e "desfazer organização"
  devolve tudo para o lugar.

Segurança: só olha dentro das pastas pessoais do usuário; ignora pastas de sistema e de programas.
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import threading
import time
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from config import settings

log = logging.getLogger("jarvis.files")

MAX_RESULTS = 5
MAX_ENTRIES = 40000
MAX_DEPTH = 5
SEARCH_BUDGET_S = 4.0
RESULTS_TTL_S = 600
SKIP_DIRS = {"node_modules", "venv", ".venv", ".git", "__pycache__", "appdata", "$recycle.bin", "site-packages",
             "dist", "build", ".cache"}
PARTIAL_EXT = {".crdownload", ".part", ".tmp", ".download", ".partial"}
RECENT_GUARD_S = 120  # arquivo mexido há menos de 2 min pode estar baixando: fica fora da organização
UNDO_PATH = settings.DATA_DIR / "organizacao_ultima.json"

KINDS: dict[str, tuple[str, set[str]]] = {
    "video": ("Vídeos", {".mp4", ".mkv", ".mov", ".avi", ".wmv", ".webm", ".flv"}),
    "image": ("Imagens", {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic", ".svg"}),
    "audio": ("Áudios", {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac"}),
    "pdf": ("PDFs", {".pdf"}),
    "sheet": ("Planilhas", {".xlsx", ".xls", ".csv", ".ods"}),
    "slides": ("Apresentações", {".pptx", ".ppt", ".odp"}),
    "doc": ("Documentos", {".docx", ".doc", ".txt", ".odt", ".rtf", ".md"}),
    "archive": ("Compactados", {".zip", ".rar", ".7z", ".tar", ".gz"}),
    "installer": ("Instaladores", {".exe", ".msi", ".msix"}),
    "code": ("Código", {".py", ".js", ".jsx", ".ts", ".html", ".css", ".json", ".bat", ".ps1"}),
}
KIND_WORDS = {
    "video": "video", "videos": "video", "gravacao": "video", "filme": "video",
    "foto": "image", "fotos": "image", "imagem": "image", "imagens": "image", "print": "image",
    "musica": "audio", "audio": "audio", "audios": "audio",
    "pdf": "pdf", "planilha": "sheet", "planilhas": "sheet", "excel": "sheet",
    "apresentacao": "slides", "slides": "slides", "powerpoint": "slides",
    "documento": "doc", "documentos": "doc", "texto": "doc", "word": "doc",
    "zip": "archive", "instalador": "installer",
    "arquivo": None, "arquivos": None,
}
STOPWORDS = {"o", "a", "os", "as", "um", "uma", "de", "do", "da", "dos", "das", "que", "eu", "meu", "minha", "no", "na",
             "em", "pra", "para", "com", "gravei", "baixei", "salvei", "fiz", "criei", "editei", "chamado", "chamada",
             "sobre", "ultimo", "ultima", "mais", "recente", "hoje", "ontem", "semana", "essa", "esta", "dessa",
             "desta", "passada", "mes", "pc", "computador"}

_lock = threading.Lock()
_last: dict[str, Any] = {"results": [], "at": 0.0}


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def personal_roots() -> list[Path]:
    """Pastas pessoais que existem neste PC (inclui as versões do OneDrive)."""
    home = Path(os.environ.get("USERPROFILE") or Path.home())
    names = ["Desktop", "Área de Trabalho", "Documents", "Documentos", "Downloads", "Videos", "Vídeos",
             "Pictures", "Imagens", "Music", "Músicas"]
    roots: list[Path] = []
    for base in (home, home / "OneDrive"):
        for name in names:
            p = base / name
            if p.is_dir() and p.resolve() not in {r.resolve() for r in roots}:
                roots.append(p)
    return roots


def folder_by_name(spoken: str) -> Optional[Path]:
    """'downloads', 'área de trabalho', 'documentos'... -> pasta pessoal correspondente."""
    wanted = _norm(spoken)
    aliases = {"downloads": ("downloads",), "download": ("downloads",),
               "area de trabalho": ("desktop", "area de trabalho"), "desktop": ("desktop", "area de trabalho"),
               "documentos": ("documents", "documentos"), "documents": ("documents", "documentos")}
    targets = aliases.get(wanted)
    if not targets:
        return None
    for root in personal_roots():
        if _norm(root.name) in targets:
            return root
    return None


# ------------------------------------------------------------------ busca
def parse_request(norm: str) -> Optional[dict]:
    """'acha o video que gravei ontem' -> {kind, when, words}. None se não for pedido de arquivo."""
    m = re.match(r"^(?:jarvis\s+)?(?:me\s+)?(?:acha|ache|achar|encontra|encontre|encontrar|procura|procure|"
                 r"localiza|localize|cade|onde (?:esta|ta|fica))\s+(?:o|a|os|as|meu|minha|meus|minhas)?\s*(.+)$", norm)
    if not m:
        return None
    tokens = m.group(1).split()
    if not tokens or tokens[0] not in KIND_WORDS:
        return None  # "procura receita de bolo" continua sendo pesquisa na web
    kind = KIND_WORDS[tokens[0]]
    rest = " ".join(tokens[1:])
    when = None
    if re.search(r"\bhoje\b", rest):
        when = "today"
    elif re.search(r"\bontem\b", rest):
        when = "yesterday"
    elif re.search(r"\b(?:essa|esta|nessa|nesta) semana\b", rest):
        when = "week"
    words = [w for w in tokens[1:] if w not in STOPWORDS and len(w) > 1]
    return {"kind": kind, "when": when, "words": words}


def _when_ok(mtime: float, when: Optional[str], now: datetime) -> bool:
    if not when:
        return True
    day = datetime.fromtimestamp(mtime).date()
    if when == "today":
        return day == now.date()
    if when == "yesterday":
        return day == (now - timedelta(days=1)).date()
    return day >= (now - timedelta(days=now.weekday())).date()


def search(kind: Optional[str], words: list[str], when: Optional[str] = None,
           roots: Optional[list[Path]] = None, now: Optional[datetime] = None) -> list[dict]:
    """Procura arquivos pelo tipo, palavras do nome e data. Mais recentes primeiro."""
    roots = roots if roots is not None else personal_roots()
    now = now or datetime.now()
    exts = KINDS[kind][1] if kind else None
    deadline = time.monotonic() + SEARCH_BUDGET_S
    seen = 0
    found: list[dict] = []
    stack = [(r, 0) for r in roots]
    while stack and seen < MAX_ENTRIES and time.monotonic() < deadline:
        folder, depth = stack.pop()
        try:
            entries = list(os.scandir(folder))
        except OSError:
            continue
        for entry in entries:
            seen += 1
            name = entry.name
            if name.startswith((".", "~$")):
                continue
            try:
                if entry.is_dir(follow_symlinks=False):
                    if depth < MAX_DEPTH and name.lower() not in SKIP_DIRS:
                        stack.append((Path(entry.path), depth + 1))
                    continue
                ext = os.path.splitext(name)[1].lower()
                if exts and ext not in exts:
                    continue
                norm_name = _norm(os.path.splitext(name)[0])
                if words and not all(w in norm_name for w in words):
                    continue
                st = entry.stat()
                if not _when_ok(st.st_mtime, when, now):
                    continue
                found.append({"path": entry.path, "name": name, "folder": Path(entry.path).parent.name,
                              "mtime": st.st_mtime, "size": st.st_size})
            except OSError:
                continue
    found.sort(key=lambda f: f["mtime"], reverse=True)
    return found[:MAX_RESULTS]


def _describe(item: dict, now: datetime) -> str:
    dt = datetime.fromtimestamp(item["mtime"])
    if dt.date() == now.date():
        day = f"hoje {dt:%H:%M}"
    elif dt.date() == (now - timedelta(days=1)).date():
        day = f"ontem {dt:%H:%M}"
    else:
        day = f"{dt:%d/%m}"
    return f"{item['name']} ({item['folder']}, {day})"


def remember(results: list[dict]) -> None:
    with _lock:
        _last["results"] = results
        _last["at"] = time.monotonic()


def last_results() -> list[dict]:
    with _lock:
        if time.monotonic() - _last["at"] > RESULTS_TTL_S:
            return []
        return list(_last["results"])


def search_reply(req: dict, results: list[dict], now: Optional[datetime] = None) -> str:
    now = now or datetime.now()
    what = KINDS[req["kind"]][0].lower() if req["kind"] else "arquivos"
    if not results:
        return f"Não encontrei {what} com essa descrição nas suas pastas pessoais, senhor."
    if len(results) == 1:
        return f"Encontrei {_describe(results[0], now)}. Diga 'abre' ou 'mostra na pasta'."
    items = "; ".join(f"{i + 1}: {_describe(r, now)}" for i, r in enumerate(results))
    return f"Encontrei {len(results)}, do mais recente: {items}. Diga 'abre o primeiro' ou 'mostra o segundo na pasta'."


_ORDINALS = {"primeiro": 0, "1": 0, "um": 0, "segundo": 1, "2": 1, "dois": 1, "terceiro": 2, "3": 2, "tres": 2,
             "quarto": 3, "4": 3, "quatro": 3, "quinto": 4, "5": 4, "cinco": 4}


def parse_followup(norm: str) -> Optional[tuple[str, int]]:
    """'abre o segundo' -> ('open', 1); 'mostra na pasta' -> ('reveal', 0)."""
    m = re.match(r"^(?:jarvis\s+)?(abre|abra|abrir|mostra|mostre|mostrar)(?:\s+(?:o|a))?(?:\s+(\w+))?(?:\s+(?:na|em)\s+pasta)?$", norm)
    if not m:
        return None
    verb, word = m.group(1), m.group(2)
    reveal = "pasta" in norm or verb.startswith("mostr")
    if word in (None, "arquivo", "ele", "ela", "isso", "esse", "essa", "pasta"):
        index = 0
    elif word in _ORDINALS:
        index = _ORDINALS[word]
    else:
        return None
    return ("reveal" if reveal else "open", index)


def open_path(path: str, reveal: bool = False) -> None:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    if sys.platform.startswith("win"):
        if reveal:
            subprocess.Popen(["explorer", "/select,", str(p)])  # noqa: S603,S607
        else:
            os.startfile(str(p))  # noqa: S606 - abre com o programa padrão do Windows
    else:  # testes/Linux
        subprocess.Popen(["xdg-open", str(p.parent if reveal else p)])  # noqa: S603,S607


# ------------------------------------------------------------------ organizar pasta
def kind_of(ext: str) -> str:
    for key, (_, exts) in KINDS.items():
        if ext in exts:
            return key
    return "other"


def folder_name(kind: str) -> str:
    return KINDS[kind][0] if kind in KINDS else "Outros"


def plan_organize(folder: Path, now_ts: Optional[float] = None) -> dict:
    """Plano: arquivos soltos na pasta -> subpasta pelo tipo. Não toca em pastas nem em downloads em andamento."""
    now_ts = now_ts or time.time()
    moves: list[dict] = []
    for entry in os.scandir(folder):
        if not entry.is_file(follow_symlinks=False) or entry.name.startswith((".", "~$")):
            continue
        ext = os.path.splitext(entry.name)[1].lower()
        if ext in PARTIAL_EXT or ext in {".lnk", ".ini", ".url"}:
            continue
        try:
            if now_ts - entry.stat().st_mtime < RECENT_GUARD_S:
                continue
        except OSError:
            continue
        moves.append({"src": entry.path, "dest_dir": str(folder / folder_name(kind_of(ext)))})
    counts: dict[str, int] = {}
    for mv in moves:
        name = Path(mv["dest_dir"]).name
        counts[name] = counts.get(name, 0) + 1
    return {"folder": str(folder), "moves": moves, "counts": counts}


def plan_text(plan: dict) -> str:
    if not plan["moves"]:
        return f"A pasta {Path(plan['folder']).name} já está organizada, senhor: não há arquivos soltos para separar."
    parts = ", ".join(f"{n} em {name}" for name, n in sorted(plan["counts"].items(), key=lambda kv: -kv[1]))
    return (f"Na pasta {Path(plan['folder']).name} há {len(plan['moves'])} arquivos soltos. Posso separar assim: {parts}. "
            "Nada é apagado e dá para desfazer. Posso mover?")


def _unique(dest: Path) -> Path:
    if not dest.exists():
        return dest
    stem, ext = dest.stem, dest.suffix
    for i in range(2, 1000):
        cand = dest.with_name(f"{stem} ({i}){ext}")
        if not cand.exists():
            return cand
    raise FileExistsError(dest)


def apply_plan(plan: dict) -> str:
    """Executa o plano aprovado. Nunca sobrescreve; guarda o caminho de volta para desfazer."""
    folder = Path(plan["folder"]).resolve()
    allowed = {r.resolve() for r in personal_roots()}
    if folder not in allowed:
        return "Por segurança, só organizo as suas pastas pessoais, senhor."
    done: list[dict] = []
    skipped = 0
    for mv in plan["moves"]:
        src, dest_dir = Path(mv["src"]), Path(mv["dest_dir"])
        if src.parent.resolve() != folder or dest_dir.parent.resolve() != folder or not src.is_file():
            skipped += 1
            continue
        dest_dir.mkdir(exist_ok=True)
        dest = _unique(dest_dir / src.name)
        try:
            src.rename(dest)
            done.append({"from": str(src), "to": str(dest)})
        except OSError:
            skipped += 1
    try:
        UNDO_PATH.write_text(json.dumps({"folder": str(folder), "moves": done,
                                         "at": datetime.now().isoformat(timespec="seconds")},
                                        ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        log.warning("Não foi possível salvar o histórico para desfazer a organização.")
    msg = f"Pronto, senhor: {len(done)} arquivos organizados em {folder.name}."
    if skipped:
        msg += f" {skipped} ficaram onde estavam (em uso ou mudaram de lugar)."
    return msg + " Se quiser voltar, diga 'desfazer organização'."


def undo_last() -> str:
    try:
        data = json.loads(UNDO_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "Não há organização recente para desfazer, senhor."
    back = 0
    for mv in reversed(data.get("moves", [])):
        src, dest = Path(mv["to"]), Path(mv["from"])
        if src.is_file() and not dest.exists():
            try:
                src.rename(dest)
                back += 1
            except OSError:
                continue
    for d in {Path(mv["to"]).parent for mv in data.get("moves", [])}:
        try:
            d.rmdir()  # só remove a subpasta se ficou vazia
        except OSError:
            pass
    try:
        UNDO_PATH.unlink()
    except OSError:
        pass
    return f"Desfeito, senhor: {back} arquivos voltaram para {Path(data.get('folder', '')).name}."


# ------------------------------------------------------------------ V4.5: criar, mover e lixeira
# Tudo só depois do "sim" (core/confirm.py) e só dentro das pastas pessoais. Lixeira = Lixeira do
# Windows (dá para restaurar); nada é apagado de vez.
_TRASH_RE = re.compile(r"^(?:jarvis\s+)?(?:manda|mande|envia|envie|joga|jogue|coloca|coloque|move|mova)\s+(?:o|a)?\s*"
                       r"(primeiro|segundo|terceiro|quarto|quinto|1|2|3|4|5)?\s*(?:arquivo|resultado)?\s*(?:pra|para) (?:a )?lixeira$")
_MOVE_RE = re.compile(r"^(?:jarvis\s+)?(?:move|mova|mover|manda|mande|leva|leve)\s+(?:o|a)?\s*"
                      r"(primeiro|segundo|terceiro|quarto|quinto|1|2|3|4|5)\s*(?:arquivo|resultado)?\s*"
                      r"(?:pra|para) (?:a )?(?:pasta )?(?:de |do |da )?(.+)$")
_MKDIR_RE = re.compile(r"^(?:jarvis\s+)?(?:cria|crie|criar|faz|faca|fazer)\s+(?:uma\s+)?(?:nova\s+)?pasta\s+(?:chamada\s+)?"
                       r"(.+?)(?:\s+(?:na|no|em)\s+(?:a\s+)?(area de trabalho|desktop|documentos|downloads))?$")
_ORDINAL = {"primeiro": 0, "segundo": 1, "terceiro": 2, "quarto": 3, "quinto": 4, "1": 0, "2": 1, "3": 2, "4": 3, "5": 4}


def _inside_personal(path: Path) -> bool:
    try:
        rp = path.resolve()
    except OSError:
        return False
    return any(rp == r.resolve() or r.resolve() in rp.parents for r in personal_roots())


def send_to_trash(path: str) -> str:
    p = Path(path)
    if not p.exists() or not _inside_personal(p):
        return "Não posso mexer nesse arquivo, senhor (fora das suas pastas pessoais ou não existe mais)."
    script = ("Add-Type -AssemblyName Microsoft.VisualBasic; "
              "$p = $env:JARVIS_TRASH; if (Test-Path -LiteralPath $p -PathType Container) "
              "{ [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory($p,'OnlyErrorDialogs','SendToRecycleBin') } "
              "else { [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($p,'OnlyErrorDialogs','SendToRecycleBin') }")
    env = {**os.environ, "JARVIS_TRASH": str(p)}
    res = subprocess.run(["powershell", "-NoProfile", "-Command", script], env=env, capture_output=True, timeout=30,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if res.returncode != 0 or p.exists():
        log.warning("Lixeira falhou para %s: %s", p, res.stderr[:200])
        return f"Não consegui mandar {p.name} para a lixeira, senhor."
    with _lock:
        _last["results"] = [r for r in _last["results"] if r.get("path") != str(p)]
    return f"Pronto, senhor: {p.name} foi para a Lixeira. Dá para restaurar de lá se precisar."


def move_to(path: str, folder: str) -> str:
    import shutil

    src, dest_dir = Path(path), Path(folder)
    if not src.exists() or not _inside_personal(src) or not _inside_personal(dest_dir):
        return "Não posso mover esse arquivo, senhor (fora das suas pastas pessoais ou não existe mais)."
    dest = _unique(dest_dir / src.name)
    shutil.move(str(src), str(dest))
    return f"Movido, senhor: {src.name} agora está em {dest_dir.name}."


def make_folder(path: str) -> str:
    p = Path(path)
    if not _inside_personal(p.parent):
        return "Só crio pastas dentro das suas pastas pessoais, senhor."
    if p.exists():
        return f"A pasta {p.name} já existe em {p.parent.name}, senhor."
    p.mkdir(parents=False)
    return f"Pasta {p.name} criada em {p.parent.name}, senhor."


def _manage_voice(norm: str) -> Optional[str]:
    from core import confirm

    m = _TRASH_RE.match(norm)
    if m:
        results = last_results()
        if not results:
            return "Primeiro me peça para achar o arquivo, senhor. Por exemplo: acha a planilha de gastos."
        idx = _ORDINAL.get(m.group(1) or "primeiro", 0)
        if idx >= len(results):
            return f"Só encontrei {len(results)}, senhor."
        item = results[idx]
        confirm.offer("file_trash", {"path": item["path"]})
        return f"Mando {item['name']} para a Lixeira, senhor? Diga sim para confirmar."
    m = _MOVE_RE.match(norm)
    if m:
        results = last_results()
        folder = folder_by_name(m.group(2))
        if not results or folder is None:
            return None
        idx = _ORDINAL.get(m.group(1), 0)
        if idx >= len(results):
            return f"Só encontrei {len(results)}, senhor."
        item = results[idx]
        confirm.offer("file_move", {"path": item["path"], "folder": str(folder)})
        return f"Movo {item['name']} para {folder.name}, senhor? Diga sim para confirmar."
    m = _MKDIR_RE.match(norm)
    if m:
        base = folder_by_name(m.group(2) or "area de trabalho")
        name = re.sub(r"[\\/:*?\"<>|]", "", m.group(1)).strip().title()
        if base is None or not name:
            return None
        confirm.offer("file_mkdir", {"path": str(base / name)})
        return f"Crio a pasta {name} em {base.name}, senhor? Diga sim para confirmar."
    return None


# ------------------------------------------------------------------ voz
_ORGANIZE_RE = re.compile(r"^(?:jarvis\s+)?(?:organiza|organize|organizar|arruma|arrume|arrumar)\s+(?:a\s+)?(?:minha\s+)?(?:pasta\s+)?(?:de\s+|do\s+|da\s+)?(.+)$")
_UNDO_RE = re.compile(r"^(?:jarvis\s+)?desfa(?:z|zer|ca)\s+(?:a\s+)?organizacao")


async def handle_voice(norm: str) -> Optional[str]:
    import asyncio

    from core import confirm

    if _UNDO_RE.match(norm):
        return await asyncio.to_thread(undo_last)
    managed = _manage_voice(norm)  # V4.5: lixeira, mover, criar pasta (com confirmação)
    if managed:
        return managed
    m = _ORGANIZE_RE.match(norm)
    if m:
        folder = folder_by_name(m.group(1))
        if folder is None:
            return None
        plan = await asyncio.to_thread(plan_organize, folder)
        if plan["moves"]:
            confirm.offer("organize", plan)
        return plan_text(plan)
    follow = parse_followup(norm)
    if follow and last_results():
        action, index = follow
        results = last_results()
        if index >= len(results):
            return f"Só encontrei {len(results)}, senhor."
        item = results[index]
        try:
            await asyncio.to_thread(open_path, item["path"], action == "reveal")
        except Exception as exc:  # noqa: BLE001
            log.warning("Falha ao abrir %s: %s", item["path"], exc)
            return f"Não consegui abrir {item['name']}, senhor."
        return f"Mostrando {item['name']} na pasta, senhor." if action == "reveal" else f"Abrindo {item['name']}, senhor."
    req = parse_request(norm)
    if req:
        results = await asyncio.to_thread(search, req["kind"], req["words"], req["when"])
        remember(results)
        return search_reply(req, results)
    return None

"""V9.4.2: janela LOGS da central — os registros do JARVIS (logs/jarvis.log) e os eventos (erros que o usuário vê).

Antes, para ver um erro era preciso abrir o arquivo logs/jarvis.log no PC (ou o Ver-Logs.bat). Agora a central mostra:
  - os ERROS e AVISOS do arquivo de log, cada um com o rastro completo (traceback) agrupado;
  - ou tudo (as últimas linhas), com busca;
lendo só o final do arquivo (no máximo LIMIT_BYTES), para não pesar com um log grande.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from config import settings

LIMIT_BYTES = 512 * 1024
MAX_ENTRIES = 400
_LINE_RE = re.compile(r"^(?P<at>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ \[(?P<level>[A-Z]+)\] (?P<name>[^:]+): (?P<msg>.*)$")
LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}


def _tail(path: Path, limit: int = LIMIT_BYTES) -> str:
    try:
        size = path.stat().st_size
        with path.open("rb") as fh:
            if size > limit:
                fh.seek(size - limit)
            data = fh.read()
    except OSError:
        return ""
    text = data.decode("utf-8", errors="replace")
    if size > limit:  # a primeira linha veio cortada no meio
        text = text.split("\n", 1)[-1]
    return text


def parse(text: str) -> list[dict]:
    """Linhas do log -> registros {at, level, name, message, detail}. Linhas que não começam com data (traceback)
    entram no "detail" do registro anterior."""
    entries: list[dict] = []
    for raw in text.splitlines():
        m = _LINE_RE.match(raw)
        if m:
            entries.append({"at": m.group("at"), "level": m.group("level"), "name": m.group("name").strip(),
                            "message": m.group("msg").strip(), "detail": ""})
        elif entries and raw.strip():
            entries[-1]["detail"] = (entries[-1]["detail"] + "\n" + raw.rstrip()).strip("\n")[-6000:]
    return entries


def read(level: str = "WARNING", query: str = "", limit: int = 200, path: Optional[Path] = None) -> dict:
    """Os registros mais novos primeiro, a partir do nível pedido (WARNING = avisos e erros; INFO = quase tudo)."""
    path = path or settings.LOG_FILE
    min_level = LEVELS.get((level or "WARNING").upper(), 30)
    q = (query or "").strip().lower()
    items = [e for e in parse(_tail(path)) if LEVELS.get(e["level"], 20) >= min_level]
    if q:
        items = [e for e in items if q in f"{e['message']} {e['name']} {e['detail']}".lower()]
    total = len(items)
    items = list(reversed(items))[: max(1, min(limit, MAX_ENTRIES))]
    counts = {"errors": sum(1 for e in items if e["level"] in ("ERROR", "CRITICAL")),
              "warnings": sum(1 for e in items if e["level"] == "WARNING")}
    return {"file": str(path.name), "total": total, "items": items, **counts}

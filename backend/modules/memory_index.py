"""V9.0: MEMÓRIA PESQUISÁVEL. Busca instantânea, local e sem IA, em tudo o que o JARVIS guarda de você.

Antes, a conversa guardada eram só as últimas 20 trocas (memory.add_conversation) e não havia como procurar
"o que eu te falei sobre a viagem?". Agora:
  - TODA troca de conversa também entra num arquivo pesquisável (SQLite + FTS5, em data/memoria_busca.db);
  - as memórias ("lembre que…"), tarefas, lembretes e os copiados entram como "retrato" (reindexados quando o
    arquivo deles muda);
  - a busca ignora acentos e maiúsculas, aceita o começo das palavras ("viag" acha "viagem") e ordena pela
    relevância (bm25), com o trecho em destaque.
Usado pela skill buscar_memoria (voz e IA) e pela paleta Ctrl+K (/api/search/local).
"""
from __future__ import annotations

import logging
import re
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import settings

log = logging.getLogger("jarvis.memory_index")

_DB_PATH = settings.DATA_DIR / "memoria_busca.db"
MAX_CONVERSAS = 20000  # ~anos de conversa; o arquivo fica pequeno (texto puro)
KINDS = ("conversa", "memoria", "tarefa", "lembrete", "copiado")
KIND_LABEL = {"conversa": "Conversa", "memoria": "Memória", "tarefa": "Tarefa", "lembrete": "Lembrete", "copiado": "Copiado"}
_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(_DB_PATH), timeout=5)
    con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5(kind UNINDEXED, title, body, at UNINDEXED, "
                "tokenize = 'unicode61 remove_diacritics 2')")
    con.execute("CREATE TABLE IF NOT EXISTS sources (kind TEXT PRIMARY KEY, stamp TEXT)")
    return con


def add(kind: str, body: str, title: str = "", at: Optional[str] = None) -> None:
    """Guarda um documento (usado para as conversas, que vão se acumulando)."""
    body = (body or "").strip()
    if not body:
        return
    at = at or datetime.now().isoformat(timespec="seconds")
    with _lock:
        con = _connect()
        try:
            con.execute("INSERT INTO docs (kind, title, body, at) VALUES (?, ?, ?, ?)", (kind, title[:200], body[:4000], at))
            if kind == "conversa":
                total = con.execute("SELECT count(*) FROM docs WHERE kind = 'conversa'").fetchone()[0]
                if total > MAX_CONVERSAS:
                    con.execute("DELETE FROM docs WHERE rowid IN (SELECT rowid FROM docs WHERE kind = 'conversa' "
                                "ORDER BY at LIMIT ?)", (total - MAX_CONVERSAS,))
            con.commit()
        finally:
            con.close()


def add_conversation(user: str, assistant: str) -> None:
    """Uma troca da conversa (chamada por memory.add_conversation). Nunca atrapalha a conversa."""
    try:
        add("conversa", f"Você: {user.strip()}\nJARVIS: {assistant.strip()}", title=user.strip()[:120])
    except (sqlite3.Error, OSError):
        log.exception("Não consegui guardar a conversa na memória pesquisável")


# ------------------------------------------------------------------ retratos (reindexados quando mudam)
def _snapshot_sources() -> dict:
    from modules import desk, memory, reminders, tasks

    def mem_docs():
        data = memory.get_memory()
        out = [(f.get("text", ""), f.get("text", ""), f.get("created_at", "")) for f in data.get("facts", []) + data.get("routine", [])]
        out += [(f"{k}: {v}", f"{k}: {v}", "") for k, v in (data.get("preferences") or {}).items()]
        return out

    def task_docs():
        return [(t.get("texto", ""), t.get("texto", "") + (" (feita)" if t.get("concluida") else ""), t.get("criada_em", "") or "")
                for t in tasks.get_tasks(True)]

    def rem_docs():
        return [(r.get("texto", ""), f"{r.get('texto', '')} — {r.get('data_hora', '')}", r.get("data_hora", "") or "")
                for r in reminders.get_reminders(False)]

    def clip_docs():
        return [(i["texto"][:120], i["texto"], i.get("em", "")) for i in desk.clips().get("itens", [])]

    return {
        "memoria": (memory._PATH, mem_docs),
        "tarefa": (tasks._TASKS_PATH, task_docs),
        "lembrete": (reminders._REMINDERS_PATH, rem_docs),
        "copiado": (desk._CLIP_PATH, clip_docs),
    }


def _stamp(path: Path) -> str:
    try:
        st = path.stat()
        return f"{st.st_mtime_ns}:{st.st_size}"
    except OSError:
        return "missing"


def refresh() -> int:
    """Reindexa os retratos cujo arquivo mudou desde a última vez. Devolve quantos tipos foram refeitos."""
    changed = 0
    with _lock:
        con = _connect()
        try:
            for kind, (path, fetch) in _snapshot_sources().items():
                stamp = _stamp(path)
                row = con.execute("SELECT stamp FROM sources WHERE kind = ?", (kind,)).fetchone()
                if row and row[0] == stamp:
                    continue
                try:
                    docs = fetch()
                except Exception:  # noqa: BLE001 - uma fonte quebrada não derruba a busca nas outras
                    log.exception("Memória pesquisável: não consegui ler %s", kind)
                    continue
                con.execute("DELETE FROM docs WHERE kind = ?", (kind,))
                con.executemany("INSERT INTO docs (kind, title, body, at) VALUES (?, ?, ?, ?)",
                                [(kind, str(t)[:200], str(b)[:4000], str(a)) for t, b, a in docs if str(b).strip()])
                con.execute("INSERT OR REPLACE INTO sources (kind, stamp) VALUES (?, ?)", (kind, stamp))
                changed += 1
            con.commit()
        finally:
            con.close()
    return changed


# ------------------------------------------------------------------ busca
_TOKEN = re.compile(r"[0-9A-Za-zÀ-ÿ]+")
_STOP = {"a", "o", "as", "os", "de", "da", "do", "das", "dos", "e", "em", "no", "na", "nos", "nas", "um", "uma",
         "que", "sobre", "pra", "para", "com", "por", "eu", "te", "me", "meu", "minha", "isso", "aquilo"}


def fts_query(text: str, mode: str = "AND") -> str:
    """'viagem pro Rio' -> '"viagem"* AND "rio"*' (prefixo: "viag" acha "viagem"; aspas: nada vira operador)."""
    words = [w.lower() for w in _TOKEN.findall(text or "") if len(w) > 1 and w.lower() not in _STOP]
    return f" {mode} ".join(f'"{w}"*' for w in words[:8])


def search(text: str, limit: int = 8, kinds: Optional[list[str]] = None) -> list[dict]:
    """Os documentos que mais combinam com o texto (mais relevantes primeiro)."""
    try:
        refresh()
    except (sqlite3.Error, OSError):
        log.exception("Memória pesquisável: falha ao atualizar o índice")
    limit = max(1, min(50, int(limit)))
    kinds = [k for k in (kinds or []) if k in KINDS]
    results: list[dict] = []
    with _lock:
        con = _connect()
        try:
            for mode in ("AND", "OR"):  # todas as palavras; se nada vier, qualquer uma delas
                q = fts_query(text, mode)
                if not q:
                    return []
                sql = ("SELECT kind, title, snippet(docs, 2, '[', ']', '…', 14), at, bm25(docs) FROM docs "
                       "WHERE docs MATCH ?" + (f" AND kind IN ({','.join('?' * len(kinds))})" if kinds else "") +
                       " ORDER BY bm25(docs) LIMIT ?")
                rows = con.execute(sql, (q, *kinds, limit)).fetchall()
                if rows:
                    results = [{"kind": k, "label": KIND_LABEL.get(k, k), "title": t, "snippet": s, "at": a} for k, t, s, a, _ in rows]
                    break
        except sqlite3.OperationalError:
            log.exception("Memória pesquisável: consulta inválida (%s)", text)
            return []
        finally:
            con.close()
    return results


def stats() -> dict:
    with _lock:
        con = _connect()
        try:
            rows = con.execute("SELECT kind, count(*) FROM docs GROUP BY kind").fetchall()
        finally:
            con.close()
    return {k: n for k, n in rows}


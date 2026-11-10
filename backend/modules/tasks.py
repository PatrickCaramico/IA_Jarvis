"""Módulo de lista de tarefas persistente para o JARVIS.
Salva tarefas em data/tarefas.json com status, data de criação e data de conclusão.
"""
import json
import logging
import re
from datetime import datetime
from typing import Optional

from config import settings
from modules.quick_replies import _norm

log = logging.getLogger("jarvis.tasks")
_TASKS_PATH = settings.DATA_DIR / "tarefas.json"


def _load_tasks() -> list[dict]:
    if not _TASKS_PATH.exists():
        return []
    try:
        data = json.loads(_TASKS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _save_tasks(tasks: list[dict]) -> None:
    _TASKS_PATH.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")


def get_tasks(include_completed: bool = False) -> list[dict]:
    tasks = _load_tasks()
    if include_completed:
        return tasks
    return [t for t in tasks if not t.get("concluida", False)]


def add_task(texto: str) -> dict:
    tasks = _load_tasks()
    new_id = (max((t.get("id", 0) for t in tasks), default=0)) + 1
    task = {
        "id": new_id,
        "texto": texto.strip(),
        "concluida": False,
        "criada_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    tasks.append(task)
    _save_tasks(tasks)
    return task


def complete_task(identificador: str) -> Optional[dict]:
    tasks = _load_tasks()
    identificador_norm = _norm(identificador)
    for t in tasks:
        if not t.get("concluida", False):
            if str(t["id"]) == identificador.strip() or identificador_norm in _norm(t["texto"]):
                t["concluida"] = True
                t["concluida_em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
                _save_tasks(tasks)
                return t
    return None


def delete_task(task_id: int) -> bool:
    tasks = _load_tasks()
    before = len(tasks)
    tasks = [t for t in tasks if t.get("id") != task_id]
    if len(tasks) < before:
        _save_tasks(tasks)
        return True
    return False


async def handle_voice(message: str, norm: str, words: int, name: str) -> Optional[str]:
    # 1. Adicionar tarefa
    add_match = re.search(
        r"\b(?:adiciona|adicione|adicionar|nova tarefa|criar tarefa|bota na lista|coloca na lista|anota na lista)\s+(?:de\s+tarefas?\s+)?(?:de\s+|que\s+|para\s+)?(.+)",
        norm
    )
    if add_match and ("tarefa" in norm or "lista" in norm):
        texto = add_match.group(1).strip()
        texto = re.sub(r"^(?:de\s+|que\s+|para\s+|pra\s+)", "", texto)
        if texto:
            task = add_task(texto)
            return f"Adicionei a tarefa: {task['texto']}."

    # 2. Concluir / marcar como feita
    done_match = re.search(
        r"\b(?:conclui|conclua|concluir|complete|completar|terminei|finalizei|marcar como feita|marca como feita|feito)\s+(?:a\s+tarefa\s+)?(.+)",
        norm
    )
    if done_match and any(w in norm for w in ("tarefa", "conclui", "conclua", "terminei")):
        ident = done_match.group(1).strip()
        t = complete_task(ident)
        if t:
            return f"Marquei a tarefa '{t['texto']}' como concluída. Bom trabalho, senhor."
        return f"Não encontrei nenhuma tarefa pendente correspondente a '{ident}'."

    # 3. Listar / o que falta fazer
    is_list_query = any(q in norm for q in (
        "o que falta fazer", "o que tenho que fazer", "o que tenho pra fazer",
        "minhas tarefas", "lista de tarefas", "quais sao as tarefas", "quais as tarefas",
        "tarefas de hoje", "tarefas pendentes", "ver tarefas"
    ))
    if is_list_query:
        pendentes = get_tasks(include_completed=False)
        if not pendentes:
            return "Nenhuma tarefa pendente, senhor. Tudo em dia."
        itens = [f"{i+1}: {t['texto']}" for i, t in enumerate(pendentes[:6])]
        msg = f"Você tem {len(pendentes)} {'tarefa pendente' if len(pendentes) == 1 else 'tarefas pendentes'}: " + "; ".join(itens)
        if len(pendentes) > 6:
            msg += f". E mais {len(pendentes) - 6} tarefas."
        return msg + "."

    return None

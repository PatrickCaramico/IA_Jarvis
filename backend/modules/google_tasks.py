"""V9.5.6: 💡 BLOCO DE IDEIAS sincronizado com o GOOGLE TAREFAS (lista "Ideias JARVIS").

O senhor queria o Google Keep, mas a API do Keep só existe para contas corporativas (Google Workspace). O Google
Tarefas tem API oficial para conta pessoal e aparece no celular, no Gmail e na Agenda. Então:
  - ideia criada/editada/apagada no JARVIS (central ou voz) vai para a lista (projeto = "📌 " no título);
  - o que for anotado nessa lista pelo app do Google Tarefas entra no bloco (ao abrir o bloco e antes do "bom dia");
  - tarefa concluída no Google = ideia deixa de ser projeto (sai do briefing), sem apagar nada.
Usa a mesma conexão do Google da agenda (modules/google_calendar.py), com a permissão de Tarefas.
Tudo com prazo (timeout); falha aqui nunca impede de salvar a ideia no JARVIS (fica no log).
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

import requests

from modules import google_calendar, ideas

log = logging.getLogger("jarvis.google_tasks")

API = "https://tasks.googleapis.com/tasks/v1"
LIST_TITLE = "Ideias JARVIS"
PIN = "📌 "
TIMEOUT_S = 15

_list_id_cache: dict[str, str] = {}


def available() -> bool:
    """Conectado ao Google e com a permissão de Tarefas (quem conectou antes da 9.5.6 precisa conectar de novo)."""
    return google_calendar.connected() and google_calendar.TASKS_SCOPE in google_calendar.granted_scopes()


def status() -> dict:
    return {
        "configured": google_calendar.configured(),
        "connected": google_calendar.connected(),
        "tasks": available(),
    }


def _req(method: str, path: str, **kw) -> requests.Response:
    r = requests.request(method, f"{API}{path}", headers={"Authorization": f"Bearer {google_calendar.access_token()}"},
                         timeout=TIMEOUT_S, **kw)
    if r.status_code == 404 and method == "DELETE":
        return r  # já não existia
    r.raise_for_status()
    return r


def list_id(req: Callable = _req) -> str:
    """A lista "Ideias JARVIS" (cria na primeira vez)."""
    if "id" in _list_id_cache:
        return _list_id_cache["id"]
    for item in req("GET", "/users/@me/lists", params={"maxResults": 100}).json().get("items", []):
        if item.get("title") == LIST_TITLE:
            _list_id_cache["id"] = item["id"]
            return item["id"]
    created = req("POST", "/users/@me/lists", json={"title": LIST_TITLE}).json()
    _list_id_cache["id"] = created["id"]
    return created["id"]


def task_body(idea: dict) -> dict:
    """Ideia -> tarefa (título com 📌 quando é projeto; o texto vai nas notas)."""
    title = (PIN if idea.get("projeto") else "") + (idea.get("titulo") or "Ideia")
    return {"title": title[:1024], "notes": _notes_of(idea)[:8000]}


def idea_from_task(task: dict) -> dict:
    """Tarefa -> campos da ideia (📌 no começo = projeto)."""
    title = (task.get("title") or "").strip()
    project = title.startswith("📌")
    title = title.lstrip("📌").strip() or "Ideia sem título"
    return {"titulo": title, "texto": (task.get("notes") or "").strip(), "projeto": project and task.get("status") != "completed"}


def _notes_of(idea: dict) -> str:
    """O texto da ideia como vai para as notas (igual ao título = sem notas)."""
    text = idea.get("texto") or ""
    return "" if text == idea.get("titulo") else text


def push(idea: dict, req: Callable = _req) -> Optional[str]:
    """Cria ou atualiza a tarefa da ideia. Devolve o id da tarefa (e guarda na ideia)."""
    lid = list_id(req)
    body = task_body(idea)
    task_id = idea.get("google_task_id")
    if task_id:
        r = req("PATCH", f"/lists/{lid}/tasks/{task_id}", json=body)
    else:
        r = req("POST", f"/lists/{lid}/tasks", json=body)
    task_id = r.json().get("id") or task_id
    if task_id and task_id != idea.get("google_task_id"):
        ideas.link_task(idea["id"], task_id)
    return task_id


def remove(task_id: str, req: Callable = _req) -> None:
    if task_id:
        req("DELETE", f"/lists/{list_id(req)}/tasks/{task_id}")


def pull(req: Callable = _req) -> dict:
    """Traz para o bloco o que mudou no Google Tarefas. Devolve {"novas": n, "atualizadas": n}."""
    lid = list_id(req)
    tasks = req("GET", f"/lists/{lid}/tasks", params={"showCompleted": "true", "showHidden": "true", "maxResults": 100}).json().get("items", [])
    by_task = {i.get("google_task_id"): i for i in ideas.list_ideas() if i.get("google_task_id")}
    novas = atualizadas = 0
    for task in tasks:
        if not task.get("id") or task.get("deleted"):
            continue
        fields = idea_from_task(task)
        mine = by_task.get(task["id"])
        if mine is None:
            if task.get("status") == "completed":
                continue  # concluída antes de chegar aqui: não vale trazer
            idea = ideas.add_idea(fields["texto"] or fields["titulo"], fields["titulo"], fields["projeto"])
            ideas.link_task(idea["id"], task["id"])
            novas += 1
        elif (mine.get("titulo"), _notes_of(mine), bool(mine.get("projeto"))) != \
                (fields["titulo"], fields["texto"], fields["projeto"]):
            ideas.update_idea(mine["id"], text=fields["texto"] or mine.get("texto"), title=fields["titulo"], project=fields["projeto"])
            atualizadas += 1
    return {"novas": novas, "atualizadas": atualizadas}


def safe(fn: Callable, *args) -> Optional[object]:
    """Roda uma sincronização sem nunca derrubar quem chamou (o erro vai para o log)."""
    if not available():
        return None
    try:
        return fn(*args)
    except Exception:  # noqa: BLE001 - sem Google agora: a ideia continua salva no JARVIS
        log.exception("Google Tarefas: não consegui sincronizar")
        return None

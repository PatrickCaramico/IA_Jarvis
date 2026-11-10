"""Rotas de atalhos, tarefas, lembretes, foco, briefing e memória."""

import asyncio
from datetime import datetime
from fastapi import HTTPException
from pydantic import BaseModel
from modules import prefs, tasks, reminders, focus, briefing, memory, event_log, notifications, protocols, routine, triggers, tools
from fastapi import APIRouter

router = APIRouter()


class ShortcutRequest(BaseModel):
    name: str
    apps: list[str] = []
    urls: list[str] = []


class SiteRequest(BaseModel):
    name: str
    url: str
    apelidos: list[str] = []
    janela_app: bool = False


@router.get("/api/sites")
async def get_sites() -> dict:
    """Lista os sites abertos por voz e pela tela de configurações."""
    return {"sites": tools.list_sites()}


@router.post("/api/sites")
async def create_site(req: SiteRequest) -> dict:
    """Cria ou atualiza um site com URL, apelidos e janela do Chrome."""
    try:
        site = tools.save_site(req.name, req.url, req.apelidos, req.janela_app)
    except ValueError as exc:
        status = 409 if "Já existe" in str(exc) else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    return {"status": "ok", "site": site, "sites": tools.list_sites()}


@router.put("/api/sites/{name}")
async def update_site(name: str, req: SiteRequest) -> dict:
    """Atualiza um site existente."""
    try:
        site = tools.update_site(name, req.name, req.url, req.apelidos, req.janela_app)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        status = 409 if "Já existe" in str(exc) else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    return {"status": "ok", "site": site, "sites": tools.list_sites()}


@router.delete("/api/sites/{name}")
async def delete_site(name: str) -> dict:
    """Remove um site da lista de atalhos."""
    if not tools.delete_site(name):
        raise HTTPException(status_code=404, detail="Site não encontrado.")
    return {"status": "ok", "sites": tools.list_sites()}


@router.get("/api/shortcuts")
async def get_shortcuts() -> dict:
    """Lista os atalhos personalizados."""
    return {"shortcuts": prefs.get_shortcuts()}


@router.post("/api/shortcuts")
async def save_shortcut(req: ShortcutRequest) -> dict:
    """Cria ou atualiza um atalho personalizado."""
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nome do atalho não pode ser vazio.")
    prefs.save_shortcut(name, req.apps, req.urls)
    return {"status": "ok", "shortcuts": prefs.get_shortcuts()}


@router.delete("/api/shortcuts/{name}")
async def delete_shortcut(name: str) -> dict:
    """Remove um atalho personalizado."""
    if not prefs.delete_shortcut(name):
        raise HTTPException(status_code=404, detail="Atalho não encontrado.")
    return {"status": "ok", "shortcuts": prefs.get_shortcuts()}


# ---------------------------------------------------------------- produtividade (Fase 2)
class TaskRequest(BaseModel):
    texto: str


class ReminderRequest(BaseModel):
    texto: str
    data_hora: str  # formato: "YYYY-MM-DD HH:MM"


class FocusRequest(BaseModel):
    minutes: int = 25
    break_minutes: int = 5


@router.get("/api/tasks")
async def list_tasks(include_completed: bool = False) -> dict:
    return {"tasks": tasks.get_tasks(include_completed=include_completed)}


@router.post("/api/tasks")
async def create_task(req: TaskRequest) -> dict:
    t = tasks.add_task(req.texto)
    return {"status": "ok", "task": t}


@router.patch("/api/tasks/{task_id}/complete")
async def mark_task_complete(task_id: int) -> dict:
    t = tasks.complete_task(str(task_id))
    if not t:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    return {"status": "ok", "task": t}


@router.delete("/api/tasks/{task_id}")
async def remove_task(task_id: int) -> dict:
    if not tasks.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    return {"status": "ok"}


@router.get("/api/reminders")
async def list_reminders(only_pending: bool = False) -> dict:
    return {"reminders": reminders.get_reminders(only_pending=only_pending)}


@router.post("/api/reminders")
async def create_reminder(req: ReminderRequest) -> dict:
    try:
        dt = datetime.strptime(req.data_hora, "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Formato de data inválido. Use YYYY-MM-DD HH:MM.") from exc
    rem = reminders.add_reminder(req.texto, dt)
    return {"status": "ok", "reminder": rem}


@router.delete("/api/reminders/{rem_id}")
async def remove_reminder(rem_id: int) -> dict:
    if not reminders.delete_reminder(rem_id):
        raise HTTPException(status_code=404, detail="Lembrete não encontrado.")
    return {"status": "ok"}


@router.get("/api/focus")
async def get_focus_status() -> dict:
    return focus.session.status()


@router.post("/api/focus/start")
async def start_focus_session(req: FocusRequest) -> dict:
    msg = focus.start_focus(minutes=req.minutes, break_minutes=req.break_minutes)
    return {"status": "ok", "message": msg, "session": focus.session.status()}


@router.post("/api/focus/stop")
async def stop_focus_session() -> dict:
    msg = focus.stop_focus()
    return {"status": "ok", "message": msg, "session": focus.session.status()}


@router.get("/api/briefing")
async def get_briefing() -> dict:
    text = await briefing.generate_daily_briefing()
    return {"status": "ok", "briefing": text}


@router.post("/api/briefing/skip")
async def skip_briefing_part() -> dict:
    """V4.3: pula para o próximo assunto do briefing em andamento (corta só a fala atual)."""
    from core import briefing_flow

    return {"status": "ok", "skipped": briefing_flow.skip()}


@router.get("/api/memory")
async def get_memory() -> dict:
    return memory.get_memory()


class MemoryRequest(BaseModel):
    text: str
    category: str = "facts"


@router.post("/api/memory")
async def save_memory(req: MemoryRequest) -> dict:
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Memória vazia.")
    item = memory.remember(req.text, req.category)
    event_log.add("memory", f"Memória adicionada: {req.text}")
    return {"status": "ok", "item": item, "memory": memory.get_memory()}


# ---------------------------------------------------------------- 4.2: protocolos e gatilhos
class ProtocolRunRequest(BaseModel):
    name: str


@router.get("/api/protocols")
async def list_protocols() -> dict:
    """Protocolos salvos (ou os exemplos padrão) e as ações disponíveis."""
    user = (await asyncio.to_thread(prefs.get_all)).get("protocols") or {}
    return {
        "protocols": protocols.all_protocols(user),
        "using_defaults": not user,
        "defaults": protocols.DEFAULT_PROTOCOLS,
        "actions": list(protocols.ACTIONS),
    }


@router.post("/api/protocols/run")
async def run_protocol(req: ProtocolRunRequest) -> dict:
    """Executa um protocolo pelo nome (a resposta traz o texto e os passos que falharam)."""
    result = await protocols.run(req.name, record=False)
    if not result["ok"] and not result["problems"]:
        raise HTTPException(status_code=404, detail=result["reply"])
    return {"status": "ok", **result}


@router.get("/api/triggers")
async def get_triggers() -> dict:
    """Gatilhos condicionais com os ajustes do usuário aplicados sobre os padrões."""
    user = (await asyncio.to_thread(prefs.get_all)).get("triggers") or {}
    return {"triggers": triggers.merged_config(user), "defaults": triggers.DEFAULTS, "limits": {
        f"{k}.{f}": list(v) for (k, f), v in triggers.LIMITS.items()
    }}


@router.get("/api/routine")
async def get_routine() -> dict:
    """Hábitos encontrados para as sugestões pela rotina e as sugestões silenciadas."""
    return await asyncio.to_thread(routine.summary)


@router.post("/api/routine/unmute")
async def unmute_routine() -> dict:
    """Volta a permitir todas as sugestões que foram silenciadas com "não sugira mais"."""
    await asyncio.to_thread(routine.unmute_all)
    return {"status": "ok"}


@router.get("/api/notifications")
async def get_notifications() -> dict:
    """Central de notificações (experimental): status da leitura e as últimas notificações."""
    return {"status": notifications.status(), "items": notifications.items()}


@router.delete("/api/notifications")
async def clear_notifications() -> dict:
    """Limpa a lista do JARVIS (as notificações do Windows não são apagadas)."""
    notifications.clear()
    return {"status": "ok"}

"""Rotas de atalhos, tarefas, lembretes, foco, briefing e memória."""

import asyncio
from datetime import datetime
from fastapi import HTTPException
from pydantic import BaseModel
from modules import prefs, tasks, reminders, focus, briefing, memory, event_log, notifications, protocols, routine, triggers, tools, alarms
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


# ---------------------------------------------------------------- V5.1: alarmes
@router.get("/api/alarms")
async def list_alarms() -> dict:
    return {"alarms": [{**a, "descricao": alarms.describe(a)} for a in alarms.list_alarms()], "ringing": alarms.ringing_info()}


@router.get("/api/alarms/ringing")
async def alarm_ringing() -> dict:
    """Pública (bloqueio): só diz se está tocando e a hora, sem o rótulo."""
    info = alarms.ringing_info()
    return {"ringing": bool(info), "hora": info["hora"] if info else None, "snooze_minutes": alarms.SNOOZE_MINUTES}


@router.post("/api/alarms/stop")
async def alarm_stop() -> dict:
    return {"stopped": bool(await alarms.stop())}


@router.post("/api/alarms/snooze")
async def alarm_snooze() -> dict:
    at = await alarms.snooze()
    return {"snoozed": bool(at), "at": at.strftime("%H:%M") if at else None}


@router.delete("/api/alarms/{alarm_id}")
async def alarm_delete(alarm_id: int) -> dict:
    if not alarms.delete_alarm(alarm_id):
        raise HTTPException(status_code=404, detail="Alarme não encontrado.")
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


class IcsRequest(BaseModel):
    url: str = ""


# ---------------------------------------------------------------- V6.8.3: Central de Agentes
class PlaceRequest(BaseModel):
    name: str
    address: str


@router.get("/api/agents")
async def agents_catalog() -> dict:
    from modules import agents

    return {"agents": agents.catalog(), "places": agents.load_places()}


@router.post("/api/agents/places")
async def agents_place_save(req: PlaceRequest) -> dict:
    from modules import agents

    key = agents._key(req.name)  # noqa: SLF001 - mesmo nome que a voz usa ("o trabalho" -> "trabalho")
    address = req.address.strip()[:160]
    if not key or not address:
        raise HTTPException(status_code=400, detail="Diga o nome do lugar e o endereço.")
    await asyncio.to_thread(agents.save_place, key, address)
    return {"places": agents.load_places()}


@router.delete("/api/agents/places/{name}")
async def agents_place_delete(name: str) -> dict:
    from modules import agents

    if not await asyncio.to_thread(agents.forget_place, agents._key(name)):  # noqa: SLF001
        raise HTTPException(status_code=404, detail="Lugar não encontrado.")
    return {"places": agents.load_places()}


@router.get("/api/calendar/status")
async def calendar_status() -> dict:
    """V6.8.1: a agenda está conectada? (seção Google Agenda dos Ajustes)"""
    from modules import calendar_hub

    return {"connected": calendar_hub.connected(), "source": calendar_hub.source_name(), "ics": bool(calendar_hub.ics_url())}


@router.post("/api/calendar/ics")
async def set_calendar_ics(req: IcsRequest) -> dict:
    """V5.6: conecta a agenda pelo endereço secreto iCal (ou desconecta com url vazia)."""
    from modules import calendar_hub

    try:
        return await asyncio.to_thread(calendar_hub.set_ics_url, req.url)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Não consegui ler essa agenda: {exc}") from exc


class ShoppingAdd(BaseModel):
    texto: str


class ShoppingPatch(BaseModel):
    comprado: bool = True


@router.get("/api/shopping")
async def shopping_list() -> dict:
    from modules import shopping

    return {"items": shopping.list_items()}


@router.post("/api/shopping")
async def shopping_add(req: ShoppingAdd) -> dict:
    from modules import shopping

    added = shopping.add(shopping._split(req.texto))  # noqa: SLF001
    await shopping.announce()
    return {"added": added, "items": shopping.list_items()}


@router.patch("/api/shopping/{item_id}")
async def shopping_mark(item_id: int, req: ShoppingPatch) -> dict:
    from modules import shopping

    if not shopping.set_bought(item_id, req.comprado):
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    await shopping.announce()
    return {"items": shopping.list_items()}


@router.delete("/api/shopping/{item_id}")
async def shopping_remove(item_id: int) -> dict:
    from modules import shopping

    shopping.remove(item_id)
    await shopping.announce()
    return {"items": shopping.list_items()}


@router.post("/api/shopping/clear")
async def shopping_clear(all: bool = False) -> dict:  # noqa: A002
    from modules import shopping

    removed = shopping.clear(only_bought=not all)
    await shopping.announce()
    return {"removed": removed, "items": shopping.list_items()}


@router.get("/api/countdowns")
async def get_countdowns() -> dict:
    from modules import countdowns

    return {"items": countdowns.list_countdowns()}


@router.delete("/api/countdowns/{countdown_id}")
async def delete_countdown(countdown_id: int) -> dict:
    from modules import countdowns

    removed = countdowns.remove(countdown_id=countdown_id)
    await countdowns._announce()  # noqa: SLF001
    return {"removed": removed, "items": countdowns.list_countdowns()}


@router.get("/api/briefing/news-themes")
async def briefing_news_themes() -> dict:
    """V6.2: temas de notícias do "bom dia" em uso (os do usuário ou os padrões) e sugestões."""
    return {"items": briefing.news_themes(), "defaults": briefing.DEFAULT_NEWS_THEMES}


@router.post("/api/briefing/entry")
async def briefing_entry() -> dict:
    """V5.4: ao entrar na central, o PC decide (para todos os aparelhos juntos): briefing, perguntar ou saudar."""
    from modules import entry_greeting

    return entry_greeting.decide()


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

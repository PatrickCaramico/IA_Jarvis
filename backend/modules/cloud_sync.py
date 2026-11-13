"""V6.6: sincronização com o MODO NUVEM (funções do Netlify, ver netlify/nuvem/core.mjs).

Com o notebook desligado, o celular usa a nuvem: compras, tarefas, lembretes, alarmes e água ficam lá.
Quando o JARVIS do PC está ligado, a cada minuto este módulo:
  1) busca as mudanças feitas na nuvem (GET /api/cloud/sync) e aplica nas listas do PC;
  2) manda a foto das listas do PC (POST /api/cloud/sync), que vira o que a nuvem mostra.

Precisa de JARVIS_NUVEM_CHAVE no .env (a mesma variável do Netlify). Sem ela, não faz nada.
Só sincroniza o perfil principal (os perfis de outras pessoas ficam só no PC).
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Any

import requests

from config import settings
from modules import about, alarms, memory, profiles, reminders, shopping, tasks, water
from modules.quick_replies import _norm

log = logging.getLogger("jarvis.cloud_sync")

INTERVAL_S = 60
# V6.6.2: preferências que a tela da nuvem usa (nada de câmera, PIN, atalhos ou chaves)
CLOUD_PREF_KEYS = (
    "ai_name", "color_theme", "theme_colors", "background_style", "personality_mode", "silent_mode",
    "a11y_text_scale", "a11y_high_contrast", "a11y_reduce_motion", "briefing_news_themes", "water_quick_ml",
    "sfx_mode", "sfx_volume",
)
STATE: dict[str, Any] = {"last_ok": None, "last_error": "", "applied": 0}


def _key() -> str:
    return os.getenv("JARVIS_NUVEM_CHAVE", "").strip()


def _base() -> str:
    url = os.getenv("JARVIS_NUVEM_URL", "").strip() or settings.SITE_ORIGIN
    return url.rstrip("/") + "/api/cloud/sync"


def enabled() -> bool:
    return bool(_key() and (os.getenv("JARVIS_NUVEM_URL", "").strip() or settings.SITE_ORIGIN))


# ---------------------------------------------------------------- aplicar as mudanças da nuvem no PC
def _find(items: list[dict], field: str, text: str) -> dict | None:
    want = _norm(text or "")
    if not want:
        return None
    return next((i for i in items if _norm(i.get(field, "")) == want), None)


def apply_op(op: dict) -> bool:
    """Aplica uma operação da nuvem nas listas do PC. Devolve False se não coube (item já sumiu etc.)."""
    kind = op.get("op")
    if kind == "shopping_add":
        shopping.add([str(t) for t in op.get("itens") or []])
        return True
    if kind == "shopping_set":
        item = _find(shopping.list_items(), "texto", op.get("texto", ""))
        return bool(item and shopping.set_bought(item["id"], bool(op.get("comprado"))))
    if kind == "shopping_remove":
        item = _find(shopping.list_items(), "texto", op.get("texto", ""))
        return bool(item and shopping.remove(item["id"]))
    if kind == "shopping_clear":
        shopping.clear(only_bought=not op.get("tudo"))
        return True
    if kind == "task_add":
        tasks.add_task(str(op.get("texto", ""))[:140])
        return True
    if kind == "task_done":
        item = _find(tasks.get_tasks(), "texto", op.get("texto", ""))
        return bool(item and tasks.complete_task(str(item["id"])))
    if kind == "task_remove":
        item = _find(tasks.get_tasks(include_completed=True), "texto", op.get("texto", ""))
        return bool(item and tasks.delete_task(item["id"]))
    if kind == "reminder_add":
        try:
            when = datetime.strptime(op.get("data_hora", ""), "%Y-%m-%d %H:%M")
        except ValueError:
            return False
        reminders.add_reminder(str(op.get("texto", ""))[:140], when)
        return True
    if kind == "reminder_remove":
        rem = next((r for r in reminders.get_reminders(only_pending=False)
                    if _norm(r.get("texto", "")) == _norm(op.get("texto", ""))
                    and (not op.get("data_hora") or r.get("data_hora") == op.get("data_hora"))), None)
        return bool(rem and reminders.delete_reminder(rem["id"]))
    if kind == "alarm_add":
        try:
            hh, mm = (int(x) for x in str(op.get("hora", "")).split(":"))
        except ValueError:
            return False
        dias = [int(d) for d in op.get("dias") or [] if 0 <= int(d) <= 6]
        now = datetime.now()
        at = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        for _ in range(8):
            if at > now and (not dias or at.weekday() in dias):
                break
            at += timedelta(days=1)
        try:
            alarms.add_alarm(at, dias, str(op.get("rotulo", "")))
        except ValueError:
            return False
        return True
    if kind == "alarm_remove":
        alarm = next((a for a in alarms.list_alarms() if a.get("hora") == op.get("hora")
                      and _norm(a.get("rotulo", "")) == _norm(op.get("rotulo", ""))), None)
        return bool(alarm and alarms.delete_alarm(alarm["id"]))
    if kind == "water_add":
        if op.get("date") and op["date"] != water.get_status()["date"]:
            return False  # registro de outro dia: o PC só conta o dia de hoje
        try:
            water.add_intake(int(op.get("ml", 0)), "copo de água (celular)")
        except ValueError:
            return False
        return True
    if kind == "water_undo":
        water.undo_last()
        return True
    if kind == "place_set":  # V6.8: lugar salvo fora de casa (agente de rotas)
        from modules import agents

        nome, endereco = str(op.get("nome") or "").strip()[:40], str(op.get("endereco") or "").strip()[:160]
        if not nome or not endereco:
            return False
        agents.save_place(nome, endereco)
        return True
    if kind == "mood_set":  # V6.7: humor registrado fora de casa
        from modules import wellbeing

        try:
            day = datetime.strptime(str(op.get("date") or datetime.now().strftime("%Y-%m-%d")), "%Y-%m-%d")
            wellbeing.log_mood(int(op.get("score", 0)), when=day.replace(hour=datetime.now().hour, minute=datetime.now().minute))
        except (TypeError, ValueError):
            return False
        return True
    if kind == "water_goal":
        try:
            water.set_goal(int(op.get("goal_ml", 0)))
        except ValueError:
            return False
        return True
    return False


# ---------------------------------------------------------------- foto das listas do PC
def snapshot() -> dict:
    st = water.get_status()
    try:
        name = profiles._name(profiles.OWNER_ID, {})  # noqa: SLF001
    except Exception:  # noqa: BLE001
        name = settings.USER_NAME
    try:
        from modules import prefs

        assistant = prefs.get_ai_name()
        all_prefs = prefs.get_all()
    except Exception:  # noqa: BLE001
        assistant, all_prefs = "JARVIS", {}
    # V6.6.2: as configurações da central valem também no modo nuvem (só as de aparência, voz e IA)
    shared = {k: all_prefs[k] for k in CLOUD_PREF_KEYS if k in all_prefs}
    try:  # V6.6.9: a mesma voz do PC (estilo escolhido em Ajustes: nome, velocidade e tom) na nuvem
        from modules import tts

        name, rate, pitch = tts.voice_params()
        shared["voice"] = {"name": name, "rate": rate, "pitch": pitch}
    except Exception:  # noqa: BLE001
        pass
    try:  # temas de notícias do "bom dia" (os seus ou os padrões) viram atalhos na aba NOTÍCIAS da nuvem
        from modules import briefing

        shared["briefing_news_themes"] = [{"title": t["title"], "q": t.get("query") or t.get("topic")} for t in briefing.news_themes()]
    except Exception:  # noqa: BLE001
        shared.pop("briefing_news_themes", None)
    return {
        "compras": shopping.list_items(),
        "tarefas": tasks.get_tasks(include_completed=True)[-120:],
        "lembretes": [r for r in reminders.get_reminders(only_pending=True)][:120],
        "alarmes": alarms.list_alarms(),
        "agua": {"goal_ml": st["goal_ml"], "today": {"date": st["date"], "total_ml": st["total_ml"], "logs": st["logs"]},
                 # V6.8: ofensiva até ontem (a nuvem continua a contagem fora de casa)
                 "streak": {"date": st["date"], "base": st.get("streak_base", 0), "best": st.get("streak_best", 0)}},
        "perfil": {
            "nome": name if name not in {"Principal", ""} else settings.USER_NAME,
            "assistente": assistant,
            "cidade": settings.WEATHER_CITY,
            "sobre": (about.get_about() or "")[:600],
            "prefs": shared,
            "memorias": memory.facts(30),  # V6.7.3: o JARVIS da nuvem também conhece o senhor
            "agenda": _agenda(),  # V6.7.4: "o que tenho amanhã?" também fora de casa
            "lugares": _places(),  # V6.8: o agente de rotas também funciona fora de casa
        },
    }


_AGENDA_TTL = 10 * 60
_agenda_cache: dict = {"at": 0.0, "items": []}


def _agenda() -> list[dict]:
    """V6.7.4: compromissos dos próximos 7 dias (Google Agenda ou iCal) para a nuvem. Atualiza a cada 10 min.

    A nuvem nunca recebe a chave do Google: só os compromissos (título, início e local).
    """
    import time

    now = time.time()
    if now - _agenda_cache["at"] < _AGENDA_TTL:
        return _agenda_cache["items"]
    items: list[dict] = []
    try:
        from modules import calendar_hub

        if calendar_hub.connected():
            for ev in calendar_hub.upcoming_events(days=7, limit=25):
                items.append({"titulo": str(ev.get("title") or "Compromisso")[:120],
                              "inicio": str(ev.get("start") or "")[:19], "local": str(ev.get("location") or "")[:80]})
    except Exception as exc:  # noqa: BLE001 - agenda fora do ar: manda o que tinha
        log.debug("Agenda indisponível para a nuvem: %s", exc)
        return _agenda_cache["items"]
    _agenda_cache.update(at=now, items=items)
    return items


def _places() -> dict:
    try:
        from modules import agents

        return dict(list(agents.load_places().items())[:30])
    except Exception:  # noqa: BLE001
        return {}


def sync_once() -> dict:
    """Uma rodada completa (bloqueante: roda numa thread)."""
    headers = {"X-Jarvis-Nuvem": _key(), "Content-Type": "application/json"}
    r = requests.get(_base(), headers=headers, timeout=15)
    r.raise_for_status()
    data = r.json()
    applied = 0
    for op in data.get("ops", []):
        try:
            if apply_op(op):
                applied += 1
        except Exception as exc:  # noqa: BLE001 - uma operação ruim não trava as outras
            log.warning("Operação da nuvem ignorada (%s): %s", op.get("op"), exc)
    r = requests.post(_base(), headers=headers, json={"ack": data.get("last_id", 0), "snapshot": snapshot()}, timeout=15)
    r.raise_for_status()
    if applied:
        log.info("Modo nuvem: %d mudança(s) do celular aplicada(s) no PC.", applied)
    return {"applied": applied, "ops": len(data.get("ops", []))}


async def _announce_changes() -> None:
    try:
        await shopping.announce()
    except Exception:  # noqa: BLE001
        pass


async def sync_loop() -> None:
    if not enabled():
        log.info("Modo nuvem: sem JARVIS_NUVEM_CHAVE no .env, sincronização desligada.")
        return
    await asyncio.sleep(8)  # deixa o JARVIS terminar de subir
    while True:
        if profiles.is_owner_active():
            try:
                res = await asyncio.to_thread(sync_once)
                STATE.update(last_ok=datetime.now().strftime("%Y-%m-%d %H:%M"), last_error="", applied=STATE["applied"] + res["applied"])
                if res["applied"]:
                    await _announce_changes()
            except Exception as exc:  # noqa: BLE001 - sem internet, Netlify fora etc.
                if STATE["last_error"] != str(exc):
                    log.warning("Modo nuvem: não consegui sincronizar (%s).", exc)
                STATE["last_error"] = str(exc)
        await asyncio.sleep(INTERVAL_S)

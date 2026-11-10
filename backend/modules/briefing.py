"""Resumo matinal / diário do JARVIS (Bom dia com clima, tarefas, lembretes e notícias).

V4.3: build_morning_briefing() monta o briefing em segmentos (clima, agenda, e-mail, notícias,
saúde), cada um com a fala e o card que entra na tela enquanto o JARVIS fala dele.
O fluxo que fala e envia os cards fica em core/briefing_flow.py.
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from urllib.parse import urlparse

from modules import email_triage, face, google_calendar, health, news, news_radar, reminders, tasks, water
from config import settings

log = logging.getLogger("jarvis.briefing")

_WEEKDAYS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
             "sexta-feira", "sábado", "domingo"]
_MONTHS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
           "agosto", "setembro", "outubro", "novembro", "dezembro"]

# Abas da barra de progresso, na ordem em que o briefing fala
TABS = [
    {"id": "clima", "label": "Clima"},
    {"id": "agenda", "label": "Agenda"},
    {"id": "email", "label": "E-mails"},
    {"id": "noticias", "label": "Notícias"},
    {"id": "saude", "label": "Prioridades"},
]

# Um card por tema. "topic" usa as seções do Google News; "query" usa a busca por tema livre.
NEWS_THEMES = [
    {"title": "Tecnologia", "topic": "tecnologia"},
    {"title": "Novos modelos de IA", "query": "novo modelo de inteligência artificial"},
    {"title": "Política", "query": "política Brasil"},
]

# Abas do fechamento do dia ("boa noite")
EVENING_TABS = [
    {"id": "tarefas", "label": "Tarefas"},
    {"id": "agenda", "label": "Amanhã"},
    {"id": "clima", "label": "Clima"},
    {"id": "agua", "label": "Água"},
    {"id": "notas", "label": "Anotações"},
]

# Frases que disparam o briefing completo (comparadas com o texto normalizado, sem acento)
MORNING_TRIGGERS = ("bom dia", "resumo do dia", "meu dia", "como esta meu dia", "briefing matinal")
# O fechamento vence quando as duas listas batem ("boa noite, resumo do dia")
EVENING_TRIGGERS = ("boa noite", "resumo da noite", "encerrar o dia", "fechar o dia", "fechamento do dia",
                    "resumo de fim de dia", "fim do dia", "balanco do dia")

# Campos da telemetria tratados como leitura sensível (nunca falados em voz alta)
_SENSITIVE_FIELDS = ("bpm", "hrv", "spo2", "stress", "sleep_hours", "sleep_efficiency",
                     "sleep_performance", "skin_temp", "respiration", "recovery", "steps")


def is_evening_request(norm: str) -> bool:
    return any(q in norm for q in EVENING_TRIGGERS)


def is_morning_request(norm: str) -> bool:
    return not is_evening_request(norm) and any(q in norm for q in MORNING_TRIGGERS)


def request_mode(norm: str, hour: int | None = None) -> str | None:
    """Qual tela o pedido quer: morning, evening, topic:<assunto> ou None.

    "resumo" e "briefing" sozinhos dependem da hora (a partir das 18h, o fechamento).
    As telas por assunto ("notícias", "agenda"...) ficam em modules/briefing_topics.py.
    """
    from modules import briefing_topics

    topic = briefing_topics.match(norm)
    if topic:
        return f"topic:{topic}"
    if is_evening_request(norm):
        return "evening"
    if is_morning_request(norm):
        return "morning"
    if norm in ("resumo", "briefing"):
        hour = datetime.now().hour if hour is None else hour
        return "evening" if hour >= 18 else "morning"
    return None


def _date_line(now: datetime) -> str:
    return f"{_WEEKDAYS[now.weekday()]}, {now.day} de {_MONTHS[now.month - 1]}"


def _fmt(value, digits: int = 1) -> str:
    """Número no formato brasileiro (26,7)."""
    return f"{value:.{digits}f}".replace(".", ",")


# ------------------------------------------------------------------ segmentos
def _weather_segment(result: dict | None) -> dict | None:
    if not result:
        return None
    from modules.tools import _WMO

    data, place = result["data"], result["place"]
    cur, daily = data.get("current", {}), data.get("daily", {})
    temp = cur.get("temperature_2m")
    if temp is None:
        return None
    desc = _WMO.get(cur.get("weather_code"), "tempo variável")
    t_min = (daily.get("temperature_2m_min") or [None])[0]
    t_max = (daily.get("temperature_2m_max") or [None])[0]
    rain = (daily.get("precipitation_probability_max") or [None])[0]
    card = {
        "kind": "weather",
        "label": "PANORAMA · CLIMA",
        "title": place,
        "temperature": temp,
        "description": desc,
        "minimum": t_min,
        "maximum": t_max,
        "apparent": cur.get("apparent_temperature"),
        "rain_probability": rain,
        "wind": cur.get("wind_speed_10m"),
        "footer": f"Open-Meteo · {datetime.now().strftime('%H:%M')}",
    }
    speech = f"Em {place}, {round(temp)} graus e {desc}"
    if t_min is not None and t_max is not None:
        speech += f", com mínima de {round(t_min)} e máxima de {round(t_max)}"
    speech += "."
    if rain is not None and rain >= 50:
        speech += f" A chance de chuva é de {round(rain)} por cento."
    return {"tab": "clima", "progress": "Lendo o clima de hoje...", "speech": speech, "card": card}


def _agenda_segment(day: datetime, calendar_events: list[dict], when: str = "hoje") -> dict:
    today = day.strftime("%Y-%m-%d")
    items = []
    for ev in calendar_events:
        start = ev.get("start") or ""
        if not start.startswith(today):
            continue
        time_str = start[11:16] if "T" in start else "Dia todo"
        items.append({"time": time_str, "title": ev.get("title", "Sem título"), "location": ev.get("location", "")})
    for r in reminders.get_reminders(only_pending=True):
        data_hora = r.get("data_hora", "")
        if data_hora.startswith(today):
            items.append({"time": data_hora[11:16], "title": r.get("texto", "Lembrete"), "location": "Lembrete"})
    items.sort(key=lambda i: i["time"])

    source = "Google Agenda + lembretes" if google_calendar.connected() else "Lembretes do JARVIS"
    card = {"kind": "agenda", "label": f"AGENDA · {when.upper()}", "items": items[:5],
            "more": max(0, len(items) - 5), "footer": source}
    if not items:
        card.update(title="Agenda livre", empty_text="Nenhum compromisso registrado",
                    empty_sub="Seu horário permanece disponível")
        speech = f"Sua agenda está livre {when}."
    else:
        card["title"] = f"{len(items)} compromisso{'s' if len(items) != 1 else ''}"
        first = items[0]
        speech = (f"Você tem {len(items)} {'compromisso' if len(items) == 1 else 'compromissos'} {when}. "
                  f"O primeiro é {first['title']}, às {first['time']}.")
    return {"tab": "agenda", "progress": f"Conferindo a agenda de {when}...", "speech": speech, "card": card}


def _email_segment(tri: dict) -> dict:
    card = {"kind": "email", "label": "COMUNICAÇÕES · E-MAIL", "connected": tri.get("connected", False),
            "received": tri.get("received", 0), "to_act": tri.get("to_act", 0),
            "items": tri.get("items", [])[:3], "more": max(0, len(tri.get("items", [])) - 3),
            "footer": "Triagem do briefing · somente itens verificados"}
    if not tri.get("connected"):
        card.update(title="E-mail não conectado", footer="Configure EMAIL_IMAP_* no .env")
        return {"tab": "email", "progress": "Verificando e-mails importantes...", "speech": "", "card": card}
    if tri.get("error"):
        card.update(title="Caixa indisponível", footer=tri["error"])
        return {"tab": "email", "progress": "Verificando e-mails importantes...",
                "speech": "Não consegui acessar sua caixa de entrada agora.", "card": card}
    if card["to_act"]:
        card["title"] = "Pedem sua atenção"
        senders = ", ".join(dict.fromkeys(i["sender"] for i in card["items"][:2]))
        speech = (f"Chegaram {card['received']} e-mails desde ontem, e {card['to_act']} "
                  f"{'pede' if card['to_act'] == 1 else 'pedem'} uma ação sua, a começar por {senders}.")
    else:
        card["title"] = "Caixa em dia"
        speech = f"Chegaram {card['received']} e-mails desde ontem; nenhum exige ação."
    return {"tab": "email", "progress": "Verificando e-mails importantes...", "speech": speech, "card": card}


def _news_segment(theme: dict, items: list[dict]) -> dict | None:
    if not items:
        return None
    top = items[0]
    domain = urlparse(top.get("source_url") or "").netloc
    card = {
        "kind": "news",
        "label": "RADAR · NOTÍCIAS",
        "title": theme["title"],
        "headline": top["title"],
        "source": top.get("source") or domain or "Google News",
        "domain": domain,
        "link": top.get("link", ""),
        "published": top.get("published", ""),
        "footer": "Google News",
    }
    speech = f"Em {theme['title'].lower()}: {top['title']}."
    if card["source"]:
        speech += f" A informação é do {card['source']}."
    return {"tab": "noticias", "progress": "Atualizando o radar de notícias...", "speech": speech, "card": card}


def _health_segment(tele: dict) -> tuple[dict, dict | None]:
    """Saúde fica sob demanda: o card só diz quantas leituras existem; nenhum valor é falado."""
    readings = sum(1 for f in _SENSITIVE_FIELDS if tele.get(f) is not None) + len(tele.get("bpm_history") or [])
    card = {
        "kind": "health",
        "label": "SAÚDE · LEITURA DE DADOS",
        "title": "Observações disponíveis",
        "chip": "sob demanda",
        "text": "Por privacidade, não leio detalhes de saúde automaticamente. Peça \"meus dados de saúde\" quando quiser.",
        "footer": f"{readings} leituras sensíveis preservadas",
    }
    segment = {"tab": "saude", "progress": "Organizando prioridades...",
               "speech": "Seus dados de saúde estão disponíveis sob demanda.", "card": card}

    readiness = None
    if tele.get("recovery") is not None:
        water_l = 0.0
        try:
            water_l = water.get_status().get("total_ml", 0) / 1000
        except Exception:  # noqa: BLE001
            pass
        readiness = {
            "recovery": tele.get("recovery"),
            "metrics": [
                {"label": "Movimento", "value": f"{tele.get('steps') or 0} passos"},
                {"label": "Esforço", "value": f"{tele.get('stress') or 0}"},
                {"label": "Sono", "value": f"{_fmt(tele.get('sleep_hours') or 0)} h"},
                {"label": "Hidratação", "value": f"{_fmt(water_l)} L"},
            ],
            "footer": f"{tele.get('device_name', 'Relógio')} · {tele.get('last_sync', '')}",
        }
    return segment, readiness


def _deviations(now: datetime, weather: dict | None) -> list[str]:
    """Pontos que justificam interromper a manhã (briefing por exceção)."""
    out = []
    overdue = 0
    for r in reminders.get_reminders(only_pending=True):
        try:
            if datetime.strptime(r.get("data_hora", ""), "%Y-%m-%d %H:%M") < now:
                overdue += 1
        except ValueError:
            continue
    if overdue:
        out.append(f"{overdue} {'lembrete atrasado' if overdue == 1 else 'lembretes atrasados'}")
    code = (weather or {}).get("data", {}).get("current", {}).get("weather_code")
    if code is not None and code >= 95:
        out.append("alerta de trovoadas")
    return out


def _closing(card_weather: dict | None, agenda_items: int, to_act: int, pending_tasks: int) -> str:
    if to_act >= 3:
        return "Hoje, resolva primeiro os e-mails que pedem ação e depois mantenha o foco no essencial."
    if card_weather and (card_weather.get("rain_probability") or 0) >= 60:
        return "Hoje, leve um guarda-chuva e mantenha o foco no essencial."
    if agenda_items >= 4:
        return "Hoje o dia está cheio; proteja os intervalos entre os compromissos."
    if pending_tasks >= 5:
        return f"Hoje, escolha duas das {pending_tasks} tarefas pendentes e comece por elas."
    return "Hoje, mantenha o foco no essencial."


async def build_morning_briefing() -> dict:
    """V4.3: briefing em segmentos para o "bom dia".

    Retorna {greeting, opening, opening_sub, segments: [{tab, progress, speech, card}], readiness,
    closing, tabs, speech}. As fontes são buscadas em paralelo; a que falhar fica de fora.
    """
    now = datetime.now()
    user_name = face.get_name()
    nome_str = f", {user_name}" if user_name else ""

    async def safe(fn, *args, default=None):
        try:
            return await asyncio.to_thread(fn, *args)
        except Exception as exc:  # noqa: BLE001
            log.warning("Briefing: falha em %s: %s", getattr(fn, "__name__", fn), exc)
            return default

    from modules.tools import _fetch_weather

    def calendar_events() -> list[dict]:
        return google_calendar.upcoming_events(days=1, limit=10) if google_calendar.connected() else []

    def news_for(theme: dict) -> list[dict]:
        if "topic" in theme:
            return news_radar.fetch_news_by_category(theme["topic"], limit=3)
        return news_radar.fetch_news_by_query(theme["query"], limit=3)

    weather_res, events, tri, *news_lists = await asyncio.gather(
        safe(_fetch_weather, settings.WEATHER_CITY),
        safe(calendar_events, default=[]),
        safe(email_triage.triage, default={"connected": False}),
        *(safe(news_for, t, default=[]) for t in NEWS_THEMES),
    )

    segments = []
    weather_seg = _weather_segment(weather_res)
    if weather_seg:
        segments.append(weather_seg)
    agenda_seg = _agenda_segment(now, events or [])
    segments.append(agenda_seg)
    email_seg = _email_segment(tri or {"connected": False})
    segments.append(email_seg)
    for theme, items in zip(NEWS_THEMES, news_lists):
        seg = _news_segment(theme, items or [])
        if seg:
            segments.append(seg)
    health_seg, readiness = _health_segment(health.load_telemetry())
    segments.append(health_seg)

    deviations = _deviations(now, weather_res)
    greeting = f"Bom dia{nome_str}. Hoje é {_date_line(now)}."
    if deviations:
        opening = f"Atenção a {len(deviations)} {'ponto' if len(deviations) == 1 else 'pontos'}"
        opening_sub = "; ".join(deviations)
        opening_speech = f"Antes do briefing, um aviso: {opening_sub}."
    else:
        opening = "Sem desvios relevantes"
        opening_sub = "dados consolidados desde ontem"
        opening_speech = "Revisei o que já está consolidado e nada exige interromper a sua manhã."

    pending = len(tasks.get_tasks(include_completed=False))
    closing = _closing(weather_seg["card"] if weather_seg else None, len(agenda_seg["card"]["items"]),
                       email_seg["card"]["to_act"], pending)

    speech = " ".join(p for p in [greeting, opening_speech, *(s["speech"] for s in segments), closing] if p)
    used_tabs = {s["tab"] for s in segments}
    return {
        "mode": "morning",
        "title": "BRIEFING",
        "greeting": greeting,
        "opening": opening,
        "opening_sub": opening_sub,
        "opening_speech": opening_speech,
        "segments": segments,
        "readiness": readiness,
        "closing": closing,
        "tabs": [t for t in TABS if t["id"] in used_tabs],
        "speech": speech,
    }


async def generate_daily_briefing() -> str:
    """Texto corrido do briefing (rota /api/briefing e telas sem a sequência de cards)."""
    try:
        return (await build_morning_briefing())["speech"]
    except Exception as exc:  # noqa: BLE001
        log.warning("Briefing em segmentos falhou, usando o resumo simples: %s", exc)
        return await _simple_daily_briefing()


async def _simple_daily_briefing() -> str:
    """Resumo da 4.2 (reserva caso o briefing em segmentos falhe)."""
    now = datetime.now()
    user_name = face.get_name()
    nome_str = f", {user_name}" if user_name else ""

    # 1. Saudação
    greeting = f"Bom dia{nome_str}! Hoje é {_date_line(now)}."

    # 2. Clima
    weather_part = ""
    try:
        from modules.tools import _fetch_weather
        w_data = await asyncio.to_thread(_fetch_weather, settings.WEATHER_CITY)
        if w_data and "data" in w_data:
            cur = w_data["data"].get("current", {})
            temp = cur.get("temperature_2m")
            if temp is not None:
                weather_part = f"Em {w_data['place']}, a temperatura atual é de {round(temp)} graus."
    except Exception as exc:  # noqa: BLE001
        log.warning("Falha ao obter clima para o resumo: %s", exc)

    # 3. Tarefas pendentes
    pendentes = tasks.get_tasks(include_completed=False)
    tasks_part = ""
    if pendentes:
        t_count = len(pendentes)
        tasks_part = f"Você tem {t_count} {'tarefa pendente' if t_count == 1 else 'tarefas pendentes'} na sua lista."
    else:
        tasks_part = "Sua lista de tarefas está em dia."

    # 4. Lembretes de hoje
    rems = reminders.get_reminders(only_pending=True)
    today_rems = []
    today_str = now.strftime("%Y-%m-%d")
    for r in rems:
        if r.get("data_hora", "").startswith(today_str):
            today_rems.append(r)

    rems_part = ""
    if today_rems:
        rems_part = f"Você tem {len(today_rems)} lembrete agendado para hoje."

    # 5. Destaque de notícias
    news_part = ""
    try:
        top_news = await asyncio.to_thread(news.fetch_top_news)
        if top_news:
            first_title = top_news[0]["title"]
            news_part = f"Nos destaques de hoje: {first_title}."
    except Exception as exc:  # noqa: BLE001
        log.warning("Falha ao obter notícias para o resumo: %s", exc)

    # Monta a fala final
    partes = [greeting, weather_part, tasks_part, rems_part, news_part, "Como posso te ajudar agora?"]
    return " ".join([p for p in partes if p]).strip()


def _tasks_segment(pending: list[dict]) -> dict:
    items = [{"text": t.get("texto", "")} for t in pending if t.get("texto")]
    card = {"kind": "tasks", "label": "TAREFAS · PENDENTES", "items": items[:4], "more": max(0, len(items) - 4),
            "total": len(items), "footer": "Lista de tarefas do JARVIS"}
    if not items:
        card.update(title="Tudo concluído", empty_text="Nenhuma tarefa pendente",
                    empty_sub="A lista fica limpa para amanhã")
        speech = "Todas as tarefas foram concluídas."
    else:
        card["title"] = f"{len(items)} pendente{'s' if len(items) != 1 else ''}"
        names = ", ".join(i["text"] for i in items[:2])
        more = f" e mais {len(items) - 2}" if len(items) > 2 else ""
        speech = (f"Ficaram {len(items)} {'tarefa pendente' if len(items) == 1 else 'tarefas pendentes'}: "
                  f"{names}{more}.")
    return {"tab": "tarefas", "progress": "Conferindo as tarefas do dia...", "speech": speech, "card": card}


def _tomorrow_weather_segment(result: dict | None) -> dict | None:
    if not result:
        return None
    from modules.tools import _WMO

    daily = result["data"].get("daily", {})

    def at(key):
        values = daily.get(key) or []
        return values[1] if len(values) > 1 else None

    t_min, t_max = at("temperature_2m_min"), at("temperature_2m_max")
    if t_min is None or t_max is None:
        return None
    desc = _WMO.get(at("weather_code"), "tempo variável")
    rain = at("precipitation_probability_max")
    card = {
        "kind": "weather",
        "label": "PANORAMA · CLIMA AMANHÃ",
        "title": result["place"],
        "temperature": t_max,
        "description": desc,
        "minimum": t_min,
        "maximum": t_max,
        "apparent": None,
        "rain_probability": rain,
        "wind": None,
        "footer": "Open-Meteo · previsão para amanhã",
    }
    speech = f"Amanhã em {result['place']}: {desc}, entre {round(t_min)} e {round(t_max)} graus."
    if rain is not None and rain >= 50:
        speech += f" Chance de chuva de {round(rain)} por cento."
    return {"tab": "clima", "progress": "Lendo a previsão de amanhã...", "speech": speech, "card": card}


def _water_segment() -> dict | None:
    try:
        st = water.get_status()
    except Exception:  # noqa: BLE001
        return None
    liters = st["total_ml"] / 1000
    card = {"kind": "water", "label": "HIDRATAÇÃO · HOJE", "title": f"{_fmt(liters)} L de {_fmt(st['goal_ml'] / 1000)} L",
            "percentage": st["percentage"], "goal_reached": st["goal_reached"], "footer": "Registro de água do JARVIS"}
    if st["goal_reached"]:
        speech = "A meta de água do dia foi batida."
    else:
        speech = f"Você bebeu {_fmt(liters)} litros de água hoje, {st['percentage']} por cento da meta."
    return {"tab": "agua", "progress": "Somando a hidratação...", "speech": speech, "card": card}


def _today_notes(now: datetime) -> list[dict]:
    from modules import tools  # noqa: PLC0415 - import tardio: evita ciclo com tools

    notes_path = tools._NOTES_PATH  # V4.5: notas do perfil ativo
    if not notes_path.exists():
        return []
    try:
        data = json.loads(notes_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        log.warning("Falha ao ler anotações para o resumo da noite: %s", exc)
        return []
    prefix = now.strftime("%d/%m")
    return [n for n in data if isinstance(n, dict) and n.get("quando", "").startswith(prefix)] if isinstance(data, list) else []


def _notes_segment(notes: list[dict]) -> dict | None:
    if not notes:
        return None
    # "quando" é gravado como "04/11 às 21:30" (tools.py)
    items = [{"time": n.get("quando", "").split("às")[-1].strip() or "—", "title": n.get("texto", ""), "location": ""}
             for n in notes if n.get("texto")]
    card = {"kind": "agenda", "label": "ANOTAÇÕES · HOJE", "title": f"{len(items)} anotaç{'ões' if len(items) != 1 else 'ão'}",
            "items": items[:4], "more": max(0, len(items) - 4), "footer": "Anotações por voz"}
    speech = (f"Você registrou {len(items)} {'anotação' if len(items) == 1 else 'anotações'} hoje. "
              f"A última: {items[-1]['title']}.")
    return {"tab": "notas", "progress": "Revisando as anotações...", "speech": speech, "card": card}


def _evening_closing(pending: int, tomorrow_items: list[dict], rain) -> str:
    if tomorrow_items and tomorrow_items[0]["time"] < "09:00":
        return f"Amanhã começa cedo, às {tomorrow_items[0]['time']}. Vale dormir um pouco antes hoje."
    if rain is not None and rain >= 60:
        return "Deixe o guarda-chuva separado para amanhã e descanse bem."
    if pending >= 3:
        return "Escolha agora a primeira tarefa de amanhã e deixe o resto para depois. Bom descanso."
    return "Desligue as telas um pouco antes de dormir. Bom descanso."


async def build_evening_briefing() -> dict:
    """V4.3: fechamento do dia em segmentos para o "boa noite" (mesmo formato do briefing da manhã)."""
    now = datetime.now()
    tomorrow = now + timedelta(days=1)
    user_name = face.get_name()
    nome_str = f", {user_name}" if user_name else ""

    from modules.tools import _fetch_weather

    async def safe(fn, *args, default=None):
        try:
            return await asyncio.to_thread(fn, *args)
        except Exception as exc:  # noqa: BLE001
            log.warning("Fechamento: falha em %s: %s", getattr(fn, "__name__", fn), exc)
            return default

    def calendar_events() -> list[dict]:
        return google_calendar.upcoming_events(days=2, limit=15) if google_calendar.connected() else []

    weather_res, events = await asyncio.gather(
        safe(_fetch_weather, settings.WEATHER_CITY),
        safe(calendar_events, default=[]),
    )
    pending = tasks.get_tasks(include_completed=False)

    segments = [_tasks_segment(pending)]
    agenda_seg = _agenda_segment(tomorrow, events or [], when="amanhã")
    segments.append(agenda_seg)
    weather_seg = _tomorrow_weather_segment(weather_res)
    if weather_seg:
        segments.append(weather_seg)
    for seg in (_water_segment(), _notes_segment(_today_notes(now))):
        if seg:
            segments.append(seg)

    greeting = f"Boa noite{nome_str}. Aqui está o fechamento de {_date_line(now)}."
    tomorrow_items = agenda_seg["card"]["items"]
    if not pending and not tomorrow_items:
        opening, opening_sub = "Dia encerrado sem pendências", "nada ficou para amanhã"
        opening_speech = "O dia está limpo: nenhuma tarefa pendente e nada marcado para amanhã."
    else:
        opening = "Fechamento do dia"
        opening_sub = f"{len(pending)} pendente{'s' if len(pending) != 1 else ''} · {len(tomorrow_items)} para amanhã"
        opening_speech = ""
    rain = weather_seg["card"]["rain_probability"] if weather_seg else None
    closing = _evening_closing(len(pending), tomorrow_items, rain)

    speech = " ".join(p for p in [greeting, opening_speech, *(s["speech"] for s in segments), closing] if p)
    used_tabs = {s["tab"] for s in segments}
    return {
        "mode": "evening",
        "title": "FECHAMENTO DO DIA",
        "greeting": greeting,
        "opening": opening,
        "opening_sub": opening_sub,
        "opening_speech": opening_speech,
        "segments": segments,
        "readiness": None,
        "closing": closing,
        "tabs": [t for t in EVENING_TABS if t["id"] in used_tabs],
        "speech": speech,
    }


async def generate_evening_briefing() -> str:
    """Texto corrido do fechamento do dia (telas sem a sequência de cards)."""
    try:
        return (await build_evening_briefing())["speech"]
    except Exception as exc:  # noqa: BLE001
        log.warning("Fechamento em segmentos falhou, usando o resumo simples: %s", exc)
        return await _simple_evening_briefing()


async def _simple_evening_briefing() -> str:
    """Gera um resumo de encerramento do dia (Boa noite com tarefas pendentes, lembretes de amanhã e anotações)."""
    now = datetime.now()
    user_name = face.get_name()
    nome_str = f", {user_name}" if user_name else ""

    # 1. Tarefas pendentes
    pendentes = tasks.get_tasks(include_completed=False)
    tasks_text = ""
    if pendentes:
        t_count = len(pendentes)
        titulos = [t.get("texto", "") for t in pendentes[:3] if t.get("texto")]
        lista_str = ", ".join(titulos)
        mais = f" e mais {t_count - 3}" if t_count > 3 else ""
        tasks_text = f"Ficaram {t_count} {'tarefa pendente' if t_count == 1 else 'tarefas pendentes'}: {lista_str}{mais}."
    
    # 2. Lembretes de amanhã
    tomorrow = now + timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")
    rems = reminders.get_reminders(only_pending=True)
    tomorrow_rems = [r for r in rems if r.get("data_hora", "").startswith(tomorrow_str)]
    rems_text = ""
    if tomorrow_rems:
        r_count = len(tomorrow_rems)
        titulos_r = [r.get("texto", "") for r in tomorrow_rems[:3] if r.get("texto")]
        rems_text = f"Para amanhã você tem {r_count} {'lembrete agendado' if r_count == 1 else 'lembretes agendados'}: {', '.join(titulos_r)}."

    # 3. Anotações de hoje
    from modules import tools  # noqa: PLC0415 - import tardio: evita ciclo com tools

    notes_path = tools._NOTES_PATH  # V4.5: notas do perfil ativo
    today_prefix = now.strftime("%d/%m")
    today_notes = []
    if notes_path.exists():
        try:
            notes_data = json.loads(notes_path.read_text(encoding="utf-8"))
            if isinstance(notes_data, list):
                today_notes = [n for n in notes_data if n.get("quando", "").startswith(today_prefix)]
        except Exception as exc:  # noqa: BLE001
            log.warning("Falha ao ler anotações para o resumo da noite: %s", exc)

    notes_text = ""
    if today_notes:
        n_count = len(today_notes)
        textos_n = [n.get("texto", "") for n in today_notes[:3] if n.get("texto")]
        notes_text = f"Você registrou {n_count} {'anotação hoje' if n_count == 1 else 'anotações hoje'}: {'; '.join(textos_n)}."

    # 4. Caso o dia esteja totalmente limpo
    if not pendentes and not tomorrow_rems and not today_notes:
        return f"Boa noite{nome_str}. O dia está limpo: nenhuma tarefa pendente e nenhum lembrete para amanhã. Bom descanso."

    # 5. Montagem da fala com itens presentes
    partes = [
        f"Boa noite{nome_str}! Aqui está o fechamento do seu dia.",
        tasks_text if tasks_text else "Todas as tarefas foram concluídas.",
        rems_text if rems_text else "Nenhum lembrete para amanhã.",
        notes_text,
        "Tenha uma ótima noite e bom descanso!"
    ]
    return " ".join([p for p in partes if p]).strip()

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

from modules import calendar_hub, email_triage, face, google_calendar, health, news, news_radar, reminders, tasks, water  # noqa: F401
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
    {"id": "proximos", "label": "Próximos dias"},  # V5.6: agenda dos próximos 3 dias e contagens
    {"id": "tarefas", "label": "Tarefas"},   # V5.3: só aparece com tarefas pendentes
    {"id": "jogo", "label": "Jogo"},         # V5.3: só em dia de jogo do time do Modo Torcedor
    {"id": "email", "label": "E-mails"},
    {"id": "noticias", "label": "Notícias"},
    {"id": "saude", "label": "Prioridades"},
]

# Um card por tema. "topic" usa as seções do Google News; "query" usa a busca por tema livre.
# V6.2: temas do "bom dia" escolhidos pelo usuário (Configurações > Geral > Notícias do briefing).
# Cada tema: {"title", "query" (busca no Google Notícias) ou "topic" (seção), "count" (1 a 5 manchetes)}.
# Sem nada salvo, valem os padrões abaixo: os três de antes e Marvel com as 3 principais.
MAX_NEWS_THEMES = 6
DEFAULT_NEWS_THEMES = [
    {"title": "Tecnologia", "topic": "tecnologia", "count": 1},
    {"title": "Novos modelos de IA", "query": "novo modelo de inteligência artificial", "count": 1},
    {"title": "Política", "query": "política Brasil", "count": 1},
    {"title": "Marvel", "query": "Marvel", "count": 3},
]


def news_themes() -> list[dict]:
    """Temas de notícias do briefing (os do usuário ou os padrões)."""
    try:
        from modules import prefs

        user = prefs._load().get("briefing_news_themes")
    except Exception:  # noqa: BLE001
        user = None
    themes = user if isinstance(user, list) and user else DEFAULT_NEWS_THEMES
    out = []
    for t in themes[:MAX_NEWS_THEMES]:
        if not isinstance(t, dict) or not str(t.get("title", "")).strip():
            continue
        if not (t.get("query") or t.get("topic")):
            continue
        out.append({**t, "count": max(1, min(5, int(t.get("count") or 1)))})
    return out


def validate_news_themes(value) -> str | None:
    """Valida o que vem das Configurações. Devolve a mensagem de erro ou None."""
    if not isinstance(value, list) or len(value) > MAX_NEWS_THEMES:
        return f"Até {MAX_NEWS_THEMES} temas."
    for t in value:
        if not isinstance(t, dict):
            return "Tema inválido."
        title = str(t.get("title", "")).strip()
        query = str(t.get("query", "") or t.get("topic", "")).strip()
        if not title or len(title) > 40 or not query or len(query) > 80:
            return "Cada tema precisa de um nome (até 40 letras) e uma busca (até 80)."
        if isinstance(t.get("count"), bool) or not isinstance(t.get("count", 1), int) or not 1 <= int(t.get("count", 1)) <= 5:
            return "A quantidade de manchetes vai de 1 a 5."
    return None


# Temas fixos da tela "notícias" (briefing_topics) — o "bom dia" usa news_themes()
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


# V6.5: resumo da tarde
AFTERNOON_TRIGGERS = ("boa tarde", "resumo da tarde", "briefing da tarde", "como esta minha tarde", "minha tarde")


def is_afternoon_request(norm: str) -> bool:
    return not is_evening_request(norm) and any(q in norm for q in AFTERNOON_TRIGGERS)


def is_morning_request(norm: str) -> bool:
    return (not is_evening_request(norm) and not is_afternoon_request(norm)
            and any(q in norm for q in MORNING_TRIGGERS))


def request_mode(norm: str, hour: int | None = None) -> str | None:
    """Qual tela o pedido quer: morning, afternoon, evening, topic:<assunto> ou None.

    "resumo" e "briefing" sozinhos dependem da hora (12h a 18h, a tarde; a partir das 18h, o fechamento).
    As telas por assunto ("notícias", "agenda"...) ficam em modules/briefing_topics.py.
    """
    from modules import briefing_topics

    topic = briefing_topics.match(norm)
    if topic:
        return f"topic:{topic}"
    if is_evening_request(norm):
        return "evening"
    if is_afternoon_request(norm):
        return "afternoon"
    if is_morning_request(norm):
        return "morning"
    if norm in ("resumo", "briefing"):
        hour = datetime.now().hour if hour is None else hour
        return "evening" if hour >= 18 else "afternoon" if hour >= 12 else "morning"
    return None


def _date_line(now: datetime) -> str:
    return f"{_WEEKDAYS[now.weekday()]}, {now.day} de {_MONTHS[now.month - 1]}"


def greeting_word(now: datetime) -> str:
    """V5.3: "bom dia" falado às 15h vira "Boa tarde" (o briefing acompanha a hora de verdade)."""
    if now.hour < 12:
        return "Bom dia"
    return "Boa tarde" if now.hour < 18 else "Boa noite"


def _day_note(now: datetime) -> str:
    """V5.3: um toque sobre o dia da semana, como uma pessoa faria."""
    return {
        0: "Começo de semana.",
        4: "Último dia útil da semana.",
        5: "É sábado.",
        6: "É domingo.",
    }.get(now.weekday(), "")


def _minutes_until(now: datetime, hm: str) -> int | None:
    try:
        h, m = (int(x) for x in hm.split(":"))
    except ValueError:
        return None
    return int((now.replace(hour=h, minute=m, second=0, microsecond=0) - now).total_seconds() // 60)


def _in_words(minutes: int) -> str:
    if minutes < 60:
        return f"daqui a {minutes} {'minuto' if minutes == 1 else 'minutos'}"
    hours, rest = divmod(minutes, 60)
    base = f"daqui a {hours} {'hora' if hours == 1 else 'horas'}"
    return base + (f" e {rest} minutos" if rest >= 10 else "")


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
    tip = weather_tip(t_min, t_max, rain, cur.get("weather_code"))
    card = {
        "kind": "weather",
        "label": "PANORAMA · CLIMA",
        "icon": weather_icon(cur.get("weather_code")),
        "tip": tip,
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
    if tip:
        speech += f" {tip}"
    return {"tab": "clima", "progress": "Lendo o clima de hoje...", "speech": speech, "card": card}


def weather_icon(code) -> str:
    """V5.3: ícone do card conforme o tempo (antes era sempre ☀)."""
    if code is None:
        return "☀"
    if code >= 95:
        return "⚡"
    if code >= 51:
        return "☂"
    if code >= 45:
        return "≋"
    if code >= 2:
        return "☁"
    return "☀"


def weather_tip(t_min, t_max, rain, code=None) -> str:
    """V5.3: um conselho prático, só quando faz diferença (trovoada, chuva, calor, frio)."""
    if code is not None and code >= 95:
        return "Há risco de trovoadas: evite sair no pior horário."
    if rain is not None and rain >= 50:
        return "Vale levar um guarda-chuva."
    if t_max is not None and t_max >= 31:
        return "Vai fazer calor: capriche na água."
    if t_min is not None and t_min <= 14:
        return "Começa frio: leve um casaco."
    return ""


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

    source = f"{calendar_hub.source_name()} + lembretes" if calendar_hub.connected() else "Lembretes do JARVIS"
    card = {"kind": "agenda", "label": f"AGENDA · {when.upper()}", "items": items[:5],
            "more": max(0, len(items) - 5), "footer": source}
    if not items:
        card.update(title="Agenda livre", empty_text="Nenhum compromisso registrado",
                    empty_sub="Seu horário permanece disponível")
        speech = f"Sua agenda está livre {when}."
    else:
        card["title"] = f"{len(items)} compromisso{'s' if len(items) != 1 else ''}"
        speech = f"Você tem {len(items)} {'compromisso' if len(items) == 1 else 'compromissos'} {when}. "
        timed = [i for i in items if ":" in i["time"]]
        # V5.3: hoje, fala do PRÓXIMO (não de um que já passou) e de quanto falta, se for logo
        now = datetime.now()
        ahead = timed
        if when == "hoje":
            ahead = [i for i in timed if (_minutes_until(now, i["time"]) or 0) >= 0]
        if ahead:
            nxt = ahead[0]
            speech += f"{'O primeiro' if nxt is timed[0] else 'O próximo'} é {nxt['title']}, às {nxt['time']}"
            mins = _minutes_until(now, nxt["time"]) if when == "hoje" else None
            if mins is not None and 0 <= mins <= 120:
                speech += f", {_in_words(mins)}"
                card["next_in"] = mins
            speech += "."
            if len(ahead) > 1:
                speech += f" Depois, {ahead[1]['title']} às {ahead[1]['time']}."
        elif timed:
            speech += "Os horários de hoje já passaram."
        else:
            speech += f"O primeiro é {items[0]['title']}."
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


def _dedupe_titles(items: list[dict]) -> list[dict]:
    """Tira manchetes quase iguais (o mesmo fato em dois sites)."""
    import re
    import unicodedata

    def key(t: str) -> set[str]:
        n = unicodedata.normalize("NFD", t.lower())
        n = "".join(c for c in n if unicodedata.category(c) != "Mn")
        return {w for w in re.findall(r"[a-z0-9]{4,}", n)}

    out, seen = [], []
    for it in items:
        k = key(it.get("title", ""))
        if any(len(k & s) >= max(3, int(0.6 * min(len(k), len(s)))) for s in seen):
            continue
        seen.append(k)
        out.append(it)
    return out


def _news_segment(theme: dict, items: list[dict]) -> dict | None:
    if not items:
        return None
    count = max(1, min(5, int(theme.get("count") or 1)))
    if count > 1:
        return _news_multi_segment(theme, _dedupe_titles(items)[:count])
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


def _news_multi_segment(theme: dict, items: list[dict]) -> dict | None:
    """V6.2: tema com várias manchetes (ex.: "as 3 principais sobre Marvel"): um card com a lista."""
    if not items:
        return None
    top = items[0]
    domain = urlparse(top.get("source_url") or "").netloc
    card = {
        "kind": "news",
        "label": f"RADAR · {theme['title'].upper()}",
        "title": theme["title"],
        "headline": top["title"],
        "source": top.get("source") or domain or "Google News",
        "domain": domain,
        "link": top.get("link", ""),
        "published": top.get("published", ""),
        "items": [{"title": i["title"], "source": i.get("source", ""), "link": i.get("link", "")} for i in items],
        "footer": f"Google Notícias · {len(items)} principais",
    }
    n = len(items)
    words = {2: "as duas principais", 3: "as três principais", 4: "as quatro principais", 5: "as cinco principais"}
    titles = [i["title"].rstrip(".") for i in items]
    if n == 1:
        speech = f"Em {theme['title']}: {titles[0]}."
    else:
        speech = f"Em {theme['title']}, {words.get(n, 'as principais')}. Primeira: {titles[0]}."
        middle = ["Segunda", "Terceira", "Quarta", "Quinta"]
        for idx, t in enumerate(titles[1:], start=0):
            speech += f" {middle[idx]}: {t}."
    return {"tab": "noticias", "progress": f"Buscando as notícias de {theme['title']}...", "speech": speech, "card": card}


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


def _days_word(days: int) -> str:
    return "amanhã" if days == 1 else "depois de amanhã" if days == 2 else f"em {days} dias"


def _upcoming_segment(now: datetime, calendar_events: list[dict], ahead: int = 3) -> dict | None:
    """V5.6: compromissos dos próximos 3 dias (agenda + lembretes), com quanto falta, e as contagens."""
    from modules import countdowns

    items = []
    for ev in calendar_events:
        start = calendar_hub.event_start(ev)
        if not start:
            continue
        days = (start.date() - now.date()).days
        if 1 <= days <= ahead:
            hm = start.strftime("%H:%M") if "T" in (ev.get("start") or "") else ""
            items.append({"days": days, "hm": hm, "title": ev.get("title", "Compromisso"), "when": start})
    for r in reminders.get_reminders(only_pending=True):
        try:
            start = datetime.strptime(r.get("data_hora", ""), "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        days = (start.date() - now.date()).days
        if 1 <= days <= ahead:
            items.append({"days": days, "hm": start.strftime("%H:%M"), "title": r.get("texto", "Lembrete"), "when": start})
    items.sort(key=lambda i: i["when"])
    counting = countdowns.briefing_lines(now)
    if not items and not counting:
        return None

    rows = [{"time": "AMANHÃ" if i["days"] == 1 else f"EM {i['days']}D",
             "title": i["title"],
             "location": f"{_WEEKDAYS[i['when'].weekday()]}" + (f", {i['hm']}" if i["hm"] else ", dia todo")}
            for i in items]
    card = {"kind": "agenda", "badge": "◷", "label": "PRÓXIMOS 3 DIAS",
            "title": f"{len(items)} compromisso{'s' if len(items) != 1 else ''} chegando" if items else "Contagem regressiva",
            "items": rows[:5], "more": max(0, len(rows) - 5),
            "footer": " · ".join(counting[:2]) if counting else (calendar_hub.source_name() or "Lembretes do JARVIS")}
    if not items:
        card.update(empty_text="Nada marcado nos próximos 3 dias", empty_sub="As contagens seguem abaixo")

    parts = []
    if items:
        spoken = [f"{_days_word(i['days'])}, {i['title']}" + (f" às {i['hm']}" if i["hm"] else "") for i in items[:3]]
        parts.append("Nos próximos dias: " + "; ".join(spoken) + ".")
    parts += counting[:2]
    return {"tab": "proximos", "progress": "Olhando os próximos dias...", "speech": " ".join(parts), "card": card}


def _focus_segment(pending: list[dict]) -> dict | None:
    """V5.3: no "bom dia", as tarefas viram um plano: as três mais antigas primeiro."""
    items = [{"text": t.get("texto", "")} for t in pending if t.get("texto")]
    if not items:
        return None
    card = {"kind": "tasks", "label": "PRIORIDADES · HOJE", "title": f"Comece por: {items[0]['text']}",
            "items": items[:3], "more": max(0, len(items) - 3), "total": len(items),
            "footer": 'As mais antigas primeiro · diga "concluir tarefa" ao terminar'}
    if len(items) == 1:
        speech = f"Você tem uma tarefa pendente: {items[0]['text']}."
    else:
        speech = (f"Você tem {len(items)} tarefas pendentes. Sugiro começar por {items[0]['text']}"
                  f", e depois {items[1]['text']}.")
    return {"tab": "tarefas", "progress": "Montando as prioridades do dia...", "speech": speech, "card": card}


def _match_segment(now: datetime) -> dict | None:
    """V5.3: dia de jogo do time do Modo Torcedor entra no "bom dia" (só lê o cache, sem rede)."""
    from modules import fan_mode, prefs, sports_provider

    try:
        p = prefs._load()
        if not p.get("fan_mode_enabled"):
            return None
        team_key = p.get("fan_team", "palmeiras")
        match = sports_provider.get_current_or_next_match(team_key)
    except Exception as exc:  # noqa: BLE001
        log.warning("Briefing: jogo do time indisponível: %s", exc)
        return None
    if not match.get("is_match_day") or match.get("status") in ("finished", "postponed", "unknown"):
        return None
    team = ((fan_mode.get_team_info(team_key) or {}).get("name")) or team_key.capitalize()
    hm = ""
    if match.get("time_known", True):
        try:
            hm = datetime.fromisoformat(match["date"]).strftime("%H:%M")
        except (KeyError, ValueError):
            hm = ""
    opponent = match.get("opponent") or "A definir"
    rows = [{"label": "Adversário", "value": opponent},
            {"label": "Horário", "value": hm or "a confirmar"},
            {"label": "Competição", "value": match.get("competition", "")}]
    if match.get("venue"):
        rows.append({"label": "Local", "value": match["venue"]})
    card = {"kind": "metrics", "badge": "◉", "label": "MODO TORCEDOR · HOJE", "title": f"{team} x {opponent}",
            "items": rows, "footer": "Agenda do time · ESPN"}
    if match.get("status") == "live":
        speech = f"E o {team} está em campo agora, contra {opponent}."
    else:
        speech = f"E hoje tem {team}, contra {opponent}" + (f", às {hm}." if hm else ", com horário a confirmar.")
    return {"tab": "jogo", "progress": "Conferindo o jogo de hoje...", "speech": speech, "card": card}


def _alarm_segment(tomorrow: datetime) -> dict | None:
    """V5.3: no "boa noite", o despertador de amanhã (se houver)."""
    from modules import alarms

    try:
        day = tomorrow.strftime("%Y-%m-%d")
        items = [a for a in alarms.list_alarms() if a.get("proximo", "").startswith(day)]
    except Exception as exc:  # noqa: BLE001
        log.warning("Fechamento: alarmes indisponíveis: %s", exc)
        return None
    if not items:
        return None
    first = items[0]
    rows = [{"label": "Toca às", "value": first["hora"]}]
    if first.get("rotulo"):
        rows.append({"label": "Para", "value": first["rotulo"]})
    if len(items) > 1:
        rows.append({"label": "Outros", "value": ", ".join(a["hora"] for a in items[1:3])})
    card = {"kind": "metrics", "badge": "◷", "label": "DESPERTADOR · AMANHÃ", "title": f"Alarme às {first['hora']}",
            "items": rows, "footer": 'Diga "cancela o alarme" para desmarcar'}
    speech = f"Seu despertador de amanhã está marcado para as {first['hora']}."
    return {"tab": "agenda", "progress": "Conferindo o despertador...", "speech": speech, "card": card}


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


def _closing(card_weather: dict | None, agenda_items: int, to_act: int, pending_tasks: int,
             first_task: str = "", next_event: dict | None = None) -> str:
    # V5.3: quando dá, o conselho junta a primeira tarefa e o próximo compromisso
    if first_task and next_event and ":" in next_event.get("time", ""):
        return f"Hoje, resolva {first_task} antes de {next_event['title']}, às {next_event['time']}."
    if to_act >= 3:
        return "Hoje, resolva primeiro os e-mails que pedem ação e depois mantenha o foco no essencial."
    if card_weather and (card_weather.get("rain_probability") or 0) >= 60:
        if first_task:
            return f"Hoje, leve um guarda-chuva e comece por {first_task}."
        return "Hoje, leve um guarda-chuva e mantenha o foco no essencial."
    if agenda_items >= 4:
        return "Hoje o dia está cheio; proteja os intervalos entre os compromissos."
    if pending_tasks >= 5:
        return f"Hoje, escolha duas das {pending_tasks} tarefas pendentes e comece por elas."
    if first_task:
        return f"Hoje, comece por {first_task} e mantenha o foco no essencial."
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
        # V5.6: 4 dias (hoje + os próximos 3) e qualquer agenda conectada (Google ou iCal)
        return calendar_hub.upcoming_events(days=4, limit=30) if calendar_hub.connected() else []

    def news_for(theme: dict) -> list[dict]:
        limit = max(3, int(theme.get("count") or 1) + 3)  # sobra para tirar repetidas
        if theme.get("topic"):
            return news_radar.fetch_news_by_category(theme["topic"], limit=limit)
        return news_radar.fetch_news_by_query(theme["query"], limit=limit)

    themes = news_themes()

    weather_res, events, tri, *news_lists = await asyncio.gather(
        safe(_fetch_weather, settings.WEATHER_CITY),
        safe(calendar_events, default=[]),
        safe(email_triage.triage, default={"connected": False}),
        *(safe(news_for, t, default=[]) for t in themes),
    )

    segments = []
    weather_seg = _weather_segment(weather_res)
    if weather_seg:
        segments.append(weather_seg)
    agenda_seg = _agenda_segment(now, events or [])
    segments.append(agenda_seg)
    upcoming_seg = _upcoming_segment(now, events or [])
    if upcoming_seg:
        segments.append(upcoming_seg)
    pending_list = tasks.get_tasks(include_completed=False)
    for extra in (_focus_segment(pending_list), _match_segment(now)):
        if extra:
            segments.append(extra)
    email_seg = _email_segment(tri or {"connected": False})
    segments.append(email_seg)
    for theme, items in zip(themes, news_lists):
        seg = _news_segment(theme, items or [])
        if seg:
            segments.append(seg)
    health_seg, readiness = _health_segment(health.load_telemetry())
    segments.append(health_seg)

    deviations = _deviations(now, weather_res)
    note = _day_note(now)
    greeting = f"{greeting_word(now)}{nome_str}. Hoje é {_date_line(now)}." + (f" {note}" if note else "")
    if deviations:
        opening = f"Atenção a {len(deviations)} {'ponto' if len(deviations) == 1 else 'pontos'}"
        opening_sub = "; ".join(deviations)
        opening_speech = f"Antes do briefing, um aviso: {opening_sub}."
    else:
        opening = "Sem desvios relevantes"
        opening_sub = "dados consolidados desde ontem"
        opening_speech = ("Revisei o que já está consolidado e nada exige interromper a sua "
                          + ("manhã." if now.hour < 12 else "tarde." if now.hour < 18 else "noite."))

    pending = len(pending_list)
    upcoming = [i for i in agenda_seg["card"]["items"]
                if ":" in i["time"] and (_minutes_until(now, i["time"]) or 0) >= 0]
    first_task = (pending_list[0].get("texto") or "") if pending_list else ""
    closing = _closing(weather_seg["card"] if weather_seg else None, len(agenda_seg["card"]["items"]),
                       email_seg["card"]["to_act"], pending, first_task, upcoming[0] if upcoming else None)

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
        "icon": weather_icon(at("weather_code")),
        "tip": weather_tip(t_min, t_max, rain, at("weather_code")),
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


def _evening_closing(pending: int, tomorrow_items: list[dict], rain, has_alarm: bool = True) -> str:
    if tomorrow_items and tomorrow_items[0]["time"] < "09:00":
        if not has_alarm:
            # V5.3: começa cedo e não tem despertador: oferece marcar
            return (f"Amanhã começa cedo, às {tomorrow_items[0]['time']}, e não há despertador marcado. "
                    'Se quiser, diga "me acorda às" e o horário.')
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
        return calendar_hub.upcoming_events(days=2, limit=15) if calendar_hub.connected() else []

    weather_res, events = await asyncio.gather(
        safe(_fetch_weather, settings.WEATHER_CITY),
        safe(calendar_events, default=[]),
    )
    pending = tasks.get_tasks(include_completed=False)

    segments = [_tasks_segment(pending)]
    agenda_seg = _agenda_segment(tomorrow, events or [], when="amanhã")
    segments.append(agenda_seg)
    alarm_seg = _alarm_segment(tomorrow)
    if alarm_seg:
        segments.append(alarm_seg)
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
    closing = _evening_closing(len(pending), tomorrow_items, rain, has_alarm=alarm_seg is not None)

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


# ---------------------------------------------------------------------- V6.5: "boa tarde"
AFTERNOON_TABS = [
    {"id": "agenda", "label": "Resto do dia"},
    {"id": "tarefas", "label": "Tarefas"},
    {"id": "clima", "label": "Clima"},
    {"id": "agua", "label": "Água"},
    {"id": "email", "label": "E-mails"},
    {"id": "noticias", "label": "Notícias"},
]


def _afternoon_closing(ahead: list[dict], pending: int, rain) -> str:
    parts = []
    if ahead:
        parts.append(f"O próximo compromisso é {ahead[0]['title']}, às {ahead[0]['time']}.")
    if pending:
        parts.append("Se der, vale riscar mais uma tarefa antes do fim do expediente.")
    if isinstance(rain, (int, float)) and rain >= 50:
        parts.append("E leve o guarda-chuva na volta.")
    return " ".join(parts) or "A tarde está tranquila. Qualquer coisa, é só chamar."


async def build_afternoon_briefing() -> dict:
    """V6.5: resumo da tarde ("boa tarde"): o que falta do dia, tarefas, clima, água, e-mails e notícias.

    Mesmo formato dos outros briefings (segmentos com cards), mais curto que o "bom dia".
    """
    now = datetime.now()
    user_name = face.get_name()
    nome_str = f", {user_name}" if user_name else ""

    async def safe(fn, *args, default=None):
        try:
            return await asyncio.to_thread(fn, *args)
        except Exception as exc:  # noqa: BLE001
            log.warning("Resumo da tarde: falha em %s: %s", getattr(fn, "__name__", fn), exc)
            return default

    from modules.tools import _fetch_weather

    def calendar_events() -> list[dict]:
        return calendar_hub.upcoming_events(days=1, limit=15) if calendar_hub.connected() else []

    def news_for(theme: dict) -> list[dict]:
        limit = max(3, int(theme.get("count") or 1) + 3)
        if theme.get("topic"):
            return news_radar.fetch_news_by_category(theme["topic"], limit=limit)
        return news_radar.fetch_news_by_query(theme["query"], limit=limit)

    themes = news_themes()
    weather_res, events, tri, *news_lists = await asyncio.gather(
        safe(_fetch_weather, settings.WEATHER_CITY),
        safe(calendar_events, default=[]),
        safe(email_triage.triage, default={"connected": False}),
        *(safe(news_for, t, default=[]) for t in themes),
    )

    segments = []
    agenda_seg = _agenda_segment(now, events or [], when="hoje")
    agenda_seg["card"]["label"] = "AGENDA · RESTO DO DIA"
    segments.append(agenda_seg)
    pending_list = tasks.get_tasks(include_completed=False)
    if pending_list:
        tasks_seg = _tasks_segment(pending_list)
        tasks_seg["speech"] = tasks_seg["speech"].replace("Ficaram", "Ainda falta" if len(pending_list) == 1 else "Ainda faltam", 1)
        tasks_seg["progress"] = "Conferindo o que falta fazer..."
        segments.append(tasks_seg)
    weather_seg = _weather_segment(weather_res)
    if weather_seg:
        segments.append(weather_seg)
    water_seg = _water_segment()
    if water_seg:
        segments.append(water_seg)
    email_seg = _email_segment(tri or {"connected": False})
    if (tri or {}).get("connected"):
        segments.append(email_seg)
    for theme, items in zip(themes, news_lists):
        seg = _news_segment(theme, items or [])
        if seg:
            segments.append(seg)

    greeting = f"Boa tarde{nome_str}. Aqui está o resumo da tarde de {_date_line(now)}."
    ahead = [i for i in agenda_seg["card"]["items"]
             if ":" in i["time"] and (_minutes_until(now, i["time"]) or 0) >= 0]
    pending = len(pending_list)
    if not ahead and not pending:
        opening, opening_sub = "Tarde livre", "nada marcado e nenhuma tarefa pendente"
        opening_speech = "A tarde está livre: nada marcado e nenhuma tarefa pendente."
    else:
        opening = "Resumo da tarde"
        opening_sub = (f"{len(ahead)} compromisso{'s' if len(ahead) != 1 else ''} pela frente · "
                       f"{pending} tarefa{'s' if pending != 1 else ''}")
        opening_speech = ""
    rain = weather_seg["card"].get("rain_probability") if weather_seg else None
    closing = _afternoon_closing(ahead, pending, rain)

    speech = " ".join(p for p in [greeting, opening_speech, *(s["speech"] for s in segments), closing] if p)
    used_tabs = {s["tab"] for s in segments}
    return {
        "mode": "afternoon",
        "title": "RESUMO DA TARDE",
        "greeting": greeting,
        "opening": opening,
        "opening_sub": opening_sub,
        "opening_speech": opening_speech,
        "segments": segments,
        "readiness": None,
        "closing": closing,
        "tabs": [t for t in AFTERNOON_TABS if t["id"] in used_tabs],
        "speech": speech,
    }


async def generate_afternoon_briefing() -> str:
    """Texto corrido do resumo da tarde (telas sem a sequência de cards)."""
    try:
        return (await build_afternoon_briefing())["speech"]
    except Exception as exc:  # noqa: BLE001
        log.warning("Resumo da tarde em segmentos falhou, usando o resumo simples: %s", exc)
        return await _simple_daily_briefing()


def routine_mode(hour: int | None = None) -> str:
    """V6.5: o briefing da entrada/rotina acompanha a hora: de 12h às 18h, o resumo da tarde."""
    hour = datetime.now().hour if hour is None else hour
    return "afternoon" if 12 <= hour < 18 else "morning"


def build_for(mode: str):
    """Construtor do briefing de cada modo (morning | afternoon | evening)."""
    return {"evening": build_evening_briefing, "afternoon": build_afternoon_briefing}.get(mode, build_morning_briefing)


def text_for(mode: str):
    return {"evening": generate_evening_briefing, "afternoon": generate_afternoon_briefing}.get(mode, generate_daily_briefing)

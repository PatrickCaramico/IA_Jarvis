"""V4.3: telas por assunto no formato do briefing (um card por item, abas, legenda e fileira).

Uma frase curta abre a tela do assunto: "notícias", "notificações", "e-mails", "agenda", "clima",
"tarefas", "meus dados de saúde" e "comandos". A frase precisa ser só isso (com ou sem "Jarvis" e
"por favor"); pedidos mais longos ("adiciona tarefa comprar pão") seguem os comandos de sempre.

Cada build_* devolve o mesmo formato de modules/briefing.build_morning_briefing, então
core/briefing_flow.py fala e mostra sem saber qual assunto é.
"""
import asyncio
import logging
from collections import Counter

from config import settings
from modules import briefing, email_triage, health, news_radar, notifications, prefs, tasks
from modules.briefing import _fmt

log = logging.getLogger("jarvis.briefing_topics")

# Frases exatas (texto normalizado, sem acento nem pontuação) que abrem cada tela
PHRASES = {
    "noticias": ("noticias", "as noticias", "ultimas noticias", "noticias do dia", "radar de noticias",
                 "manchetes", "mostra as noticias", "mostrar noticias", "quais as noticias", "me da as noticias"),
    "notificacoes": ("notificacoes", "minhas notificacoes", "quais sao minhas notificacoes", "mostra as notificacoes",
                     "mostrar notificacoes", "tenho notificacoes", "ver notificacoes"),
    "email": ("emails", "email", "e mails", "e mail", "meus emails", "meus e mails", "caixa de entrada",
              "triagem de email", "triagem de emails", "tenho email", "tenho emails", "ver emails"),
    "agenda": ("agenda", "minha agenda", "agenda de hoje", "compromissos", "meus compromissos", "ver agenda"),
    "clima": ("clima", "panorama do clima", "previsao do tempo", "clima de hoje"),
    "tarefas": ("tarefas", "minhas tarefas", "pendencias", "minhas pendencias", "ver tarefas"),
    "saude": ("meus dados de saude", "dados de saude", "minha saude", "prontidao", "minha prontidao"),
    "comandos": ("comandos", "ajuda", "o que posso falar", "o que eu posso falar", "o que voce faz",
                 "lista de comandos", "comandos de voz"),
}

TITLES = {
    "noticias": "RADAR · NOTÍCIAS",
    "notificacoes": "CENTRAL · NOTIFICAÇÕES",
    "email": "COMUNICAÇÕES · E-MAIL",
    "agenda": "AGENDA · HOJE",
    "clima": "PANORAMA · CLIMA",
    "tarefas": "TAREFAS · PENDENTES",
    "saude": "SAÚDE · SOB DEMANDA",
    "comandos": "COMANDOS DE VOZ",
}

# Temas extras só na tela de notícias (o briefing da manhã usa os três de briefing.NEWS_THEMES)
EXTRA_NEWS = [
    {"title": "Economia", "topic": "economia"},
    {"title": "Mundo", "topic": "mundo"},
]

# O que mostrar na tela "comandos" (e na faixa DIGA: da central)
COMMANDS = [
    {"say": "bom dia", "does": "Briefing da manhã: clima, agenda, e-mails, notícias e saúde"},
    {"say": "boa noite", "does": "Fechamento do dia: tarefas, amanhã, clima, água e anotações"},
    {"say": "notícias", "does": "Radar com um card por tema"},
    {"say": "notificações", "does": "Notificações do Windows por aplicativo"},
    {"say": "e-mails", "does": "Triagem: quantos chegaram e quais pedem ação"},
    {"say": "agenda", "does": "Compromissos e lembretes de hoje"},
    {"say": "clima", "does": "Panorama do tempo agora"},
    {"say": "tarefas", "does": "Pendências da sua lista"},
    {"say": "meus dados de saúde", "does": "Prontidão, sono e movimento (sob demanda)"},
]

def _clean(norm: str) -> str:
    words = norm.strip()
    for f in ("jarvis ", "por favor "):
        if words.startswith(f):
            words = words[len(f):]
    for f in (" jarvis", " por favor"):
        if words.endswith(f):
            words = words[: -len(f)]
    return words.strip()


def match(norm: str) -> str | None:
    """Qual tela a frase pede (chave de PHRASES) ou None."""
    text = _clean(norm)
    for topic, phrases in PHRASES.items():
        if text in phrases:
            return topic
    return None


def _wrap(topic: str, segments: list[dict], opening: str, opening_sub: str, speech_open: str,
          closing: str, readiness: dict | None = None) -> dict:
    """Monta o formato comum. Cada segmento ganha uma aba própria (o título do card)."""
    tabs = []
    for i, seg in enumerate(segments):
        seg["tab"] = f"t{i}"
        tabs.append({"id": seg["tab"], "label": seg["card"].get("tab_label") or seg["card"].get("title", "")[:22]})
    speech = " ".join(p for p in [speech_open, *(s["speech"] for s in segments), closing] if p)
    return {
        "mode": f"topic:{topic}",
        "title": TITLES[topic],
        "greeting": "",
        "opening": opening,
        "opening_sub": opening_sub,
        "opening_speech": speech_open,
        "segments": segments,
        "readiness": readiness,
        "closing": closing,
        "tabs": tabs,
        "speech": speech,
    }


async def _thread(fn, *args, default=None):
    try:
        return await asyncio.to_thread(fn, *args)
    except Exception as exc:  # noqa: BLE001
        log.warning("Tela por assunto: falha em %s: %s", getattr(fn, "__name__", fn), exc)
        return default


# ------------------------------------------------------------------ assuntos
async def _news() -> dict:
    themes = briefing.NEWS_THEMES + EXTRA_NEWS

    def fetch(theme):
        if "topic" in theme:
            return news_radar.fetch_news_by_category(theme["topic"], limit=3)
        return news_radar.fetch_news_by_query(theme["query"], limit=3)

    lists = await asyncio.gather(*(_thread(fetch, t, default=[]) for t in themes))
    segments = [s for s in (briefing._news_segment(t, items or []) for t, items in zip(themes, lists)) if s]
    if not segments:
        return _wrap("noticias", [], "Radar sem sinal", "não consegui ler as notícias agora",
                     "Não consegui ler as notícias agora. Verifique a internet.", "")
    return _wrap("noticias", segments, "Radar de notícias", f"{len(segments)} temas · Google News",
                 "Aqui estão os destaques por tema.", "Quer abrir alguma? Use o botão Abrir matéria no card.")


async def _notifications() -> dict:
    p = prefs.get_all()
    card = {"kind": "notifications", "label": "CENTRAL · NOTIFICAÇÕES", "items": [], "footer": "Notificações do Windows"}
    if not p.get("notifications_enabled"):
        card.update(title="Central desligada", empty_text="A leitura das notificações está desligada",
                    empty_sub="Ligue em Configurações > Automação")
        seg = {"progress": "Verificando notificações...", "card": card,
               "speech": "A central de notificações está desligada. Ela fica em Configurações, na aba Automação."}
        return _wrap("notificacoes", [seg], "Notificações", "central desligada", "", "")
    await notifications.poll()
    st = notifications.status()
    current = notifications.items()
    read_content = bool(p.get("notifications_read_content"))
    if not st.get("available"):
        card.update(title="Indisponível", empty_text="O Windows não liberou a leitura", empty_sub=st.get("reason", ""))
        seg = {"progress": "Verificando notificações...", "card": card,
               "speech": "A central de notificações não está disponível agora."}
        return _wrap("notificacoes", [seg], "Notificações", "indisponível", "", "")
    counts = Counter(n["app"] for n in current)
    if not current:
        card.update(title="Nada novo", empty_text="Nenhuma notificação", empty_sub="Tudo tranquilo por aqui")
        seg = {"progress": "Verificando notificações...", "card": card, "speech": "Nenhuma notificação nova."}
        return _wrap("notificacoes", [seg], "Notificações", "nenhuma nova", "", "")
    segments = []
    for app, count in counts.most_common(5):
        mine = [n for n in current if n["app"] == app]
        app_card = {
            "kind": "notifications", "label": "CENTRAL · NOTIFICAÇÕES", "title": app, "tab_label": app[:14],
            "count": count,
            # o conteúdo só aparece na tela; na fala, só se "ler o conteúdo" estiver ligado
            "items": [{"title": n.get("title", ""), "body": n.get("body", "")} for n in mine[:3]],
            "more": max(0, count - 3),
            "footer": "Notificações do Windows",
        }
        speech = f"{count} do {app}."
        if read_content and mine[0].get("title"):
            speech += f" A mais recente: {mine[0]['title']}."
        segments.append({"progress": "Lendo as notificações...", "card": app_card, "speech": speech})
    return _wrap("notificacoes", segments, "Notificações", f"{len(current)} no total · {len(counts)} aplicativos",
                 f"Você tem {len(current)} notificações.", "")


async def _email() -> dict:
    tri = await _thread(email_triage.triage, default={"connected": False})
    seg = briefing._email_segment(tri or {"connected": False})
    if not seg["speech"]:
        seg["speech"] = "A triagem de e-mail ainda não está conectada. As instruções estão no card."
    sub = f"{seg['card']['received']} recebidos · {seg['card']['to_act']} para agir" if seg["card"]["connected"] else "não conectado"
    return _wrap("email", [seg], "Triagem de e-mail", sub, "", "")


async def _agenda() -> dict:
    from datetime import datetime

    def events():
        from modules import calendar_hub

        return calendar_hub.upcoming_events(days=1, limit=10) if calendar_hub.connected() else []

    seg = briefing._agenda_segment(datetime.now(), await _thread(events, default=[]) or [])
    return _wrap("agenda", [seg], "Agenda de hoje", seg["card"]["footer"], "", "")


async def _weather() -> dict:
    from modules.tools import _fetch_weather

    res = await _thread(_fetch_weather, settings.WEATHER_CITY)
    segments = [s for s in (briefing._weather_segment(res), briefing._tomorrow_weather_segment(res)) if s]
    if len(segments) == 2:
        segments[0]["card"]["tab_label"] = "Hoje"
        segments[1]["card"]["tab_label"] = "Amanhã"
    if not segments:
        return _wrap("clima", [], "Clima sem sinal", "não consegui consultar o clima",
                     "Não consegui consultar o clima agora.", "")
    return _wrap("clima", segments, "Panorama do clima", segments[0]["card"]["title"], "", "")


async def _tasks() -> dict:
    seg = briefing._tasks_segment(tasks.get_tasks(include_completed=False))
    return _wrap("tarefas", [seg], "Suas tarefas", f"{seg['card']['total']} pendentes", "", "")


async def _health() -> dict:
    """Pedido explícito: aqui os números aparecem e os principais são falados."""
    tele = health.load_telemetry()
    _, readiness = briefing._health_segment(tele)
    metrics = [
        {"label": "Recuperação", "value": f"{tele.get('recovery', '—')}%"},
        {"label": "Sono", "value": f"{_fmt(tele.get('sleep_hours') or 0)} h"},
        {"label": "Eficiência do sono", "value": f"{tele.get('sleep_efficiency', '—')}%"},
        {"label": "Batimentos", "value": f"{tele.get('bpm', '—')} bpm"},
        {"label": "HRV", "value": f"{tele.get('hrv', '—')} ms"},
        {"label": "SpO2", "value": f"{tele.get('spo2', '—')}%"},
        {"label": "Estresse", "value": f"{tele.get('stress', '—')}"},
        {"label": "Passos", "value": f"{tele.get('steps', 0)}"},
    ]
    card = {"kind": "metrics", "label": "SAÚDE · LEITURA DE DADOS", "title": "Seus dados de hoje", "items": metrics,
            "footer": f"{tele.get('device_name', 'Relógio')} · {tele.get('last_sync', '')}"}
    speech = (f"Recuperação de {tele.get('recovery', 0)} por cento e {_fmt(tele.get('sleep_hours') or 0)} "
              f"horas de sono. Os outros números estão na tela.")
    seg = {"progress": "Lendo os dados de saúde...", "card": card, "speech": speech}
    return _wrap("saude", [seg], "Saúde sob demanda", "você pediu: os dados aparecem na tela", "", "",
                 readiness=readiness)


async def _commands() -> dict:
    card = {"kind": "commands", "label": "COMANDOS DE VOZ", "title": "Diga uma destas frases", "items": COMMANDS,
            "footer": "Fale com o microfone ligado (Espaço) ou digite"}
    seg = {"progress": "Listando os comandos...", "card": card,
           "speech": "Você pode dizer bom dia, boa noite, notícias, notificações, e-mails, agenda, clima, tarefas "
                     "ou meus dados de saúde. A lista está na tela."}
    return _wrap("comandos", [seg], "Comandos de voz", f"{len(COMMANDS)} atalhos", "", "")


BUILDERS = {
    "noticias": _news, "notificacoes": _notifications, "email": _email, "agenda": _agenda,
    "clima": _weather, "tarefas": _tasks, "saude": _health, "comandos": _commands,
}


async def build(topic: str) -> dict:
    return await BUILDERS[topic]()

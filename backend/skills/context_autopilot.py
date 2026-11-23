"""Skill Context Autopilot (V8.11): o JARVIS se adianta à agenda.

Alguns minutos antes de um compromisso com horário (padrão: 5), ele avisa e oferece o MODO REUNIÃO:
"Senhor, Daily do time começa em 5 minutos. Quer que eu ative o modo reunião e abra o link? Diga sim."
Com o "sim" (ou pedindo direto: "ativa o modo reunião"):
  - pausa o Spotify (se estiver conectado);
  - abre o link da chamada (Meet, Zoom, Teams, Webex, Jitsi), quando o evento tiver;
  - remonta o workspace "reuniao", se o senhor tiver salvo um ("salva esse layout como reunião");
  - fica em silêncio (só texto na tela) até "terminei a reunião", ou sozinho quando o evento acaba.

Outras frases: "qual minha próxima reunião?", "me avise 10 minutos antes das reuniões",
"desliga o piloto automático da agenda" / "liga o piloto automático da agenda".
Agenda: a mesma do briefing (Google Agenda conectado ou endereço iCal, modules/calendar_hub.py).
Com a central bloqueada, o aviso vai só para o celular pareado (sem falar o título no PC).
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Optional

from config import settings
from core import safe_io
from core.skills import Permission, SkillContext, SkillResult, service, skill

log = logging.getLogger("jarvis.skills.autopilot")

_PATH = settings.DATA_DIR / "piloto_agenda.json"
CHECK_EVERY_S = 60
FETCH_EVERY_S = 300
DEFAULT_LEAD_MIN = 5
MAX_MEETING_S = 3 * 3600  # sem horário de fim: sai do modo reunião sozinho depois de 3 h
SILENCE_DELAY_S = 8  # dá tempo de falar a confirmação antes de silenciar

_MEET_RE = re.compile(r"https?://(?:meet\.google\.com|(?:[\w-]+\.)*zoom\.us|teams\.microsoft\.com|teams\.live\.com|"
                      r"(?:[\w-]+\.)*webex\.com|meet\.jit\.si|whereby\.com)/[^\s<>\"')]+", re.I)


# ------------------------------------------------------------------ estado
def _defaults() -> dict:
    return {"enabled": True, "lead_min": DEFAULT_LEAD_MIN, "offered": {}, "meeting": None}


def load_state() -> dict:
    try:
        data = safe_io.read_json(_PATH) if _PATH.exists() else {}
    except (OSError, ValueError):
        data = {}
    return {**_defaults(), **data} if isinstance(data, dict) else _defaults()


def save_state(state: dict) -> None:
    safe_io.write_json(_PATH, state)


# ------------------------------------------------------------------ partes puras
def meeting_link(ev: dict) -> str:
    """O link da chamada do evento (campo próprio, local ou descrição), ou ""."""
    for field in ("meet", "location", "description"):
        m = _MEET_RE.search(str(ev.get(field) or ""))
        if m:
            return m.group(0).rstrip(".,;")
    return ""


def _start(ev: dict) -> Optional[datetime]:
    from modules import calendar_hub

    if "T" not in str(ev.get("start") or ""):
        return None  # dia inteiro: não é reunião
    return calendar_hub.event_start(ev)


def _end(ev: dict) -> Optional[datetime]:
    raw = str(ev.get("end") or "")
    if "T" not in raw:
        return None
    from modules import calendar_hub

    return calendar_hub.event_start({"start": raw})


def event_key(ev: dict) -> str:
    return f"{ev.get('id') or ev.get('title')}|{ev.get('start')}"


def due_events(events: list[dict], now: datetime, lead_min: int, offered: dict) -> list[tuple[dict, int]]:
    """Eventos com horário que começam dentro do aviso (e ainda não avisados): (evento, minutos que faltam)."""
    out = []
    for ev in events:
        start = _start(ev)
        if start is None:
            continue
        left = (start - now).total_seconds() / 60
        if -1 <= left <= lead_min + 0.5 and event_key(ev) not in offered:
            out.append((ev, max(0, round(left))))
    return out


def offer_text(ev: dict, minutes: int, link: str, ask: bool = True) -> str:
    title = (ev.get("title") or "Seu compromisso").strip()
    when = "está começando agora" if minutes <= 0 else f"começa em {minutes} {'minuto' if minutes == 1 else 'minutos'}"
    text = f"Senhor, {title} {when}."
    if ask:
        extra = " e abra o link da chamada" if link else ""
        text += f" Quer que eu ative o modo reunião{extra}? Diga sim para ativar."
    return text


def _prune(offered: dict, now_ts: float) -> dict:
    return {k: v for k, v in offered.items() if now_ts - float(v) < 2 * 86400}


# ------------------------------------------------------------------ agenda (com cache)
_events_cache: dict = {"at": 0.0, "items": []}


def _fetch_events(force: bool = False) -> list[dict]:
    from modules import calendar_hub

    if not force and time.time() - _events_cache["at"] < FETCH_EVERY_S:
        return list(_events_cache["items"])
    if not calendar_hub.connected():
        _events_cache.update(at=time.time(), items=[])
        return []
    items = calendar_hub.upcoming_events(days=1, limit=20)
    _events_cache.update(at=time.time(), items=list(items))
    return list(items)


# ------------------------------------------------------------------ aviso proativo
async def _deliver(text: str, title_for_phone: str) -> None:
    from core import runtime, speech
    from modules import access

    runtime.notify("reminder", "📅 Reunião chegando", title_for_phone)
    if access.is_restricted():
        return  # bloqueado: só o celular pareado recebe (o título pode ser pessoal)
    await runtime.manager.broadcast({"type": "alert", "text": text})
    runtime.track(speech.say_quietly(text))


async def check_once(now: Optional[datetime] = None) -> int:
    """Uma rodada do piloto: avisa os eventos que estão chegando. Devolve quantos avisou."""
    from core import confirm, session
    from core.skills import registry

    state = load_state()
    if not state.get("enabled", True) or not registry.is_enabled("modo_reuniao"):
        return 0
    now = now or datetime.now()
    meeting = state.get("meeting")
    if meeting and meeting.get("active"):
        ends = float(meeting.get("ends_at") or 0) or float(meeting.get("since", 0)) + MAX_MEETING_S
        if time.time() > ends + 300:
            await asyncio.to_thread(end_meeting)  # o evento acabou: volta a falar sozinho
        return 0
    try:
        events = await asyncio.to_thread(_fetch_events)
    except Exception:  # noqa: BLE001 - agenda fora do ar: tenta na próxima rodada
        log.warning("Piloto da agenda: não consegui ler a agenda", exc_info=True)
        return 0
    due = due_events(events, now, int(state.get("lead_min") or DEFAULT_LEAD_MIN), state.get("offered") or {})
    if not due:
        return 0
    if session.busy and all(m > 1 for _, m in due):
        return 0  # respondendo outra coisa: avisa na próxima rodada (ainda dá tempo)
    ev, minutes = due[0]
    link = meeting_link(ev)
    ask = confirm.pending() is None  # já há outra pergunta no ar: só avisa, sem perguntar por cima
    text = offer_text(ev, minutes, link, ask=ask)
    if ask:
        end = _end(ev)
        confirm.offer("skill", {"name": "modo_reuniao", "origin": "autopilot", "message": "",
                                "args": {"evento": ev.get("title") or "", "link": link,
                                         "fim": end.strftime("%Y-%m-%dT%H:%M:%S") if end else ""}})
    offered = _prune(state.get("offered") or {}, time.time())
    for e, _ in due:  # vários no mesmo horário: um aviso só
        offered[event_key(e)] = time.time()
    state["offered"] = offered
    save_state(state)
    await _deliver(text, f"{ev.get('title') or 'Compromisso'} às {(_start(ev) or now):%H:%M}")
    return 1


@service("piloto_agenda")
async def autopilot_loop() -> None:
    await asyncio.sleep(30)  # deixa o JARVIS terminar de ligar
    while True:
        try:
            await check_once()
        except Exception:  # noqa: BLE001
            log.exception("Piloto da agenda falhou nesta rodada")
        await asyncio.sleep(CHECK_EVERY_S)


# ------------------------------------------------------------------ modo reunião
def _silence(active: bool) -> None:
    from modules import prefs

    prefs.set_silent_mode(active)


async def _silence_later(delay: float) -> None:
    await asyncio.sleep(delay)
    state = load_state()
    if (state.get("meeting") or {}).get("active"):
        await asyncio.to_thread(_silence, True)
        from core import runtime

        await runtime.manager.broadcast({"type": "prefs_updated", "silent_mode": True})


def _pause_music() -> bool:
    try:
        from modules import spotify

        if not spotify.connected():
            return False
        spotify.pause()
        return True
    except Exception:  # noqa: BLE001 - nada tocando, sem dispositivo ativo...
        log.info("Modo reunião: não deu para pausar o Spotify", exc_info=True)
        return False


@skill(
    name="modo_reuniao",
    title="o modo reunião",
    description=("Prepara o computador para uma reunião: pausa a música, abre o link da chamada (se houver), "
                 "monta o workspace 'reuniao' (se existir) e deixa o JARVIS em silêncio até o fim."),
    permission=Permission.ACTION,
    timeout=50,
    triggers=[r"\b(?:ativa|ative|ativar|liga|ligue|ligar|entra|entre|entrar|inicia|inicie|iniciar|coloca|coloque)\s+"
              r"(?:o\s+|no\s+|em\s+)?modo\s+(?:de\s+)?reuniao\b",
              r"\b(?:vou|vamos)\s+entrar\s+(?:em|na|numa)\s+reuniao\b",
              r"^(?:jarvis\s+)?modo\s+(?:de\s+)?reuniao$"],
    params={"type": "object", "properties": {
        "evento": {"type": "string", "description": "Nome da reunião (opcional)."},
        "link": {"type": "string", "description": "Link da chamada (Meet, Zoom, Teams), se houver."},
        "fim": {"type": "string", "description": "Horário de término (AAAA-MM-DDTHH:MM:SS), se souber."}}},
    examples=["ativa o modo reunião", "vou entrar em reunião"],
)
async def modo_reuniao(ctx: SkillContext, evento: str = "", link: str = "", fim: str = "") -> SkillResult:
    from core import runtime
    from modules import prefs

    state = load_state()
    if (state.get("meeting") or {}).get("active"):
        return SkillResult(speech="O modo reunião já está ativo, senhor. Quando acabar, diga: terminei a reunião.")
    done: list[str] = []
    if await asyncio.to_thread(_pause_music):
        done.append("música pausada")
    url = link if _MEET_RE.fullmatch(link or "") else ""
    if url:
        done.append("abrindo o link da chamada")
    try:
        from skills.workspace import has_workspace

        if has_workspace("reuniao"):
            result = await ctx.call("abrir_workspace", nome="reuniao")
            if result.ok:
                done.append("janelas no lugar")
    except ImportError:
        pass
    ends_at = 0.0
    if fim:
        try:
            ends_at = datetime.fromisoformat(fim).timestamp()
        except ValueError:
            ends_at = 0.0
    state["meeting"] = {"active": True, "since": time.time(), "ends_at": ends_at, "event": evento[:120],
                        "prev_silent": bool(await asyncio.to_thread(prefs.is_silent_mode))}
    await asyncio.to_thread(save_state, state)
    runtime.track(_silence_later(SILENCE_DELAY_S))
    feito = (": " + ", ".join(done)) if done else ""
    return SkillResult(speech=f"Modo reunião ativado{feito}. Fico em silêncio até o senhor dizer: terminei a reunião.",
                       url=url)


def end_meeting() -> Optional[dict]:
    """Sai do modo reunião (volta o silêncio ao que era antes). Devolve o estado da reunião, ou None."""
    state = load_state()
    meeting = state.get("meeting") or {}
    if not meeting.get("active"):
        return None
    _silence(bool(meeting.get("prev_silent")))
    state["meeting"] = None
    save_state(state)
    return meeting


@skill(
    name="sair_modo_reuniao",
    title="sair do modo reunião",
    description="Encerra o modo reunião: o JARVIS volta a falar.",
    permission=Permission.ACTION,
    timeout=8,
    triggers=[r"\b(?:sai|saia|sair|desativa|desative|desativar|desliga|desligue|encerra|encerre|termina|termine)\s+"
              r"(?:o\s+|do\s+)?modo\s+(?:de\s+)?reuniao\b",
              r"\b(?:terminei|acabou|acabei|encerrei|finalizei)\s+(?:a\s+)?(?:minha\s+)?reuniao\b",
              r"\breuniao\s+(?:acabou|terminou)\b"],
    examples=["terminei a reunião", "sai do modo reunião"],
)
def sair_modo_reuniao(ctx: SkillContext) -> SkillResult:
    meeting = end_meeting()
    if meeting is None:
        return SkillResult(speech="O modo reunião não estava ativo, senhor.")
    minutes = max(1, round((time.time() - float(meeting.get("since") or time.time())) / 60))
    return SkillResult(speech=f"Modo reunião encerrado depois de {minutes} minutos. Voltei a falar, senhor.")


# ------------------------------------------------------------------ consulta e ajustes
@skill(
    name="proxima_reuniao",
    title="ver a próxima reunião",
    description="Diz qual é o próximo compromisso com horário na agenda (hoje ou amanhã) e se tem link de chamada.",
    permission=Permission.READ,
    timeout=20,
    triggers=[r"\b(?:qual|quando|que horas)\s+(?:e\s+|sera\s+)?(?:a\s+|o\s+)?(?:minha\s+|meu\s+)?proxim[oa]\s+"
              r"(?:reuniao|compromisso|evento|call)\b",
              r"\btenho\s+(?:alguma\s+)?reuniao\s+(?:agora|hoje|daqui a pouco)\b"],
    examples=["qual minha próxima reunião?"],
)
def proxima_reuniao(ctx: SkillContext) -> SkillResult:
    from modules import calendar_hub

    if not calendar_hub.connected():
        return SkillResult(ok=False, speech="A agenda ainda não está conectada, senhor. Conecte em Configurações, na aba Agenda.")
    now = datetime.now()
    events = [e for e in _fetch_events(force=True) if (_start(e) or now - timedelta(1)) >= now - timedelta(minutes=1)]
    if not events:
        return SkillResult(speech="Não há reuniões com horário marcado para hoje, senhor.")
    ev = min(events, key=lambda e: _start(e))
    start = _start(ev)
    day = "hoje" if start.date() == now.date() else "amanhã"
    left = (start - now).total_seconds() / 60
    when = f"daqui a {round(left)} minutos" if 0 <= left < 60 else f"{day} às {start:%H:%M}"
    link = meeting_link(ev)
    speech = f"Sua próxima reunião é {ev.get('title') or 'sem título'}, {when}."
    if link:
        speech += " Tem link de chamada; na hora eu ofereço abrir."
    return SkillResult(speech=speech, data={"titulo": ev.get("title"), "inicio": ev.get("start"), "link": link},
                       cards=[{"type": "skill", "data": {"tag": "PRÓXIMA REUNIÃO", "source": when,
                                                         "rows": [{"label": f"{start:%H:%M}", "value": ev.get("title") or ""}]}}])


_LEAD_RE = re.compile(r"\b(?:me\s+)?(?:avise|avisa|lembre|lembra)(?:-me)?\s+(?P<min>\d{1,2})\s+minutos?\s+antes\s+d[aeo]s?\s+"
                      r"(?:reunioes|reuniao|compromissos|eventos)\b")
_TOGGLE_RE = re.compile(r"\b(?P<verb>liga|ligue|ativa|ative|desliga|desligue|desativa|desative|pausa|pause)\s+"
                        r"(?:o\s+)?(?:piloto automatico|aviso(?:s)? de reuni(?:ao|oes)|piloto)\s+(?:da|de)\s+(?:agenda|reunioes)\b")


def _parse_config(norm_text: str, _original: str) -> Optional[dict]:
    m = _LEAD_RE.search(norm_text)
    if m:
        return {"minutos": int(m.group("min"))}
    m = _TOGGLE_RE.search(norm_text)
    if m:
        return {"ativo": not m.group("verb").startswith(("desl", "desat", "paus"))}
    return None


@skill(
    name="piloto_agenda",
    title="ajustar o piloto da agenda",
    description="Liga/desliga os avisos antes das reuniões (ativo) e/ou muda com quantos minutos de antecedência avisar (minutos, 1 a 30).",
    permission=Permission.ACTION,
    timeout=5,
    parse=_parse_config,
    params={"type": "object", "properties": {
        "ativo": {"type": "boolean"},
        "minutos": {"type": "integer", "description": "Minutos de antecedência do aviso (1 a 30)."}}},
    examples=["me avise 10 minutos antes das reuniões", "desliga o piloto automático da agenda"],
)
def piloto_agenda(ctx: SkillContext, ativo: Optional[bool] = None, minutos: Optional[int] = None) -> SkillResult:
    state = load_state()
    if minutos is not None:
        if not 1 <= int(minutos) <= 30:
            return SkillResult(ok=False, speech="Consigo avisar de 1 a 30 minutos antes, senhor.")
        state["lead_min"] = int(minutos)
        state["enabled"] = True
    if ativo is not None:
        state["enabled"] = bool(ativo)
    if ativo is None and minutos is None:
        on = "ligado" if state.get("enabled", True) else "desligado"
        meeting = state.get("meeting") or {}
        # V8.11: data = o estado para a tela do Modo Desk (aba Agenda)
        return SkillResult(speech=f"O piloto da agenda está {on}, avisando {state.get('lead_min')} minutos antes, senhor.",
                           data={"ativo": bool(state.get("enabled", True)), "minutos": int(state.get("lead_min") or DEFAULT_LEAD_MIN),
                                 "reuniao_ativa": bool(meeting.get("active")), "reuniao": meeting.get("event", "")})
    save_state(state)
    if not state["enabled"]:
        return SkillResult(speech="Piloto da agenda desligado: não aviso mais antes das reuniões, senhor.")
    return SkillResult(speech=f"Combinado: aviso {state['lead_min']} minutos antes de cada reunião, senhor.")

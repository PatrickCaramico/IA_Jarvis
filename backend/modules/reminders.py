"""Lembretes persistentes do JARVIS com data e hora que sobrevivem ao reinício.
Salva lembretes em data/lembretes.json e monitora continuamente em background.
"""
import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Awaitable, Callable, Optional

from config import settings

log = logging.getLogger("jarvis.reminders")
_REMINDERS_PATH = settings.DATA_DIR / "lembretes.json"

_announcer: Optional[Callable[[str], Awaitable[None]]] = None


def set_announcer(fn: Callable[[str], Awaitable[None]]) -> None:
    global _announcer
    _announcer = fn


def _load_reminders() -> list[dict]:
    if not _REMINDERS_PATH.exists():
        return []
    try:
        data = json.loads(_REMINDERS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _save_reminders(rems: list[dict]) -> None:
    _REMINDERS_PATH.write_text(json.dumps(rems, ensure_ascii=False, indent=2), encoding="utf-8")


def get_reminders(only_pending: bool = True) -> list[dict]:
    rems = _load_reminders()
    if only_pending:
        return [r for r in rems if not r.get("disparado", False)]
    return rems


def add_reminder(texto: str, data_hora: datetime, recorrencia: Optional[str] = None) -> dict:
    rems = _load_reminders()
    new_id = (max((r.get("id", 0) for r in rems), default=0)) + 1
    rem = {
        "id": new_id,
        "texto": texto.strip(),
        "data_hora": data_hora.strftime("%Y-%m-%d %H:%M"),
        "recorrencia": recorrencia,
        "disparado": False,
        "criado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    rems.append(rem)
    _save_reminders(rems)
    return rem


def postpone_reminder(minutes: int = 10) -> Optional[dict]:
    """Adia o lembrete disparado mais recente ou o próximo agendado."""
    rems = _load_reminders()
    if not rems:
        return None

    candidato = None
    disparados = [r for r in rems if r.get("disparado", False)]
    if disparados:
        candidato = disparados[-1]
    else:
        pendentes = [r for r in rems if not r.get("disparado", False)]
        if pendentes:
            candidato = pendentes[0]

    if not candidato:
        return None

    novo_horario = datetime.now() + timedelta(minutes=minutes)
    candidato["data_hora"] = novo_horario.strftime("%Y-%m-%d %H:%M")
    candidato["disparado"] = False
    _save_reminders(rems)
    return candidato


def delete_reminder(rem_id: int) -> bool:
    rems = _load_reminders()
    before = len(rems)
    rems = [r for r in rems if r.get("id") != rem_id]
    if len(rems) < before:
        _save_reminders(rems)
        return True
    return False


def clear_reminders() -> int:
    rems = _load_reminders()
    count = len([r for r in rems if not r.get("disparado", False)])
    _save_reminders([])
    return count


async def check_pending_reminders() -> None:
    """Verifica e dispara lembretes agendados cuja data e hora já chegaram."""
    rems = _load_reminders()
    agora = datetime.now()
    alterado = False

    for r in rems:
        if not r.get("disparado", False):
            try:
                alvo = datetime.strptime(r["data_hora"], "%Y-%m-%d %H:%M")
                if agora >= alvo:
                    if r.get("recorrencia") == "diaria":
                        # Reagenda lembrete diário para o dia seguinte
                        novo_alvo = alvo + timedelta(days=1)
                        while novo_alvo <= agora:
                            novo_alvo += timedelta(days=1)
                        r["data_hora"] = novo_alvo.strftime("%Y-%m-%d %H:%M")
                        r["ultimo_disparo"] = agora.strftime("%Y-%m-%d %H:%M")
                        r["disparado"] = False
                    else:
                        r["disparado"] = True
                    alterado = True
                    log.info("Disparando lembrete: %s", r["texto"])
                    if _announcer:
                        msg = f"Atenção, lembrete: {r['texto']}."
                        try:
                            await _announcer(msg)
                        except Exception:  # noqa: BLE001
                            log.exception("Falha ao anunciar lembrete")
            except ValueError:
                pass

    if alterado:
        _save_reminders(rems)


async def reminder_worker_loop() -> None:
    """Worker assíncrono que roda em background conferindo lembretes a cada 5 segundos."""
    while True:
        try:
            await check_pending_reminders()
        except asyncio.CancelledError:
            break
        except Exception:  # noqa: BLE001
            log.exception("Erro no loop de lembretes")
        await asyncio.sleep(5)


def _parse_datetime(norm: str) -> tuple[Optional[datetime], str, Optional[str]]:
    agora = datetime.now()
    alvo = agora
    clean = norm

    # Recorrência diária ("todo dia às 8h", "todos os dias", "diariamente")
    is_daily = bool(re.search(r"\b(?:todo\s+dia|todos\s+os\s+dias|diariamente)\b", clean))
    if is_daily:
        recorrencia = "diaria"
        clean = re.sub(r"\b(?:todo\s+dia|todos\s+os\s+dias|diariamente)\b", " ", clean)
    else:
        recorrencia = None

    # Relativo a minutos ou horas
    min_match = re.search(r"\bdaqui\s+(?:a\s+)?(\d+)\s+minutos?\b|\bem\s+(\d+)\s+minutos?\b", clean)
    if min_match:
        m = int(min_match.group(1) or min_match.group(2))
        alvo = agora + timedelta(minutes=m)
        clean = re.sub(r"\b(?:daqui\s+(?:a\s+)?|em\s+)\d+\s+minutos?\b", " ", clean)
        return alvo, clean.strip(), recorrencia

    # Amanhã
    is_tomorrow = "amanha" in clean
    if is_tomorrow:
        alvo = agora + timedelta(days=1)
        clean = re.sub(r"\bamanha\b", " ", clean)

    # Horário: "as 14 e 30", "as 15 horas", "as 18h", "as 9"
    time_match = re.search(r"\bas\s+(\d{1,2})(?::(\d{2})|(?:\s+e\s+(\d{1,2}))|\s*horas?|\s*h)?\b", clean)
    if time_match:
        hora = int(time_match.group(1))
        minuto = int(time_match.group(2) or time_match.group(3) or 0)
        alvo = alvo.replace(hour=hora, minute=minuto, second=0, microsecond=0)
        if not is_tomorrow and alvo < agora:
            alvo += timedelta(days=1)
        clean = re.sub(r"\bas\s+\d{1,2}(?::\d{2}|\s+e\s+\d{1,2}|\s*horas?|\s*h)?\b", " ", clean)
        return alvo, clean.strip(), recorrencia

    return None, clean.strip(), recorrencia


async def handle_voice(message: str, norm: str, words: int, name: str) -> Optional[str]:
    # Checar se pede lista de lembretes
    if any(q in norm for q in ("quais sao meus lembretes", "meus lembretes", "lista de lembretes", "ver lembretes")):
        pending = get_reminders(only_pending=True)
        if not pending:
            return "Você não tem nenhum lembrete agendado no momento."
        itens = [
            f"{r['texto']} para as {r['data_hora'].split(' ')[1]}" + (" (diário)" if r.get("recorrencia") == "diaria" else "")
            for r in pending[:5]
        ]
        return f"Você tem {len(pending)} {'lembrete' if len(pending) == 1 else 'lembretes'}: " + "; ".join(itens) + "."

    # Apagar lembretes
    if re.search(r"\b(?:apague|apagar|cancela|cancelar|limpar)\b", norm) and "lembrete" in norm:
        count = clear_reminders()
        return f"Apaguei {count} lembretes pendentes." if count else "Você não tinha lembretes pendentes."

    # Adiar lembrete ("adie 10 minutos", "adiar 10 minutos", "adia por 15 minutos")
    postpone_match = re.search(r"\b(?:adie|adiar|adia)\b(?:\s+por)?(?:\s+(?:mais|de))?\s+(\d+)\s+minutos?\b", norm)
    if postpone_match:
        minutos = int(postpone_match.group(1))
        rem = postpone_reminder(minutos)
        if rem:
            hora_alvo = rem["data_hora"].split(" ")[1]
            return f"Lembrete '{rem['texto']}' adiado por {minutos} minutos. Te aviso às {hora_alvo}."
        return "Não encontrei nenhum lembrete recente ou pendente para adiar."

    # Criar lembrete com data/hora e recorrência
    if any(w in norm for w in ("me lembre", "me lembra", "lembre me", "criar lembrete", "agendar lembrete", "lembrete")):
        data_hora, texto, recorrencia = _parse_datetime(norm)
        if data_hora:
            # Limpa conectores do texto
            texto = re.sub(r"^(?:de|que|para|pra|em|sobre)\s+", "", texto)
            texto = re.sub(r"\b(?:me\s+lembre|me\s+lembra|lembre\s+me|lembrete)\b", "", texto).strip()
            texto = re.sub(r"\s+", " ", texto).strip()
            if not texto:
                texto = "compromisso agendado"
            add_reminder(texto, data_hora, recorrencia=recorrencia)
            hora_str = data_hora.strftime("%H:%M")
            if recorrencia == "diaria":
                return f"Combinado. Lembrete recorrente agendado para todos os dias às {hora_str}: {texto}."
            dia_str = "amanhã" if data_hora.date() > datetime.now().date() else "hoje"
            return f"Combinado. Criei um lembrete para {dia_str} às {hora_str}: {texto}."

    return None

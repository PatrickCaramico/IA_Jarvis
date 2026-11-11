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
from modules import when

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


def when_norm(text: str) -> str:
    """Texto sem acentos e em minúsculas (para achar o lembrete pelo assunto)."""
    import unicodedata

    return "".join(c for c in unicodedata.normalize("NFD", str(text or "").lower()) if unicodedata.category(c) != "Mn")


def get_reminders(only_pending: bool = True) -> list[dict]:
    rems = _load_reminders()
    if only_pending:
        return [r for r in rems if not r.get("disparado", False)]
    return rems


def add_reminder(texto: str, data_hora: datetime, recorrencia: Optional[str] = None,
                 dias: Optional[list[int]] = None) -> dict:
    rems = _load_reminders()
    new_id = (max((r.get("id", 0) for r in rems), default=0)) + 1
    rem = {
        "id": new_id,
        "texto": texto.strip(),
        "data_hora": data_hora.strftime("%Y-%m-%d %H:%M"),
        "recorrencia": recorrencia,
        "dias": sorted(dias) if dias else [],  # V5.1: repetição em dias da semana (0 = segunda)
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
                    if r.get("recorrencia") == "semanal" and r.get("dias"):
                        # V5.1: reagenda para o próximo dia da semana escolhido
                        r["data_hora"] = when.next_on_days(
                            alvo.hour, alvo.minute, r["dias"], max(agora, alvo)
                        ).strftime("%Y-%m-%d %H:%M")
                        r["ultimo_disparo"] = agora.strftime("%Y-%m-%d %H:%M")
                        r["disparado"] = False
                    elif r.get("recorrencia") == "diaria":
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


def _parse_datetime(norm: str) -> tuple[Optional[datetime], str, Optional[str], list[int]]:
    """V5.1: o mesmo entendimento de horários dos alarmes (modules/when.py).

    Devolve (quando, texto que sobrou, recorrência "diaria" | "semanal" | None, dias da semana).
    """
    w = when.parse(norm)
    rest = w.rest.strip()
    if w.at is None:
        return None, rest, None, []
    if w.days and sorted(w.days) == list(range(7)):
        return w.at, rest, "diaria", []
    if w.days:
        return w.at, rest, "semanal", sorted(w.days)
    return w.at, rest, None, []


def _describe(r: dict) -> str:
    at = datetime.strptime(r["data_hora"], "%Y-%m-%d %H:%M")
    if r.get("recorrencia") == "diaria":
        return when.describe(at, list(range(7)))
    if r.get("recorrencia") == "semanal" and r.get("dias"):
        return when.describe(at, r["dias"])
    return when.describe(at)


def _list_reply() -> str:
    pending = get_reminders(only_pending=True)
    if not pending:
        return "Você não tem nenhum lembrete agendado no momento."
    itens = [f"{r['texto']}, {_describe(r)}" for r in pending[:5]]
    return f"Você tem {len(pending)} {'lembrete' if len(pending) == 1 else 'lembretes'}: " + "; ".join(itens) + "."


_CANCEL = re.compile(r"\b(?:apague|apagar|apaga|cancela|cancele|cancelar|limpar|limpe|remova|remove|tira|tire|exclua|exclui)\b")


def _cancel_reply(norm: str) -> str:
    """Cancela todos ("apaga todos os lembretes") ou um só, pelo assunto ou pela hora."""
    pending = get_reminders(only_pending=True)
    if not pending:
        return "Você não tinha lembretes pendentes."
    if re.search(r"\btod[oa]s?\b", norm):
        count = clear_reminders()
        return f"Apaguei {count} {'lembrete' if count == 1 else 'lembretes'} pendentes."
    alvo = re.sub(r"^.*?\blembretes?\b\s*(?:d[eoa]s?\s+|para\s+|pra\s+|sobre\s+)?", "", norm).strip()
    w = when.parse(alvo)
    if w.at is not None:
        options = {f"{w.at.hour:02d}:{w.at.minute:02d}", f"{(w.at.hour + 12) % 24:02d}:{w.at.minute:02d}"}
        match = [r for r in pending if r["data_hora"].split(" ")[1] in options]
    else:
        words = [p for p in alvo.split() if len(p) > 2]
        match = [r for r in pending if words and all(p in when_norm(r["texto"]) for p in words)]
        if not words and len(pending) == 1:
            match = pending
    if len(match) == 1:
        delete_reminder(match[0]["id"])
        return f"Lembrete \"{match[0]['texto']}\" cancelado."
    if len(match) > 1:
        for r in match:
            delete_reminder(r["id"])
        return f"Cancelei {len(match)} lembretes."
    return "Qual lembrete, senhor? " + _list_reply()


async def handle_voice(message: str, norm: str, words: int, name: str) -> Optional[str]:
    # Checar se pede lista de lembretes
    if any(q in norm for q in ("quais sao meus lembretes", "meus lembretes", "lista de lembretes", "ver lembretes",
                               "quais lembretes", "tenho algum lembrete", "tenho lembrete")):
        return _list_reply()

    # Apagar lembretes (todos ou um só)
    if _CANCEL.search(norm) and "lembrete" in norm:
        return _cancel_reply(norm)

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
        data_hora, texto, recorrencia, dias = _parse_datetime(norm)
        if data_hora:
            # Tira o pedido ("me lembra", "jarvis", "por favor") e os conectores que sobram nas pontas
            texto = re.sub(r"\b(?:jarvis|por\s+favor|me\s+lembre|me\s+lembra|lembre\s+me|criar|crie|cria|agendar|agende|"
                           r"um|novo|lembrete)\b", " ", texto)
            texto = re.sub(r"\s+", " ", texto).strip()
            texto = re.sub(r"^(?:(?:de|que|para|pra|em|sobre|do|da)\s+)+", "", texto)
            texto = re.sub(r"(?:\s+(?:de|que|para|pra|em|e|no|na))+$", "", texto).strip()
            if not texto:
                texto = "compromisso agendado"
            rem = add_reminder(texto, data_hora, recorrencia=recorrencia, dias=dias)
            return f"Combinado. Vou te lembrar {_describe(rem)}: {texto}."

    return None

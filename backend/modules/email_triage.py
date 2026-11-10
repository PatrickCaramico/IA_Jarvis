"""V4.3: triagem de e-mail para o briefing (IMAP, somente leitura).

Lê só os cabeçalhos (remetente, assunto, data) das últimas horas com BODY.PEEK, então nada é
marcado como lido. A senha fica no .env (EMAIL_IMAP_PASSWORD) e nunca vai para a tela nem para o log.
"""
import email
import imaplib
import logging
import re
import unicodedata
from datetime import datetime, timedelta
from email.header import decode_header, make_header
from email.utils import parseaddr

from config import settings

log = logging.getLogger("jarvis.email_triage")

MAX_HEADERS = 60  # limite de mensagens lidas por briefing

# Assuntos que pedem uma ação sua (pagamento, prazo, confirmação, segurança)
_ACTION_WORDS = (
    "fatura", "boleto", "pagamento", "vencimento", "vence", "prazo", "urgente", "acao necessaria",
    "confirme", "confirmar", "verifique", "assinatura", "renovacao", "pendente", "atrasad",
    "seguranca", "senha", "acesso", "codigo", "aprovacao", "responder", "convite",
)
# Remetentes automáticos que quase nunca pedem ação (promoções, redes sociais)
_NOISE_WORDS = ("newsletter", "promo", "oferta", "desconto", "noreply-marketing", "no-reply@marketing")


def configured() -> bool:
    return bool(settings.EMAIL_IMAP_HOST and settings.EMAIL_IMAP_USER and settings.EMAIL_IMAP_PASSWORD)


def _decode(value: str) -> str:
    try:
        return str(make_header(decode_header(value or ""))).strip()
    except Exception:  # noqa: BLE001 - cabeçalho malformado
        return (value or "").strip()


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFD", (text or "").lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _sender_name(raw_from: str) -> str:
    name, addr = parseaddr(_decode(raw_from))
    if name:
        return name.strip('"')
    domain = addr.split("@")[-1] if "@" in addr else addr
    return domain.split(".")[0].capitalize() if domain else "Remetente"


def classify(sender: str, subject: str) -> bool:
    """True quando o e-mail parece exigir uma ação sua."""
    text = _norm(f"{sender} {subject}")
    if any(w in text for w in _NOISE_WORDS):
        return False
    return any(w in text for w in _ACTION_WORDS)


def summarize(headers: list[dict]) -> dict:
    """Monta a triagem a partir de cabeçalhos já lidos: {received, to_act, items}."""
    action = [h for h in headers if classify(h["sender"], h["subject"])]
    action.sort(key=lambda h: h.get("date") or "", reverse=True)
    items = [
        {"sender": h["sender"], "summary": re.sub(r"\s+", " ", h["subject"])[:110] or "(sem assunto)"}
        for h in action
    ]
    return {"received": len(headers), "to_act": len(action), "items": items}


def fetch_recent_headers() -> list[dict]:
    """Cabeçalhos da caixa de entrada nas últimas EMAIL_LOOKBACK_HOURS horas."""
    since = (datetime.now() - timedelta(hours=settings.EMAIL_LOOKBACK_HOURS)).strftime("%d-%b-%Y")
    conn = imaplib.IMAP4_SSL(settings.EMAIL_IMAP_HOST, timeout=12)
    try:
        conn.login(settings.EMAIL_IMAP_USER, settings.EMAIL_IMAP_PASSWORD)
        conn.select("INBOX", readonly=True)
        status, data = conn.search(None, "SINCE", since)
        if status != "OK" or not data or not data[0]:
            return []
        ids = data[0].split()[-MAX_HEADERS:]
        status, rows = conn.fetch(b",".join(ids), "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
        if status != "OK":
            return []
        headers = []
        for row in rows:
            if not isinstance(row, tuple):
                continue
            msg = email.message_from_bytes(row[1])
            headers.append({
                "sender": _sender_name(msg.get("From", "")),
                "subject": _decode(msg.get("Subject", "")),
                "date": msg.get("Date", ""),
            })
        return headers
    finally:
        try:
            conn.logout()
        except Exception:  # noqa: BLE001
            pass


def triage() -> dict:
    """Triagem pronta para o card: {connected, received, to_act, items, error?}."""
    if not configured():
        return {"connected": False, "received": 0, "to_act": 0, "items": []}
    try:
        return {"connected": True, **summarize(fetch_recent_headers())}
    except (imaplib.IMAP4.error, OSError) as exc:
        log.warning("Falha na triagem de e-mail: %s", type(exc).__name__)
        return {"connected": True, "received": 0, "to_act": 0, "items": [], "error": "Não consegui acessar a caixa de entrada."}

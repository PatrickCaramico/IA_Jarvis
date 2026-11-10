"""V4.5: mensagens no WhatsApp com a sua confirmação.

- "manda uma mensagem no whatsapp para a Ana dizendo que eu chego às 8"
- "whatsapp para o João: bom dia!"
- "salva o contato Ana 11 99999-8888" (contatos ficam em data/contatos.json, só neste PC)

O JARVIS repete o que vai mandar e pergunta. No "sim", abre o WhatsApp do PC (aplicativo ou web) com a
conversa e o texto já preenchidos; quem toca em enviar é você. Ele nunca envia sozinho.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
import webbrowser
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from config import settings

CONTACTS_PATH: Path = settings.DATA_DIR / "contatos.json"

_SEND_RE = re.compile(
    r"^(?:jarvis\s+)?(?:manda|mande|envia|envie|escreve|escreva)?\s*(?:uma\s+)?(?:mensagem|msg|zap)?\s*"
    r"(?:no|pelo|por)?\s*(?:whatsapp|whats|zap)\s+(?:para|pra|pro)\s+(?:a\s+|o\s+)?(.+?)\s*(?::|dizendo(?: que)?|falando(?: que)?|com o texto)\s+(.+)$",
    re.IGNORECASE,
)
_SAVE_RE = re.compile(r"^(?:jarvis\s+)?(?:salva|salve|grava|grave|adiciona|adicione)\s+(?:o\s+)?contato\s+(.+?)\s+([+\d][\d\s().-]{7,})$",
                      re.IGNORECASE)


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", text).strip()


def _load() -> dict[str, str]:
    try:
        data = json.loads(CONTACTS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_contact(name: str, phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if len(digits) in (10, 11):  # número brasileiro sem o 55
        digits = "55" + digits
    data = _load()
    data[name.strip().title()] = digits
    CONTACTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONTACTS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return digits


def find_contact(name: str) -> Optional[tuple[str, str]]:
    wanted = _norm(name)
    for saved, phone in _load().items():
        if _norm(saved) == wanted or _norm(saved).split(" ")[0] == wanted:
            return saved, phone
    return None


def parse(original: str) -> Optional[dict]:
    m = _SEND_RE.match(original.strip())
    if not m:
        return None
    who, text = m.group(1).strip(" ,"), m.group(2).strip()
    if not who or not text:
        return None
    contact = find_contact(who)
    return {"who": contact[0] if contact else who.title(), "phone": contact[1] if contact else "", "text": text}


def open_chat(data: dict) -> str:
    """Abre o WhatsApp com o texto preenchido (você toca em enviar)."""
    text = quote(data["text"])
    phone = data.get("phone", "")
    app_url = f"whatsapp://send?phone={phone}&text={text}" if phone else f"whatsapp://send?text={text}"
    web_url = f"https://web.whatsapp.com/send?phone={phone}&text={text}" if phone else f"https://web.whatsapp.com/send?text={text}"
    try:
        os.startfile(app_url)  # type: ignore[attr-defined]  # WhatsApp para Windows
    except (OSError, AttributeError):
        webbrowser.open(web_url)
    if phone:
        return f"Abri a conversa com {data['who']} com a mensagem pronta, senhor. É só tocar em enviar."
    return (f"Abri o WhatsApp com a mensagem pronta, senhor. Escolha {data['who']} na lista e toque em enviar. "
            f"Dica: diga 'salva o contato {data['who']}' com o número para eu abrir direto da próxima vez.")


def handle_voice(original: str) -> Optional[str]:
    from core import confirm

    m = _SAVE_RE.match(original.strip())
    if m:
        digits = save_contact(m.group(1), m.group(2))
        return f"Contato {m.group(1).strip().title()} salvo, senhor (+{digits})."
    data = parse(original)
    if not data:
        return None
    confirm.offer("whatsapp", data)
    return f"Vou abrir o WhatsApp para {data['who']} com a mensagem: \"{data['text']}\". Posso abrir? Diga sim."

"""V6.5.11: "abra o YouTube" pergunta em qual navegador abrir.

Preferência "site_browser":
  "ask"      pergunta sempre ("Em qual navegador, senhor? Chrome ou Edge?") e mostra a lista na tela (padrão);
  "default"  usa o navegador padrão do Windows, sem perguntar;
  "chrome" | "edge" | "firefox" | "brave" | "opera"  sempre aquele.
Responder: falando ("no Chrome", "Edge", "o padrão", "sempre no Chrome") ou tocando na lista.
Com um navegador só instalado, não pergunta. O pedido pendente vale por 2 minutos.
"""
from __future__ import annotations

import re
import time

from modules.quick_replies import _norm

NAMES = {"chrome": "Chrome", "edge": "Edge", "firefox": "Firefox", "brave": "Brave", "opera": "Opera"}
_SAY = {  # como a pessoa fala -> id
    "chrome": ("chrome", "google chrome", "crome", "cromo"),
    "edge": ("edge", "microsoft edge", "edje", "ed"),
    "firefox": ("firefox", "fire fox", "mozilla", "raposa"),
    "brave": ("brave", "breive"),
    "opera": ("opera", "opera gx"),
}
_DEFAULT_WORDS = ("padrao", "qualquer", "tanto faz", "o normal", "o de sempre", "voce escolhe")
_CANCEL_WORDS = ("cancela", "cancelar", "deixa", "esquece", "nao precisa", "nenhum")
TTL_SECONDS = 120

_pending: dict = {"urls": [], "at": 0.0, "new": False}


def installed() -> list[dict]:
    from modules import browser_window

    return [{"id": k, "name": NAMES[k]} for k in NAMES if browser_window.exe_for(k)]


def mode() -> str:
    from modules import prefs

    return str(prefs.get_all().get("site_browser") or "ask")


def should_ask() -> bool:
    return mode() == "ask" and len(installed()) > 1


def request(url: str) -> None:
    """Guarda a URL até a pessoa escolher o navegador."""
    if time.time() - _pending["at"] > TTL_SECONDS:
        _pending["urls"] = []
    if url not in _pending["urls"]:
        _pending["urls"].append(url)
    _pending["at"] = time.time()
    _pending["new"] = True


def pending() -> bool:
    if _pending["urls"] and time.time() - _pending["at"] > TTL_SECONDS:
        clear()
    return bool(_pending["urls"])


def take_new() -> bool:
    """Este turno acabou de pedir para abrir algo (e a resposta deve virar a pergunta)?"""
    was = _pending["new"]
    _pending["new"] = False
    return was and pending()


def clear() -> None:
    _pending.update(urls=[], at=0.0, new=False)


def question() -> str:
    names = [b["name"] for b in installed()]
    listed = ", ".join(names[:-1]) + f" ou {names[-1]}" if len(names) > 1 else (names[0] if names else "")
    return f"Em qual navegador, senhor? {listed}?"


def parse(text: str) -> tuple[str | None, bool]:
    """("chrome" | "default" | "cancel" | None, lembrar?) a partir da resposta falada."""
    norm = _norm(text)
    remember = bool(re.search(r"\b(?:sempre|daqui pra frente|de agora em diante|lembra|lembre)\b", norm))
    if any(w in norm for w in _CANCEL_WORDS):
        return "cancel", False
    for bid, words in _SAY.items():
        for w in words:
            if re.search(rf"\b{re.escape(w)}\b", norm):
                return bid, remember
    if any(w in norm for w in _DEFAULT_WORDS):
        return "default", remember
    return None, False


def choose(browser: str, remember: bool = False) -> str:
    """Abre o que estava esperando no navegador escolhido. Devolve a frase da resposta."""
    from modules import browser_window, prefs

    urls = list(_pending["urls"])
    clear()
    if browser == "cancel":
        return "Tudo bem, não abri nada."
    if browser != "default" and not browser_window.exe_for(browser):
        return f"Não encontrei o {NAMES.get(browser, browser)} neste computador."
    if remember:
        prefs.update(site_browser=browser)
    for url in urls:
        browser_window.open_url(url, browser=None if browser == "default" else browser, force=True)
    where = "no navegador padrão" if browser == "default" else f"no {NAMES.get(browser, browser)}"
    tail = " Vou usar sempre esse daqui pra frente." if remember else ""
    if not urls:
        return f"Certo, senhor.{tail}"
    return f"Abrindo {where}, senhor.{tail}"

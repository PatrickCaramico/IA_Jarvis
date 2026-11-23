"""V9.0: conversa com o Chrome (ou Edge) do PC pelo protocolo de depuração (CDP), só em 127.0.0.1.

O JARVIS abre o navegador com um perfil próprio (data/chrome_jarvis) e a porta de depuração ligada: o Chrome não
aceita essa porta no perfil padrão. O senhor entra uma vez nos sites nesse perfil e ele fica guardado.
Tudo aqui é síncrono e com prazo curto; as skills rodam numa thread (o motor cuida disso).
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import requests

from config import settings

log = logging.getLogger("jarvis.skills.navegador")

HOST = "127.0.0.1"
PORT = 9222
HTTP_TIMEOUT_S = 2.0
EVAL_TIMEOUT_S = 10.0
PROFILE_DIR = settings.DATA_DIR / "chrome_jarvis"


class BrowserError(RuntimeError):
    """Falha falável: a mensagem já é a frase para o usuário."""


def _url(path: str) -> str:
    return f"http://{HOST}:{PORT}{path}"


def available() -> bool:
    try:
        return requests.get(_url("/json/version"), timeout=HTTP_TIMEOUT_S).ok
    except requests.RequestException:
        return False


def tabs() -> list[dict]:
    """As abas abertas (mais recente primeiro), só páginas."""
    try:
        data = requests.get(_url("/json/list"), timeout=HTTP_TIMEOUT_S).json()
    except (requests.RequestException, ValueError) as exc:
        raise BrowserError("O navegador do JARVIS não está aberto, senhor.") from exc
    return [t for t in data if t.get("type") == "page"]


def web_tabs() -> list[dict]:
    return [t for t in tabs() if str(t.get("url", "")).startswith(("http://", "https://"))]


def new_tab(url: str) -> None:
    r = requests.put(_url("/json/new?" + quote(url, safe=":/?&=#%+@,;~")), timeout=HTTP_TIMEOUT_S)
    if not r.ok:  # Chrome antigo só aceita GET
        requests.get(_url("/json/new?" + quote(url, safe=":/?&=#%+@,;~")), timeout=HTTP_TIMEOUT_S).raise_for_status()


def close_tab(tab_id: str) -> None:
    requests.get(_url(f"/json/close/{quote(tab_id)}"), timeout=HTTP_TIMEOUT_S)


def activate(tab_id: str) -> None:
    requests.get(_url(f"/json/activate/{quote(tab_id)}"), timeout=HTTP_TIMEOUT_S)


def find_browser() -> Optional[str]:
    roots = [os.environ.get(k, "") for k in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")]
    rels = [r"Google\Chrome\Application\chrome.exe", r"Microsoft\Edge\Application\msedge.exe"]
    for rel in rels:  # Chrome primeiro, Edge como reserva (os dois falam CDP)
        for root in roots:
            if root and Path(root, rel).exists():
                return str(Path(root, rel))
    return None


def launch(urls: list[str]) -> None:
    """Abre o navegador do JARVIS (perfil próprio, porta de depuração) e espera a porta responder."""
    exe = find_browser()
    if not exe:
        raise BrowserError("Não achei o Chrome nem o Edge instalados, senhor.")
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    args = [exe, f"--remote-debugging-port={PORT}", f"--user-data-dir={PROFILE_DIR}", "--no-first-run",
            "--no-default-browser-check", *urls]
    subprocess.Popen(args, close_fds=True, creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))  # noqa: S603
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if available():
            return
        time.sleep(0.4)
    raise BrowserError("O navegador abriu, mas não respondeu a tempo, senhor.")


def open_urls(urls: list[str]) -> None:
    """Abre as páginas em abas novas; liga o navegador do JARVIS se precisar."""
    if not urls:
        return
    if not available():
        launch(urls)
        return
    for u in urls:
        new_tab(u)


def evaluate(tab: dict, expression: str, timeout: float = EVAL_TIMEOUT_S):
    """Roda JavaScript na aba e devolve o valor (Runtime.evaluate)."""
    from websockets.sync.client import connect

    ws_url = tab.get("webSocketDebuggerUrl")
    if not ws_url:
        raise BrowserError("Essa aba está ocupada por outra ferramenta de depuração, senhor.")
    with connect(ws_url, open_timeout=3, close_timeout=1, max_size=16 * 1024 * 1024) as ws:
        ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate",
                            "params": {"expression": expression, "returnByValue": True, "awaitPromise": True}}))
        deadline = time.monotonic() + timeout
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                raise TimeoutError("Runtime.evaluate sem resposta")
            msg = json.loads(ws.recv(timeout=left))
            if msg.get("id") != 1:
                continue
            res = msg.get("result", {})
            if "exceptionDetails" in res:
                raise BrowserError("A página não aceitou o passo, senhor.")
            return res.get("result", {}).get("value")

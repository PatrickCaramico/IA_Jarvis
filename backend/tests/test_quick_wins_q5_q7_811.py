"""V8.11: Q5 (buscadores em corrida), Q6 (abas sem PowerShell) e Q7 (mensagens honestas da IA)."""
import asyncio
import time
from types import SimpleNamespace

import pytest

from modules import tools
from services import llm_orchestrator as llm


def run(coro):
    return asyncio.run(coro)


# ------------------------------------------------------------------ Q5
def test_fastest_engine_wins(monkeypatch):
    def slow_google(q):
        time.sleep(2)
        return ["google"], []

    monkeypatch.setattr(tools, "_search_google", slow_google)
    monkeypatch.setattr(tools, "_search_bing", lambda q: (["bing diz isto"], [{"url": "https://b"}]))
    monkeypatch.setattr(tools, "_search_duckduckgo", lambda q: (_ for _ in ()).throw(RuntimeError("fora")))
    started = time.monotonic()
    assert tools._fetch_web_results("teste") == (["bing diz isto"], [{"url": "https://b"}])
    assert time.monotonic() - started < 1.5  # antes: esperava o Google


def test_empty_and_broken_engines_give_nothing(monkeypatch):
    monkeypatch.setattr(tools, "_search_google", lambda q: ([], []))
    monkeypatch.setattr(tools, "_search_bing", lambda q: (_ for _ in ()).throw(RuntimeError("x")))
    monkeypatch.setattr(tools, "_search_duckduckgo", lambda q: ([], []))
    assert tools._fetch_web_results("teste") == ([], [])


def test_race_has_a_ceiling(monkeypatch):
    def stuck(q):
        time.sleep(3)
        return ["tarde"], []

    for name in ("_search_google", "_search_bing", "_search_duckduckgo"):
        monkeypatch.setattr(tools, name, stuck)
    started = time.monotonic()
    assert tools._fetch_web_results("teste", timeout=0.4) == ([], [])
    assert time.monotonic() - started < 1.5


# ------------------------------------------------------------------ Q6
class Desk:
    def __init__(self, windows, fg, focus_ok=True):
        self._w, self.fg, self.focus_ok, self.keys, self.focused = windows, fg, focus_ok, [], []

    def windows(self):
        return self._w

    def foreground(self):
        return self.fg

    def focus_checked(self, hwnd, timeout=0.6):
        self.focused.append(hwnd)
        return self.focus_ok

    def send_combo(self, *keys):
        self.keys.append(keys)


def win(hwnd, process, title):
    return SimpleNamespace(hwnd=hwnd, process=process, title=title, minimized=False)


@pytest.fixture
def desk(monkeypatch):
    from skills.workspace import desktop

    d = Desk([win(1, "chrome.exe", "JARVIS - Central"), win(2, "msedge.exe", "Notícias - Edge"),
              win(3, "Code.exe", "main.py")], fg=1)
    monkeypatch.setattr(desktop, "get_desktop", lambda: d)
    return d


def test_tab_keys_go_to_a_real_browser_window_not_the_central(desk):
    assert run(tools._h_browser("proxima aba", "proxima aba", 2, "")) == "Mudei para a próxima aba, senhor."
    assert desk.focused == [2] and desk.keys == [("ctrl", "tab")]
    run(tools._h_browser("fechar aba", "fechar aba", 2, ""))
    assert desk.keys[-1] == ("ctrl", "w")


def test_front_browser_is_preferred(desk):
    desk.fg = 2
    desk._w.insert(0, win(4, "firefox.exe", "Outra coisa"))
    run(tools._h_browser("reabrir aba", "reabrir aba no navegador", 4, ""))
    assert desk.focused == [2] and desk.keys == [("ctrl", "shift", "t")]


def test_never_closes_the_central_tab(desk):
    desk._w = [win(1, "chrome.exe", "JARVIS - Central")]
    reply = run(tools._h_browser("fechar aba", "fechar aba", 2, ""))
    assert "central do JARVIS" in reply and desk.keys == []


def test_no_keys_when_the_browser_does_not_come_forward(desk):
    desk.focus_ok = False
    reply = run(tools._h_browser("fechar aba", "fechar aba", 2, ""))
    assert "Clique nele" in reply and desk.keys == []


def test_no_browser(desk):
    desk._w = [win(3, "Code.exe", "main.py")]
    assert "Não encontrei uma janela do navegador" in run(tools._h_browser("abre uma nova aba", "abre uma nova aba", 4, ""))


# ------------------------------------------------------------------ Q7
@pytest.mark.parametrize("exc,expected", [
    (RuntimeError("GEMINI_API_KEY não configurada no arquivo .env."), "Configurações, na aba Cérebro"),
    (RuntimeError("Error code: 401 - invalid_api_key"), "chave foi recusada"),
    (ConnectionError("getaddrinfo failed"), "internet caiu"),
    (RuntimeError("finish_reason SAFETY blocked"), "se recusou"),
    (ValueError("algo estranho"), "o detalhe ficou no log"),
])
def test_friendly_errors(exc, expected):
    text = llm.friendly_error(exc)
    assert expected in text and "Error code" not in text and "getaddrinfo" not in text


def test_empty_answer_is_admitted(monkeypatch):
    monkeypatch.setattr(llm, "_call_llm", lambda *a, **k: "")
    monkeypatch.setattr(llm, "_last_grounding_data", {"queries": [], "sources": []})
    text = run(llm.generate_jarvis_response("explique os buracos negros"))
    assert "não devolveu resposta" in text and "concluída" not in text


def test_chat_explains_the_failure_instead_of_error_500(isolated_data, monkeypatch):
    from fastapi.testclient import TestClient

    import main
    from core import session, speech
    from modules import access

    async def fake_speak(text, release_busy=True, idle_after=True):
        session.busy = False

    async def broken(*a, **k):
        raise ConnectionError("Connection refused")

    monkeypatch.setattr(speech, "speak", fake_speak)
    monkeypatch.setattr(speech, "filler_loop", lambda stop: asyncio.sleep(0))
    monkeypatch.setattr("core.turns.generate_jarvis_response", broken)
    access.reset_for_tests(access.UNLOCKED)
    session.busy = False
    try:
        r = TestClient(main.app).post("/api/chat", json={"message": "me explique a teoria das cordas em detalhes"})
    finally:
        access.reset_for_tests(access.LOCKED)
    assert r.status_code == 200
    assert "internet caiu" in r.json()["response"]

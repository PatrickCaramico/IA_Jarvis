"""V9.0: macros de navegador (sessões, abas, macros de passos, resumo da página). O Chrome é falso."""
import asyncio
import json

import pytest

import skills.navegador as nav
from core.skills import registry, router
from modules.quick_replies import _norm


def match(phrase):
    return registry.match(_norm(phrase), phrase)


def ask(phrase):
    return asyncio.run(router.try_fast_path(phrase))


def test_phrases(real_skills):
    cases = [
        ("salva as abas como sessão trabalho", "sessao_navegador", {"acao": "salvar", "nome": "trabalho"}),
        ("abre a sessão trabalho", "sessao_navegador", {"acao": "abrir", "nome": "trabalho"}),
        ("quais sessões do navegador eu tenho?", "sessao_navegador", {"acao": "listar"}),
        ("fecha as abas do youtube", "abas_navegador", {"acao": "fechar", "site": "youtube"}),
        ("vai para a aba do gmail", "abas_navegador", {"acao": "ir", "site": "gmail"}),
        ("quantas abas estão abertas?", "abas_navegador", {"acao": "contar"}),
        ("reabre as abas que você fechou", "abas_navegador", {"acao": "reabrir"}),
        ("roda a macro bater ponto", "macro_navegador", {"nome": "bater ponto"}),
        ("quais macros eu tenho?", "macro_navegador", {}),
        ("resume essa página", "resumir_pagina", {}),
    ]
    for phrase, name, args in cases:
        hit = match(phrase)
        assert hit and hit[0].name == name and hit[1] == args, (phrase, hit and (hit[0].name, hit[1]))
    for phrase in ("abre o youtube", "abre o chrome", "fecha o chrome", "resume o que eu copiei", "abre a pasta downloads"):
        hit = match(phrase)
        assert hit is None or hit[0].name not in {"sessao_navegador", "abas_navegador", "macro_navegador", "resumir_pagina"}, phrase


class FakeChrome:
    def __init__(self):
        self.open = [{"id": "1", "type": "page", "url": "https://mail.google.com/", "title": "Gmail"},
                     {"id": "2", "type": "page", "url": "https://www.youtube.com/watch?v=x", "title": "Vídeo"},
                     {"id": "3", "type": "page", "url": "https://youtube.com/", "title": "YouTube"},
                     {"id": "4", "type": "page", "url": "chrome://newtab/", "title": "Nova guia"}]
        self.up = True
        self.opened, self.closed, self.activated, self.js = [], [], [], []
        self.js_result = True

    def install(self, mp):
        mp.setattr(nav.cdp, "available", lambda: self.up)
        mp.setattr(nav.cdp, "tabs", lambda: list(self.open))
        mp.setattr(nav.cdp, "open_urls", lambda urls: self.opened.extend(urls))
        mp.setattr(nav.cdp, "close_tab", lambda i: self.closed.append(i))
        mp.setattr(nav.cdp, "activate", lambda i: self.activated.append(i))

        def evaluate(tab, expr, timeout=10):
            self.js.append(expr)
            if expr == nav._JS_READY:
                return "complete"
            return self.js_result

        mp.setattr(nav.cdp, "evaluate", evaluate)
        mp.setattr(nav.time, "sleep", lambda s: None)


@pytest.fixture
def chrome(monkeypatch):
    fake = FakeChrome()
    fake.install(monkeypatch)
    return fake


def test_sessions_save_open_list(real_skills, chrome):
    assert ask("salva as abas como sessão trabalho").speech == "Sessão trabalho guardada com 3 sites, senhor."
    assert nav._load()["sessoes"]["trabalho"]["urls"][0] == "https://youtube.com/"  # ordem de abertura
    assert ask("abre a sessão trabalho").speech == "Abrindo a sessão trabalho: 3 sites, senhor."
    assert "https://mail.google.com/" in chrome.opened and not any(u.startswith("chrome://") for u in chrome.opened)
    assert ask("quais sessões do navegador eu tenho?").speech == "O senhor tem 1 sessão: trabalho."
    assert "Não tenho a sessão estudo" in ask("abre a sessão estudo").speech


def test_tabs_close_reopen_go_count(real_skills, chrome):
    assert ask("quantas abas estão abertas?").speech.startswith("4 abas abertas, senhor. De mail.google.com, youtube.com")
    assert ask("vai para a aba do gmail").speech == "Pronto, na aba de gmail, senhor."
    assert chrome.activated == ["1"]
    assert ask("fecha as abas do youtube").speech.startswith("Fechei 2 abas de youtube")
    assert chrome.closed == ["2", "3"]
    assert ask("reabre as abas que você fechou").speech == "Reabri 2 abas, senhor."
    assert chrome.opened == ["https://www.youtube.com/watch?v=x", "https://youtube.com/"]
    assert "Não tenho abas fechadas" in ask("reabre as abas que você fechou").speech
    assert ask("fecha as abas do twitter").speech == "Não há aba de twitter aberta, senhor."


def test_browser_closed_is_honest(real_skills, chrome):
    chrome.up = False
    assert ask("quantas abas estão abertas?").speech.startswith("O navegador do JARVIS não está aberto, senhor.")

    def broken():
        raise nav.cdp.BrowserError("O navegador do JARVIS não está aberto, senhor.")

    import skills.navegador.cdp as cdp_mod
    cdp_mod_tabs = cdp_mod.web_tabs
    try:
        cdp_mod.web_tabs = broken
        assert ask("salva as abas como sessão casa").speech == "O navegador do JARVIS não está aberto, senhor."
    finally:
        cdp_mod.web_tabs = cdp_mod_tabs


def test_macro_runs_steps_safely(real_skills, chrome):
    data = nav._load()
    data["macros"]["bater ponto"] = {"passos": [{"abrir": "https://mail.google.com/x"}, {"esperar": 1},
                                                {"digitar": "#user", "texto": "pa'trick\"</script>"}, {"clicar": "button.ok"}]}
    data["macros"]["ruim"] = {"passos": [{"abrir": "javascript:alert(1)"}]}
    nav._save(data)
    assert ask("roda a macro bater ponto").speech == "Macro bater ponto concluída, senhor: 4 passos."
    assert chrome.opened == ["https://mail.google.com/x"]
    typed = [j for j in chrome.js if "dispatchEvent" in j][0]
    assert json.dumps("pa'trick\"</script>") in typed  # texto vai como literal JSON, nunca como código
    assert "A macro ruim tem um passo inválido" in ask("roda a macro ruim").speech
    chrome.js_result = False
    assert "não achei o elemento" in ask("roda a macro bater ponto").speech
    assert ask("quais macros eu tenho?").speech == "Macros do navegador: bater ponto, ruim."


def test_validate_steps_rejects_bad_input():
    for bad in ([], [{"abrir": "file:///c:/x"}], [{"esperar": 60}], [{"digitar": "#a"}], [{"rodar": "cmd"}], [1]):
        with pytest.raises(ValueError):
            nav.validate_steps(bad)
    assert nav.validate_steps(nav.EXEMPLO_MACRO["passos"])[0] == {"abrir": "https://exemplo.com/login"}


def test_summarize_page(real_skills, chrome, monkeypatch):
    from services import llm_orchestrator as llm

    page = json.dumps({"t": "Notícia", "x": "Texto longo da notícia sobre o tempo em Maceió. " * 5})
    monkeypatch.setattr(nav.cdp, "evaluate", lambda tab, expr, timeout=10: page)
    seen = {}
    monkeypatch.setattr(llm, "ask_text", lambda prompt, max_tokens=0: seen.setdefault("p", prompt) and "Vai chover em Maceió.")
    res = ask("resume essa página")
    assert res.speech == "Vai chover em Maceió." and "Maceió" in seen["p"]
    assert res.cards[0]["data"]["source"] == "mail.google.com"

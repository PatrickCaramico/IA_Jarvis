"""Macros de navegador (V9.0): o JARVIS mexe no Chrome do PC, sem API externa (protocolo de depuração local).

Frases:
- "salva as abas como sessão trabalho"   -> guarda os sites abertos com um nome
- "abre a sessão trabalho"               -> reabre todos de uma vez (liga o navegador se precisar)
- "quais sessões do navegador eu tenho?"
- "quantas abas estão abertas?", "vai para a aba do gmail", "fecha as abas do youtube"
- "reabre as abas que você fechou"       -> o que o JARVIS fechou fica guardado
- "roda a macro bater ponto"             -> passos gravados em data/navegador.json (abrir, esperar, clicar, digitar)
- "resume essa página"                   -> a IA resume a aba aberta
O navegador do JARVIS usa um perfil próprio (data/chrome_jarvis); entre nos sites uma vez nele.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from config import settings
from core import safe_io
from core.skills import Permission, SkillContext, SkillResult, skill

from . import cdp

log = logging.getLogger("jarvis.skills.navegador")

_PATH = settings.DATA_DIR / "navegador.json"
MAX_SESSIONS = 30
MAX_STEPS = 30
MAX_WAIT_S = 10
MAX_PAGE_CHARS = 8000
EXEMPLO_MACRO = {"passos": [{"abrir": "https://exemplo.com/login"}, {"esperar": 2},
                            {"digitar": "#usuario", "texto": "meu.usuario"}, {"clicar": "button[type=submit]"}]}


# ------------------------------------------------------------------ dados
def _load() -> dict:
    data = safe_io.read_json(_PATH) if _PATH.exists() else {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("sessoes", {})
    data.setdefault("macros", {})
    data.setdefault("fechadas", [])
    return data


def _save(data: dict) -> None:
    safe_io.write_json(_PATH, data)


def _key(name: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s-]", "", (name or "").lower())).strip()[:40]


def _web(url: str) -> bool:
    return isinstance(url, str) and url.startswith(("http://", "https://")) and len(url) < 2048


def host_of(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _speak_error(exc: Exception) -> SkillResult:
    if isinstance(exc, cdp.BrowserError):
        return SkillResult(ok=False, speech=str(exc))
    log.exception("Navegador: falha")
    return SkillResult(ok=False, speech="Não consegui falar com o navegador agora, senhor. O detalhe ficou no log.")


def _closed_hint() -> str:
    return " Peça para eu abrir uma sessão ou rodar uma macro que eu ligo o navegador do JARVIS."


# ------------------------------------------------------------------ sessões
_SESSION_PATTERNS = [
    (re.compile(r"\b(?:salva|salve|guarda|guarde|grava|grave)\s+(?:as\s+|essas\s+|minhas\s+)?abas(?:\s+(?:abertas|do navegador))?\s+"
                r"(?:como|na|com o nome)\s+(?:a\s+)?(?:sessao\s+|rotina\s+)?(?P<nome>[\w\s-]{2,40})$"), "salvar"),
    (re.compile(r"\b(?:abre|abra|abrir|carrega|carregue|restaura|restaure)\s+(?:a\s+|minha\s+)?sessao\s+(?:de\s+|do\s+|da\s+)?"
                r"(?P<nome>[\w\s-]{2,40})$"), "abrir"),
    (re.compile(r"\b(?:quais|que)\s+sessoes(?:\s+do navegador)?(?:\s+eu tenho|\s+tem|\s+existem)?\??$"), "listar"),
    (re.compile(r"\b(?:lista|mostra)\s+(?:as\s+|minhas\s+)?sessoes(?:\s+do navegador)?$"), "listar"),
]


def _parse_session(norm: str, _original: str) -> Optional[dict]:
    for rx, acao in _SESSION_PATTERNS:
        m = rx.search(norm)
        if m:
            out = {"acao": acao}
            if "nome" in rx.groupindex:
                out["nome"] = m.group("nome").strip()
            return out
    return None


@skill(
    name="sessao_navegador",
    title="usar as sessões do navegador",
    description=("Sessões de abas do Chrome do PC: salvar os sites abertos com um nome (acao salvar), reabrir todos "
                 "(acao abrir) ou listar as sessões guardadas (acao listar)."),
    permission=Permission.ACTION,
    allow_remote=False,
    timeout=25,
    parse=_parse_session,
    params={"type": "object", "required": ["acao"], "properties": {
        "acao": {"type": "string", "enum": ["salvar", "abrir", "listar"]},
        "nome": {"type": "string", "description": "Nome da sessão (ex.: trabalho, estudo)."}}},
    examples=["salva as abas como sessão trabalho", "abre a sessão trabalho"],
)
def sessao_navegador(ctx: SkillContext, acao: str, nome: str = "") -> SkillResult:
    data = _load()
    sessions = data["sessoes"]
    if acao == "listar":
        if not sessions:
            return SkillResult(speech="Ainda não há sessões guardadas, senhor. Diga, por exemplo: salva as abas como sessão trabalho.")
        rows = [{"label": k, "value": f"{len(v.get('urls', []))} sites"} for k, v in sorted(sessions.items())]
        names = ", ".join(sorted(sessions))
        return SkillResult(speech=f"O senhor tem {len(sessions)} {'sessão' if len(sessions) == 1 else 'sessões'}: {names}.",
                           cards=[{"type": "skill", "data": {"tag": "SESSÕES DO NAVEGADOR", "source": "Chrome do JARVIS", "rows": rows}}])
    key = _key(nome)
    if not key:
        return SkillResult(ok=False, speech="Qual o nome da sessão, senhor?")
    try:
        if acao == "salvar":
            urls = [t["url"] for t in cdp.web_tabs()][::-1]  # na ordem em que foram abertas
            if not urls:
                return SkillResult(ok=False, speech="Não há sites abertos no navegador do JARVIS para guardar, senhor.")
            if key not in sessions and len(sessions) >= MAX_SESSIONS:
                return SkillResult(ok=False, speech=f"Já são {MAX_SESSIONS} sessões, senhor. Apague alguma no arquivo antes.")
            sessions[key] = {"urls": urls[:40], "salva_em": datetime.now().isoformat(timespec="seconds")}
            _save(data)
            return SkillResult(speech=f"Sessão {key} guardada com {len(urls[:40])} sites, senhor.")
        sess = sessions.get(key)
        if not sess:
            return SkillResult(ok=False, speech=f"Não tenho a sessão {key}, senhor."
                               + (f" As que existem: {', '.join(sorted(sessions))}." if sessions else ""))
        urls = [u for u in sess.get("urls", []) if _web(u)]
        cdp.open_urls(urls)
        return SkillResult(speech=f"Abrindo a sessão {key}: {len(urls)} {'site' if len(urls) == 1 else 'sites'}, senhor.")
    except Exception as exc:  # noqa: BLE001 - vira frase honesta + log
        return _speak_error(exc)


# ------------------------------------------------------------------ abas
_SITE = r"(?:do|da|de|dos|das)\s+(?P<site>[\w.-]{2,40})"
_TAB_PATTERNS = [
    (re.compile(r"\b(?:fecha|feche|fechar)\s+(?:as|a|todas as)\s+abas?\s+" + _SITE + r"$"), "fechar"),
    (re.compile(r"\b(?:vai|va|muda|mude|troca|troque|volta|volte)\s+(?:para|pra|pro)\s+a\s+aba\s+" + _SITE + r"$"), "ir"),
    (re.compile(r"\bquantas abas(?:\s+(?:tem|tenho|estao|ha))?(?:\s+abertas)?(?:\s+no navegador)?\??$"), "contar"),
    (re.compile(r"\b(?:reabre|reabra|reabrir|volta|devolve)\s+(?:as\s+)?abas\s+(?:que\s+(?:voce\s+)?(?:fechou|fechei)|fechadas)$"), "reabrir"),
]


def _parse_tabs(norm: str, _original: str) -> Optional[dict]:
    for rx, acao in _TAB_PATTERNS:
        m = rx.search(norm)
        if m:
            out = {"acao": acao}
            if "site" in rx.groupindex:
                out["site"] = m.group("site")
            return out
    return None


def _matching(all_tabs: list[dict], word: str) -> list[dict]:
    w = word.lower().removeprefix("www.")
    return [t for t in all_tabs if w in host_of(t.get("url", "")) or w in str(t.get("title", "")).lower()]


@skill(
    name="abas_navegador",
    title="mexer nas abas do navegador",
    description=("Abas do Chrome do PC: contar (acao contar), ir para a aba de um site (acao ir), fechar as abas de um "
                 "site (acao fechar; ficam guardadas) ou reabrir as que o JARVIS fechou (acao reabrir)."),
    permission=Permission.ACTION,
    allow_remote=False,
    timeout=15,
    parse=_parse_tabs,
    params={"type": "object", "required": ["acao"], "properties": {
        "acao": {"type": "string", "enum": ["contar", "ir", "fechar", "reabrir"]},
        "site": {"type": "string", "description": "Parte do endereço ou do título (ex.: youtube, gmail)."}}},
    examples=["fecha as abas do youtube", "vai para a aba do gmail", "quantas abas estão abertas?"],
)
def abas_navegador(ctx: SkillContext, acao: str, site: str = "") -> SkillResult:
    try:
        if acao == "reabrir":
            data = _load()
            urls = [u for u in data["fechadas"] if _web(u)]
            if not urls:
                return SkillResult(ok=False, speech="Não tenho abas fechadas por mim para reabrir, senhor.")
            cdp.open_urls(urls)
            data["fechadas"] = []
            _save(data)
            return SkillResult(speech=f"Reabri {len(urls)} {'aba' if len(urls) == 1 else 'abas'}, senhor.")
        if not cdp.available():
            return SkillResult(ok=False, speech="O navegador do JARVIS não está aberto, senhor." + _closed_hint())
        all_tabs = cdp.tabs()
        if acao == "contar":
            n = len(all_tabs)
            sites = sorted({host_of(t.get("url", "")) for t in all_tabs if _web(t.get("url", ""))})
            return SkillResult(speech=f"{n} {'aba aberta' if n == 1 else 'abas abertas'}, senhor."
                               + (f" De {', '.join(sites[:5])}." if sites else ""))
        if not site:
            return SkillResult(ok=False, speech="De qual site, senhor?")
        found = _matching(all_tabs, site)
        if not found:
            return SkillResult(ok=False, speech=f"Não há aba de {site} aberta, senhor.")
        if acao == "ir":
            cdp.activate(found[0]["id"])
            return SkillResult(speech=f"Pronto, na aba de {site}, senhor.")
        data = _load()
        data["fechadas"] = ([t["url"] for t in found if _web(t.get("url", ""))] + data["fechadas"])[:40]
        _save(data)  # guarda antes de fechar: "reabre as abas que você fechou" devolve
        for t in found:
            cdp.close_tab(t["id"])
        return SkillResult(speech=f"Fechei {len(found)} {'aba' if len(found) == 1 else 'abas'} de {site}, senhor. "
                                  "Se quiser de volta, diga: reabre as abas que você fechou.")
    except Exception as exc:  # noqa: BLE001
        return _speak_error(exc)


# ------------------------------------------------------------------ macros de passos
_JS_CLICK = "(()=>{const e=document.querySelector(%s);if(!e)return false;e.scrollIntoView({block:'center'});e.click();return true})()"
_JS_TYPE = ("(()=>{const e=document.querySelector(%s);if(!e)return false;e.focus();"
            "const p=Object.getPrototypeOf(e),d=Object.getOwnPropertyDescriptor(p,'value');"
            "if(d&&d.set){d.set.call(e,%s)}else{e.value=%s}"
            "e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));return true})()")
_JS_READY = "document.readyState"


def validate_steps(steps) -> list[dict]:
    """Só os passos conhecidos e com valores do tipo certo (o arquivo é do usuário, mas nada vira comando)."""
    if not isinstance(steps, list) or not steps or len(steps) > MAX_STEPS:
        raise ValueError("a macro precisa de 1 a 30 passos")
    out = []
    for i, st in enumerate(steps, 1):
        if not isinstance(st, dict):
            raise ValueError(f"passo {i} inválido")
        if "abrir" in st and _web(st["abrir"]):
            out.append({"abrir": st["abrir"]})
        elif "esperar" in st and isinstance(st["esperar"], (int, float)) and 0 < st["esperar"] <= MAX_WAIT_S:
            out.append({"esperar": float(st["esperar"])})
        elif "clicar" in st and isinstance(st["clicar"], str) and 0 < len(st["clicar"]) <= 300:
            out.append({"clicar": st["clicar"]})
        elif "digitar" in st and isinstance(st["digitar"], str) and isinstance(st.get("texto"), str) and len(st["texto"]) <= 2000:
            out.append({"digitar": st["digitar"], "texto": st["texto"]})
        else:
            raise ValueError(f"passo {i} inválido")
    return out


def _wait_ready(tab: dict, limit: float = 10) -> None:
    deadline = time.monotonic() + limit
    while time.monotonic() < deadline:
        try:
            if cdp.evaluate(tab, _JS_READY, timeout=2) == "complete":
                return
        except (cdp.BrowserError, TimeoutError, OSError):
            pass  # página ainda trocando; tenta de novo até o prazo
        time.sleep(0.3)


def _current_tab(url: str = "") -> dict:
    found = cdp.tabs()
    if url:
        found = [t for t in found if t.get("url", "").startswith(url.split("#")[0][:60])] or found
    if not found:
        raise cdp.BrowserError("Não achei a aba da macro, senhor.")
    return found[0]


def run_steps(steps: list[dict], broadcast=None) -> int:
    tab: Optional[dict] = None
    last_url = ""
    for i, st in enumerate(steps, 1):
        if broadcast:
            broadcast(i, len(steps))
        if "abrir" in st:
            cdp.open_urls([st["abrir"]])
            last_url = st["abrir"]
            time.sleep(0.6)
            tab = _current_tab(last_url)
            _wait_ready(tab)
        elif "esperar" in st:
            time.sleep(st["esperar"])
        else:
            tab = tab or _current_tab(last_url)
            if "clicar" in st:
                ok = cdp.evaluate(tab, _JS_CLICK % json.dumps(st["clicar"]))
            else:
                txt = json.dumps(st["texto"])
                ok = cdp.evaluate(tab, _JS_TYPE % (json.dumps(st["digitar"]), txt, txt))
            if not ok:
                raise cdp.BrowserError(f"No passo {i}, não achei o elemento na página, senhor.")
            time.sleep(0.3)
    return len(steps)


_MACRO_RUN = re.compile(r"\b(?:roda|rode|rodar|executa|execute|executar|faz|faca|inicia|inicie)\s+a\s+macro\s+"
                        r"(?:de\s+|do\s+|da\s+)?(?P<nome>[\w\s-]{2,40})$")
_MACRO_LIST = re.compile(r"\b(?:quais|que)\s+macros(?:\s+do navegador)?(?:\s+eu tenho|\s+tem|\s+existem)?\??$")


def _parse_macro(norm: str, _original: str) -> Optional[dict]:
    m = _MACRO_RUN.search(norm)
    if m:
        return {"nome": m.group("nome").strip()}
    return {} if _MACRO_LIST.search(norm) else None


@skill(
    name="macro_navegador",
    title="rodar a macro do navegador",
    description=("Roda uma macro gravada do navegador (abrir site, esperar, clicar, digitar) pelo nome. Use listar "
                 "para dizer quais existem."),
    permission=Permission.ACTION,
    allow_remote=False,
    timeout=90,
    llm=False,  # pode passar do prazo do turno da IA; vai pela voz/central
    parse=_parse_macro,
    params={"type": "object", "properties": {"nome": {"type": "string"}}},
    examples=["roda a macro bater ponto", "quais macros eu tenho?"],
)
async def macro_navegador(ctx: SkillContext, nome: str = "") -> SkillResult:
    macros = _load()["macros"]
    if not nome:
        if not macros:
            return SkillResult(speech="Ainda não há macros, senhor. Elas ficam no arquivo navegador.json da pasta data; "
                                      "o guia de comandos tem um exemplo.")
        return SkillResult(speech=f"Macros do navegador: {', '.join(sorted(macros))}.")
    key = _key(nome)
    macro = macros.get(key)
    if not macro:
        return SkillResult(ok=False, speech=f"Não tenho a macro {key}, senhor."
                           + (f" As que existem: {', '.join(sorted(macros))}." if macros else ""))
    try:
        steps = validate_steps(macro.get("passos"))
    except ValueError as exc:
        log.warning("Macro %s inválida: %s", key, exc)
        return SkillResult(ok=False, speech=f"A macro {key} tem um passo inválido, senhor. Confira o arquivo.")

    loop = asyncio.get_running_loop()

    def card(status: str, text: str) -> dict:
        return {"type": "agent", "agent": "macro_navegador", "label": f"Macro {key}", "icon": "🌐", "status": status, "text": text}

    def progress(i: int, total: int) -> None:  # roda na thread da macro; a tela é do event loop
        asyncio.run_coroutine_threadsafe(ctx.broadcast(card("working", f"passo {i} de {total}")), loop)

    try:
        n = await asyncio.to_thread(run_steps, steps, progress)  # passos com espera: fora do event loop
    except Exception as exc:  # noqa: BLE001
        await ctx.broadcast(card("error", "parou"))
        return _speak_error(exc)
    await ctx.broadcast(card("done", f"{n} passos"))
    return SkillResult(speech=f"Macro {key} concluída, senhor: {n} passos.")


# ------------------------------------------------------------------ resumir a página aberta
_JS_TEXT = "JSON.stringify({t: document.title, x: (document.body ? document.body.innerText : '').slice(0, %d)})" % MAX_PAGE_CHARS


@skill(
    name="resumir_pagina",
    title="resumir a página aberta",
    description="Lê a aba aberta no navegador do JARVIS e resume o conteúdo dela.",
    permission=Permission.READ,
    allow_remote=False,
    timeout=40,
    triggers=[r"\b(?:resume|resuma|resumir)\s+(?:essa|esta|a)\s+(?:pagina|aba|materia|noticia)(?:\s+(?:aberta|do navegador))?$"],
    params={"type": "object", "properties": {}},
    examples=["resume essa página"],
)
def resumir_pagina(ctx: SkillContext) -> SkillResult:
    from services import llm_orchestrator as llm

    try:
        if not cdp.available():
            return SkillResult(ok=False, speech="O navegador do JARVIS não está aberto, senhor." + _closed_hint())
        page_tabs = cdp.web_tabs()
        if not page_tabs:
            return SkillResult(ok=False, speech="Não há página aberta para resumir, senhor.")
        raw = cdp.evaluate(page_tabs[0], _JS_TEXT)
        page = json.loads(raw or "{}")
    except Exception as exc:  # noqa: BLE001
        return _speak_error(exc)
    text = re.sub(r"\n{3,}", "\n\n", str(page.get("x", ""))).strip()
    if len(text) < 80:
        return SkillResult(ok=False, speech="Essa página quase não tem texto para resumir, senhor.")
    prompt = ("Resuma em português, em 2 a 4 frases curtas para serem faladas, sem markdown, o conteúdo da página abaixo. "
              "Use só o que está no texto.\n\nTÍTULO: " + str(page.get("t", ""))[:200] + "\n\nTEXTO:\n" + text)
    try:
        answer = llm.ask_text(prompt, max_tokens=500).strip()
    except Exception as exc:  # noqa: BLE001
        log.exception("Resumo da página: a IA falhou")
        return SkillResult(ok=False, speech=llm.friendly_error(exc))
    if not answer:
        return SkillResult(ok=False, speech="A inteligência artificial não devolveu resposta desta vez, senhor. Tente de novo.")
    return SkillResult(speech=answer, cards=[{"type": "skill", "data": {
        "tag": "RESUMO DA PÁGINA", "source": host_of(page_tabs[0].get("url", "")), "rows": [{"label": "", "value": answer[:900]}]}}])

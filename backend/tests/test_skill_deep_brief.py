"""V8.11: Skill Deep Brief (pesquisa a fundo + dossiê salvo). A IA e a pesquisa são trocadas por falsas."""
import asyncio
import json

import pytest

import skills.deep_brief as db
from core import confirm
from core.skills import registry, router
from modules import deep_search_quota, prefs
from services import llm_orchestrator as llm

PLAN = '```json\n{"perguntas": ["carros elétricos: contexto no Brasil", "carros elétricos: vendas recentes", "carros elétricos: prós e contras"]}\n```'
SYNTH = json.dumps({"titulo": "Carros elétricos no Brasil", "resumo_falado": "As vendas de elétricos cresceram em 2026. "
                    "A recarga ainda é o gargalo fora das capitais.", "pontos": ["Vendas em alta", "Poucos carregadores"],
                    "secoes": [{"titulo": "Mercado", "texto": "O mercado cresceu."}], "em_aberto": ["Preço da bateria"]})


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def brief(real_skills, monkeypatch):
    calls = {"web": [], "text": []}

    def fake_text(prompt, web=False, max_tokens=None):
        calls["text"].append(prompt)
        return PLAN if "Divida em" in prompt else SYNTH

    def fake_web(prompt, max_tokens=None):
        calls["web"].append(prompt)
        n = len(calls["web"])
        return (f"Resultado {n}: as vendas cresceram 80% em 2026 segundo a ABVE.",
                [{"name": "ABVE", "headline": "Vendas de elétricos", "url": "https://abve.org.br/a"},
                 {"name": f"Site {n}", "headline": f"Notícia {n}", "url": f"https://site{n}.com/x"}])

    monkeypatch.setattr(llm, "ask_text", fake_text)
    monkeypatch.setattr(llm, "ask_web", fake_web)
    prefs.update(deep_search_allowed=True)
    events = []

    async def fake_broadcast(event):
        events.append(event)

    from core import runtime

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    calls["events"] = events
    return calls


@pytest.mark.parametrize("phrase,tema", [
    ("faz um dossie sobre carros eletricos no brasil", "carros eletricos no brasil"),
    ("jarvis monta um relatorio sobre a reforma tributaria", "a reforma tributaria"),
    ("prepara um resumo completo sobre o james webb", "o james webb"),
    ("dossie sobre energia solar", "energia solar"),
])
def test_phrases(real_skills, phrase, tema):
    sk, args = registry.match(phrase, phrase)
    assert sk.name == "deep_brief" and args == {"tema": tema}


@pytest.mark.parametrize("phrase", ["pesquisa profunda sobre carros", "mostra o relatorio de agua", "relatorio de erros",
                                    "bom dia", "resumo do dia", "pesquise a fundo sobre ia", "faz um resumo"])
def test_legacy_phrases_are_not_captured(real_skills, phrase):
    assert registry.match(phrase, phrase) is None


def test_builds_and_saves_the_dossier(brief):
    before = deep_search_quota.get_status()["count"]
    result = run(router.try_fast_path("Jarvis, faz um dossiê sobre carros elétricos no Brasil"))
    assert result.ok
    assert result.speech.startswith("As vendas de elétricos cresceram em 2026.")
    assert "com 4 fontes, ficou salvo" in result.speech and "lê o dossiê sobre carros elétricos no Brasil" in result.speech
    assert len(brief["web"]) == 3  # um por ângulo, em paralelo
    data = result.cards[0]["data"]
    assert result.cards[0]["type"] == "deep_search" and data["badge"] == "4 FONTES"
    assert [s["url"] for s in data["sources"]].count("https://abve.org.br/a") == 1  # sem fonte repetida
    entry = db.load_index()[0]
    md = (db._DIR / entry["arquivo"]).read_text(encoding="utf-8")
    assert md.startswith("# Carros elétricos no Brasil")
    assert "## Principais pontos" in md and "## Mercado" in md and "## Fontes" in md and "https://abve.org.br/a" in md
    assert deep_search_quota.get_status()["count"] == before + 1
    assert [e["status"] for e in brief["events"] if e.get("type") == "agent"][-1] == "done"


def test_reads_the_dossier_again(brief):
    run(router.try_fast_path("faz um dossiê sobre carros elétricos no Brasil"))
    result = run(router.try_fast_path("lê o dossiê sobre carros elétricos"))
    assert result.speech.startswith("Dossiê sobre carros elétricos no Brasil (de ")
    assert "A recarga ainda é o gargalo" in result.speech and result.cards[0]["type"] == "deep_search"
    assert "faz um dossiê sobre" in run(router.try_fast_path("lê o dossiê sobre vulcões")).speech
    assert "Dossiês salvos: carros elétricos no Brasil" in run(router.try_fast_path("quais são meus dossiês?")).speech


def test_disabled_deep_search_asks_first(brief):
    prefs.update(deep_search_allowed=False)
    result = run(router.try_fast_path("faz um dossiê sobre energia solar"))
    assert result.pending and "Libero só desta vez" in result.speech and brief["web"] == []
    reply = run(confirm.answer("sim"))
    assert reply.startswith("As vendas de elétricos") and len(brief["web"]) == 3


def test_research_failure_refunds_the_quota(brief, monkeypatch):
    def broken(prompt, max_tokens=None):
        raise TimeoutError("timed out")

    monkeypatch.setattr(llm, "ask_web", broken)
    before = deep_search_quota.get_status()["count"]
    result = run(router.try_fast_path("faz um dossiê sobre energia solar"))
    assert result.ok is False and "Não gastei a sua cota" in result.speech
    assert deep_search_quota.get_status()["count"] == before
    assert db.load_index() == []


def test_bad_synthesis_falls_back_to_the_research(brief, monkeypatch):
    monkeypatch.setattr(llm, "ask_text", lambda prompt, web=False, max_tokens=None: "não sei fazer JSON")
    result = run(router.try_fast_path("faz um dossiê sobre energia solar"))
    assert result.ok and result.speech.startswith("Resultado ")
    md = (db._DIR / db.load_index()[0]["arquivo"]).read_text(encoding="utf-8")
    assert "## O que é e contexto" in md  # seções saem dos ângulos padrão


def test_without_sources_says_so(brief, monkeypatch):
    monkeypatch.setattr(llm, "ask_web", lambda prompt, max_tokens=None: ("Texto sem internet sobre o tema.", []))
    result = run(router.try_fast_path("faz um dossiê sobre energia solar"))
    assert "ficou sem fontes da internet" in result.speech
    assert "sem pesquisa na internet" in (db._DIR / db.load_index()[0]["arquivo"]).read_text(encoding="utf-8")


def test_quota_exhausted(brief, monkeypatch):
    monkeypatch.setattr(deep_search_quota, "can_consume", lambda: (False, "O limite de pesquisas profundas de hoje acabou, senhor."))
    result = run(router.try_fast_path("faz um dossiê sobre energia solar"))
    assert result.ok is False and "limite" in result.speech and brief["web"] == []


def test_pure_helpers():
    assert db.parse_json('ok ```json\n{"a": 1}\n``` fim') == {"a": 1}
    assert db.parse_json("nada") is None
    assert db.clean_angles({"perguntas": ["curta", "uma pergunta boa", "uma pergunta boa"]}, "x") == ["uma pergunta boa"]
    assert db.clean_angles(None, "x") == db.default_angles("x")
    assert db.original_text("Jarvis, faz um dossiê sobre Carros Elétricos!", "carros eletricos") == "Carros Elétricos"
    assert db.slug("Reforma Tributária 2026") == "reforma-tributaria-2026"


def test_ask_web_keeps_sources_per_call(monkeypatch):
    """As pesquisas rodam em paralelo: cada uma precisa das PRÓPRIAS fontes (antes era uma variável global)."""
    import threading

    def fake_ask_text(prompt, web=False, max_tokens=None):
        llm._grounding_local.sources = [{"url": prompt}]
        return prompt

    monkeypatch.setattr(llm, "ask_text", fake_ask_text)
    out = {}

    def worker(q):
        out[q] = llm.ask_web(q)

    threads = [threading.Thread(target=worker, args=(q,)) for q in ("a", "b", "c")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert all(out[q] == (q, [{"url": q}]) for q in "abc")

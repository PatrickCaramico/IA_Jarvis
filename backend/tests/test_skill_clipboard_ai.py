"""V8.11: Skill Clipboard AI (resumir, explicar, traduzir e corrigir o texto copiado)."""
import asyncio

import pytest

import skills.clipboard_ai as cb
from core.skills import executor, registry, router
from core.skills.base import SkillContext
from services import llm_orchestrator as llm


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def clip(real_skills, monkeypatch):
    state = {"text": "O relatório de vendas mostra alta de 20% no trimestre, puxada pelo Nordeste.", "written": [], "prompts": []}
    monkeypatch.setattr(cb, "read_clipboard", lambda: state["text"])
    monkeypatch.setattr(cb, "write_clipboard", lambda t: state["written"].append(t) or True)

    def fake_ask(prompt, web=False, max_tokens=None):
        state["prompts"].append(prompt)
        if prompt.startswith("Traduza"):
            return '"The sales report shows a 20% rise."'
        if prompt.startswith("Corrija"):
            return "```\nTexto corrigido.\n```"
        return "As vendas subiram 20% no trimestre, principalmente no Nordeste."

    monkeypatch.setattr(llm, "ask_text", fake_ask)
    return state


@pytest.mark.parametrize("phrase,args", [
    ("resume o que eu copiei", {"acao": "resumir"}),
    ("jarvis explica o texto copiado", {"acao": "explicar"}),
    ("traduz o que eu copiei", {"acao": "traduzir"}),
    ("traduz o que copiei para o espanhol", {"acao": "traduzir", "idioma": "espanhol"}),
    ("corrige o texto que eu copiei", {"acao": "corrigir"}),
    ("revisa o que copiei", {"acao": "corrigir"}),
])
def test_phrases(real_skills, phrase, args):
    sk, got = registry.match(phrase, phrase)
    assert sk.name == "area_de_transferencia_ia" and got == args


@pytest.mark.parametrize("phrase", ["resume o dia", "traduz bom dia para o ingles", "corrige a pasta downloads",
                                    "o que eu copiei", "mostra os copiados"])
def test_legacy_phrases_not_captured(real_skills, phrase):
    hit = registry.match(phrase, phrase)
    assert hit is None or hit[0].name != "area_de_transferencia_ia"


def test_summary_is_spoken_and_not_copied(clip):
    result = run(router.try_fast_path("resume o que eu copiei"))
    assert result.speech == "As vendas subiram 20% no trimestre, principalmente no Nordeste."
    assert clip["written"] == [] and result.cards[0]["data"]["tag"] == "RESUMO DO COPIADO"
    assert "O relatório de vendas" in clip["prompts"][0]


def test_translation_goes_back_to_the_clipboard(clip):
    result = run(router.try_fast_path("traduz o que eu copiei"))
    assert clip["written"] == ["The sales report shows a 20% rise."]  # sem as aspas da IA
    assert "traduzido para o inglês" in result.speech and "é só colar" in result.speech
    assert "para inglês" in clip["prompts"][0]


def test_english_text_translates_to_portuguese(clip):
    clip["text"] = "The quarterly sales report shows strong growth in all regions and markets."
    run(router.try_fast_path("traduz o que eu copiei"))
    assert "para português" in clip["prompts"][0]


def test_correction_strips_fences(clip):
    result = run(router.try_fast_path("corrige o texto que eu copiei"))
    assert clip["written"] == ["Texto corrigido."] and "texto corrigido" in result.speech


def test_empty_clipboard(clip):
    clip["text"] = "   "
    result = run(router.try_fast_path("resume o que eu copiei"))
    assert result.ok is False and "vazia" in result.speech and clip["prompts"] == []


def test_ai_failure_is_honest(clip, monkeypatch):
    monkeypatch.setattr(llm, "ask_text", lambda *a, **k: (_ for _ in ()).throw(ConnectionError("Connection refused")))
    assert "internet caiu" in run(router.try_fast_path("resume o que eu copiei")).speech


def test_remote_is_refused(clip):
    result = run(executor.execute("area_de_transferencia_ia", {"acao": "resumir"}, SkillContext(remote=True)))
    assert result.ok is False and clip["prompts"] == []


def test_language_detection():
    assert cb.looks_portuguese("Isso é um texto em português para o teste de idioma")
    assert not cb.looks_portuguese("This is clearly an English sentence for the language test")
    assert cb.target_language("qualquer", "o espanhol") == "espanhol"

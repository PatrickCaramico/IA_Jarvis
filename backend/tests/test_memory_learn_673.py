"""V6.7.3: memória que aprende sozinha com as conversas."""
import asyncio

import pytest

from modules import cloud_sync, memory, memory_learn, prefs
from modules.quick_replies import _norm


@pytest.fixture
def fake_llm(monkeypatch):
    calls = []

    def answer(text):
        def _ask(prompt):
            calls.append(prompt)
            return text
        monkeypatch.setattr(memory_learn, "_ask_llm", _ask)
        return calls
    return answer


def learn(text):
    return asyncio.run(memory_learn.learn_from(text))


def test_learns_durable_facts_without_repeating(fake_llm):
    calls = fake_llm('```json\n["Gosta de café sem açúcar", "Treina às 18h de segunda a sexta"]\n```')
    assert learn("eu sempre tomo café sem açúcar e treino às 18h de segunda a sexta") == [
        "Gosta de café sem açúcar", "Treina às 18h de segunda a sexta"]
    assert all(f["source"] == "auto" for f in memory.get_memory()["facts"])
    # o que já sabe vai junto no pedido e não é guardado de novo
    fake_llm('["Gosta de café sem açúcar.", "A esposa se chama Ana"]')
    assert learn("minha esposa Ana também gosta de café") == ["A esposa se chama Ana"]
    assert "Gosta de café sem açúcar" in calls[0] or "Memórias que você já tem" in calls[0]
    assert len(memory.facts(50)) == 3


def test_only_tries_when_talking_about_himself(fake_llm):
    calls = fake_llm('["x"]')
    for text in ("que horas são", "qual a capital da França?", "previsão do tempo amanhã em São Paulo"):
        assert learn(text) == []
    assert calls == []


def test_never_keeps_sensitive_or_garbage(fake_llm):
    fake_llm('["Minha senha do banco é 1234", "ok", "Mora em Campinas", 42]')
    assert learn("eu moro em Campinas, anota aí") == ["Mora em Campinas"]
    fake_llm("não sei")
    assert learn("eu gosto muito de pizza de calabresa") == []
    calls = fake_llm('["x"]')
    before = len(calls)
    assert learn("minha senha do cartão é 1234") == [] and len(calls) == before  # nem pergunta à IA


def test_voice_toggle(fake_llm):
    calls = fake_llm('["Gosta de rock"]')
    assert "Paro de aprender" in memory_learn.handle_voice(_norm("Jarvis, pare de aprender sobre mim"))
    assert prefs._load()["memory_auto_learn"] is False
    assert learn("eu gosto muito de rock dos anos 80") == [] and calls == []
    assert "Volto a guardar" in memory_learn.handle_voice(_norm("pode voltar a aprender sobre mim"))
    assert learn("eu gosto muito de rock dos anos 80") == ["Gosta de rock"]


def test_duplicate_detection():
    assert memory_learn.is_duplicate("Gosta de café sem açúcar", ["Gosta de cafe sem acucar"])
    assert not memory_learn.is_duplicate("Gosta de chá verde", ["Gosta de café sem açúcar"])


def test_cloud_gets_memories():
    memory.remember("Torce para o Palmeiras", source="auto")
    assert "Torce para o Palmeiras" in cloud_sync.snapshot()["perfil"]["memorias"]

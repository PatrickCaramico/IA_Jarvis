"""V9.0: memória pesquisável (SQLite FTS5 local): conversas, memórias, tarefas, lembretes e copiados."""
import asyncio
from datetime import datetime, timedelta

from core.skills import registry, router
from modules import desk, memory, memory_index, reminders, tasks
from modules.quick_replies import _norm


def match(phrase):
    return registry.match(_norm(phrase), phrase)


def test_every_conversation_is_archived_not_only_the_last_20():
    for i in range(30):
        memory.add_conversation(f"pergunta número {i} sobre a viagem a Maceió", f"resposta {i}")
    assert len(memory.get_memory()["conversation"]) == 20  # a memória curta continua igual
    assert memory_index.stats()["conversa"] == 30
    hits = memory_index.search("viagem maceio", limit=50)
    assert len(hits) == 30 and hits[0]["kind"] == "conversa"


def test_search_ignores_accents_uses_prefixes_and_snapshots():
    memory.remember("O wifi da casa da praia é Praia2026")
    tasks.add_task("Renovar o passaporte")
    reminders.add_reminder("Consulta no dentista", datetime.now() + timedelta(days=1))
    desk.clip_add("Rua das Acácias, 123 - Maceió")
    assert memory_index.search("passaport")[0]["kind"] == "tarefa"  # começo da palavra
    assert memory_index.search("DENTISTA")[0]["kind"] == "lembrete"
    assert memory_index.search("acacias")[0]["kind"] == "copiado"  # sem acento acha com acento
    assert memory_index.search("wifi praia")[0]["kind"] == "memoria"
    tasks.add_task("Comprar protetor solar")  # arquivo mudou: entra na próxima busca
    assert memory_index.search("protetor")[0]["title"] == "Comprar protetor solar"
    assert memory_index.search("palavrainexistente") == []
    assert memory_index.search("") == []


def test_any_word_when_all_words_find_nothing():
    memory.add_conversation("vamos para Gramado em julho", "Ótimo destino, senhor.")
    assert memory_index.search("gramado inverno")[0]["kind"] == "conversa"


def test_query_cannot_inject_fts_syntax():
    memory.add_conversation("teste de aspas", "ok")
    assert memory_index.fts_query('a" OR "b NEAR(x') == '"or"* AND "near"*'  # vira palavras comuns
    memory_index.search('") OR * --')  # nada quebra


def test_voice_phrases(real_skills):
    for phrase, q in [("o que eu te falei sobre a viagem?", "a viagem"), ("o que eu anotei sobre o dentista", "o dentista"),
                      ("procura na memoria sobre o carro", "o carro"), ("busca nas minhas conversas o wifi", "wifi"),
                      ("quando eu falei do aniversario da minha mae", "aniversario da minha mae")]:
        hit = match(phrase)
        assert hit and hit[0].name == "buscar_memoria", phrase
        assert hit[1]["consulta"] == q, phrase
    for phrase in ("lembre que eu treino as 18h", "o que voce sabe sobre mim", "pesquisa sobre o egito", "procura um restaurante"):
        hit = match(phrase)
        assert hit is None or hit[0].name != "buscar_memoria", phrase


def test_skill_answer(real_skills):
    memory.add_conversation("a viagem para Maceió vai ser em dezembro", "Anotado, senhor.")
    res = asyncio.run(router.try_fast_path("o que eu te falei sobre a viagem?"))
    assert res.speech.startswith("Achei 1 coisa sobre a viagem") and "dezembro" in res.speech
    assert res.cards[0]["data"]["tag"] == "MEMÓRIA"
    none = asyncio.run(router.try_fast_path("o que eu te falei sobre submarinos?"))
    assert "Não achei nada sobre submarinos" in none.speech


def test_route(isolated_data):
    from fastapi.testclient import TestClient

    import main
    from modules import access

    memory.add_conversation("o carro precisa de revisão", "Vou lembrar, senhor.")
    access.reset_for_tests(access.UNLOCKED)
    try:
        c = TestClient(main.app)
        items = c.get("/api/search/local", params={"q": "revisao"}).json()["items"]
        assert items and items[0]["label"] == "Conversa" and "[revisão]" in items[0]["snippet"]
        assert c.get("/api/search/local", params={"q": "a"}).json() == {"items": []}
        # bloqueada, a busca na memória pessoal não abre (só as rotas públicas da tela de bloqueio)
        assert not access.is_allowed("GET", "/api/search/local", access.LOCKED)
    finally:
        access.reset_for_tests(access.LOCKED)


def test_addresses_are_not_mistaken_for_passwords():
    assert not desk.looks_secret("Rua das Acácias, 123 - Maceió")
    assert desk.looks_secret("Tr0ub4dor&3")  # senha de verdade continua de fora
    assert desk.looks_secret("4111 1111 1111 1111")

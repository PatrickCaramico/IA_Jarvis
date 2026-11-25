"""V9.5.4: atualizar o JARVIS por voz. Antes, com o aviso "atualizo sozinho em dois minutos" na tela, "pode atualizar"
não era entendido (só os botões funcionavam)."""
import asyncio

import pytest

import skills.atualizar as sk_up
from core.skills import SkillContext, executor, registry, router
from modules import auto_update, self_update


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def upd(real_skills, monkeypatch):
    auto_update.reset_for_tests()
    started = []

    async def fake_start():
        started.append(True)

    monkeypatch.setattr(sk_up, "_start_update", fake_start)
    monkeypatch.setattr(self_update, "check", lambda force=False: {"available": True, "latest": "9.6.0"})
    yield started
    auto_update.reset_for_tests()


@pytest.mark.parametrize("phrase, acao", [
    ("pode atualizar", "agora"),
    ("jarvis atualiza agora", "agora"),
    ("atualiza agora por favor", "agora"),
    ("pode atualizar o jarvis", "agora"),
    ("atualizar o sistema", "agora"),
    ("faz a atualizacao agora", "agora"),
    ("instala a versao nova", "agora"),
    ("adia a atualizacao", "adiar"),
    ("atualiza depois", "adiar"),
    ("nao atualiza agora", "adiar"),
])
def test_frases_chegam_na_skill(real_skills, phrase, acao):
    sk, args = registry.match(phrase, phrase)
    assert sk.name == "atualizar_jarvis" and args == {"acao": acao}


@pytest.mark.parametrize("phrase", [
    "atualiza a lista de compras", "atualiza as noticias", "atualizar o clima", "atualiza minha agenda",
    "o que mudou na atualizacao", "qual a versao do jarvis", "atualiza o spotify",
])
def test_frases_que_nao_sao_atualizar_o_jarvis(real_skills, phrase):
    hit = registry.match(phrase, phrase)
    assert hit is None or hit[0].name != "atualizar_jarvis"


def test_com_o_aviso_na_tela_e_o_atualizar_agora(upd):
    auto_update._state["notice"] = {"type": "update_soon", "version": "9.6.0"}
    r = run(router.try_fast_path("pode atualizar"))
    assert r.speech == "Atualizando agora, senhor. Volto em instantes."
    assert auto_update._state["now"] is True
    assert upd == []  # quem atualiza é a rodada automática que já está esperando


def test_adiar_com_o_aviso(upd):
    auto_update._state["notice"] = {"type": "update_soon", "version": "9.6.0"}
    r = run(router.try_fast_path("adia a atualização"))
    assert "uma hora" in r.speech and auto_update.postponed()


def test_adiar_sem_aviso(upd):
    assert run(router.try_fast_path("adia a atualização")).speech == "Não há atualização marcada agora, senhor."


def test_sem_aviso_confere_e_atualiza(upd):
    r = run(router.try_fast_path("atualiza o jarvis"))
    assert r.speech == "Atualizando para a versão 9.6.0, senhor. Volto em instantes."
    assert upd == [True]


def test_sem_versao_nova(upd, monkeypatch):
    monkeypatch.setattr(self_update, "check", lambda force=False: {"available": False})
    assert run(router.try_fast_path("pode atualizar")).speech == "Já estou na versão mais nova, senhor."
    assert upd == []


def test_falha_ao_procurar_responde_com_calma(upd, monkeypatch):
    def boom(force=False):
        raise OSError("sem rede")

    monkeypatch.setattr(self_update, "check", boom)
    assert "Não consegui procurar" in run(router.try_fast_path("pode atualizar")).speech


def test_pedido_de_outro_aparelho_nao_atualiza_sem_aviso(upd):
    r = run(executor.execute("atualizar_jarvis", {"acao": "agora"}, SkillContext(remote=True)))
    assert "próprio PC" in r.speech and upd == []

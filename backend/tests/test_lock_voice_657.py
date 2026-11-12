"""V6.5.7: frases que levam a central para a tela de bloqueio."""
import pytest

from core.turns import JARVIS_LOCK_CMD
from modules.quick_replies import _norm


@pytest.mark.parametrize("phrase", [
    "modo bloqueio", "Jarvis, modo bloqueio", "ativa o modo bloqueio", "entra no modo de bloqueio",
    "entrar em modo bloqueio", "liga o modo sentinela", "modo sentinela", "bloqueia a central",
    "Jarvis, bloquear", "volta pra tela de bloqueio", "tela de bloqueio", "pode bloquear o jarvis",
])
def test_lock_phrases(phrase):
    assert JARVIS_LOCK_CMD.fullmatch(_norm(phrase))


@pytest.mark.parametrize("phrase", [
    "bloquear a tela",          # bloqueia o Windows (system_control), não a central
    "como funciona o modo bloqueio",
    "modo cinema",
    "desativar o modo bloqueio",
])
def test_not_lock_phrases(phrase):
    assert not JARVIS_LOCK_CMD.fullmatch(_norm(phrase))

"""V6.7: modo bem-estar (segurança, respiração, aterramento e humor)."""
import asyncio
import re
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from modules import cloud_sync, sentinel, wellbeing


def say(text):
    return asyncio.run(wellbeing.handle_voice(text))


@pytest.mark.parametrize("text", [
    "quero me matar", "Jarvis, quero morrer.", "às vezes não quero mais viver", "penso em me machucar",
    "tenho pensamentos suicidas", "seria melhor se eu não existisse", "estou pensando em me cortar",
])
def test_crisis_gets_fixed_help(text):
    reply = say(text)
    assert "188" in reply and "192" in reply


@pytest.mark.parametrize("text", [
    "vou me matar de rir", "me matar de trabalhar", "quero morrer de vergonha", "tenho medo de me machucar na academia",
    "vou me cortar o cabelo amanhã", "que horas são", "me lembra de pagar a luz",
])
def test_common_phrases_are_not_crisis(text):
    assert wellbeing.crisis_reply(text) is None


def test_crisis_works_even_locked():
    r = asyncio.run(sentinel.classify_and_answer("jarvis, quero morrer", "locked"))
    assert r["public"] and not r["requires_unlock"] and "188" in r["reply"]
    g = asyncio.run(sentinel.classify_and_answer("jarvis, quero morrer", "guest"))
    assert "188" in g["reply"]


def test_breathing_and_grounding():
    assert say("Jarvis, exercício de respiração") == wellbeing.BREATH_478
    assert say("vamos fazer a respiração quadrada") == wellbeing.BREATH_BOX
    assert say("me ajuda a me acalmar") == wellbeing.GROUNDING
    assert say("o carro não está respirando bem no motor, o mecânico disse que precisa trocar o filtro") is None


def test_mood_log_and_summary():
    assert "3 de 5" in say("meu humor hoje é 3")
    assert "4 de 5" in say("estou me sentindo 4 de 5")
    assert "2 de 5" in say("registra meu humor como ruim")
    now = datetime.now()
    for i, score in enumerate([2, 2, 4, 5]):
        wellbeing.log_mood(score, when=now - timedelta(days=3 - i))
    text = say("como foi meu humor essa semana?")
    assert "média" in text and "melhorando" in text
    assert "Humor que o usuário registrou" in wellbeing.prompt_context()


def test_mood_from_cloud_reaches_pc():
    assert cloud_sync.apply_op({"op": "mood_set", "score": 5, "date": datetime.now().strftime("%Y-%m-%d")})
    assert wellbeing.recent(1)[-1][1] == 5
    assert cloud_sync.apply_op({"op": "mood_set", "score": "x"}) is False


def test_cloud_has_the_same_safety_text():
    """A nuvem (netlify/nuvem/core.mjs) repete a resposta de segurança: os dois textos têm que ser iguais."""
    js = (Path(__file__).resolve().parents[2] / "netlify" / "nuvem" / "core.mjs").read_text(encoding="utf-8")
    block = js[js.index("export const CRISIS_REPLY"):js.index(";", js.index("export const CRISIS_REPLY"))]
    joined = "".join(re.findall(r'"([^"]*)"', block))
    assert joined == wellbeing.CRISIS_REPLY

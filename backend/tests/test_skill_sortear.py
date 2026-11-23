"""V8.13: sorteios (moeda, dados, número, escolher entre opções). O sorteio usa uma semente fixa no teste."""
import asyncio
import random

import pytest

import skills.sorteio as sorteio
from core.skills import executor, registry, router
from core.skills.base import SkillContext
from modules.quick_replies import _norm


@pytest.fixture(autouse=True)
def seeded(monkeypatch):
    monkeypatch.setattr(sorteio, "_rng", random.Random(42))


def match(phrase):
    return registry.match(_norm(phrase), phrase)


def test_phrases_to_params(real_skills):
    assert match("cara ou coroa?")[1] == {"tipo": "moeda"}
    assert match("joga uma moeda")[1] == {"tipo": "moeda"}
    assert match("joga um dado")[1] == {"tipo": "dado", "quantidade": 1, "lados": 6}
    assert match("rola dois dados")[1] == {"tipo": "dado", "quantidade": 2, "lados": 6}
    assert match("joga um dado de 20 lados")[1] == {"tipo": "dado", "quantidade": 1, "lados": 20}
    assert match("sorteia um número de 1 a 100")[1] == {"tipo": "numero", "minimo": 1, "maximo": 100}
    assert match("escolhe um numero entre 5 e 10")[1] == {"tipo": "numero", "minimo": 5, "maximo": 10}
    assert match("Escolhe entre pizza, hambúrguer ou sushi")[1] == {"tipo": "escolha", "opcoes": ["pizza", "hambúrguer", "sushi"]}
    assert match("sorteia entre Ana e Bruno")[1] == {"tipo": "escolha", "opcoes": ["Ana", "Bruno"]}
    assert match("decide pra mim: cinema ou série?")[1]["opcoes"] == ["cinema", "série"]


def test_other_phrases_are_not_captured(real_skills):
    for phrase in ("escolhe uma música no spotify", "que dados tem no relatório", "abre o dado", "joga o lixo fora",
                   "escolhe entre", "sorteia"):
        hit = match(phrase)
        assert hit is None or hit[0].name != "sortear", phrase


def run(args):
    return asyncio.run(executor.execute("sortear", args, SkillContext(origin="test")))


def test_results(real_skills):
    assert run({"tipo": "moeda"}).speech in ("Deu cara, senhor.", "Deu coroa, senhor.")
    one = run({"tipo": "dado"})
    assert 1 <= one.data["resultados"][0] <= 6 and one.speech.startswith("Deu ")
    two = run({"tipo": "dado", "quantidade": 3, "lados": 20})
    assert len(two.data["resultados"]) == 3 and two.data["total"] == sum(two.data["resultados"])
    assert "Total" in two.speech
    n = run({"tipo": "numero", "minimo": 10, "maximo": 1})
    assert 1 <= n.data["resultado"] <= 10
    pick = run({"tipo": "escolha", "opcoes": ["pizza", "sushi"]})
    assert pick.data["escolha"] in ("pizza", "sushi") and pick.speech.startswith("Eu fico com")


def test_limits(real_skills):
    assert run({"tipo": "dado", "quantidade": 50}).ok is False
    assert run({"tipo": "dado", "lados": 1}).ok is False
    assert run({"tipo": "numero", "minimo": 0, "maximo": 10**12}).ok is False
    assert run({"tipo": "escolha", "opcoes": ["só uma"]}).ok is False


def test_fast_path_answer(real_skills):
    res = asyncio.run(router.try_fast_path("cara ou coroa"))
    assert res.speech in ("Deu cara, senhor.", "Deu coroa, senhor.")

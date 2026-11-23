"""V8.13: calculadora de datas (dia fixo nos testes: segunda-feira, 23/11/2026)."""
import asyncio
from datetime import date

import pytest

import skills.datas as datas
from core.skills import registry, router

TODAY = date(2026, 11, 23)  # segunda-feira


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr(datas, "_today", lambda: TODAY)


def ask(phrase):
    return asyncio.run(router.try_fast_path(phrase))


def test_phrases_to_params(real_skills):
    cases = {
        "que dia vai ser daqui a 45 dias": {"acao": "somar", "quantidade": 45, "unidade": "dias"},
        "que dia cai daqui a tres semanas": {"acao": "somar", "quantidade": 3, "unidade": "semanas"},
        "que data e daqui a 2 meses": {"acao": "somar", "quantidade": 2, "unidade": "meses"},
        "que dia foi ha 10 dias": {"acao": "somar", "quantidade": -10, "unidade": "dias"},
        "quantos dias se passaram desde 10 de marco": {"acao": "desde", "data": "2026-03-10"},
        "ha quantos dias foi o carnaval": {"acao": "desde", "data": "2026-02-17"},
        "que dia da semana cai o natal": {"acao": "dia_semana", "data": "2026-12-25"},
        "25/12/2027 cai em que dia da semana": {"acao": "dia_semana", "data": "2027-12-25"},
        "quantos dias entre 10/03 e 25/12": {"acao": "entre", "data": "2026-03-10", "data_fim": "2026-12-25"},
    }
    for phrase, args in cases.items():
        hit = registry.match(phrase.replace("/", " "), phrase)  # o JARVIS normaliza a frase (a barra some)
        assert hit and hit[0].name == "calcular_datas", phrase
        assert hit[1] == args, phrase


def test_countdown_and_other_phrases_are_not_captured(real_skills):
    for phrase in ("quanto falta para o natal", "quantos dias faltam para a viagem", "contagem regressiva para o natal",
                   "que dia e hoje", "me lembra daqui a 10 minutos", "timer de 5 minutos", "abre o calendario"):
        hit = registry.match(phrase, phrase)
        assert hit is None or hit[0].name != "calcular_datas", phrase


def test_answers(real_skills):
    assert ask("que dia vai ser daqui a 45 dias").speech == "Daqui a 45 dias será quinta-feira, 7 de janeiro de 2027, senhor."
    assert ask("que dia foi há 1 dia").speech == "Há 1 dia foi domingo, 22 de novembro, senhor."
    assert ask("quantos dias se passaram desde 1 de janeiro").speech.startswith("Desde 1 de janeiro se passaram 326 dias")
    assert ask("que dia da semana cai o natal").speech == "25 de dezembro cai numa sexta-feira, senhor."
    assert ask("que dia da semana foi 7 de setembro de 2022").speech == "7 de setembro de 2022 foi numa quarta-feira, senhor."
    assert ask("quantos dias entre 25/12 e 10/03").speech == "Entre 10 de março e 25 de dezembro são 290 dias, senhor."


def test_month_math_and_easter():
    assert datas._add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert datas._add_months(date(2026, 11, 23), -12) == date(2025, 11, 23)
    assert datas.easter(2026) == date(2026, 4, 5)
    assert datas.easter(2027) == date(2027, 3, 28)


def test_bad_inputs(real_skills):
    out = asyncio.run(_run("calcular_datas", {"acao": "desde", "data": "xx"}))
    assert out.ok is False
    out = asyncio.run(_run("calcular_datas", {"acao": "somar", "quantidade": 0}))
    assert out.ok is False
    out = asyncio.run(_run("calcular_datas", {"acao": "desde", "data": "2026-12-25"}))
    assert "ainda não chegou" in out.speech


async def _run(name, args):
    from core.skills import executor
    from core.skills.base import SkillContext

    return await executor.execute(name, args, SkillContext(origin="test"))

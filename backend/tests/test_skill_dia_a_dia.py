"""V8.11: conversor de unidades local e gerador de senha (skills/dia_a_dia.py)."""
import asyncio
import string

import pytest

import skills.dia_a_dia as dd
from core.skills import registry, router
from modules import access


def run(coro):
    return asyncio.run(coro)


@pytest.mark.parametrize("phrase,speech", [
    ("Quanto é 5 milhas em km?", "5 milhas são 8,05 quilômetros."),
    ("converte 350 °F para celsius", "350 graus Fahrenheit são 176,67 graus Celsius."),
    ("2 xícaras em ml", "2 xícaras são 480 mililitros."),
    ("quantos gramas tem 3 libras", "3 libras são 1.361 gramas."),
    ("quanto é 1,5 GB em MB", "1,5 gigabytes são 1.536 megabytes."),
    ("100 km/h em mph", "100 quilômetros por hora são 62,14 milhas por hora."),
    ("cinco milhas em quilômetros", "5 milhas são 8,05 quilômetros."),
    ("1 polegada em centímetros", "1 polegada é 2,54 centímetros."),
    ("0 celsius em kelvin", "0 graus Celsius são 273,15 kelvins."),
])
def test_conversions(real_skills, phrase, speech):
    assert run(router.try_fast_path(phrase)).speech == speech


@pytest.mark.parametrize("phrase", ["quanto é 5 + 3", "quanto é 100 dólares em reais", "me avise em 10 minutos",
                                    "qual o clima em recife", "converte 5 metros em litros", "abre o youtube"])
def test_not_a_conversion(real_skills, phrase):
    hit = registry.match(phrase, phrase)
    assert hit is None or hit[0].name != "converter_unidades"


def test_conversion_works_with_the_central_locked(real_skills, credentials):
    access.reset_for_tests(access.LOCKED)
    assert run(router.try_fast_path("5 milhas em km", public_only=True)).speech == "5 milhas são 8,05 quilômetros."


def test_numbers_in_portuguese():
    assert dd._to_float("1,5") == 1.5 and dd._to_float("1.000") == 1000 and dd._to_float("2.5") == 2.5
    assert dd.fmt_number(1609.344) == "1.609" and dd.fmt_number(0.03937) == "0,0394" and dd.fmt_number(8.0) == "8"


def test_password_is_strong_and_copied_never_spoken(real_skills, monkeypatch):
    import skills.clipboard_ai as cb

    copied = []
    monkeypatch.setattr(cb, "write_clipboard", lambda t: copied.append(t) or True)
    result = run(router.try_fast_path("gera uma senha forte de 16 caracteres"))
    (pwd,) = copied
    assert len(pwd) == 16 and pwd not in result.speech and "16 caracteres" in result.speech
    assert any(c.isupper() for c in pwd) and any(c.islower() for c in pwd)
    assert any(c.isdigit() for c in pwd) and any(c in dd.SYMBOLS for c in pwd)
    assert not set(pwd) & set("O0Il1")
    assert result.cards == []


def test_password_sizes_and_uniqueness():
    assert len(dd.make_password(4)) == 12 and len(dd.make_password(500)) == 64
    assert len({dd.make_password() for _ in range(50)}) == 50
    assert set(dd.make_password(64)) <= set(string.ascii_letters + string.digits + dd.SYMBOLS)


def test_password_without_clipboard(real_skills, monkeypatch):
    import skills.clipboard_ai as cb

    monkeypatch.setattr(cb, "write_clipboard", lambda t: False)
    assert run(router.try_fast_path("cria uma senha")).ok is False

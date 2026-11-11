"""Horários falados para alarmes e lembretes (V5.1). "Agora" = terça, 10/11/2026, 14:00."""
from datetime import datetime

import pytest

from modules.when import describe, parse

NOW = datetime(2026, 11, 10, 14, 0)


@pytest.mark.parametrize("text, expected", [
    ("as 7", datetime(2026, 11, 10, 19, 0)),          # 7 já passou hoje: entende 19h
    ("as 7 da manha", datetime(2026, 11, 11, 7, 0)),
    ("amanha as 7", datetime(2026, 11, 11, 7, 0)),
    ("as 6 e meia", datetime(2026, 11, 10, 18, 30)),
    ("as 15h", datetime(2026, 11, 10, 15, 0)),
    ("as 16 e 45", datetime(2026, 11, 10, 16, 45)),
    ("6h30 amanha", datetime(2026, 11, 11, 6, 30)),
    ("as 7 da noite", datetime(2026, 11, 10, 19, 0)),
    ("as sete horas da noite", datetime(2026, 11, 10, 19, 0)),
    ("meio dia amanha", datetime(2026, 11, 11, 12, 0)),
    ("meia noite", datetime(2026, 11, 11, 0, 0)),
    ("sexta as 10", datetime(2026, 11, 13, 10, 0)),
    ("dia 15 as 9", datetime(2026, 11, 15, 9, 0)),
    ("daqui a 20 minutos", datetime(2026, 11, 10, 14, 20)),
    ("em 2 horas", datetime(2026, 11, 10, 16, 0)),
    ("daqui a uma hora e meia", datetime(2026, 11, 10, 15, 30)),
    ("em meia hora", datetime(2026, 11, 10, 14, 30)),
])
def test_horarios(text, expected):
    assert parse(text, NOW).at == expected


def test_repeticoes():
    w = parse("de segunda a sexta as 6", NOW)
    assert w.days == [0, 1, 2, 3, 4] and w.at == datetime(2026, 11, 11, 6, 0)
    w = parse("todo dia as 7 da manha", NOW)
    assert w.days == list(range(7)) and w.at == datetime(2026, 11, 11, 7, 0)
    w = parse("toda terca as 19", NOW)
    assert w.days == [1] and w.at == datetime(2026, 11, 10, 19, 0)
    assert parse("fim de semana as 9", NOW).days == [5, 6]


def test_rotulo_sobra_e_sem_horario():
    assert parse("as 7 para a reuniao", NOW).rest == "para a reuniao"
    w = parse("comprar pao", NOW)
    assert w.at is None and w.rest == "comprar pao"


def test_descricao_falada():
    assert describe(datetime(2026, 11, 11, 7, 0), now=NOW) == "amanhã às 07:00"
    assert describe(datetime(2026, 11, 10, 19, 30), now=NOW) == "hoje às 19:30"
    assert describe(datetime(2026, 11, 13, 10, 0), now=NOW) == "sexta às 10:00"
    assert describe(datetime(2026, 11, 11, 6, 0), [0, 1, 2, 3, 4], NOW) == "de segunda a sexta às 06:00"

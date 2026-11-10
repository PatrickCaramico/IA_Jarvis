"""Lembrete de água: intervalo configurável e contagem a partir do último evento."""
from datetime import timedelta

import pytest

from modules import water


@pytest.fixture
def at_noon(isolated_data, monkeypatch):
    noon = water._now().replace(hour=12, minute=0, second=0, microsecond=0)
    monkeypatch.setattr(water, "_now", lambda: noon)
    return noon


def _write(monkeypatch_now, **fields):
    data = water._load_data()
    data.update(fields)
    water._save_data(data)


def test_old_intake_does_not_cause_reminder_every_loop(at_noon):
    """Bug real: ingestão antiga + lembrete recente fazia lembrar a cada 2 minutos."""
    _write(at_noon, last_intake_ts=(at_noon - timedelta(hours=14)).isoformat(),
           last_reminder_ts=(at_noon - timedelta(minutes=2)).isoformat())
    water.set_reminder(120)
    assert water.should_remind_water() is False


def test_reminds_after_interval(at_noon):
    water.set_reminder(120)
    _write(at_noon, last_reminder_ts=(at_noon - timedelta(minutes=121)).isoformat())
    assert water.should_remind_water() is True
    assert water.should_remind_water() is False  # acabou de lembrar


def test_recent_intake_postpones(at_noon):
    water.set_reminder(120)
    _write(at_noon, last_reminder_ts=(at_noon - timedelta(hours=5)).isoformat(),
           last_intake_ts=(at_noon - timedelta(minutes=30)).isoformat())
    assert water.should_remind_water() is False


def test_zero_disables(at_noon):
    water.set_reminder(0)
    assert water.should_remind_water() is False


def test_default_is_two_hours(isolated_data):
    assert water.get_status()["reminder_interval_min"] == 120


def test_invalid_values(isolated_data):
    with pytest.raises(ValueError):
        water.set_reminder(7)
    with pytest.raises(ValueError):
        water.set_reminder(None, 20, 8)

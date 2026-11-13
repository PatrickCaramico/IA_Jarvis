"""V7.2: a saudação do desbloqueio vem só de vez em quando."""
from datetime import datetime, timedelta

from modules import entry_greeting, prefs

NOW = datetime(2026, 11, 13, 14, 0)


def setup(monkeypatch, mode="sometimes", pending=False):
    prefs.update(lock_unlock_greeting=mode, unlock_greeting={})
    monkeypatch.setattr(entry_greeting, "briefing_pending", lambda now=None: pending)


def test_sometimes_greets_first_then_silent_until_gap(isolated_data, monkeypatch):
    setup(monkeypatch)
    assert entry_greeting.unlock_speech("Boa tarde.", "Ok.", now=NOW) == "Boa tarde."
    assert entry_greeting.unlock_speech("Boa tarde.", "Ok.", now=NOW + timedelta(minutes=20)) == ""
    assert entry_greeting.unlock_speech("Boa tarde.", "Ok.", " Houve 1 tentativa.", now=NOW + timedelta(hours=1)) == "Houve 1 tentativa."
    assert entry_greeting.unlock_speech("Boa noite.", "Ok.", now=NOW + timedelta(hours=3, minutes=1)) == "Boa noite."


def test_new_day_always_greets(isolated_data, monkeypatch):
    setup(monkeypatch)
    late = datetime(2026, 11, 13, 23, 30)
    assert entry_greeting.unlock_speech("Oi.", "Ok.", now=late) == "Oi."
    assert entry_greeting.unlock_speech("Bom dia.", "Ok.", now=late + timedelta(hours=1)) == "Bom dia."


def test_modes_and_briefing(isolated_data, monkeypatch):
    setup(monkeypatch, mode="always")
    assert entry_greeting.unlock_speech("Oi.", "Ok.", now=NOW) == "Oi."
    assert entry_greeting.unlock_speech("Oi.", "Ok.", now=NOW) == "Oi."
    setup(monkeypatch, mode="off")
    assert entry_greeting.unlock_speech("Oi.", "Ok.", now=NOW) == ""
    setup(monkeypatch, pending=True)
    assert entry_greeting.unlock_speech("Oi.", "Identidade confirmada.", now=NOW) == "Identidade confirmada."
    assert prefs.validate_patch({"lock_unlock_greeting": "talvez"})
    assert prefs.validate_patch({"lock_unlock_greeting": "sometimes"}) is None

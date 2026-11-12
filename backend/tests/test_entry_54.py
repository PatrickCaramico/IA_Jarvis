"""V5.4: ao entrar na central, o briefing/pergunta valem para todos os aparelhos juntos (decisão no PC)."""
import random

import pytest
from datetime import datetime

from modules import entry_greeting, prefs

MORNING = datetime(2026, 11, 12, 8, 0)


@pytest.fixture(autouse=True)
def _one_screen_at_a_time(monkeypatch):
    """Nestes testes cada chamada é uma entrada nova (a janela de "mesma entrada" fica desligada)."""
    monkeypatch.setattr(entry_greeting, "SAME_ENTRY_SECONDS", 0)
    monkeypatch.setattr(entry_greeting, "_last_decision_at", 0.0)


def test_first_entry_runs_briefing_then_asks_once_then_stays_quiet():
    assert entry_greeting.decide(MORNING) == {"action": "briefing", "command": "bom dia"}
    second = entry_greeting.decide(MORNING)
    assert second["action"] == "ask" and second["command"] == "bom dia"
    assert "Bem-vindo" not in second["text"]  # V6.1: o desbloqueio já cumprimentou
    assert entry_greeting.decide(MORNING) == {"action": "none"}


def test_greeting_never_repeats_the_last_one(monkeypatch):
    monkeypatch.setattr(entry_greeting, "GREET_AFTER_UNLOCK", True)  # saudação extra (desligada por padrão)
    entry_greeting.mark_briefed(MORNING)
    prefs.update(briefing_entry={**prefs._load()["briefing_entry"], "asked": True})
    rng = random.Random(1)
    texts = [entry_greeting.decide(MORNING, rng)["text"] for _ in range(20)]
    assert all(a != b for a, b in zip(texts, texts[1:]))


def test_voice_briefing_counts_as_done():
    entry_greeting.mark_briefed(MORNING)
    assert entry_greeting.decide(MORNING)["action"] == "ask"


def test_new_day_starts_over():
    entry_greeting.decide(MORNING)
    entry_greeting.decide(MORNING)
    assert entry_greeting.decide(datetime(2026, 11, 13, 7, 30))["action"] == "briefing"


def test_evening_command_and_modes():
    assert entry_greeting.decide(datetime(2026, 11, 12, 20, 0))["command"] == "boa noite"
    prefs.update(lock_daily_summary="always")
    assert entry_greeting.decide(MORNING)["action"] == "briefing"
    assert entry_greeting.decide(MORNING)["action"] == "briefing"
    prefs.update(lock_daily_summary="off")
    assert entry_greeting.decide(datetime(2026, 11, 14, 8, 0))["action"] == "none"


def test_briefing_pending_tells_unlock_not_to_greet():
    assert entry_greeting.briefing_pending(MORNING) is True
    entry_greeting.decide(MORNING)
    assert entry_greeting.briefing_pending(MORNING) is False


def test_two_screens_entering_together_speak_once(monkeypatch):
    """V5.6.2: aba antiga + aba nova (ou PC + celular) entrando juntas: só a primeira fala."""
    clock = [1000.0]
    monkeypatch.setattr(entry_greeting, "SAME_ENTRY_SECONDS", 120)
    monkeypatch.setattr(entry_greeting.time, "monotonic", lambda: clock[0])
    assert entry_greeting.decide(MORNING)["action"] == "briefing"
    clock[0] += 5
    assert entry_greeting.decide(MORNING) == {"action": "none"}
    clock[0] += entry_greeting.SAME_ENTRY_SECONDS + 1
    assert entry_greeting.decide(MORNING)["action"] == "ask"

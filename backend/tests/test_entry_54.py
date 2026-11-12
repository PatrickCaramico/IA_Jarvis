"""V5.4: ao entrar na central, o briefing/pergunta valem para todos os aparelhos juntos (decisão no PC)."""
import random
from datetime import datetime

from modules import entry_greeting, prefs

MORNING = datetime(2026, 11, 12, 8, 0)


def test_first_entry_runs_briefing_then_asks_once_then_greets():
    assert entry_greeting.decide(MORNING) == {"action": "briefing", "command": "bom dia"}
    second = entry_greeting.decide(MORNING)
    assert second["action"] == "ask" and second["command"] == "bom dia"
    third = entry_greeting.decide(MORNING)
    assert third["action"] == "greet" and third["text"] in entry_greeting.QUICK_WELCOMES


def test_greeting_never_repeats_the_last_one():
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
    assert entry_greeting.decide(datetime(2026, 11, 14, 8, 0))["action"] == "greet"

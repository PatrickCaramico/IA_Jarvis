"""V6.5.3: a entrada não fala sempre a mesma coisa."""
import random

from modules import phrases


def test_never_repeats_the_last_two():
    rng = random.Random(7)
    recent = []
    for _ in range(200):
        i = phrases.choose_index(8, recent, rng)
        assert i not in recent[-phrases.AVOID_LAST:]
        recent.append(i)


def test_small_pool_still_works():
    assert phrases.choose_index(1, [0, 0]) == 0


def test_pick_varies_and_fills_fields():
    seen = set()
    for _ in range(30):
        text = phrases.pick("unlock_hello", tg="boa tarde", TG="Boa tarde", who=", Patrick")
        assert "{" not in text and "Patrick" in text
        seen.add(text)
    assert len(seen) >= 4  # várias versões de verdade


def test_every_pool_formats_without_name():
    for key, pool in phrases.POOLS.items():
        for _ in range(len(pool) * 2):
            text = phrases.pick(key, tg="bom dia", TG="Bom dia", who="", day="quinta-feira, 12 de novembro",
                                period="manhã")
            assert text and "{" not in text and " ." not in text and ",." not in text, (key, text)

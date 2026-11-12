"""V6.5.17: aviso diário (chuva amanhã) não se repete depois de reiniciar o JARVIS."""
from modules import triggers


def test_fired_survives_restart():
    triggers.reset_for_tests()
    assert triggers._new(("rain:2026-11-12", "Chuva amanhã."), "rain_tomorrow") is not None  # noqa: SLF001
    # "reinicia": memória vazia, lê do disco
    triggers._fired.clear()  # noqa: SLF001
    triggers._fired_loaded = False  # noqa: SLF001
    assert triggers._new(("rain:2026-11-12", "Chuva amanhã."), "rain_tomorrow") is None  # noqa: SLF001
    # no dia seguinte avisa de novo
    assert triggers._new(("rain:2026-11-13", "Chuva amanhã."), "rain_tomorrow") is not None  # noqa: SLF001
    triggers.reset_for_tests()

"""V8.13.1: bloqueio por ausência com 1 e 2 minutos (antes o mínimo era 5)."""
from modules import prefs


def test_new_short_relock_options():
    for minutes in (0, 1, 2, 5, 10, 15, 30):
        assert prefs.validate_patch({"lock_auto_relock_minutes": minutes}) is None, minutes
    for bad in (3, 7, -1, True, "1"):
        assert prefs.validate_patch({"lock_auto_relock_minutes": bad}) is not None, bad

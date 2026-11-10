"""Testes do PIN de reserva, do registro de tentativas e da política de acesso (seção 17 e Sentinela)."""
import json
import time

import pytest

from modules import access, lock_log, lock_pin, prefs


# ------------------------------------------------------------------ PIN
def test_pin_hash_salted_and_never_plain(isolated_data):
    lock_pin.set_pin("4821")
    raw = (isolated_data / "lock_pin.json").read_text(encoding="utf-8")
    assert "4821" not in raw
    data = json.loads(raw)
    assert data["algo"] == "scrypt" and len(bytes.fromhex(data["salt"])) == 16
    # Mesmo PIN gera hash diferente (sal novo)
    first_hash = data["hash"]
    lock_pin.set_pin("4821", current_pin="4821")
    assert json.loads((isolated_data / "lock_pin.json").read_text())["hash"] != first_hash


def test_pin_verify_ok_and_wrong(isolated_data):
    lock_pin.set_pin("123987")
    assert lock_pin.verify("123987")["verified"] is True
    res = lock_pin.verify("000000")
    assert res["verified"] is False and res["remaining_attempts"] == 4


def test_pin_format_validation(isolated_data):
    for bad in ("123", "123456789", "12a4", ""):
        with pytest.raises(lock_pin.PinError):
            lock_pin.set_pin(bad)


def test_pin_change_requires_current(isolated_data):
    lock_pin.set_pin("5555")
    with pytest.raises(lock_pin.PinError):
        lock_pin.set_pin("6666")
    with pytest.raises(lock_pin.PinError):
        lock_pin.set_pin("6666", current_pin="1111")
    lock_pin.set_pin("6666", current_pin="5555")
    assert lock_pin.verify("6666")["verified"]


def test_pin_lockout_persists_and_doubles(isolated_data):
    lock_pin.set_pin("2468")
    now = 1_000_000.0
    for _ in range(4):
        assert lock_pin.verify("1111", now=now)["reason"] == "wrong"
    res = lock_pin.verify("1111", now=now)
    assert res["reason"] == "locked_out" and res["locked_until"] == pytest.approx(now + 300)
    # Mesmo com o PIN certo, continua bloqueado (estado lido do arquivo = sobrevive a reinício)
    assert lock_pin.verify("2468", now=now + 10)["reason"] == "locked_out"
    assert lock_pin.status(now=now + 10)["locked_until"] == pytest.approx(now + 300)
    # Segundo bloqueio dobra (10 min)
    later = now + 301
    for _ in range(5):
        res = lock_pin.verify("1111", now=later)
    assert res["locked_until"] == pytest.approx(later + 600)
    # Limite máximo de 30 min
    t = later + 601
    for _round in range(4):
        for _ in range(5):
            res = lock_pin.verify("1111", now=t)
        assert res["locked_until"] - t <= 30 * 60
        t = res["locked_until"] + 1


def test_pin_never_in_log(isolated_data, caplog):
    caplog.set_level("DEBUG")
    lock_pin.set_pin("90817")
    lock_pin.verify("11111")
    lock_pin.verify("90817")
    assert "90817" not in caplog.text and "11111" not in caplog.text


def test_pin_clear(isolated_data):
    lock_pin.set_pin("7777")
    with pytest.raises(lock_pin.PinError):
        lock_pin.clear_pin("1234")
    lock_pin.clear_pin("7777")
    assert lock_pin.has_pin() is False


def test_weak_pin_detection():
    assert lock_pin.is_weak("1234") and lock_pin.is_weak("9999")
    assert not lock_pin.is_weak("4821")


# ------------------------------------------------------------------ registro
def test_lock_log_failures_since_last_success(isolated_data):
    lock_log.add("face", "ok")
    lock_log.add("face", "fail", 0.12)
    lock_log.add("pin", "fail")
    lock_log.add("face", "ok", 0.55)
    assert lock_log.failures_before_last_success() == 2
    lock_log.add("face", "ok", 0.6)
    assert lock_log.failures_before_last_success() == 0


def test_lock_log_limit_and_no_images(isolated_data):
    for i in range(250):
        lock_log.add("face", "fail", 0.1)
    entries = json.loads((isolated_data / "lock_log.json").read_text())
    assert len(entries) == 200
    assert set(entries[0]) <= {"at", "method", "result", "score", "mode"}


def test_intruder_retention(isolated_data):
    for i in range(25):
        p = lock_log.INTRUDERS_DIR
        p.mkdir(parents=True, exist_ok=True)
        (p / f"x{i:02d}.jpg").write_bytes(b"jpg")
    removed = lock_log.prune_intruders()
    assert removed == 5 and len(list(lock_log.INTRUDERS_DIR.glob("*.jpg"))) == 20
    old = lock_log.INTRUDERS_DIR / "x24.jpg"
    import os
    os.utime(old, (time.time() - 31 * 86400,) * 2)
    lock_log.prune_intruders()
    assert not old.exists()


# ------------------------------------------------------------------ política de acesso
def test_no_credentials_means_not_restricted(isolated_data):
    access.lock("t")
    assert access.effective_state() == access.UNLOCKED  # sem foto e sem PIN


def test_restricted_with_pin(isolated_data):
    lock_pin.set_pin("4821")
    access.lock("t")
    assert access.is_restricted()
    assert not access.is_allowed("GET", "/api/tasks")
    assert not access.is_allowed("GET", "/api/memory")
    assert access.is_allowed("GET", "/api/weather")
    assert access.is_allowed("POST", "/api/auth/pin")
    access.unlock("pin")
    assert access.is_allowed("GET", "/api/tasks")


def test_enforcement_can_be_disabled(isolated_data):
    lock_pin.set_pin("4821")
    prefs.update({"lock_backend_enforce": False})
    access.lock("t")
    assert not access.is_restricted()
    access.enter_guest()
    assert access.is_restricted()  # visitante sempre restringe
    assert not access.is_allowed("GET", "/api/tasks")


def test_guest_allows_music_but_locked_does_not(isolated_data):
    lock_pin.set_pin("4821")
    assert access.is_allowed("POST", "/api/integrations/spotify/control", access.GUEST)
    assert not access.is_allowed("POST", "/api/integrations/spotify/control", access.LOCKED)


def test_profile_photo_change_locked_only_without_pin(isolated_data):
    assert access.is_allowed("POST", "/api/profile", access.LOCKED)
    lock_pin.set_pin("4821")
    assert not access.is_allowed("POST", "/api/profile", access.LOCKED)


def test_public_prefs_have_no_personal_keys(isolated_data):
    data = prefs.get_all()
    pub = prefs.public_view(data)
    for key in ("custom_shortcuts", "widget_layout", "llm_provider", "camera_index", "lock_intro_playlist_uri"):
        assert key not in pub
    assert "clap_wake_enabled" in pub and "lock_cards" in pub


def test_prefs_validation():
    assert prefs.validate_patch({"clap_sensitivity": 11})
    assert prefs.validate_patch({"clap_sensitivity": True})
    assert prefs.validate_patch({"clap_scope": "sempre"})
    assert prefs.validate_patch({"lock_cards": ["clock", "agenda"]})
    assert prefs.validate_patch({"lock_auto_relock_minutes": 7})
    assert prefs.validate_patch({"water_vessel": "balde"})
    assert prefs.validate_patch({"water_quick_ml": [10]})
    assert prefs.validate_patch({"lock_intro_playlist_uri": "https://example.com/x"})
    ok = {"clap_sensitivity": 7, "clap_scope": "lock", "lock_cards": ["clock", "water", "clock"],
          "lock_auto_relock_minutes": 15, "water_vessel": "reactor", "water_quick_ml": [250, 500],
          "lock_intro_playlist_uri": "https://open.spotify.com/playlist/abc?si=1"}
    assert prefs.validate_patch(ok) is None
    assert ok["lock_cards"] == ["clock", "water"]

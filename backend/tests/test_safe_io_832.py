"""V8.3.2: gravar no OneDrive sem "Acesso negado" (o fan_cache.json não salvava)."""
import os

from core import safe_io


def test_replace_ok(tmp_path):
    t, tmp = tmp_path / "a.json", tmp_path / "a.tmp"
    t.write_text("velho")
    tmp.write_text("novo")
    safe_io.replace_file(tmp, t)
    assert t.read_text() == "novo" and not tmp.exists()


def test_replace_retries_then_works(tmp_path, monkeypatch):
    t, tmp = tmp_path / "a.json", tmp_path / "a.tmp"
    tmp.write_text("novo")
    real, fails, waits = os.replace, [2], []

    def flaky(a, b):
        if fails[0]:
            fails[0] -= 1
            raise PermissionError(5, "Acesso negado")
        real(a, b)

    monkeypatch.setattr(safe_io.os, "replace", flaky)
    safe_io.replace_file(tmp, t, sleep=waits.append)
    assert t.read_text() == "novo" and len(waits) == 2


def test_replace_falls_back_to_writing_over(tmp_path, monkeypatch):
    t, tmp = tmp_path / "fan_cache.json", tmp_path / "fan_cache.tmp"
    t.write_text("velho")
    tmp.write_text("novo")
    monkeypatch.setattr(safe_io.os, "replace", lambda a, b: (_ for _ in ()).throw(PermissionError(5, "Acesso negado")))
    safe_io.replace_file(tmp, t, sleep=lambda s: None)
    assert t.read_text() == "novo" and not tmp.exists()


def test_write_text(tmp_path):
    safe_io.write_text(tmp_path / "x.json", "{}")
    assert (tmp_path / "x.json").read_text() == "{}"


def test_all_tmp_replaces_use_safe_io():
    from pathlib import Path

    mods = Path(__file__).resolve().parents[1] / "modules"
    for name in ["sports_provider", "desk_missions", "face", "lock_pin", "profiles"]:
        src = (mods / f"{name}.py").read_text(encoding="utf-8")
        # V9.4.3: safe_io.write_json também vale (grava pelo replace_file e atualiza o cache de leitura)
        assert ("replace_file(" in src or "safe_io.write_json(" in src) and "tmp.replace(" not in src, name

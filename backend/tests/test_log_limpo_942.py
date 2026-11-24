"""V9.4.2: o que o log do PC mostrou — lista de programas lenta no Windows, ruído do asyncio e arquivo preso pelo
OneDrive."""
import os
import time
import types

import psutil
import pytest

import main
from core import safe_io
from modules import pc_scan, sports_provider

TASKLIST = '''"System Idle Process","0","Services","0","8 K"
"System","4","Services","0","2.944 K"
"chrome.exe","1200","Console","1","312.448 K"
"chrome.exe","1300","Console","1","100.000 K"
"Teams.exe","2000","Console","1","1,024 K"
"linha quebrada"
'''


def test_parse_and_group_tasklist():
    rows = pc_scan.parse_tasklist(TASKLIST)
    assert ("chrome.exe", 1200, 312448 * 1024) in rows and ("Teams.exe", 2000, 1024 * 1024) in rows  # "1,024" ou "1.024"
    groups = pc_scan.group(rows, me=999)
    assert set(groups) == {"chrome.exe", "teams.exe"}  # 0 e 4 (sistema) ficam de fora
    assert groups["chrome.exe"]["count"] == 2 and groups["chrome.exe"]["pids"] == [1200, 1300]


def test_windows_path_uses_one_tasklist_and_measures_cpu_only_of_the_heaviest(monkeypatch):
    calls = {"tasklist": 0, "cpu": []}

    def fake_tasklist():
        calls["tasklist"] += 1
        return pc_scan.parse_tasklist(TASKLIST)

    def fake_cpu(ps, groups, cores, wait=0.5):
        calls["cpu"].append([g["name"] for g in groups])

    monkeypatch.setattr(pc_scan, "os", types.SimpleNamespace(name="nt", getpid=lambda: 999))
    monkeypatch.setattr(pc_scan, "_tasklist", fake_tasklist)
    monkeypatch.setattr(pc_scan, "_cpu_for", fake_cpu)
    monkeypatch.setattr(pc_scan, "CPU_TOP_GROUPS", 1)
    out = {p["name"]: p for p in pc_scan._processes(psutil)}
    assert calls["tasklist"] == 1 and calls["cpu"] == [["chrome.exe"]]  # só o mais pesado
    assert out["chrome.exe"]["mem_mb"] == round((312448 + 100000) * 1024 / 1024 ** 2) and out["chrome.exe"]["count"] == 2


def test_falls_back_to_psutil_when_tasklist_fails(monkeypatch):
    def broken():
        raise RuntimeError("sem tasklist")

    monkeypatch.setattr(pc_scan, "os", types.SimpleNamespace(name="nt", getpid=os.getpid))
    monkeypatch.setattr(pc_scan, "_tasklist", broken)
    monkeypatch.setattr(pc_scan, "_cpu_for", lambda ps, groups, cores, wait=0.5: None)
    assert pc_scan._processes(psutil)  # a lista vem pelo psutil


@pytest.mark.skipif(os.name != "nt", reason="tasklist só existe no Windows")
def test_real_windows_listing_is_fast():
    t0 = time.monotonic()
    out = pc_scan._processes(psutil)
    assert time.monotonic() - t0 < 6 and len(out) > 5
    assert all(p["mem_mb"] >= 0 for p in out)


def test_connection_reset_is_quiet_other_errors_are_not():
    seen = []
    loop = types.SimpleNamespace(default_exception_handler=lambda ctx: seen.append(ctx))
    main.quiet_connection_reset(loop, {"message": "Exception in callback _ProactorBasePipeTransport._call_connection_lost(None)",
                                       "exception": ConnectionResetError(10054, "reset")})
    assert seen == []
    other = {"message": "Task exception was never retrieved", "exception": ValueError("x")}
    main.quiet_connection_reset(loop, other)
    assert seen == [other]


def test_locked_file_is_read_again(tmp_path, monkeypatch):
    path = tmp_path / "fan_cache.json"
    path.write_text('{"ok": true}', encoding="utf-8")
    real = type(path).read_text
    tries = {"n": 0}

    def flaky(self, *a, **k):
        tries["n"] += 1
        if tries["n"] < 3:
            raise PermissionError(13, "Permission denied")
        return real(self, *a, **k)

    monkeypatch.setattr(type(path), "read_text", flaky)
    monkeypatch.setattr(safe_io, "DELAY_S", 0)
    assert safe_io.read_text_retry(path, delay=0) == '{"ok": true}' and tries["n"] == 3
    monkeypatch.setattr(sports_provider, "CACHE_FILE", path)
    tries["n"] = 0
    assert sports_provider.load_fan_cache() == {"ok": True}

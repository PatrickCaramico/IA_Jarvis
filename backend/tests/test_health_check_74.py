"""V7.4: 🩺 DIAGNÓSTICO."""
import asyncio
from datetime import datetime

from fastapi.testclient import TestClient

import main
from modules import access, event_log, health_check


def test_data_check_finds_broken_json(tmp_path):
    (tmp_path / "ok.json").write_text('{"a": 1}', encoding="utf-8")
    assert health_check.check_data(tmp_path)["status"] == "ok"
    (tmp_path / "ruim.json").write_text("{quebrado", encoding="utf-8")
    item = health_check.check_data(tmp_path)
    assert item["status"] == "fail" and "ruim.json" in item["detail"] and item["fix"]


def test_errors_last_24h(isolated_data, monkeypatch):
    now = datetime(2026, 11, 13, 20, 0)
    monkeypatch.setattr(event_log, "list_events", lambda limit=50: [
        {"kind": "error", "message": "Falha X", "at": "2026-11-13T19:00:00"},
        {"kind": "error", "message": "Antiga", "at": "2026-11-10T10:00:00"},
        {"kind": "memory", "message": "ok", "at": "2026-11-13T19:30:00"},
    ])
    item = health_check.check_errors(now)
    assert item["status"] == "warn" and "1 erro" in item["detail"] and "Falha X" in item["detail"]


def test_ai_without_key_and_cache(monkeypatch):
    monkeypatch.setattr(health_check, "_ai_configured", lambda: False)
    item = asyncio.run(health_check.check_ai())
    assert item["status"] == "fail" and ".env" in item["fix"]


def test_route_runs_on_lock_screen(monkeypatch, credentials):
    async def fake(*a, **k):
        return health_check._item("x", "X", "ok", "ok")

    monkeypatch.setattr(health_check, "check_ai", fake)
    monkeypatch.setattr(health_check, "check_voice", fake)
    monkeypatch.setattr(health_check, "check_internet", lambda: health_check._item("internet", "I", "ok", "ok"))
    access.reset_for_tests(access.LOCKED)
    r = TestClient(main.app).get("/api/system/health-check")
    assert r.status_code == 200
    ids = [i["id"] for i in r.json()["items"]]
    assert ids[0] == "backend" and {"cloud", "disk", "data", "errors"} <= set(ids)

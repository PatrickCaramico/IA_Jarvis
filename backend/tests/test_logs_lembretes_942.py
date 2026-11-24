"""V9.4.2: janela 📜 LOGS (erros com o rastro completo) e a faixa de lembretes da central que atualiza na hora."""
from fastapi.testclient import TestClient

import main
from core import runtime
from modules import access, log_view

LOG = """2026-11-25 10:00:00,001 [INFO] jarvis.main: ligado
2026-11-25 10:00:05,002 [WARNING] jarvis.skills.auto_analise: Auto-análise: processos passou de 12 s; segui sem essa parte.
2026-11-25 10:01:00,003 [ERROR] jarvis.skills: skill=auto_analise status=error
Traceback (most recent call last):
  File "x.py", line 1, in <module>
TimeoutError: demorou
2026-11-25 10:02:00,004 [INFO] jarvis.tts: falando
"""


def test_parse_groups_traceback_and_filters(tmp_path):
    path = tmp_path / "jarvis.log"
    path.write_text(LOG, encoding="utf-8")
    entries = log_view.parse(LOG)
    assert [e["level"] for e in entries] == ["INFO", "WARNING", "ERROR", "INFO"]
    assert entries[2]["detail"].startswith("Traceback") and "TimeoutError: demorou" in entries[2]["detail"]
    r = log_view.read("WARNING", path=path)
    assert [e["level"] for e in r["items"]] == ["ERROR", "WARNING"] and r["errors"] == 1 and r["warnings"] == 1  # mais novo primeiro
    assert len(log_view.read("INFO", path=path)["items"]) == 4
    assert [e["level"] for e in log_view.read("INFO", query="auto-análise", path=path)["items"]] == ["WARNING"]
    assert log_view.read(path=tmp_path / "nao_existe.log")["items"] == []


def test_tail_reads_only_the_end(tmp_path):
    path = tmp_path / "jarvis.log"
    line = "2026-11-25 10:00:00,001 [ERROR] jarvis.x: erro número {}\n"
    path.write_text("".join(line.format(i) for i in range(20000)), encoding="utf-8")
    r = log_view.read("WARNING", limit=5, path=path)
    assert r["items"][0]["message"] == "erro número 19999" and len(r["items"]) == 5


def test_logs_route_is_private(isolated_data, monkeypatch, tmp_path):
    assert not access.is_allowed("GET", "/api/logs/file", access.LOCKED)
    path = tmp_path / "jarvis.log"
    path.write_text(LOG, encoding="utf-8")
    monkeypatch.setattr(log_view.settings, "LOG_FILE", path)
    access.reset_for_tests(access.UNLOCKED)
    r = TestClient(main.app).get("/api/logs/file?level=WARNING").json()
    assert r["errors"] == 1 and r["items"][0]["detail"].startswith("Traceback")


def test_reminder_create_and_delete_update_the_central(isolated_data, monkeypatch, tmp_path):
    from modules import reminders

    monkeypatch.setattr(reminders, "_REMINDERS_PATH", tmp_path / "lembretes.json")
    sent = []

    async def fake_broadcast(e):
        sent.append(e)

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    access.reset_for_tests(access.UNLOCKED)
    client = TestClient(main.app)
    rem = client.post("/api/reminders", json={"texto": "ligar para a mãe", "data_hora": "2030-01-01 09:00"}).json()["reminder"]
    assert {"type": "reminders_updated"} in sent
    sent.clear()
    assert client.delete(f"/api/reminders/{rem['id']}").json() == {"status": "ok"}
    assert sent == [{"type": "reminders_updated"}]

"""Arquivos por voz e sugestões pela rotina (4.2), em pastas temporárias."""
import asyncio
import os
import time
from datetime import datetime, timedelta

import pytest

from core import confirm, session
from modules import files, routine


@pytest.fixture
def home(tmp_path, monkeypatch):
    downloads = tmp_path / "Downloads"
    videos = tmp_path / "Videos"
    downloads.mkdir()
    videos.mkdir()
    monkeypatch.setattr(files, "personal_roots", lambda: [downloads, videos])
    monkeypatch.setattr(files, "UNDO_PATH", tmp_path / "undo.json")
    return tmp_path


def _touch(path, age_s=3600):
    path.write_bytes(b"x")
    t = time.time() - age_s
    os.utime(path, (t, t))
    return path


def test_parse_request_only_claims_file_words():
    assert files.parse_request("acha o video que gravei ontem") == {"kind": "video", "when": "yesterday", "words": []}
    req = files.parse_request("cade a planilha de gastos")
    assert req["kind"] == "sheet" and req["words"] == ["gastos"]
    assert files.parse_request("procura receita de bolo") is None  # continua indo para a web


def test_search_filters_by_kind_words_and_date(home):
    _touch(home / "Videos" / "gameplay final.mp4", age_s=60)
    _touch(home / "Videos" / "antigo.mp4", age_s=10 * 86400)
    _touch(home / "Downloads" / "gastos outubro.xlsx")
    found = files.search("video", [], "today", roots=files.personal_roots())
    assert [f["name"] for f in found] == ["gameplay final.mp4"]
    assert files.search("sheet", ["gastos"], roots=files.personal_roots())[0]["name"] == "gastos outubro.xlsx"
    assert files.search("pdf", [], roots=files.personal_roots()) == []


def test_followups():
    assert files.parse_followup("abre o segundo") == ("open", 1)
    assert files.parse_followup("mostra na pasta") == ("reveal", 0)
    assert files.parse_followup("abre o youtube") is None


def test_organize_plan_apply_and_undo(home):
    dl = home / "Downloads"
    _touch(dl / "foto.jpg")
    _touch(dl / "nota.pdf")
    _touch(dl / "setup.exe")
    _touch(dl / "baixando.crdownload")
    _touch(dl / "acabou_de_chegar.zip", age_s=5)
    (dl / "Imagens").mkdir()
    _touch(dl / "Imagens" / "foto.jpg")  # mesmo nome já existe no destino
    plan = files.plan_organize(dl)
    assert plan["counts"] == {"Imagens": 1, "PDFs": 1, "Instaladores": 1}
    msg = files.apply_plan(plan)
    assert "3 arquivos" in msg
    assert (dl / "Imagens" / "foto (2).jpg").exists()  # nada sobrescrito
    assert (dl / "baixando.crdownload").exists() and (dl / "acabou_de_chegar.zip").exists()
    assert "3 arquivos voltaram" in files.undo_last()
    assert (dl / "foto.jpg").exists() and (dl / "nota.pdf").exists() and not (dl / "PDFs").exists()


def test_organize_refuses_outside_personal_folders(home, tmp_path):
    other = tmp_path / "Sistema"
    other.mkdir()
    _touch(other / "a.txt")
    plan = files.plan_organize(other)
    assert "segurança" in files.apply_plan(plan)
    assert (other / "a.txt").exists()


def test_organize_waits_for_yes(home, monkeypatch):
    monkeypatch.setattr(files, "folder_by_name", lambda name: home / "Downloads")
    _touch(home / "Downloads" / "nota.pdf")
    session.pending_action = None
    reply = asyncio.run(files.handle_voice("organiza a pasta downloads"))
    assert "Posso mover?" in reply and (home / "Downloads" / "nota.pdf").exists()
    assert "1 arquivos organizados" in asyncio.run(confirm.answer("sim"))
    assert (home / "Downloads" / "PDFs" / "nota.pdf").exists()


# ------------------------------------------------------------------ rotina
def _events(key, label, kind, value, days, hour, minute=0, now=None):
    now = now or datetime(2026, 10, 30, 8, 0, tzinfo=routine.SP_TZ)
    return [{"key": key, "label": label, "kind": kind, "value": value,
             "ts": (now - timedelta(days=d)).replace(hour=hour, minute=minute).isoformat(timespec="minutes")}
            for d in days]


def test_habit_needs_three_days_same_time():
    now = datetime(2026, 10, 30, 8, 55, tzinfo=routine.SP_TZ)
    ev = _events("protocol:trabalho", "Trabalho", "protocol", "trabalho", [1, 2, 3], 9, 5, now)
    habits = routine.find_habits(ev, now)
    assert habits and habits[0]["minute"] == 9 * 60 + 5
    assert routine.find_habits(ev[:2], now) == []
    scattered = _events("open:x", "X", "open", "x", [1], 9) + _events("open:x", "X", "open", "x", [2], 14) \
        + _events("open:x", "X", "open", "x", [3], 20)
    assert routine.find_habits(scattered, now) == []


def test_due_suggestion_once_per_day_and_dismiss(tmp_path, monkeypatch):
    monkeypatch.setattr(routine, "DATA_PATH", tmp_path / "rotina.json")
    now = datetime(2026, 10, 30, 8, 58, tzinfo=routine.SP_TZ)
    for ev in _events("protocol:trabalho", "Trabalho", "protocol", "trabalho", [1, 2, 4], 9, 0, now):
        routine.record(ev["key"], ev["label"], ev["kind"], ev["value"], now=datetime.fromisoformat(ev["ts"]))
    first = routine.due_suggestion(now)
    assert first and "protocolo Trabalho" in first["text"] and "9h" in first["text"]
    assert routine.due_suggestion(now + timedelta(minutes=5)) is None  # já ofereceu hoje
    routine.dismiss("protocol:trabalho", forever=True)
    assert routine.summary(now)["muted"] == ["protocol:trabalho"]
    assert routine.due_suggestion(now + timedelta(days=1)) is None


def test_confirm_yes_runs_routine(monkeypatch):
    called = {}

    async def fake_execute(habit):
        called["habit"] = habit["key"]
        return "Protocolo trabalho ativo."

    monkeypatch.setattr(routine, "execute", fake_execute)
    monkeypatch.setattr(routine, "dismiss", lambda key, forever=False: called.setdefault("dismiss", (key, forever)))
    confirm.offer("routine", {"key": "protocol:trabalho"})
    assert asyncio.run(confirm.answer("pode")) == "Protocolo trabalho ativo."
    assert confirm.pending() is None
    confirm.offer("routine", {"key": "protocol:trabalho"})
    assert "Não vou mais sugerir" in asyncio.run(confirm.answer("nao sugira mais isso"))
    assert called["dismiss"] == ("protocol:trabalho", True)
    confirm.offer("routine", {"key": "k"})
    assert asyncio.run(confirm.answer("qual a previsao do tempo")) is None  # outra pergunta: segue o fluxo normal
    session.pending_action = None

"""Botão ATUALIZAR: baixa a versão nova, avisa por voz e reinicia (Git e reinício simulados)."""
import time

from fastapi.testclient import TestClient

import main
from config import settings
from core import speech
from modules import self_update


def _patch(monkeypatch, pull_result):
    calls = {"restart": 0, "said": []}

    async def fake_say(text):
        calls["said"].append(text)

    def fake_restart():
        calls["restart"] += 1
        return True

    monkeypatch.setattr(self_update, "pull", lambda: pull_result)
    monkeypatch.setattr(self_update, "restart", fake_restart)
    monkeypatch.setattr(speech, "say_quietly", fake_say)
    return calls


def _wait(cond, seconds=2.0):
    end = time.monotonic() + seconds
    while time.monotonic() < end and not cond():
        time.sleep(0.02)
    return cond()


def test_atualiza_fala_e_reinicia(monkeypatch):
    calls = _patch(monkeypatch, {"ok": True, "changed": True, "before": "a1", "after": "b2", "message": "ok"})
    with TestClient(main.app) as client:
        res = client.post("/api/system/update", json={"confirm": True})
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "restarting" and body["changed"] is True
        assert body["boot_id"] == client.get("/api/health").json()["boot_id"]
        assert _wait(lambda: calls["restart"] == 1)
    assert calls["said"] == ["Senhor, estou atualizando os meus sistemas. Volto em instantes."]


def test_falha_no_git_nao_reinicia(monkeypatch):
    calls = _patch(monkeypatch, {"ok": False, "changed": False, "before": "a1", "after": "a1", "message": "mudanças locais"})
    with TestClient(main.app) as client:
        res = client.post("/api/system/update", json={"confirm": True})
        assert res.status_code == 200 and res.json()["status"] == "error"
        time.sleep(0.2)
    assert calls["restart"] == 0


def test_recusa_outro_site_e_pedido_sem_confirmacao(monkeypatch):
    calls = _patch(monkeypatch, {"ok": True, "changed": False, "before": "", "after": "", "message": ""})
    client = TestClient(main.app)
    assert client.post("/api/system/update", json={"confirm": True},
                       headers={"Origin": "https://site-qualquer.example"}).status_code == 403
    assert client.post("/api/system/update", json={"confirm": False}).status_code == 400
    assert client.post("/api/system/update", content="confirm=true",
                       headers={"content-type": "text/plain"}).status_code in (400, 422)
    ok = client.post("/api/system/update", json={"confirm": True}, headers={"Origin": settings.SITE_ORIGIN})
    assert ok.status_code == 200
    assert _wait(lambda: calls["restart"] == 1)


def test_pull_sem_git_so_reinicia(monkeypatch, tmp_path):
    monkeypatch.setattr(self_update, "ROOT", tmp_path)
    result = self_update.pull()
    assert result["ok"] is True and result["changed"] is False

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
    monkeypatch.setattr(self_update, "frontend_stale", lambda: False)
    monkeypatch.setattr(self_update, "check", lambda force=False: {"notes": ["JARVIS 9.9.9: teste"]})
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
    # V8.15.1: com o "with", o laço de eventos vive até o fim do teste. Sem ele, cada pedido tinha um laço próprio
    # desmontado na resposta, e a tarefa de reinício (runtime.track) às vezes morria antes de rodar (falha rara,
    # que aparecia com a máquina carregada).
    with TestClient(main.app) as client:
        assert client.post("/api/system/update", json={"confirm": True},
                           headers={"Origin": "https://site-qualquer.example"}).status_code == 403
        assert client.post("/api/system/update", json={"confirm": False}).status_code == 400
        assert client.post("/api/system/update", content="confirm=true",
                           headers={"content-type": "text/plain"}).status_code in (400, 422)
        ok = client.post("/api/system/update", json={"confirm": True}, headers={"Origin": settings.SITE_ORIGIN})
        assert ok.status_code == 200
        assert _wait(lambda: calls["restart"] == 1, seconds=5.0)


def test_pull_sem_git_so_reinicia(monkeypatch, tmp_path):
    monkeypatch.setattr(self_update, "ROOT", tmp_path)
    result = self_update.pull()
    assert result["ok"] is True and result["changed"] is False


def test_v817_build_antes_de_reiniciar_e_voz_nao_segura(monkeypatch):
    """V8.1.7: a interface nova é montada com o JARVIS ainda ligado; a voz lenta não atrasa o reinício."""
    import asyncio

    calls = _patch(monkeypatch, {"ok": True, "changed": True, "before": "a1", "after": "b2", "message": "ok"})
    order = []

    async def slow_say(text):
        await asyncio.sleep(30)

    monkeypatch.setattr(speech, "say_quietly", slow_say)
    monkeypatch.setattr(self_update, "frontend_stale", lambda: True)
    monkeypatch.setattr(self_update, "fetch_prebuilt", lambda: order.append("fetch") and False)  # site sem a versão pronta
    monkeypatch.setattr(self_update, "build_frontend", lambda: order.append("build") or True)

    def fake_restart():
        order.append("restart")
        calls["restart"] += 1
        return True

    monkeypatch.setattr(self_update, "restart", fake_restart)
    with TestClient(main.app) as client:
        t0 = time.monotonic()
        assert client.post("/api/system/update", json={"confirm": True}).json()["status"] == "restarting"
        assert _wait(lambda: calls["restart"] == 1, seconds=8)
        assert time.monotonic() - t0 < 7  # não esperou os 30 s da fala
        p = client.get("/api/system/update/progress").json()
        assert p["etapa"] == "reiniciando" and p["depois"] == "b2" and p["notas"] == ["JARVIS 9.9.9: teste"]
    assert order == ["fetch", "restart"]  # V8.2.3: não monta mais antes de reiniciar


def test_v817_frontend_stale(monkeypatch, tmp_path):
    fe = tmp_path / "frontend"
    (fe / "src").mkdir(parents=True)
    monkeypatch.setattr(self_update, "FRONTEND", fe)
    assert self_update.frontend_stale() is True  # sem build
    (fe / "src" / "a.js").write_text("x")
    (fe / "dist").mkdir()
    (fe / "dist" / "index.html").write_text("<html>")
    import os

    os.utime(fe / "src" / "a.js", (1, 1))
    # V8.11: datas fixas. No Windows, o index.html e o b.js gravados em seguida saíam com o MESMO horário e o
    # "b.js é mais novo" falhava às vezes (teste instável no CI).
    os.utime(fe / "dist" / "index.html", (1000, 1000))
    assert self_update.frontend_stale() is False
    (fe / "src" / "b.js").write_text("novo")
    os.utime(fe / "src" / "b.js", (2000, 2000))
    assert self_update.frontend_stale() is True


def test_v821_build_does_not_wait_for_pipes(monkeypatch, tmp_path):
    """V8.2.1: o build escreve num arquivo e o JARVIS espera só o processo (não o tubo); passou do tempo, encerra."""
    import shutil as _sh
    import sys

    fe = tmp_path / "frontend"
    (fe / "node_modules").mkdir(parents=True)
    monkeypatch.setattr(self_update, "FRONTEND", fe)
    monkeypatch.setattr(self_update, "ROOT", tmp_path)
    script = tmp_path / "fake_npm.py"
    # o "build" deixa um filho vivo segurando a saída (como o esbuild no Windows) e termina na hora
    script.write_text("import subprocess, sys, time\nsubprocess.Popen([sys.executable, '-c', 'import time; time.sleep(20)'])\nprint('built')\n")
    monkeypatch.setattr(_sh, "which", lambda name: "x" if name in ("npm.cmd", "npm") else None)
    real_popen = self_update.subprocess.Popen
    monkeypatch.setattr(self_update.subprocess, "Popen", lambda cmd, **kw: real_popen([sys.executable, str(script)], **kw))
    t0 = time.monotonic()
    assert self_update.build_frontend() is True
    assert time.monotonic() - t0 < 10
    assert "built" in (tmp_path / "logs" / "build.log").read_text()

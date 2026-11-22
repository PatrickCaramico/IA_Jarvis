"""V8.11: "microfone só no botão" (nada fica ouvindo sozinho: a música no fone não fica distorcida)."""
import asyncio
import sys
import threading
from pathlib import Path

from core.skills import registry, router
from modules import prefs

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import clap_launcher as cl  # noqa: E402
import voice_listener as vl  # noqa: E402


def test_default_is_push_to_talk_and_readable_while_locked():
    assert prefs.get_all()["mic_push_to_talk"] is True
    assert "mic_push_to_talk" in prefs.public_view(prefs.get_all())  # o ouvido e as palmas leem sem a chave
    assert prefs.validate_patch({"mic_push_to_talk": "sim"})


def test_voice_switch(real_skills, monkeypatch):
    from core import runtime

    sent = []

    async def fake_broadcast(event):
        sent.append(event)

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    for phrase, value in [("microfone so no botao", True), ("para de me ouvir o tempo todo", True),
                          ("pode ficar me ouvindo o tempo todo", False), ("liga a escuta continua", False)]:
        sk, args = registry.match(phrase, phrase)
        assert sk.name == "modo_microfone" and args == {"so_no_botao": value}
    reply = asyncio.run(router.try_fast_path("pode ficar me ouvindo o tempo todo"))
    assert "volto a ouvir" in reply.speech and prefs.get_all()["mic_push_to_talk"] is False
    asyncio.run(router.try_fast_path("microfone só no botão"))
    assert prefs.get_all()["mic_push_to_talk"] is True
    assert sent[-1] == {"type": "prefs_updated", "mic_push_to_talk": True}  # a central troca na hora
    assert registry.match("liga o microfone", "liga o microfone") is None


def test_offline_ear_follows_the_preference():
    assert vl.push_to_talk({"prefs": {"mic_push_to_talk": False}}) is False
    assert vl.push_to_talk({"mic_push_to_talk": True}, last=False) is True
    assert vl.push_to_talk(None, last=False) is False  # JARVIS fora do ar: o último valor conhecido
    assert vl.push_to_talk(None) is True  # nunca soube: microfone fechado


def test_offline_ear_gate_reads_it(monkeypatch):
    answers = {"/api/health": {"status": "ok"}, "/api/lock/status": {"devices": 0, "phones": 0},
               "/api/prefs": {"prefs": {"mic_push_to_talk": False, "voice_listener_enabled": True}}}
    monkeypatch.setattr(vl, "_get", lambda path: answers.get(path))
    gate = vl.Gate()
    assert gate.push_to_talk is True
    gate.poll()
    assert gate.push_to_talk is False and gate.open is True
    answers["/api/prefs"] = {"prefs": {"mic_push_to_talk": True}}
    gate.at = 0
    gate.poll()
    assert gate.push_to_talk is True


def test_clap_listener_keeps_the_mic_closed(monkeypatch, tmp_path):
    path = tmp_path / "microfone_botao"
    monkeypatch.setattr(cl, "PTT_PATH", path)
    assert cl.last_push_to_talk() is True
    cl.save_push_to_talk(False)
    assert cl.last_push_to_talk() is False
    assert cl.read_push_to_talk(fetch=lambda url: {"prefs": {"mic_push_to_talk": True}}) is True
    assert cl.read_push_to_talk(fetch=lambda url: None) is False  # JARVIS fora: última escolha

    cfg = dict(cl.load_config()) if hasattr(cl, "load_config") else {}
    listener = cl.Listener({**cfg, "presence_interval_s": 0}, test_mode=False)
    monkeypatch.setattr(cl, "probe", lambda: (True, 0))
    monkeypatch.setattr(cl, "read_push_to_talk", lambda fetch=None: True)
    calls = {"n": 0}

    def stop_after_one(timeout=None):
        calls["n"] += 1
        listener.stop.set()
        return True

    monkeypatch.setattr(listener.stop, "wait", stop_after_one)
    threading.Thread(target=listener.presence_loop).run()
    assert listener.paused.is_set()  # microfone fechado mesmo sem página aberta
    assert cl.last_push_to_talk() is True

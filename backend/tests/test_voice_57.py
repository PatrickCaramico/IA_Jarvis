"""V5.7: a voz sai no aparelho que pediu (celular) e não na caixa de som do PC."""
import asyncio

from fastapi.testclient import TestClient

import main
from core import runtime, speech, voice_route
from modules import access, prefs


def test_target_rules():
    assert voice_route.target_for("cabc12345", "app", True) == "cabc12345"      # app do celular
    assert voice_route.target_for("cabc12345", "web", False) == "cabc12345"     # navegador de outro aparelho
    assert voice_route.target_for("cabc12345", "web", True) is None             # central no próprio PC
    assert voice_route.target_for("cabc12345", "pc", False) is None             # celular escolheu "voz no PC"
    assert voice_route.target_for("x", "app", False) is None                    # id inválido


def _capture(monkeypatch):
    events, played = [], []

    async def fake_broadcast(ev):
        events.append(ev)

    async def fake_play(text, on_playback_start=None):
        played.append(text)

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    monkeypatch.setattr(speech, "generate_and_play_speech", fake_play)
    monkeypatch.setattr(voice_route, "estimate_seconds", lambda text: 0)
    prefs.update(silent_mode=False)
    return events, played


def test_phone_request_speaks_only_on_phone(monkeypatch):
    events, played = _capture(monkeypatch)

    async def run():
        token = voice_route.set_target("cphone1234")
        try:
            await speech.speak("Olá do celular.")
        finally:
            voice_route.reset(token)

    asyncio.run(run())
    assert played == []
    assert {"type": "speak_on_device", "client_id": "cphone1234", "text": "Olá do celular."} in events


def test_pc_request_speaks_on_pc(monkeypatch):
    events, played = _capture(monkeypatch)
    asyncio.run(speech.speak("Olá do PC."))
    assert played == ["Olá do PC."] and not any(e.get("type") == "speak_on_device" for e in events)


def test_speak_on_pc_route_forces_the_pc(monkeypatch):
    said = []

    async def fake_quiet(text):
        said.append(text)

    monkeypatch.setattr(speech, "say_quietly", fake_quiet)
    access.reset_for_tests(access.UNLOCKED)
    client = TestClient(main.app)
    res = client.post("/api/speak/pc", json={"text": "O jantar está pronto!"},
                      headers={"X-Jarvis-Client": "cphone1234", "X-Jarvis-Device": "app"})
    assert res.status_code == 200
    assert client.post("/api/speak/pc", json={"text": "  "}).status_code == 400
    access.reset_for_tests(access.LOCKED)


def test_middleware_routes_speak_request_to_the_phone(monkeypatch):
    events, played = _capture(monkeypatch)
    access.reset_for_tests(access.UNLOCKED)
    with TestClient(main.app) as client:
        client.post("/api/speak", json={"text": "Teste no celular."},
                    headers={"X-Jarvis-Client": "cphone1234", "X-Jarvis-Device": "app"})
        for _ in range(50):
            if any(e.get("type") == "speak_on_device" for e in events):
                break
            asyncio.run(asyncio.sleep(0.02))
    access.reset_for_tests(access.LOCKED)
    assert played == []
    assert any(e.get("type") == "speak_on_device" and e["client_id"] == "cphone1234" for e in events)

"""V5.5: aparelhos conectados e voz tocada no próprio aparelho (/api/tts)."""
from pathlib import Path

from fastapi.testclient import TestClient

import main
from core import runtime
from modules import access
from modules import tts as tts_module

APP_UA = ("Mozilla/5.0 (Linux; Android 14; SM-A546E Build/UP1A.231005.007; wv) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Version/4.0 Chrome/130.0 Mobile Safari/537.36 JarvisApp/5.5.0")
CHROME_PHONE = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36"


def test_device_names():
    assert runtime.describe_device("192.168.1.58", APP_UA, False)["name"] == "Celular · SM-A546E"
    assert runtime.describe_device("192.168.1.58", APP_UA, False)["kind"] == "app"
    assert runtime.describe_device("127.0.0.1", "Mozilla/5.0 (Windows NT 10.0)", True)["name"] == "Este PC"
    assert runtime.describe_device("192.168.1.70", CHROME_PHONE, False)["name"] == "Navegador do celular"


def test_websocket_lists_devices_and_endpoint():
    access.reset_for_tests(access.UNLOCKED)
    client = TestClient(main.app)
    with client.websocket_connect("/ws") as ws:
        events = [ws.receive_json() for _ in range(3)]
        devices = next(e for e in events if e["type"] == "devices")
        assert any(d["kind"] == "pc" for d in devices["items"])
        listed = client.get("/api/devices").json()["items"]
        assert [d["name"] for d in listed].count("Este PC") == 1
    access.reset_for_tests(access.LOCKED)


def test_tts_returns_mp3(monkeypatch):
    async def fake(text, path):
        Path(path).write_bytes(b"ID3fake-mp3")

    monkeypatch.setattr(tts_module, "_synthesize", fake)
    access.reset_for_tests(access.UNLOCKED)
    res = TestClient(main.app).post("/api/tts", json={"text": "Olá, senhor."})
    assert res.status_code == 200 and res.headers["content-type"] == "audio/mpeg" and res.content == b"ID3fake-mp3"
    assert TestClient(main.app).post("/api/tts", json={"text": "  "}).status_code == 400
    access.reset_for_tests(access.LOCKED)

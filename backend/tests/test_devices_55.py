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


def test_lock_status_is_public_and_has_nothing_personal():
    """V5.6.1: cartão SISTEMAS do bloqueio funciona bloqueado e não mostra nomes nem rótulos."""
    from datetime import datetime, timedelta

    from modules import alarms

    access.reset_for_tests(access.LOCKED)
    alarms.add_alarm(datetime.now() + timedelta(days=1), label="remédio secreto")
    data = TestClient(main.app).get("/api/lock/status").json()
    assert set(data) == {"devices", "phones", "next_alarm"}
    assert data["next_alarm"].startswith("amanhã às") and "remédio" not in str(data)


def test_lock_public_info_works_locked(monkeypatch):
    """V5.8: cotações e manchete do bloqueio: rota pública, só dado público."""
    from modules import news_radar
    from routes import access as access_routes
    from services import quotes

    monkeypatch.setattr(quotes, "fetch_rates", lambda: {"USDBRL": {"code": "USD", "name": "Dólar", "bid": "5.5",
                                                                   "pctChange": "0.2", "high": "5.6", "low": "5.4"}})
    monkeypatch.setattr(news_radar, "fetch_news_by_category",
                        lambda cat, limit=3: [{"title": "Manchete X", "source": "g1"}] if cat == "brasil" else [])
    access_routes._PUBLIC_INFO.update(at=0.0, data=None)
    access.reset_for_tests(access.LOCKED)
    data = TestClient(main.app).get("/api/lock/public-info").json()
    assert data["rates"][0]["code"] == "USD" and data["rates"][0]["bid"] == 5.5
    assert data["headline"] == {"title": "Manchete X", "source": "g1", "published": "", "category": "brasil"}

"""V4.5: app Android — página de download, APK, pareamento e regras de acesso."""
from fastapi.testclient import TestClient

import main
from core import runtime
from modules import access
from routes import mobile


def _client(host="testclient"):
    return TestClient(main.app, client=(host, 50000))


def test_info_has_download_without_token(monkeypatch):
    monkeypatch.setattr(mobile, "local_ip", lambda: "192.168.0.10")
    access.reset_for_tests(access.LOCKED)
    data = _client().get("/api/mobile/info").json()  # pública com a central bloqueada
    assert data["download_url"] == "http://192.168.0.10:8000/api/mobile"
    assert runtime.ACCESS_TOKEN not in str(data)  # o QR do bloqueio nunca leva o token


def test_download_page_and_apk(monkeypatch, tmp_path):
    access.reset_for_tests(access.LOCKED)
    monkeypatch.setattr(mobile, "APK_PATH", tmp_path / "JARVIS.apk")
    page = _client().get("/api/mobile")
    assert page.status_code == 200 and "APP AINDA NÃO GERADO" in page.text
    assert _client().get("/api/mobile/app.apk").status_code == 404

    (tmp_path / "JARVIS.apk").write_bytes(b"PK\x03\x04fake")
    page = _client().get("/api/mobile")
    assert "BAIXAR JARVIS.apk" in page.text and runtime.ACCESS_TOKEN not in page.text
    apk = _client().get("/api/mobile/app.apk")
    assert apk.status_code == 200
    assert apk.headers["content-type"] == "application/vnd.android.package-archive"


def test_phone_without_token_only_reaches_download(monkeypatch, tmp_path):
    """Celular na rede (modo rede ligado), sem token: baixa o app, mas não acessa o resto."""
    monkeypatch.setattr(main.settings, "NETWORK_MODE", True)
    monkeypatch.setattr(mobile, "APK_PATH", tmp_path / "JARVIS.apk")
    (tmp_path / "JARVIS.apk").write_bytes(b"PK")
    phone = _client("192.168.0.50")
    assert phone.get("/api/mobile").status_code == 200
    assert phone.get("/api/mobile/app.apk").status_code == 200
    assert phone.get("/api/mobile/pair").status_code == 401   # pareamento exige o token
    assert phone.get("/api/mobile/info").status_code == 401
    assert phone.get("/api/health").status_code == 401

    monkeypatch.setattr(main.settings, "NETWORK_MODE", False)
    assert phone.get("/api/mobile").status_code == 403        # modo rede desligado: nada


def test_notifications_feed_needs_token_even_locally():
    """Os avisos (podem ser pessoais) só saem com a chave de pareamento, mesmo do próprio PC."""
    access.reset_for_tests(access.LOCKED)
    runtime.NOTIFY_FEED.clear()
    client = _client()
    assert client.get("/api/mobile/notifications").status_code == 401
    t = runtime.ACCESS_TOKEN
    start = client.get(f"/api/mobile/notifications?since=-1&token={t}").json()
    assert start["items"] == []
    runtime.notify("reminder", "Lembrete do JARVIS", "Ligar para o dentista")
    runtime.notify("fan", "⚽ GOL DO PALMEIRAS!", "Palmeiras 1 a 0 Remo.")
    got = client.get(f"/api/mobile/notifications?since={start['latest']}", headers={"X-Jarvis-Token": t}).json()
    assert [n["title"] for n in got["items"]] == ["Lembrete do JARVIS", "⚽ GOL DO PALMEIRAS!"]
    assert got["items"][0]["body"] == "Ligar para o dentista"  # o celular pareado recebe o texto completo
    again = client.get(f"/api/mobile/notifications?since={got['latest']}&token={t}").json()
    assert again["items"] == []


def test_reminder_alert_reaches_phone_but_screen_stays_generic(monkeypatch):
    import asyncio

    from core import speech

    sent = []

    async def fake_broadcast(event):
        sent.append(event)

    async def quiet(text):
        return None

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    monkeypatch.setattr(speech, "say_quietly", quiet)
    monkeypatch.setattr(access, "is_restricted", lambda: True)
    runtime.NOTIFY_FEED.clear()
    asyncio.run(speech.announce("Reunião com a Ana às 15h"))
    assert sent[-1]["text"] == speech.LOCKED_ALERT            # a tela bloqueada não mostra o conteúdo
    assert runtime.NOTIFY_FEED[-1]["body"] == "Reunião com a Ana às 15h"  # o celular pareado mostra


def test_pair_with_owner_pin(monkeypatch, tmp_path):
    """O app pareia com o PIN do dono (sem token), só no modo rede, e conta no limite de tentativas."""
    from modules import lock_pin, profiles

    monkeypatch.setattr(main.settings, "NETWORK_MODE", True)
    monkeypatch.setattr(main.settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr(lock_pin, "PIN_PATH", tmp_path / "lock_pin.json")
    phone = _client("192.168.0.50")
    assert phone.post("/api/mobile/pair-pin", json={"pin": "4826"}).status_code == 403  # sem PIN no PC: não pareia
    lock_pin.set_pin("4826")
    bad = phone.post("/api/mobile/pair-pin", json={"pin": "1111"})
    assert bad.status_code == 403 and "Restam" in bad.json()["detail"]
    ok = phone.post("/api/mobile/pair-pin", json={"pin": "4826"})
    assert ok.status_code == 200
    # mesmo endereço que o celular usou para chegar ao PC, na porta da interface, com a chave
    assert ok.json()["url"].endswith(f":5173/?token={runtime.ACCESS_TOKEN}")
    assert phone.get("/api/health").status_code == 401  # sem a chave, o resto continua fechado
    assert profiles.active_id() == profiles.OWNER_ID


def test_download_page_has_open_app_button(monkeypatch, tmp_path):
    monkeypatch.setattr(mobile, "APK_PATH", tmp_path / "JARVIS.apk")
    (tmp_path / "JARVIS.apk").write_bytes(b"PK")
    page = _client().get("/api/mobile")
    assert "ABRIR O JARVIS" in page.text and "scheme=jarvis" in page.text and "setup?host=" in page.text


def test_pair_page_opens_app_with_token(monkeypatch, credentials):
    monkeypatch.setattr(main.settings, "NETWORK_MODE", True)
    access.reset_for_tests(access.UNLOCKED)
    page = _client("192.168.0.50").get(f"/api/mobile/pair?token={runtime.ACCESS_TOKEN}")
    assert page.status_code == 200
    assert "intent://connect?url=" in page.text and "package=com.patrick.jarvis" in page.text
    assert "jarvis://connect?url=" in page.text
    access.reset_for_tests(access.LOCKED)
    # Com a central bloqueada, o pareamento não abre (só quem entrou no PC pareia)
    assert _client("192.168.0.50").get(f"/api/mobile/pair?token={runtime.ACCESS_TOKEN}").status_code == 403


def test_qr_abre_o_app_instalado_e_so_baixa_sem_ele(monkeypatch):
    """V5.1.1: a página do QR tenta abrir o app (que se atualiza sozinho); sem o app, baixa o APK."""
    from fastapi.testclient import TestClient

    import main
    from routes import mobile

    class FakeApk:
        def exists(self):
            return True

        def stat(self):
            class S:
                st_size = 74596
            return S()

    monkeypatch.setattr(mobile, "APK_PATH", FakeApk())
    client = TestClient(main.app, base_url="http://192.168.15.7:8000")
    html = client.get("/api/mobile").text
    assert "intent://open?host=192.168.15.7#Intent;scheme=jarvis;package=com.patrick.jarvis;" in html
    assert "S.browser_fallback_url=http%3A%2F%2F192.168.15.7%3A8000%2Fapi%2Fmobile%2Fapp.apk" in html
    assert "o app se atualiza sozinho" in html and "<script>" in html
    assert "<script>" not in client.get("/api/mobile?app=0").text  # sem o app: não tenta de novo


def test_pair_qr_opens_app_by_itself_and_offers_download(monkeypatch):
    """V5.4: o QR de pareamento abre o app sozinho; sem o app, a página volta oferecendo o APK."""
    monkeypatch.setattr(main.settings, "NETWORK_MODE", True)
    monkeypatch.setattr(mobile, "apk_available", lambda: True)
    access.reset_for_tests(access.UNLOCKED)
    try:
        page = _client("192.168.0.50").get(f"/api/mobile/pair?token={runtime.ACCESS_TOKEN}").text
        assert "location.href" in page and "S.browser_fallback_url" in page and "app%3D0" in page
        fallback = _client("192.168.0.50").get(f"/api/mobile/pair?token={runtime.ACCESS_TOKEN}&app=0").text
        assert "location.href" not in fallback and "BAIXAR JARVIS.apk" in fallback
    finally:
        access.reset_for_tests(access.LOCKED)

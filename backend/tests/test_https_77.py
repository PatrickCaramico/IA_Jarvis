"""V7.7: conexão criptografada (https) na rede de casa."""
import ssl

from cryptography import x509
from fastapi.testclient import TestClient

import main
from core import runtime
from modules import access, tls


def test_certificate_covers_addresses_and_is_signed_by_jarvis(tmp_path):
    p = tls.ensure(tmp_path, dns=["localhost", "meupc"], ips=["127.0.0.1", "192.168.0.10"])
    ca = x509.load_pem_x509_certificate(p["ca_crt"].read_bytes())
    pc = x509.load_pem_x509_certificate(p["crt"].read_bytes())
    san = pc.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert {str(i) for i in san.get_values_for_type(x509.IPAddress)} == {"127.0.0.1", "192.168.0.10"}
    assert pc.issuer == ca.subject
    pc.verify_directly_issued_by(ca)
    # o python aceita o par chave/certificado num servidor TLS de verdade
    ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER).load_cert_chain(str(p["crt"]), str(p["key"]))
    assert len(tls.ca_fingerprint(tmp_path).split(":")) == 32


def test_new_ip_remakes_pc_certificate_but_keeps_authority(tmp_path):
    first = tls.ensure(tmp_path, dns=["localhost"], ips=["127.0.0.1", "192.168.0.10"])
    ca_before, pc_before = first["ca_crt"].read_bytes(), first["crt"].read_bytes()
    tls.ensure(tmp_path, dns=["localhost"], ips=["127.0.0.1", "192.168.0.10"])
    assert first["crt"].read_bytes() == pc_before  # nada mudou: não refaz
    tls.ensure(tmp_path, dns=["localhost"], ips=["127.0.0.1", "192.168.1.77"])
    assert first["ca_crt"].read_bytes() == ca_before and first["crt"].read_bytes() != pc_before


def test_toggle_flag(tmp_path, monkeypatch):
    monkeypatch.delenv("JARVIS_HTTPS", raising=False)
    assert not tls.enabled(tmp_path)
    tls.set_enabled(True, tmp_path)
    assert tls.enabled(tmp_path)
    tls.set_enabled(False, tmp_path)
    assert not tls.enabled(tmp_path)
    monkeypatch.setenv("JARVIS_HTTPS", "1")
    assert tls.enabled(tmp_path)


def _phone(scheme="http", token=None):
    c = TestClient(main.app, base_url=f"{scheme}://192.168.0.10:8000", client=("192.168.0.50", 50000))
    if token:
        c.headers["X-Jarvis-Token"] = token
    return c


def test_key_never_travels_over_plain_http_when_https_is_on(monkeypatch, tmp_path):
    monkeypatch.setattr(main.settings, "NETWORK_MODE", True)
    monkeypatch.setattr(tls, "_DIR", tmp_path)
    monkeypatch.delenv("JARVIS_HTTPS", raising=False)
    access.reset_for_tests(access.UNLOCKED)
    assert _phone(token=runtime.ACCESS_TOKEN).get("/api/health").status_code == 200  # https desligado: como antes
    tls.set_enabled(True, tmp_path)
    r = _phone(token=runtime.ACCESS_TOKEN).get("/api/health")
    assert r.status_code == 403 and r.json()["code"] == "https_required" and ":5443" in r.json()["detail"]
    assert _phone("https", runtime.ACCESS_TOKEN).get("/api/health").status_code == 200
    # páginas públicas seguem por http (baixar o app e o certificado)
    page = _phone().get("/api/mobile/certificado")
    assert page.status_code == 200 and "BAIXAR O CERTIFICADO" in page.text and runtime.ACCESS_TOKEN not in page.text
    crt = _phone().get("/api/mobile/certificado.crt")
    assert crt.status_code == 200 and crt.headers["content-type"] == "application/x-x509-ca-cert"
    x509.load_der_x509_certificate(crt.content)
    assert "BEGIN PRIVATE KEY" not in crt.text


def test_qr_points_to_https_when_on(monkeypatch, tmp_path):
    from routes import system

    monkeypatch.setattr(tls, "_DIR", tmp_path)
    monkeypatch.delenv("JARVIS_HTTPS", raising=False)
    monkeypatch.setattr(system, "local_ip", lambda: "192.168.0.10")
    access.reset_for_tests(access.UNLOCKED)
    assert TestClient(main.app).get("/api/network-access").json()["url"].startswith("http://192.168.0.10:5173/?token=")
    tls.set_enabled(True, tmp_path)
    data = TestClient(main.app).get("/api/network-access").json()
    assert data["url"].startswith("https://192.168.0.10:5443/?token=") and data["https"]
    assert data["app_pair_url"].startswith("https://192.168.0.10:8443/api/mobile/pair")


def test_only_pc_can_toggle(monkeypatch, tmp_path):
    from modules import self_update

    monkeypatch.setattr(main.settings, "NETWORK_MODE", True)
    monkeypatch.setattr(tls, "_DIR", tmp_path)
    monkeypatch.setattr(self_update, "restart", lambda: False)
    access.reset_for_tests(access.UNLOCKED)
    assert _phone("https", runtime.ACCESS_TOKEN).post("/api/security/https", json={"on": True}).status_code in (401, 403)
    r = TestClient(main.app).post("/api/security/https", json={"on": True})
    assert r.status_code == 200 and r.json()["enabled"] and r.json()["has_certificate"]


def test_cors_allows_https_central_on_home_network():
    r = TestClient(main.app).options("/api/health", headers={
        "Origin": "https://192.168.0.10:5443", "Access-Control-Request-Method": "GET"})
    assert r.headers.get("access-control-allow-origin") == "https://192.168.0.10:5443"
    bad = TestClient(main.app).options("/api/health", headers={
        "Origin": "https://evil.example:5443", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in bad.headers


def test_diagnostic_warns_when_devices_use_plain_http(monkeypatch, tmp_path):
    from modules import device_access, health_check

    monkeypatch.setattr(tls, "_DIR", tmp_path)
    monkeypatch.delenv("JARVIS_HTTPS", raising=False)
    device_access.claim("Galaxy", "celular", "192.168.0.50")  # migração: já aprovado
    item = health_check.check_security()
    assert item["status"] == "warn" and "https" in item["fix"]
    tls.set_enabled(True, tmp_path)
    item = health_check.check_security()
    assert item["status"] == "ok" and "https ligado" in item["detail"]

"""V7.7: conexão criptografada (https) na REDE DE CASA. Ideia 2, parte 2 do documento de atualização.

- O JARVIS cria a própria "autoridade" (certificado raiz "JARVIS · rede de casa") e, com ela, o certificado do
  PC para os endereços dele na rede (192.168…, nome do computador, localhost). Tudo fica em data/tls/.
- Ligado (Configurações > Segurança), o PC atende a rede em https (central 5443, backend 8443).
  Este próprio PC continua em http://127.0.0.1 (não sai do computador), então nada muda para ele.
- Com https ligado, a chave de acesso NUNCA viaja por http na rede: só as páginas públicas (baixar o app e o
  certificado) continuam em http.
- O celular confia no certificado instalando o raiz UMA vez (página /api/mobile/certificado).
O certificado do PC é refeito sozinho quando o endereço dele na rede muda.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import ipaddress
import logging
import os
import socket
from pathlib import Path

from config import settings

log = logging.getLogger("jarvis.tls")

FRONT_HTTPS_PORT = 5443
API_HTTPS_PORT = 8443
FRONT_HTTP_PORT = 5173
API_HTTP_PORT = 8000

_DIR = settings.DATA_DIR / "tls"


def _paths(base: Path | None = None) -> dict[str, Path]:
    d = Path(base or _DIR)
    return {"dir": d, "ca_key": d / "jarvis-ca.key", "ca_crt": d / "jarvis-ca.crt",
            "key": d / "jarvis-pc.key", "crt": d / "jarvis-pc.crt", "flag": d / "https-ligado"}


def enabled(base: Path | None = None) -> bool:
    env = os.getenv("JARVIS_HTTPS", "").strip().lower()
    if env in {"0", "false", "no", "off"}:
        return False
    if env in {"1", "true", "yes", "on"}:
        return True
    return _paths(base)["flag"].exists()


def set_enabled(on: bool, base: Path | None = None) -> None:
    p = _paths(base)
    p["dir"].mkdir(parents=True, exist_ok=True)
    if on:
        ensure(base)
        p["flag"].write_text("1", encoding="utf-8")
    elif p["flag"].exists():
        p["flag"].unlink()


def local_ipv4s() -> list[str]:
    ips: set[str] = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    try:  # o endereço "de saída" (o que o celular enxerga)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ips.add(s.getsockname()[0])
    except OSError:
        pass
    return sorted(ip for ip in ips if not ip.startswith("127."))


def _names() -> tuple[list[str], list[str]]:
    host = socket.gethostname() or "jarvis"
    dns = sorted({"localhost", host, f"{host}.local"})
    ips = sorted({"127.0.0.1", *local_ipv4s()})
    return dns, ips


def _load_crt(path: Path):
    from cryptography import x509

    return x509.load_pem_x509_certificate(path.read_bytes())


def _covers(crt_path: Path, dns: list[str], ips: list[str]) -> bool:
    from cryptography import x509

    try:
        cert = _load_crt(crt_path)
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        have_ips = {str(i) for i in san.get_values_for_type(x509.IPAddress)}
        have_dns = set(san.get_values_for_type(x509.DNSName))
        not_after = getattr(cert, "not_valid_after_utc", None) or cert.not_valid_after.replace(tzinfo=dt.timezone.utc)
        fresh = not_after - dt.datetime.now(dt.timezone.utc) > dt.timedelta(days=30)
        return fresh and set(ips) <= have_ips and set(dns) <= have_dns
    except Exception:  # noqa: BLE001 - arquivo ruim: refaz
        return False


def ensure(base: Path | None = None, dns: list[str] | None = None, ips: list[str] | None = None) -> dict[str, Path]:
    """Garante a autoridade do JARVIS e o certificado do PC para os endereços atuais. Devolve os caminhos."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

    p = _paths(base)
    p["dir"].mkdir(parents=True, exist_ok=True)
    if dns is None or ips is None:
        dns, ips = _names()
    now = dt.datetime.now(dt.timezone.utc)

    def write_key(path: Path, key) -> None:
        path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                           serialization.NoEncryption()))
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass

    if not (p["ca_key"].exists() and p["ca_crt"].exists()):
        ca_key = ec.generate_private_key(ec.SECP256R1())
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "JARVIS - rede de casa"),
                          x509.NameAttribute(NameOID.ORGANIZATION_NAME, "JARVIS (este PC)")])
        ca = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(ca_key.public_key())
              .serial_number(x509.random_serial_number()).not_valid_before(now - dt.timedelta(days=1))
              .not_valid_after(now + dt.timedelta(days=3650))
              .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
              .add_extension(x509.KeyUsage(digital_signature=True, key_cert_sign=True, crl_sign=True,
                                           content_commitment=False, key_encipherment=False, data_encipherment=False,
                                           key_agreement=False, encipher_only=False, decipher_only=False), critical=True)
              .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
              .sign(ca_key, hashes.SHA256()))
        write_key(p["ca_key"], ca_key)
        p["ca_crt"].write_bytes(ca.public_bytes(serialization.Encoding.PEM))
        if p["crt"].exists():
            p["crt"].unlink()  # autoridade nova: refaz o do PC
        log.info("Certificado raiz do JARVIS criado.")

    if not (p["key"].exists() and _covers(p["crt"], dns, ips)):
        ca_key = serialization.load_pem_private_key(p["ca_key"].read_bytes(), password=None)
        ca = _load_crt(p["ca_crt"])
        key = ec.generate_private_key(ec.SECP256R1())
        alt = [x509.DNSName(n) for n in dns] + [x509.IPAddress(ipaddress.ip_address(i)) for i in ips]
        cert = (x509.CertificateBuilder()
                .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, dns[0] if dns else "jarvis")]))
                .issuer_name(ca.subject).public_key(key.public_key()).serial_number(x509.random_serial_number())
                .not_valid_before(now - dt.timedelta(days=1)).not_valid_after(now + dt.timedelta(days=825))
                .add_extension(x509.SubjectAlternativeName(alt), critical=False)
                .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
                .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
                .sign(ca_key, hashes.SHA256()))
        write_key(p["key"], key)
        p["crt"].write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        log.info("Certificado do PC (re)feito para: %s", ", ".join(dns + ips))
    return p


def ca_pem(base: Path | None = None) -> bytes:
    return ensure(base)["ca_crt"].read_bytes()


def ca_der(base: Path | None = None) -> bytes:
    from cryptography.hazmat.primitives import serialization

    return _load_crt(ensure(base)["ca_crt"]).public_bytes(serialization.Encoding.DER)


def ca_fingerprint(base: Path | None = None) -> str:
    """SHA-256 do certificado raiz, em pares (para conferir no celular, se quiser)."""
    h = hashlib.sha256(ca_der(base)).hexdigest().upper()
    return ":".join(h[i:i + 2] for i in range(0, len(h), 2))


def frontend_url(ip: str) -> str:
    """Endereço da central para outro aparelho da rede (é o que vai no QR code)."""
    return f"https://{ip}:{FRONT_HTTPS_PORT}" if enabled() else f"http://{ip}:{FRONT_HTTP_PORT}"


def backend_url(ip: str) -> str:
    return f"https://{ip}:{API_HTTPS_PORT}" if enabled() else f"http://{ip}:{API_HTTP_PORT}"


def status() -> dict:
    p = _paths()
    has_ca = p["ca_crt"].exists()
    return {
        "enabled": enabled(),
        "has_certificate": has_ca,
        "fingerprint": ca_fingerprint() if has_ca else "",
        "ips": local_ipv4s(),
        "front_port": FRONT_HTTPS_PORT,
        "api_port": API_HTTPS_PORT,
    }

"""A central publicada no site (/app/) fala com o backend do PC: CORS e rede local do Chrome."""
from fastapi.testclient import TestClient

import main
from config import settings

SITE = settings.SITE_ORIGIN


def test_preflight_do_site_libera_cors_e_rede_local():
    client = TestClient(main.app)
    res = client.options(
        "/api/profile",
        headers={
            "Origin": SITE,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Private-Network": "true",
        },
    )
    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == SITE
    assert res.headers["access-control-allow-private-network"] == "true"


def test_outro_site_nao_ganha_cors():
    client = TestClient(main.app)
    res = client.options(
        "/api/profile",
        headers={"Origin": "https://exemplo-malicioso.netlify.app", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in res.headers

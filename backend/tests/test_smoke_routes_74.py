"""V7.4: varredura: TODA rota GET sem parâmetro responde sem erro interno (500).

502/503/504 são aceitos: dependem de internet ou de um serviço externo (clima, notícias, Spotify…).
"""
import pytest
from fastapi.testclient import TestClient

import main
from modules import access

SKIP = {
    "/api/camera/stream", "/api/screen/stream", "/api/stream", "/ws",  # transmissões contínuas
    "/api/system/update/status",  # consulta o GitHub
    "/api/system/health-check",  # testa IA e voz de verdade (teste próprio em test_health_check_74)
}


def _get_routes():
    for path, ops in main.app.openapi().get("paths", {}).items():
        if "get" in ops and "{" not in path and path not in SKIP and "stream" not in path:
            yield path


@pytest.mark.parametrize("path", sorted(set(_get_routes())))
def test_get_route_has_no_internal_error(path, isolated_data, monkeypatch):
    access.reset_for_tests(access.UNLOCKED)
    import requests

    def offline(*a, **k):
        raise requests.ConnectionError("sem internet no teste")

    monkeypatch.setattr(requests.Session, "request", offline)
    r = TestClient(main.app).get(path)
    assert r.status_code != 500, f"{path}: {r.text[:300]}"

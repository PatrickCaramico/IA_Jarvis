from fastapi.testclient import TestClient

from main import app


def test_fan_logo_route_serves_palmeiras_shield():
    client = TestClient(app)
    response = client.get("/api/fan/logo/ours")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")

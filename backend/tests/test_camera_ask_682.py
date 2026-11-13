"""V6.8.2: "o que é isso?" com a foto da câmera do aparelho."""
import base64

from fastapi.testclient import TestClient

import main
from modules import access, camera_ask
from services import llm_orchestrator

JPEG = "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff\xe0" + b"x" * 100).decode()


def test_route_sends_photo_to_ai(monkeypatch):
    access.reset_for_tests(access.UNLOCKED)
    seen = {}

    def fake(prompt, image):
        seen.update(prompt=prompt, image=image)
        return "É uma jabuticabeira, senhor."

    monkeypatch.setattr(llm_orchestrator, "ask_with_image", fake)
    r = TestClient(main.app).post("/api/camera/ask", json={"image": JPEG, "question": "que planta é essa?"})
    assert r.status_code == 200 and r.json()["text"] == "É uma jabuticabeira, senhor."
    assert "que planta é essa?" in seen["prompt"] and not seen["image"].startswith("data:")


def test_rejects_non_images():
    for bad in ("", "data:image/jpeg;base64,!!!", base64.b64encode(b"<html>").decode()):
        try:
            camera_ask.clean_image(bad)
            raise AssertionError("deveria recusar")
        except ValueError:
            pass


def test_personal_route_needs_unlock(credentials):
    access.reset_for_tests(access.LOCKED)
    r = TestClient(main.app).post("/api/camera/ask", json={"image": JPEG})
    assert r.status_code == 403

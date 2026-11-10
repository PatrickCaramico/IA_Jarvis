"""Testes da verificação facial com câmera simulada (seção 16)."""
import numpy as np
import pytest

from modules import face


class FakeCap:
    def __init__(self, n_frames=40, fail_after=None):
        self.n = n_frames
        self.released = False
        self.reads = 0
        self.fail_after = fail_after

    def read(self):
        self.reads += 1
        if self.fail_after is not None and self.reads > self.fail_after:
            raise RuntimeError("câmera caiu")
        return True, np.zeros((240, 320, 3), dtype=np.uint8)

    def release(self):
        self.released = True


class FakeRecognizer:
    def __init__(self, scores):
        self.scores = list(scores)

    def alignCrop(self, img, face_box):  # noqa: N802 - API do OpenCV
        return img

    def feature(self, img):
        return np.ones((1, 128), dtype=np.float32)

    def match(self, a, b, kind):
        return self.scores.pop(0) if self.scores else 0.0


@pytest.fixture
def fake_face(monkeypatch, tmp_path):
    photo = tmp_path / "profile.jpg"
    photo.write_bytes(b"x")
    monkeypatch.setattr(face, "PHOTO_PATH", photo)
    monkeypatch.setattr(face, "_load_models", lambda: None)
    monkeypatch.setattr(face.cv2, "imdecode", lambda *a, **k: np.zeros((10, 10, 3), dtype=np.uint8))
    monkeypatch.setattr(face, "_embedding", lambda img: (np.ones((1, 128), dtype=np.float32), 1))
    monkeypatch.setattr(face, "_faces", lambda img: [np.array([80, 60, 100, 120, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.99])])
    monkeypatch.setattr(face.settings, "FACE_TIMEOUT", 2.0)
    monkeypatch.setattr(face.settings, "FACE_STREAM_FPS", 1000.0)  # não limita no teste
    return monkeypatch


def test_on_frame_receives_expected_fields_and_verifies(fake_face):
    cap = FakeCap()
    fake_face.setattr(face, "open_camera", lambda: cap)
    fake_face.setattr(face, "_recognizer", FakeRecognizer([0.1, 0.2, 0.9]))
    frames = []
    result = face.verify_against_profile(on_frame=frames.append)
    assert result["verified"] is True and result["score"] == pytest.approx(0.9)
    assert cap.released
    assert frames and set(frames[-1]) == {"jpeg", "box", "saw_face", "score", "phase"}
    assert frames[-1]["phase"] == "verified"
    assert frames[-1]["jpeg"][:2] == b"\xff\xd8"
    box = frames[-1]["box"]
    assert box == pytest.approx([0.25, 0.25, 0.3125, 0.5], abs=1e-3)
    assert {"searching", "comparing"} & {f["phase"] for f in frames}


def test_without_on_frame_result_is_identical(fake_face):
    fake_face.setattr(face, "open_camera", lambda: FakeCap())
    fake_face.setattr(face, "_recognizer", FakeRecognizer([0.1, 0.2, 0.9]))
    a = face.verify_against_profile()
    fake_face.setattr(face, "_recognizer", FakeRecognizer([0.1, 0.2, 0.9]))
    frames = []
    b = face.verify_against_profile(on_frame=frames.append)
    assert a == b


def test_threshold_not_loosened(fake_face):
    fake_face.setattr(face, "open_camera", lambda: FakeCap())
    just_below = face.settings.FACE_THRESHOLD - 0.001
    fake_face.setattr(face, "_recognizer", FakeRecognizer([just_below] * 500))
    fake_face.setattr(face.settings, "FACE_TIMEOUT", 0.3)
    frames = []
    res = face.verify_against_profile(on_frame=frames.append)
    assert res["verified"] is False and frames[-1]["phase"] == "failed"


def test_camera_released_on_error(fake_face):
    cap = FakeCap(fail_after=8)
    fake_face.setattr(face, "open_camera", lambda: cap)
    fake_face.setattr(face, "_recognizer", FakeRecognizer([0.0] * 50))
    with pytest.raises(RuntimeError):
        face.verify_against_profile(on_frame=lambda f: None)
    assert cap.released


def test_on_frame_errors_do_not_break_verification(fake_face):
    fake_face.setattr(face, "open_camera", lambda: FakeCap())
    fake_face.setattr(face, "_recognizer", FakeRecognizer([0.95]))

    def boom(frame):
        raise ValueError("ws caiu")

    assert face.verify_against_profile(on_frame=boom)["verified"] is True


def test_detect_presence(fake_face):
    cap = FakeCap()
    fake_face.setattr(face, "open_camera", lambda: cap)
    assert face.detect_presence(0.5) is True and cap.released
    fake_face.setattr(face, "_faces", lambda img: [])
    cap2 = FakeCap()
    fake_face.setattr(face, "open_camera", lambda: cap2)
    assert face.detect_presence(0.4) is False and cap2.released

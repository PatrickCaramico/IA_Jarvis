"""V9.1.2: desbloqueio pelo rosto SEM saudação (já cumprimentou há pouco) devolve a central para "em espera".

Antes: a câmera punha a tela em PROCESSANDO e, como não havia fala para terminar, ninguém mandava "em espera":
a central ficava "Está demorando (51 s)" depois de toda entrada que não tinha saudação.
"""
import pytest
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from core import session, speech  # noqa: E402
from modules import access, entry_greeting, face, lock_pin  # noqa: E402
from modules import tts as tts_module  # noqa: E402


@pytest.fixture
def unlock(isolated_data, monkeypatch):
    spoken, sent = [], []

    async def fake_speak(text, release_busy=True, idle_after=True):
        spoken.append(text)
        session.busy = False

    async def fake_broadcast(event):
        sent.append(event)

    async def fake_send_local(event):
        return 1

    monkeypatch.setattr(speech, "speak", fake_speak)
    monkeypatch.setattr(tts_module, "stop_playback", lambda: None)
    monkeypatch.setattr(main.manager, "broadcast", fake_broadcast)
    monkeypatch.setattr(main.manager, "send_local", fake_send_local)
    monkeypatch.setattr(face, "has_profile", lambda: True)
    monkeypatch.setattr(face, "get_name", lambda: "Patrick")
    monkeypatch.setattr(face, "verify_against_profile",
                        lambda timeout=None, on_frame=None: {"verified": True, "saw_face": True, "score": 0.6})
    lock_pin.set_pin("4821")
    access.lock("test")
    session.busy = False
    return spoken, sent


def states(sent):
    return [e["state"] for e in sent if e.get("type") == "state"]


def test_silent_unlock_goes_back_to_idle(unlock, monkeypatch):
    spoken, sent = unlock
    monkeypatch.setattr(entry_greeting, "unlock_speech", lambda *a, **k: "")
    r = TestClient(main.app).post("/api/auth/verify", json={"mode": "login"}).json()
    assert r["verified"] is True and r["message"].startswith("Acesso liberado")
    assert spoken == [] and session.busy is False
    assert states(sent) == ["processing", "idle"]  # a tela sai do PROCESSANDO da câmera


def test_unlock_with_greeting_still_speaks(unlock, monkeypatch):
    spoken, sent = unlock
    monkeypatch.setattr(entry_greeting, "unlock_speech", lambda *a, **k: "Bem-vindo de volta, senhor.")
    TestClient(main.app).post("/api/auth/verify", json={"mode": "login"})
    assert spoken == ["Bem-vindo de volta, senhor."]  # a fala devolve "em espera" quando termina

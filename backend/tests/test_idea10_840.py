"""V8.4.0 (ideia 10): modo leve, voz pela Groq, brincadeiras do avatar e piscar liga/desliga."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from config import settings
from modules import access, desk, voice_groq


@pytest.fixture
def client():
    import main

    access.reset_for_tests(access.UNLOCKED)
    return TestClient(main.app)


def test_desk_config_new_options():
    cfg = desk.config()
    assert cfg["desempenho"] == {"leve": "auto"}
    assert cfg["avatar"]["piscar"] is True and cfg["avatar"]["brincadeiras"] is True
    cfg = desk.update_config({"desempenho": {"leve": "sim"}, "avatar": {"piscar": False, "brincadeiras": False}})
    assert cfg["desempenho"]["leve"] == "sim" and cfg["avatar"]["piscar"] is False and cfg["avatar"]["brincadeiras"] is False
    cfg = desk.update_config({"desempenho": {"leve": "turbo"}, "avatar": {"piscar": "sim"}})  # inválidos: ignorados
    assert cfg["desempenho"]["leve"] == "sim" and cfg["avatar"]["piscar"] is False


def test_island_route_carries_lite_mode(client):
    desk.update_config({"desempenho": {"leve": "nao"}})
    assert client.get("/api/desk/island").json()["desempenho"] == {"leve": "nao"}


class FakeGroq:
    def __init__(self, text="  liga a luz da sala  ", fail=False):
        self.calls = []
        tr = SimpleNamespace(create=self._create)
        self.audio = SimpleNamespace(transcriptions=tr)
        self.text, self.fail = text, fail

    def _create(self, **kw):
        self.calls.append(kw)
        if self.fail:
            raise RuntimeError("401 chave sk-secreta inválida")
        return SimpleNamespace(text=self.text)


def test_transcribe_rules(monkeypatch):
    monkeypatch.setattr(settings, "GROQ_API_KEY", "", raising=False)
    with pytest.raises(voice_groq.VoiceError) as e:
        voice_groq.transcribe(b"x" * 2000)
    assert e.value.status == 409 and "Groq" in str(e.value)
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_teste", raising=False)
    with pytest.raises(voice_groq.VoiceError) as e:
        voice_groq.transcribe(b"x" * 10)
    assert e.value.status == 400
    fake = FakeGroq()
    assert voice_groq.transcribe(b"x" * 2000, "audio/webm;codecs=opus", client_factory=lambda: fake) == "liga a luz da sala"
    kw = fake.calls[0]
    assert kw["model"] == voice_groq.MODEL and kw["language"] == "pt" and kw["file"][0] == "fala.webm" and kw["file"][2] == "audio/webm"
    with pytest.raises(voice_groq.VoiceError) as e:  # erro da Groq: mensagem amigável, sem vazar detalhes
        voice_groq.transcribe(b"x" * 2000, client_factory=lambda: FakeGroq(fail=True))
    assert e.value.status == 502 and "sk-" not in str(e.value)
    assert voice_groq.file_name("audio/ogg") == "fala.ogg" and voice_groq.file_name("") == "fala.webm"


def test_transcribe_route(client, monkeypatch):
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_teste", raising=False)
    monkeypatch.setattr(voice_groq, "_client", lambda: FakeGroq("oi jarvis"))
    import routes.desk as rd  # noqa: F401 - garante a rota

    monkeypatch.setattr("core.runtime.is_local_conn", lambda conn: True)
    r = client.post("/api/voice/transcribe", content=b"x" * 2000, headers={"content-type": "audio/webm"})
    assert r.status_code == 200 and r.json() == {"texto": "oi jarvis"}
    big = client.post("/api/voice/transcribe", content=b"x" * 10, headers={"content-type": "audio/webm", "content-length": str(9 * 1024 * 1024)})
    assert big.status_code in (400, 413)
    assert client.get("/api/voice/groq").json() == {"disponivel": True}
    monkeypatch.setattr("core.runtime.is_local_conn", lambda conn: False)
    assert client.post("/api/voice/transcribe", content=b"x" * 2000).status_code in (401, 403)

"""V4.2.2: versão única, preferências de som (e, mais abaixo, diagnóstico e exportar/importar)."""
import re
from pathlib import Path

import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from modules import prefs  # noqa: E402
from version import VERSION  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def client(isolated_data):
    return TestClient(main.app)


def test_version_is_the_same_everywhere(client):
    assert VERSION == "6.7.6"
    assert client.get("/api/health").json()["version"] == VERSION
    assert main.app.version == VERSION
    front = (ROOT / "frontend/src/utils/version.js").read_text(encoding="utf-8")
    assert re.search(r'APP_VERSION = "([^"]+)"', front).group(1) == VERSION


def test_sound_prefs_defaults_and_validation(client):
    data = client.get("/api/prefs").json()
    assert data["sfx_volume"] == 60 and data["sfx_mode"] == "all"
    ok = client.patch("/api/prefs", json={"sfx_volume": 35, "sfx_mode": "important"})
    assert ok.status_code == 200 and ok.json()["sfx_volume"] == 35 and ok.json()["sfx_mode"] == "important"
    assert client.patch("/api/prefs", json={"sfx_volume": 150}).status_code in (400, 422)
    assert client.patch("/api/prefs", json={"sfx_mode": "alto"}).status_code in (400, 422)
    assert "sfx_volume" in prefs.PUBLIC_KEYS and "sfx_mode" in prefs.PUBLIC_KEYS


# ---------------------------------------------------------------- diagnóstico
def test_redact_hides_secrets_and_command_text():
    from modules.diagnostics import redact

    raw = ("Comando: manda email para ana@exemplo.com\n"
           "Detalhes: 403 https://x.googleapis.com/v1?key=AIzaSyA1234567890abcdefghijkLMNOP "
           "Authorization: Bearer abc.def.ghi sk-proj-ABCDEF1234567890 senha=minhasenha")
    out = redact(raw)
    for secret in ("ana@exemplo.com", "AIzaSy", "abc.def.ghi", "sk-proj", "minhasenha", "manda email"):
        assert secret not in out
    assert "403" in out and "[oculto]" in out


def test_diagnostics_route_has_no_secrets_or_personal_text(client, monkeypatch):
    from config import settings
    from modules import event_log

    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test-SEGREDO-123456789")
    event_log.add("command", "abre o meu diário secreto")
    event_log.add("memory", "Memória adicionada: meu remédio é às 8h")
    event_log.add("error", "Falha ao processar solicitação", "Comando: texto pessoal\nDetalhes: token=XYZ987 timeout")
    data = client.get("/api/diagnostics").json()
    dumped = str(data)
    for leaked in ("sk-test", "SEGREDO", "diário secreto", "remédio", "texto pessoal", "XYZ987"):
        assert leaked not in dumped, leaked
    assert data["jarvis"] == VERSION and data["ai_keys_configured"]["openai"] is True
    kinds = [e["kind"] for e in data["recent_events"]]
    assert kinds[:3] == ["error", "memory", "command"]
    assert "timeout" in data["recent_events"][0]["detail"]
    text = client.get("/api/diagnostics?format=text").json()["text"]
    assert text.startswith(f"Diagnóstico JARVIS v{VERSION}") and "SEGREDO" not in text


def test_diagnostics_is_blocked_when_locked(client):
    from modules import access, lock_pin

    lock_pin.set_pin("4821")
    access.lock("test")
    assert client.get("/api/diagnostics").status_code == 403
    assert client.get("/api/prefs/export").status_code == 403
    assert client.post("/api/prefs/import", json={"prefs": {"sfx_volume": 10}}).status_code == 403


# ---------------------------------------------------------------- exportar / importar
def test_export_import_roundtrip(client):
    client.patch("/api/prefs", json={"sfx_volume": 25, "color_theme": "green", "clap_sensitivity": 8})
    exported = client.get("/api/prefs/export").json()
    assert exported["jarvis_settings"] == VERSION
    assert exported["prefs"]["sfx_volume"] == 25 and "camera_index" not in exported["prefs"]
    assert "theme_colors" not in exported["prefs"]  # campos calculados não vão
    client.patch("/api/prefs", json={"sfx_volume": 90, "color_theme": "blue"})
    r = client.post("/api/prefs/import", json={"prefs": {**exported["prefs"], "camera_index": 3, "desconhecido": 1}})
    assert r.status_code == 200
    body = r.json()
    assert body["prefs"]["sfx_volume"] == 25 and body["prefs"]["color_theme"] == "green"
    assert "camera_index" in body["ignored"] and "desconhecido" in body["ignored"]


def test_import_rejects_invalid_values_without_changing_anything(client):
    client.patch("/api/prefs", json={"sfx_volume": 40})
    assert client.post("/api/prefs/import", json={"prefs": {"sfx_volume": 500}}).status_code == 400
    assert client.post("/api/prefs/import", json={"prefs": {"color_theme": "rosa"}}).status_code == 400
    assert client.post("/api/prefs/import", json={"prefs": {"clap_sensitivity": "alto"}}).status_code == 400
    assert client.post("/api/prefs/import", json={"prefs": {"nada": 1}}).status_code == 400
    assert client.get("/api/prefs").json()["sfx_volume"] == 40


# ---------------------------------------------------------------- "abrir central" no Sentinela
UNLOCK_YES = ["abrir central", "abre a central", "abra a central", "liberar", "libera a central", "desbloquear",
              "desbloqueia o sistema", "destrava a tela", "entrar", "quero entrar", "me deixa entrar", "pode liberar",
              "abrir o jarvis", "liberar por favor"]
UNLOCK_NO = ["abrir", "abre o spotify", "abrir youtube", "que horas sao", "abrir central de notificacoes",
             "bloquear a central", "liberar espaco no disco", "entrar no modo foco", ""]


def test_unlock_phrase_rule_matches_frontend():
    from modules import sentinel

    for t in UNLOCK_YES:
        assert sentinel.is_unlock_only(sentinel._norm(t)), t
    for t in UNLOCK_NO:
        assert not sentinel.is_unlock_only(sentinel._norm(t)), t
    front = (ROOT / "frontend/tests/unlockPhrase.test.js").read_text(encoding="utf-8")
    assert all(f'"{t}"' in front or t.lower() in front.lower() for t in ("abrir central", "me deixa entrar", "abre o spotify"))


def test_sentinel_unlock_only_reply():
    import asyncio

    from modules import sentinel

    for msg in ("abrir central", "Jarvis, abrir central", "jarvis liberar"):
        r = asyncio.run(sentinel.classify_and_answer(msg, "locked"))
        assert r["action"] == "unlock_only" and r["requires_unlock"] is True, msg
    guest = asyncio.run(sentinel.classify_and_answer("abrir central", "guest"))
    assert guest["requires_unlock"] is False
    other = asyncio.run(sentinel.classify_and_answer("Jarvis, abre minhas tarefas", "locked"))
    assert other["action"] == "unlock"


# ---------------------------------------------------------------- "Tocando agora" (Spotify)
def test_parse_now_playing():
    from modules import spotify

    assert spotify.parse_now_playing(204, None) == {"state": "idle"}
    payload = {"is_playing": True, "progress_ms": 61000, "item": {
        "name": "Trem-Bala", "duration_ms": 200000, "artists": [{"name": "Ana Vilela"}],
        "album": {"name": "Ana Vilela", "images": [{"url": "big", "width": 640}, {"url": "mid", "width": 300}, {"url": "small", "width": 64}]}}}
    r = spotify.parse_now_playing(200, payload)
    assert r == {"state": "playing", "title": "Trem-Bala", "artist": "Ana Vilela", "album": "Ana Vilela", "image": "mid",
                 "progress_ms": 61000, "duration_ms": 200000}
    assert spotify.parse_now_playing(200, {**payload, "is_playing": False})["state"] == "paused"


def test_track_route_respects_lock_card(client):
    from modules import access, lock_pin

    client.patch("/api/prefs", json={"lock_cards": ["clock", "weather"]})
    lock_pin.set_pin("4821")
    access.lock("test")
    assert client.get("/api/integrations/spotify/track").status_code == 403
    access.unlock("test")
    client.patch("/api/prefs", json={"lock_cards": ["clock", "weather", "spotify"]})
    access.lock("test")
    r = client.get("/api/integrations/spotify/track")
    assert r.status_code == 200 and r.json()["state"] in {"off", "idle", "error", "playing", "paused"}


def test_spotify_card_migration_runs_once(isolated_data):
    import json as _json

    path = prefs._SETTINGS_PATH
    path.write_text(_json.dumps({"lock_cards": ["clock"]}), encoding="utf-8")
    assert "spotify" in prefs.get_all()["lock_cards"]
    prefs.update({"lock_cards": ["clock"]})  # o usuário desligou: não volta sozinho
    assert prefs.get_all()["lock_cards"] == ["clock"]

"""V9.3: segurança e otimização — vigia da câmera (local), pendrive, otimização do dia e relatório."""
import asyncio

import pytest
from fastapi.testclient import TestClient

import main
from core import runtime, speech
from core.skills import registry, router
from modules import access, face, lock_log, prefs
from modules.quick_replies import _norm
from skills import seguranca as sec

NOBODY = {"faces": 0, "known": 0, "unknown": 0}
ME = {"faces": 1, "known": 1, "unknown": 0}
STRANGER = {"faces": 1, "known": 0, "unknown": 1, "jpeg": b"\xff\xd8foto"}


def match(phrase):
    return registry.match(_norm(phrase), phrase)


# ------------------------------------------------------------------ o vigia (parte pura)
def test_locked_stranger_needs_two_looks_and_respects_cooldown():
    g = sec.CameraGuard()
    t = 1_000_000.0
    assert g.step(t, True, STRANGER) == []  # uma olhada só pode ser engano
    assert g.step(t + 20, True, STRANGER) == ["intruso"]
    assert g.step(t + 40, True, STRANGER) == []  # no máximo 1 aviso a cada 5 min
    assert g.step(t + 20 + sec.EVENT_COOLDOWN_S, True, STRANGER) == ["intruso"]
    g2 = sec.CameraGuard()
    assert g2.step(t, True, STRANGER) == [] and g2.step(t + 20, True, {**STRANGER, "known": 1}) == []  # o dono junto: tudo bem


def test_unlocked_stranger_locks_and_owner_away_locks():
    g = sec.CameraGuard()
    t = 2_000_000.0
    assert g.step(t, False, ME) == []
    assert g.step(t + 60, False, STRANGER) == []
    assert g.step(t + 120, False, STRANGER) == ["estranho"]
    away = sec.CameraGuard()
    away.step(t, False, ME)
    for i in range(1, 5):
        assert away.step(t + i * 60, False, NOBODY, away_minutes=5) == []
    assert away.step(t + 5 * 60, False, NOBODY, away_minutes=5) == ["ausente"]
    off = sec.CameraGuard()
    off.step(t, False, ME)
    assert off.step(t + 600, False, NOBODY, away_minutes=5, auto_lock=False) == []


def test_presence_counts_time_and_absences():
    g = sec.CameraGuard()
    t = 3_000_000.0
    g.step(t, False, ME)
    g.step(t + 30 * 60, False, ME)
    assert g.presence(t + 30 * 60) == {"present": True, "minutes": 30, "absences": 0}
    g.step(t + 30 * 60 + sec.PRESENCE_GAP_S + 10, False, NOBODY, away_minutes=15)
    assert g.presence(t + 40 * 60)["present"] is False and g.presence(t + 40 * 60)["absences"] == 1


# ------------------------------------------------------------------ ações
@pytest.fixture
def quiet(isolated_data, monkeypatch):
    sent, notified, said = [], [], []

    async def fake_broadcast(e):
        sent.append(e)

    async def fake_say(text):
        said.append(text)

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    monkeypatch.setattr(runtime, "notify", lambda kind, title, body: notified.append((title, body)))
    monkeypatch.setattr(speech, "say_quietly", fake_say)
    return sent, notified, said


def test_intruder_saves_photo_and_warns(quiet):
    sent, notified, said = quiet
    asyncio.run(sec._on_action("intruso", STRANGER))
    ev = sec._load()["events"][-1]
    assert ev["kind"] == "intruso" and (lock_log.INTRUDERS_DIR / ev["photo"]).read_bytes() == b"\xff\xd8foto"
    assert notified[0][0] == "🚨 Pessoa não reconhecida"
    assert said == ["Não reconheço quem está aí. O acesso continua bloqueado e o dono foi avisado."]


def test_stranger_locks_the_central(quiet):
    access.reset_for_tests(access.UNLOCKED)
    asyncio.run(sec._on_action("estranho", STRANGER))
    assert access.get_state() == access.LOCKED
    assert sec._load()["events"][-1]["kind"] == "estranho"
    access.reset_for_tests(access.UNLOCKED)
    asyncio.run(sec._on_action("ausente", NOBODY))
    assert access.get_state() == access.LOCKED and sec._load()["events"][-1]["kind"] == "ausente"


def test_usb_and_optimization_rules():
    assert sec.new_drives({"E:\\": "E:\\ (29 GB)"}, {"E:\\": "E:\\ (29 GB)", "F:\\": "F:\\ (1 GB)"}) == ["F:\\ (1 GB)"]
    assert sec.new_drives({}, {}) == []
    items = sec.worth_optimizing({"temp_bytes": 2 * 1024 ** 3, "recycle_bytes": 0, "startup": 11, "disk_percent": 50})
    assert items == ["2,0 GB de arquivos temporários", "11 programas abrindo junto com o Windows"]
    assert sec.worth_optimizing({"temp_bytes": 10, "startup": 3}) == []


# ------------------------------------------------------------------ relatório
def test_report_route_with_photo_and_seen(quiet):
    access.reset_for_tests(access.UNLOCKED)
    lock_log.INTRUDERS_DIR.mkdir(parents=True, exist_ok=True)
    (lock_log.INTRUDERS_DIR / "tentativa_20261124_101500.jpg").write_bytes(b"jpg")
    sec.add_event("intruso", "Uma pessoa que não reconheço apareceu.", "tentativa_20261124_101500.jpg")
    sec.add_event("usb", "Pendrive ligado: E:\\ (29 GB).")
    sec.add_event("ausente", "O senhor saiu.")
    with TestClient(main.app) as client:
        r = client.get("/api/security/report").json()
        assert r["unseen"] == 2 and r["events"][0]["kind"] == "ausente"
        intr = next(e for e in r["events"] if e["kind"] == "intruso")
        assert intr["photo_b64"] == "anBn" and intr["new"] is True and intr["label"] == "Pessoa não reconhecida"
        assert r["speech"].startswith("Senhor, desde a última vez: 1 vez alguém que não reconheço") and "1 pendrive ligado" in r["speech"]
        assert client.post("/api/security/seen").status_code == 200
        assert client.get("/api/security/report").json()["unseen"] == 0


def test_report_route_is_private():
    assert not access.is_allowed("GET", "/api/security/report", access.LOCKED)


# ------------------------------------------------------------------ frases
def test_phrases(real_skills):
    for phrase, name in [("relatório de segurança", "relatorio_de_seguranca"), ("alguém tentou entrar?", "relatorio_de_seguranca"),
                         ("alguém mexeu no meu PC?", "relatorio_de_seguranca"), ("liga o vigia da câmera", "vigia_da_camera"),
                         ("desliga a vigilância pela câmera", "vigia_da_camera"), ("há quanto tempo eu estou no PC?", "presenca_no_pc"),
                         ("o que eu estou fazendo", "presenca_no_pc")]:
        hit = match(phrase)
        assert hit and hit[0].name == name, phrase
    assert match("desliga o vigia da câmera")[1] == {"ativo": False}
    for phrase in ("liga o vigia do sistema", "abre a câmera", "bloqueia a tela"):
        hit = match(phrase)
        assert hit is None or hit[0].name not in {"vigia_da_camera", "relatorio_de_seguranca", "presenca_no_pc"}, phrase


def test_camera_toggle_needs_a_face(real_skills, isolated_data, monkeypatch):
    access.reset_for_tests(access.UNLOCKED)
    monkeypatch.setattr(face, "has_profile", lambda: False)
    assert "foto do seu rosto" in asyncio.run(router.try_fast_path("liga o vigia da câmera")).speech
    monkeypatch.setattr(face, "has_profile", lambda: True)
    res = asyncio.run(router.try_fast_path("liga o vigia da câmera"))
    assert res.speech.startswith("Vigia da câmera ligado") and prefs.get_all()["camera_guard_enabled"] is True
    assert asyncio.run(router.try_fast_path("desliga o vigia da câmera")).speech == "Vigia da câmera desligado, senhor."


def test_presence_answer(real_skills, isolated_data, monkeypatch):
    access.reset_for_tests(access.UNLOCKED)
    assert "ligue o vigia da câmera" in asyncio.run(router.try_fast_path("há quanto tempo eu estou no PC?")).speech
    prefs.update(camera_guard_enabled=True)
    monkeypatch.setattr(sec._guard, "presence", lambda now: {"present": True, "minutes": 95, "absences": 2})
    s = asyncio.run(router.try_fast_path("há quanto tempo eu estou no PC?")).speech
    assert s == "O senhor está na frente do PC há 1 hora e 35 minutos e saiu 2 vezes hoje. Que tal uma pausa para esticar as pernas?"

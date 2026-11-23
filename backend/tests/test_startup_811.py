"""V8.11: ligar junto com o Windows, guardião e atualizar ao abrir a central."""
import asyncio
import sys
from pathlib import Path

import pytest

from modules import autostart

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import guardiao  # noqa: E402
import ligar_jarvis  # noqa: E402
import voice_listener  # noqa: E402


@pytest.fixture
def windows(monkeypatch, tmp_path):
    appdata = tmp_path / "AppData"
    pyw = tmp_path / "pythonw.exe"
    pyw.write_text("", encoding="utf-8")
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setattr(autostart, "_is_windows", lambda: True)
    monkeypatch.setattr(autostart, "pythonw", lambda: pyw)
    calls = []

    def fake_run(args, env=None, **kw):
        calls.append((args, env))
        Path(env["JARVIS_LNK"]).write_text("lnk", encoding="utf-8")  # o PowerShell criaria o atalho

    monkeypatch.setattr(autostart.subprocess, "run", fake_run)
    return calls, pyw


# ------------------------------------------------------------------ ligar junto com o Windows
def test_enable_and_disable_the_startup_shortcut(windows):
    calls, pyw = windows
    assert autostart.status() == {"available": True, "enabled": False, "message": ""}
    res = autostart.enable()
    assert res["ok"] and res["enabled"] and autostart.shortcut_path().name == "JARVIS.lnk"
    args, env = calls[0]
    assert args[:3] == ["powershell", "-NoProfile", "-NonInteractive"] and "$env:JARVIS_LNK" in args[-1]
    assert env["JARVIS_PYW"] == str(pyw) and env["JARVIS_ARGS"].endswith("ligar_jarvis.py\" --logon")
    assert autostart.disable()["enabled"] is False and not autostart.shortcut_path().exists()


def test_not_available_outside_windows(monkeypatch):
    monkeypatch.setattr(autostart, "_is_windows", lambda: False)
    assert autostart.status()["available"] is False
    assert autostart.enable()["ok"] is False


def test_autostart_routes(windows, isolated_data):
    from fastapi.testclient import TestClient

    import main
    from modules import access

    access.reset_for_tests(access.UNLOCKED)
    try:
        client = TestClient(main.app)
        assert client.get("/api/system/autostart").json()["enabled"] is False
        assert client.post("/api/system/autostart", json={"enabled": True}).json()["enabled"] is True
        assert client.post("/api/system/autostart", json={"enabled": False}).json()["enabled"] is False
    finally:
        access.reset_for_tests(access.LOCKED)


def test_voice_skill(real_skills, windows):
    from core.skills import registry, router

    for phrase, acao in [("liga o jarvis junto com o windows", "ligar"), ("nao liga mais com o windows", "desligar"),
                         ("voce liga junto com o windows", "consultar"), ("coloca o jarvis na inicializacao", "ligar")]:
        sk, args = registry.match(phrase, phrase)
        assert sk.name == "iniciar_com_windows" and args == {"acao": acao}
    for phrase in ("abre o windows explorer", "liga a luz", "abre o word"):
        hit = registry.match(phrase, phrase)
        assert hit is None or hit[0].name != "iniciar_com_windows"
    assert "eu ligo sozinho" in asyncio.run(router.try_fast_path("liga o JARVIS junto com o Windows")).speech
    assert autostart.status()["enabled"] is True
    assert asyncio.run(router.try_fast_path("você liga junto com o Windows?")).speech.startswith("Sim, senhor")
    asyncio.run(router.try_fast_path("não liga mais com o Windows"))
    assert autostart.status()["enabled"] is False


# ------------------------------------------------------------------ guardião
def test_guardian_revives_only_after_a_real_fall():
    g = guardiao.Guardian()
    assert g.should_revive(False, 0, None) is False  # nunca esteve no ar: quem liga é o Iniciar
    assert g.should_revive(True, 10, None) is False
    assert g.should_revive(False, 20, None) is False  # caiu agora
    assert g.should_revive(False, 20 + guardiao.DOWN_FOR_S - 1, None) is False
    assert g.should_revive(False, 20 + guardiao.DOWN_FOR_S, None) is True  # caiu de verdade: religa


def test_guardian_waits_while_starting_or_updating():
    g = guardiao.Guardian()
    g.should_revive(True, 0, None)
    g.should_revive(False, 10, None)
    assert g.should_revive(False, 100, starting_age=30) is False  # Iniciar trabalhando (atualização)
    assert g.should_revive(False, 100, starting_age=guardiao.STARTING_GRACE_S + 1) is True


def test_guardian_backs_off_and_has_a_ceiling():
    g = guardiao.Guardian()
    g.should_revive(True, 0, None)
    t, revived = 1000.0, []
    for _ in range(360):  # caído por 1 h, conferindo a cada 10 s
        if g.should_revive(False, t, None):
            revived.append(t)
        t += guardiao.CHECK_EVERY_S
    assert len(revived) == guardiao.MAX_PER_HOUR
    gaps = [b - a for a, b in zip(revived, revived[1:])]
    assert gaps == sorted(gaps) and gaps[0] >= guardiao.COOLDOWNS_S[0]


def test_heartbeat(tmp_path):
    beat = tmp_path / "guardiao.beat"
    assert guardiao.beat_is_fresh(path=beat) is False
    beat.write_text("1", encoding="ascii")
    assert guardiao.beat_is_fresh(path=beat) is True


def test_ear_leaves_reviving_to_the_guardian(monkeypatch, tmp_path):
    (tmp_path / "logs").mkdir()
    monkeypatch.setattr(voice_listener, "ROOT", tmp_path)
    assert voice_listener.guardian_alive() is False
    (tmp_path / "logs" / "guardiao.beat").write_text("1", encoding="ascii")
    assert voice_listener.guardian_alive() is True
    revived = []
    monkeypatch.setattr(voice_listener, "revive_backend", lambda: revived.append(1))
    monkeypatch.setattr(voice_listener, "_get", lambda path: None)
    gate = voice_listener.Gate()
    gate.seen_up, gate.down_since = True, -10_000.0
    gate.poll()
    assert revived == []


def test_launcher_command_and_missing_bat(tmp_path):
    assert ligar_jarvis.start_command(Path("C:/J/Iniciar-JARVIS.bat")) == ["cmd.exe", "/c", str(Path("C:/J/Iniciar-JARVIS.bat")), "site"]
    assert ligar_jarvis.start_hidden(tmp_path / "nao-existe.bat") is False


# ------------------------------------------------------------------ atualizar ao abrir a central
def test_update_status_tells_the_central_what_to_do(isolated_data, monkeypatch):
    from fastapi.testclient import TestClient

    import main
    from modules import access, desk, self_update

    monkeypatch.setattr(self_update, "check", lambda force=False: {"available": True, "latest": "8.12.0", "forced": force})
    access.reset_for_tests(access.UNLOCKED)
    try:
        client = TestClient(main.app)
        info = client.get("/api/system/update/status?force=true").json()
        assert info["available"] and info["forced"] and info["auto_on_open"] is True and info["busy"] is False
        desk.update_config({"atualizacao": {"ao_abrir": False}})
        assert client.get("/api/system/update/status").json()["auto_on_open"] is False
        assert desk.config()["atualizacao"]["automatica"] is True  # a outra opção continua como estava
    finally:
        access.reset_for_tests(access.LOCKED)

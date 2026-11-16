"""V8.5.0: pílula sem "Pensando…" preso, atualização automática, zoom e tamanho do painel da ilha."""
import asyncio
import importlib.util
from pathlib import Path

from core import runtime, session
from modules import auto_update, desk

ROOT = Path(__file__).resolve().parents[2]


def _desktop():
    spec = importlib.util.spec_from_file_location("jarvis_desktop_v850", ROOT / "desktop" / "jarvis_desktop.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_island_state_does_not_stay_stuck(monkeypatch):
    monkeypatch.setattr(session, "busy", False)
    runtime.note_island({"type": "state", "state": "processing"})
    t0 = runtime.ISLAND["estado_em"]
    assert runtime.island_state(t0 + 5) == "processing"
    assert runtime.island_state(t0 + runtime.STUCK_STATE_S + 1) == "idle"  # o "parado" se perdeu
    monkeypatch.setattr(session, "busy", True)
    assert runtime.island_state(t0 + 600) == "processing"  # ainda rodando de verdade: mostra
    runtime.note_island({"type": "state", "state": "idle"})


def test_desk_island_panel_zoom_and_auto_update_options():
    cfg = desk.config()
    assert cfg["ilha"]["painel"] == "medio" and cfg["ilha"]["zoom"] == 0.9 and cfg["atualizacao"]["automatica"] is True
    cfg = desk.update_config({"ilha": {"painel": "grande", "zoom": 1.2}, "atualizacao": {"automatica": False}})
    assert cfg["ilha"]["painel"] == "grande" and cfg["ilha"]["zoom"] == 1.2 and cfg["atualizacao"]["automatica"] is False
    cfg = desk.update_config({"ilha": {"painel": "gigante", "zoom": 9}, "atualizacao": {"automatica": "sim"}})
    assert cfg["ilha"]["painel"] == "grande" and cfg["ilha"]["zoom"] == 1.4 and cfg["atualizacao"]["automatica"] is False
    desk.update_config({"atualizacao": {"automatica": True}, "ilha": {"zoom": 0.9, "painel": "medio"}})


def test_auto_update_waits_for_quiet_and_respects_switch(monkeypatch):
    from modules import self_update

    calls = []

    async def fake_update(announce=True):
        calls.append(announce)
        return {"status": "restarting"}

    import routes.system as rs

    monkeypatch.setattr(rs, "perform_update", fake_update)
    monkeypatch.setattr(self_update, "check", lambda force=False: {"available": True, "latest": "9.9.9"})

    async def no_sleep(s):
        return None

    # desligada
    desk.update_config({"atualizacao": {"automatica": False}})
    assert asyncio.run(auto_update.check_and_update(sleep=no_sleep)) == "desligada"
    desk.update_config({"atualizacao": {"automatica": True}})
    # sempre ocupado: desiste da rodada, sem atualizar
    monkeypatch.setattr(auto_update, "is_quiet", lambda now=None: False)
    assert asyncio.run(auto_update.check_and_update(sleep=no_sleep)) == "ocupado" and calls == []
    # parado: atualiza sem falar e avisa na ilha
    monkeypatch.setattr(auto_update, "is_quiet", lambda now=None: True)
    assert asyncio.run(auto_update.check_and_update(sleep=no_sleep)) == "atualizando"
    assert calls == [False] and "9.9.9" in runtime.ISLAND["resposta"]
    # em dia
    monkeypatch.setattr(self_update, "check", lambda force=False: {"available": False})
    assert asyncio.run(auto_update.check_and_update(sleep=no_sleep)) == "em dia"


def test_is_quiet(monkeypatch):
    import time

    monkeypatch.setattr(session, "busy", False)
    runtime.note_island({"type": "state", "state": "idle"})
    runtime.ISLAND["resposta_em"] = time.time()
    assert not auto_update.is_quiet()
    runtime.ISLAND["resposta_em"] = time.time() - auto_update.QUIET_FOR_S - 5
    assert auto_update.is_quiet()
    monkeypatch.setattr(session, "busy", True)
    assert not auto_update.is_quiet()


def test_update_route_uses_shared_flow():
    src = (ROOT / "backend" / "routes" / "system.py").read_text(encoding="utf-8")
    assert "return await perform_update(announce=True)" in src and "async def perform_update(announce: bool = True)" in src
    main = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
    assert "auto_update.auto_update_loop()" in main


def test_desktop_panel_sizes_relaunch_and_reshape():
    d = _desktop()
    _, _, w, h = d.island_position(1920, "media", "painel", 0.5, "grande")
    assert (w, h) == d.PANEL_SIZES["grande"]
    _, _, w, h = d.island_position(1920, "media", "painel", 0.5, "compacto")
    assert (w, h) == d.PANEL_SIZES["compacto"]
    assert d.island_position(1920, "media", "painel", 0.5, "xyz")[2:] == d.ISLAND_PANEL
    assert not d.should_relaunch(None, 100, "mini", True)
    assert not d.should_relaunch(90, 100, "mini", True)  # acabou de mudar: espera a atualização terminar
    assert not d.should_relaunch(0, 100, "painel", True)  # não interrompe a ilha aberta
    assert not d.should_relaunch(0, 100, "mini", False)  # JARVIS ainda reiniciando
    assert d.should_relaunch(0, 100, "mini", True)
    assert len(d.source_fingerprint()) == 64
    b = d.Bridge()
    public = {n for n in dir(b) if not n.startswith("_")}
    assert {"island_layout", "island_set_pos", "island_center"} <= public
    b.island_layout("grande")
    assert b._panel == "grande"
    b.island_layout("xyz")
    assert b._panel == "grande"
    b.island_set_pos(0.25)
    assert b._pos == 0.25
    src = Path(d.__file__).read_text(encoding="utf-8")
    assert "_reshape_later" in src and "watch_self_update" in src


def test_v860_pacman_and_idle():
    """V8.6.0: o avatar corre atrás do mouse (acelera, sempre alcança), o tempo parado do PC e a pílula maior."""
    d = _desktop()
    (x, y), dist = d.chase_step((0, 0), (300, 400), 10)
    assert dist == 500 and abs(x - 6) < 1e-9 and abs(y - 8) < 1e-9
    (x, y), dist = d.chase_step((0, 0), (3, 4), 10)
    assert (x, y) == (3.0, 4.0) and dist == 5  # chegou
    assert d.chase_speed(0) < d.chase_speed(3) <= d.chase_speed(60) == 26.0
    assert d.chase_speed(0, 2.0) == 2 * d.chase_speed(0)
    # sempre alcança antes do tempo máximo, mesmo com o mouse longe
    pos, t = (0.0, 0.0), 0.0
    while True:
        pos, dist = d.chase_step(pos, (2500.0, 1400.0), d.chase_speed(t))
        t += d.PACMAN_FRAME_S
        if dist < 16:
            break
    assert t < d.PACMAN_MAX_CHASE_S
    b = d.Bridge()
    assert b.pacman_start() is False  # sem a janela (ou fora do Windows) não faz nada
    if __import__("sys").platform != "win32":
        assert b.idle_seconds() == -1.0
    assert {"pacman_start", "idle_seconds"} <= {n for n in dir(b) if not n.startswith("_")}
    assert d.ISLAND_SIZES["media"][1] >= 56  # pílula mais alta: o avatar cabe maior
    src = Path(d.__file__).read_text(encoding="utf-8")
    assert "SetCursorPos" in src and "0x1B" in src  # devolve o mouse e o Esc para tudo

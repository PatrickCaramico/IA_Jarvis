"""V9.5.7: música em todo briefing que o senhor inicia (bom dia, boa tarde, boa noite), sem o "uma vez por dia", e
quando não dá ele diz por quê. Antes, clicando em "bom dia" de novo no mesmo dia, ele não falava nada do Spotify."""
import asyncio

from core import briefing_flow
from modules import morning_music as mm
from modules import prefs, spotify


def _music(monkeypatch, *, trying, skip=None, plan=None):
    async def fake_start():
        return plan

    async def no_pause():
        return None

    monkeypatch.setattr(briefing_flow, "_morning_music_start", fake_start)
    monkeypatch.setattr(briefing_flow, "_pause_music", no_pause)
    monkeypatch.setattr(briefing_flow, "_morning_music_wanted", lambda: trying)
    monkeypatch.setattr(briefing_flow, "_morning_music_skip", lambda: skip)


def _run(mode="morning"):
    falas = []

    async def say(text):
        falas.append(text)

    async def go():
        m = briefing_flow.Music(mode)
        m.task = asyncio.ensure_future(m._run())
        await m.wait_pause()
        await m.wait_ready(say=say)
        await m.task

    asyncio.run(go())
    return falas


def test_spotify_desconectado_avisa(monkeypatch):
    _music(monkeypatch, trying=False, skip="not_connected")
    assert _run() == [briefing_flow.NOT_CONNECTED_SPEECH]


def test_tentou_e_nao_tocou_avisa(monkeypatch):
    _music(monkeypatch, trying=True, plan=None)
    assert _run() == [briefing_flow.FAILED_SPEECH]


def test_tocou_nao_precisa_de_aviso(monkeypatch):
    _music(monkeypatch, trying=True, plan=mm.Plan("Back in Black", "pc1", "uri", playing=True))
    assert _run() == []


def test_quem_nunca_configurou_ou_desligou_nao_ouve_aviso(monkeypatch):
    for skip in ("not_configured", "off", "silent"):
        _music(monkeypatch, trying=False, skip=skip)
        assert _run() == []


def test_boa_tarde_e_boa_noite_tambem_tem_musica(monkeypatch):
    for mode in ("afternoon", "evening"):
        _music(monkeypatch, trying=True, plan=None)
        assert _run(mode) == [briefing_flow.FAILED_SPEECH]  # tentou tocar
    _music(monkeypatch, trying=True, plan=None)
    assert _run("topic") == []  # telas por assunto: sem música


def test_motivo_de_nao_tocar(monkeypatch):
    monkeypatch.setattr(spotify, "connected", lambda: False)
    monkeypatch.setattr(spotify, "configured", lambda: True)
    assert mm.skip_reason() == "not_connected"
    monkeypatch.setattr(spotify, "configured", lambda: False)
    assert mm.skip_reason() == "not_configured"
    monkeypatch.setattr(spotify, "connected", lambda: True)
    assert mm.skip_reason() is None
    prefs.update(intro_song_morning=False)
    assert mm.skip_reason() == "off"


def test_boa_noite_termina_no_volume_do_painel(monkeypatch):
    prefs.update(music_volume=45, briefing_end_volume=80)
    assert mm.evening_volume() == 45
    vols = []
    monkeypatch.setattr(spotify, "set_volume", lambda v, device_id=None: vols.append(v))
    mm.finish(mm.Plan("x", "pc1", "uri", playing=True), sleep=lambda s: None, target=mm.evening_volume())
    assert vols[-1] == 45 and max(vols) <= 45

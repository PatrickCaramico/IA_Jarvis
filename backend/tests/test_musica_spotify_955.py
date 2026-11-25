"""V9.5.5: música do "bom dia" no Spotify do PC. Antes, com o Spotify do celular aberto, o JARVIS escolhia o celular e
nem abria o programa no PC; uma tentativa que falhou cedo bloqueava a música do dia; e o briefing não avisava que
estava esperando o Spotify. Agora: abre o do PC, diz "Conectando ao Spotify, senhor." e só então começa."""
import asyncio
from datetime import date

from core import briefing_flow
from modules import morning_music as mm
from modules import prefs, spotify

TODAY = date(2026, 11, 25)
PHONE = {"id": "cel", "type": "Smartphone", "is_active": False}
PC = {"id": "pc1", "type": "Computer", "is_active": False}


# ------------------------------------------------------------------ o Spotify do PC
def test_prefere_o_pc_mesmo_com_o_celular_aberto(monkeypatch):
    rodadas = iter([[PHONE], [PHONE], [PHONE, PC]])
    abriu = []
    monkeypatch.setattr(spotify, "devices", lambda: next(rodadas))
    monkeypatch.setattr(spotify, "_launch_app", lambda: abriu.append(True) or True)
    got = spotify.ensure_device(wait_s=10, sleep=lambda s: None, prefer_computer=True)
    assert got == "pc1" and abriu == [True]  # abriu o programa no PC e esperou ele aparecer


def test_pc_ja_aberto_nao_abre_de_novo(monkeypatch):
    monkeypatch.setattr(spotify, "devices", lambda: [PHONE, PC])
    monkeypatch.setattr(spotify, "_launch_app", lambda: (_ for _ in ()).throw(AssertionError("não devia abrir")))
    assert spotify.ensure_device(prefer_computer=True) == "pc1"


def test_pc_nao_aparece_usa_o_celular(monkeypatch):
    monkeypatch.setattr(spotify, "devices", lambda: [PHONE])
    monkeypatch.setattr(spotify, "_launch_app", lambda: True)
    assert spotify.ensure_device(wait_s=0.01, sleep=lambda s: None, prefer_computer=True) == "cel"


def test_sem_preferir_o_pc_continua_como_antes(monkeypatch):
    monkeypatch.setattr(spotify, "devices", lambda: [PHONE])
    assert spotify.ensure_device() == "cel"


# ------------------------------------------------------------------ a marca antiga não bloqueia mais
def test_marca_antiga_gravada_antes_de_tocar_e_ignorada(monkeypatch):
    monkeypatch.setattr(spotify, "connected", lambda: True)
    prefs.update(intro_song_morning_day=TODAY.isoformat(), intro_song_morning_ok_day="")
    assert mm.wanted(TODAY)  # pode tocar hoje
    prefs.update(intro_song_morning_ok_day=TODAY.isoformat())
    assert mm.wanted(TODAY) is None  # só a marca de quando tocou de verdade conta


# ------------------------------------------------------------------ "Conectando ao Spotify" antes do briefing
def _cenario(monkeypatch, demora, trying=True):
    falas = []

    async def fake_start():
        await asyncio.sleep(demora)
        falas.append("musica")
        return mm.Plan("Back in Black", "pc1", "uri", playing=True)

    async def no_pause():
        return None

    async def say(text):
        falas.append(text)

    monkeypatch.setattr(briefing_flow, "_morning_music_start", fake_start)
    monkeypatch.setattr(briefing_flow, "_pause_music", no_pause)
    monkeypatch.setattr(briefing_flow, "_morning_music_wanted", lambda: trying)
    monkeypatch.setattr(briefing_flow, "CONNECT_NOTICE_AFTER_S", 0.05)

    async def run():
        m = briefing_flow.Music("morning")
        m.task = asyncio.ensure_future(m._run())
        await m.wait_pause()
        await m.wait_ready(say=say)
        falas.append("briefing")
        await m.task

    asyncio.run(run())
    return falas


def test_spotify_abrindo_avisa_e_so_depois_comeca(monkeypatch):
    assert _cenario(monkeypatch, demora=0.2) == [briefing_flow.CONNECT_SPEECH, "musica", "briefing"]


def test_musica_rapida_nao_precisa_de_aviso(monkeypatch):
    assert _cenario(monkeypatch, demora=0.0) == ["musica", "briefing"]


def test_sem_spotify_nao_avisa_nem_espera(monkeypatch):
    assert _cenario(monkeypatch, demora=0.2, trying=False) == ["briefing"]

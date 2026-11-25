"""V9.5.4: briefing logo depois de ligar o PC. Antes, se a voz falhava numa parte, ela passava na hora (o briefing
"pulava" direto para as notícias) e, se a música da manhã não começava junto (Spotify abrindo), ficava sem música."""
import asyncio
from datetime import date

import pytest

from core import briefing_flow, speech
from modules import morning_music as mm
from modules import prefs, spotify

TODAY = date(2026, 11, 25)


# ------------------------------------------------------------------ a parte não passa voando quando a voz falha
def test_voz_falhou_tenta_de_novo_e_segura_o_cartao(monkeypatch):
    falas, esperas = [], []

    async def speak(text, **kw):
        falas.append(text)
        return False  # serviço de voz ainda fora

    async def sleep(s):
        esperas.append(s)

    monkeypatch.setattr(speech, "speak", speak)
    monkeypatch.setattr(briefing_flow.asyncio, "sleep", sleep)
    monkeypatch.setattr(prefs, "is_silent_mode", lambda: False)
    texto = "Hoje faz 24 graus em São Paulo, com chance de chuva à tarde e vento fraco o dia inteiro."
    asyncio.run(briefing_flow._say(texto))
    assert falas == [texto, texto]  # tentou duas vezes
    assert esperas[0] == briefing_flow.VOICE_RETRY_S
    assert 3 <= esperas[-1] <= briefing_flow.MAX_READ_S  # o cartão fica o tempo de ler


def test_voz_ok_nao_espera_nada_a_mais(monkeypatch):
    esperas = []

    async def speak(text, **kw):
        return True

    async def sleep(s):
        esperas.append(s)

    monkeypatch.setattr(speech, "speak", speak)
    monkeypatch.setattr(briefing_flow.asyncio, "sleep", sleep)
    monkeypatch.setattr(prefs, "is_silent_mode", lambda: False)
    asyncio.run(briefing_flow._say("Bom dia, senhor."))
    assert esperas == []


def test_voz_volta_na_segunda_tentativa(monkeypatch):
    respostas = iter([False, True])
    esperas = []

    async def speak(text, **kw):
        return next(respostas)

    async def sleep(s):
        esperas.append(s)

    monkeypatch.setattr(speech, "speak", speak)
    monkeypatch.setattr(briefing_flow.asyncio, "sleep", sleep)
    monkeypatch.setattr(prefs, "is_silent_mode", lambda: False)
    asyncio.run(briefing_flow._say("Agenda de hoje: duas reuniões."))
    assert esperas == [briefing_flow.VOICE_RETRY_S]


# ------------------------------------------------------------------ a música da manhã
@pytest.fixture
def fake(monkeypatch):
    log = []
    state = {"now": {"state": "idle"}, "track": {"uri": "spotify:track:bib", "name": "Back In Black"}, "device_ok": True}
    monkeypatch.setattr(spotify, "connected", lambda: True)
    monkeypatch.setattr(spotify, "now_playing", lambda: state["now"])
    monkeypatch.setattr(spotify, "find_track", lambda q: state["track"])

    def ensure_device(launch=True):
        if not state["device_ok"]:
            raise spotify.SpotifyError("no_device", "sem aparelho")
        return "pc1"

    monkeypatch.setattr(spotify, "ensure_device", ensure_device)
    monkeypatch.setattr(spotify, "set_volume", lambda v, device_id=None: log.append(("vol", v, device_id)))
    monkeypatch.setattr(spotify, "_play", lambda body=None, launch=True, device_id=None: log.append(("play", body["uris"][0], device_id)))
    return log, state


def test_falha_no_comeco_nao_marca_o_dia(fake):
    log, state = fake
    state["device_ok"] = False  # Spotify ainda abrindo
    assert mm.start(TODAY) is None
    assert prefs.get_all().get("intro_song_morning_day") != "2026-11-25"  # ainda pode tocar hoje


def test_segunda_chance_no_fim_toca_no_volume_de_depois(fake):
    log, _ = fake
    assert mm.start_late(TODAY) is True
    assert log == [("vol", mm.target_volume(), "pc1"), ("play", "spotify:track:bib", "pc1")]
    assert prefs.get_all()["intro_song_morning_day"] == "2026-11-25"
    log.clear()
    assert mm.start_late(TODAY) is False and log == []  # uma vez por dia


def test_segunda_chance_so_sobe_o_volume_se_a_primeira_tocou_atrasada(fake):
    log, state = fake
    state["now"] = {"state": "playing", "title": "Back in Black"}
    assert mm.start_late(TODAY) is True
    assert log == [("vol", mm.target_volume(), None)]  # não toca de novo por cima


def test_segunda_chance_nao_interrompe_outra_musica(fake):
    log, state = fake
    state["now"] = {"state": "playing", "title": "Outra música"}
    assert mm.start_late(TODAY) is False and log == []


def test_fim_do_briefing_chama_a_segunda_chance(monkeypatch):
    chamadas = []
    monkeypatch.setattr(mm, "start_late", lambda today=None: chamadas.append("late") or True)

    async def run(mode, paused, canceled):
        m = briefing_flow.Music(mode)
        m.paused = paused
        await m.finish(canceled)

    asyncio.run(run("morning", None, False))
    asyncio.run(run("morning", None, True))  # cancelado: não toca
    asyncio.run(run("afternoon", None, False))  # só no bom dia
    asyncio.run(run("morning", {"device": "x"}, False))  # a sua música volta, não a da manhã
    assert chamadas == ["late"]

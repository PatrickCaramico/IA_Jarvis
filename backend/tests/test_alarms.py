"""Alarmes por voz (V5.1). "Agora" = terça, 10/11/2026, 14:00. Som e voz simulados."""
import asyncio
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

import main
from core import session, speech
from modules import access, alarms

NOW = datetime(2026, 11, 10, 14, 0)


@pytest.fixture(autouse=True)
def quiet(monkeypatch):
    said, events = [], []

    async def fake_speak(text):
        said.append(text)

    async def fake_broadcast(event):
        events.append(event)

    monkeypatch.setattr(alarms, "player", lambda: None)
    monkeypatch.setattr(alarms, "_ringing", None)
    monkeypatch.setattr(alarms, "_ring_task", None)
    monkeypatch.setattr(alarms, "_pending_create", 0.0)
    alarms.configure(broadcast=fake_broadcast, speak=fake_speak, is_restricted=lambda: False)
    yield said, events
    alarms._ringing = None


def say(text):
    return asyncio.run(alarms.handle_voice(text, NOW))


def test_criar_listar_e_cancelar_por_voz():
    assert say("jarvis me acorda amanha as 7") == "Alarme definido para amanhã às 07:00."
    assert say("alarme de segunda a sexta as 6 e meia") == "Alarme definido para de segunda a sexta às 06:30."
    assert "reuniao" in say("coloca um alarme as 16 para a reuniao")
    reply = say("quais sao meus alarmes")
    assert reply.startswith("Você tem 3 alarmes") and "amanhã às 07:00" in reply
    assert say("cancela o alarme das 7") == "Alarme de amanhã às 07:00 cancelado."
    assert len(alarms.list_alarms()) == 2
    assert say("apaga todos os alarmes") == "Pronto. Apaguei os 2 alarmes."


def test_sem_horario_pergunta_e_entende_a_resposta():
    assert say("me acorda") == "Para que horas, senhor?"
    assert say("as 6 da manha") == "Alarme definido para amanhã às 06:00."
    assert say("as 6 da manha") is None  # já respondeu: frase solta não vira alarme


def test_toca_fala_a_hora_e_para(quiet):
    said, events = quiet

    async def run():
        alarms.add_alarm(datetime(2026, 11, 10, 7, 0), None, "")
        await alarms.check_due(datetime(2026, 11, 10, 7, 0, 5))
        assert alarms.is_ringing()
        await asyncio.sleep(0.05)
        reply = await alarms.handle_ringing_voice("jarvis parar")
        return reply

    assert asyncio.run(run()) == "Alarme desligado, senhor."
    assert not alarms.is_ringing() and alarms.list_alarms() == []  # alarme único some depois de tocar
    assert said and said[0] == "Senhor, são 7 horas."
    assert [e["state"] for e in events] == ["ringing", "stopped"]


def test_soneca_e_repeticao(quiet):
    async def run():
        alarms.add_alarm(datetime(2026, 11, 10, 6, 0), [0, 1, 2, 3, 4], "academia")
        await alarms.check_due(datetime(2026, 11, 10, 6, 0, 30))
        return await alarms.handle_ringing_voice("mais 5 minutos")

    reply = asyncio.run(run())
    assert reply.startswith("Certo, senhor. Toco de novo às")
    items = alarms.list_alarms()
    # o que repete foi para quarta 06:00; a soneca virou um alarme único
    assert any(a["dias"] == [0, 1, 2, 3, 4] and a["proximo"] == "2026-11-11 06:00" for a in items)
    assert any(not a["dias"] and a["rotulo"] == "academia" for a in items)


def test_alarme_perdido_nao_toca_atrasado():
    async def run():
        alarms.add_alarm(datetime(2026, 11, 10, 7, 0), None, "")
        await alarms.check_due(datetime(2026, 11, 10, 9, 0))

    asyncio.run(run())
    assert not alarms.is_ringing() and alarms.list_alarms() == []


def test_bloqueado_esconde_o_rotulo(quiet):
    said, events = quiet
    alarms.configure(is_restricted=lambda: True)

    async def run():
        alarms.add_alarm(datetime(2026, 11, 10, 7, 30), None, "remédio da pressão")
        await alarms.check_due(datetime(2026, 11, 10, 7, 30))
        await asyncio.sleep(0.05)
        await alarms.stop()

    asyncio.run(run())
    assert events[0]["rotulo"] == "" and "remédio" not in " ".join(said)
    assert said[0] == "Senhor, são 7 e meia."


def test_parar_pela_rota_com_a_central_bloqueada(monkeypatch):
    access.lock("test")
    alarms._ringing = {"id": 99, "hora": "07:00", "rotulo": "", "since": 0}
    client = TestClient(main.app)
    assert client.get("/api/alarms/ringing").json()["ringing"] is True
    assert client.post("/api/alarms/stop").json() == {"stopped": True}
    assert alarms._ringing is None


def test_falar_parar_pelo_chat_bloqueado(monkeypatch):
    async def quiet_speak(*_a, **_k):
        return None

    monkeypatch.setattr(speech, "speak", quiet_speak)
    access.lock("test")
    session.busy = False
    alarms._ringing = {"id": 7, "hora": "07:00", "rotulo": "", "since": 0}
    r = TestClient(main.app).post("/api/chat", json={"message": "Jarvis, parar"}).json()
    assert r["source"] == "alarm" and alarms._ringing is None


def test_hora_falada():
    assert alarms.spoken_time("07:00") == "são 7 horas"
    assert alarms.spoken_time("13:00") == "é 1 hora"
    assert alarms.spoken_time("18:30") == "são 6 e meia"
    assert alarms.spoken_time("12:00") == "é meio-dia"
    assert alarms.spoken_time("00:15") == "são 12 e 15"


# ---------------------------------------------------------------- lembretes com horários naturais (V5.1)
from modules import reminders  # noqa: E402


def lembrete(text):
    from modules.tools import _norm
    n = _norm(text)
    return asyncio.run(reminders.handle_voice(text, n, len(n.split()), ""))


def test_lembretes_horarios_naturais_e_cancelar_um_so():
    r = lembrete("Jarvis, me lembra de ligar para o dentista amanhã às 3 da tarde")
    assert r.endswith("amanhã às 15:00: ligar para o dentista.")
    r = lembrete("me lembra toda terça às 19 de levar o lixo")
    assert "toda terça às 19:00" in r and "levar o lixo" in r
    assert reminders.get_reminders()[-1]["recorrencia"] == "semanal"
    assert "2 lembretes" in lembrete("quais são meus lembretes")
    assert lembrete("cancela o lembrete do dentista") == 'Lembrete "ligar para o dentista" cancelado.'
    assert len(reminders.get_reminders()) == 1
    assert lembrete("apaga todos os lembretes").startswith("Apaguei 1 lembrete")

"""V6.0: rotinas em 1 comando ("modo dormir", "vou dormir", "estou saindo")."""
import asyncio
from datetime import datetime, timedelta

from modules import alarms, protocols, shopping, spotify, system_control, tools

WEATHER = {"place": "São Paulo", "data": {
    "current": {"temperature_2m": 22.4, "weather_code": 61},
    "daily": {"temperature_2m_min": [18, 16], "temperature_2m_max": [26, 24], "weather_code": [61, 1],
              "precipitation_probability_max": [80, 10]}}}


def _fakes(monkeypatch):
    calls = []
    monkeypatch.setattr(tools, "_fetch_weather", lambda city: WEATHER)
    monkeypatch.setattr(spotify, "connected", lambda: True)
    monkeypatch.setattr(spotify, "pause", lambda: calls.append("pause"))
    monkeypatch.setattr(system_control, "_lock_screen", lambda: calls.append("lock"))
    monkeypatch.setattr(system_control, "_set_volume", lambda v: calls.append(f"vol{v}"))
    return calls


def test_vou_dormir(monkeypatch):
    calls = _fakes(monkeypatch)
    alarms.add_alarm((datetime.now() + timedelta(days=1)).replace(hour=6, minute=30, second=0, microsecond=0))
    reply = asyncio.run(protocols.handle_natural("jarvis vou dormir"))
    assert "Seu despertador toca às 06:30." in reply and "Amanhã: céu predominantemente limpo, entre 16 e 24 graus." in reply
    assert reply.endswith("Bom descanso, senhor.") and calls[:2] == ["pause", "vol15"]


def test_estou_saindo(monkeypatch):
    calls = _fakes(monkeypatch)
    shopping.add(["leite", "pão"])
    reply = asyncio.run(protocols.handle_natural("estou saindo"))
    assert reply.startswith("Lá fora, 22 graus") and "guarda-chuva" in reply
    assert "Na lista de compras: leite e pão." in reply and "lock" in calls


def test_modo_frases(monkeypatch):
    _fakes(monkeypatch)
    assert asyncio.run(protocols.handle_natural("modo dormir")).endswith("Bom descanso, senhor.")
    assert asyncio.run(protocols.handle_natural("modo silencioso")) is None  # não é rotina: segue para outro
    assert asyncio.run(protocols.handle_natural("qual o clima")) is None

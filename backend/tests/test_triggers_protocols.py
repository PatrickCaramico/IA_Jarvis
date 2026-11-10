"""Gatilhos condicionais e protocolos (4.2), sem rede e sem mexer no Windows."""
import asyncio
from datetime import datetime

import pytest

from modules import protocols, triggers

SP = triggers.SP_TZ


@pytest.fixture(autouse=True)
def _clean():
    triggers.reset_for_tests()
    yield
    triggers.reset_for_tests()


def _cfg(**over):
    cfg = triggers.merged_config(None)
    for key, values in over.items():
        cfg[key].update(values)
    return cfg


# ------------------------------------------------------------------ gatilhos
def test_rain_only_after_hour_and_above_probability():
    cfg = _cfg()["rain_tomorrow"]
    forecast = {"daily": {"precipitation_probability_max": [10, 80]}}
    assert triggers.rule_rain_tomorrow(cfg, datetime(2026, 10, 30, 19, 0, tzinfo=SP), forecast, "SP") is None
    key, text = triggers.rule_rain_tomorrow(cfg, datetime(2026, 10, 30, 20, 5, tzinfo=SP), forecast, "SP")
    assert "80%" in text and key == "rain:2026-10-30"
    dry = {"daily": {"precipitation_probability_max": [90, 30]}}
    assert triggers.rule_rain_tomorrow(cfg, datetime(2026, 10, 30, 21, 0, tzinfo=SP), dry, "SP") is None


def test_match_soon_window():
    cfg = _cfg()["match_soon"]
    match = {"id": "m1", "date": "2026-10-30T21:30", "status": "scheduled", "opponent": "Santos",
             "seconds_until_match": 25 * 60}
    key, text = triggers.rule_match_soon(cfg, match, "Palmeiras")
    assert "Santos" in text and "25 minutos" in text
    assert triggers.rule_match_soon(cfg, {**match, "seconds_until_match": 3 * 3600}, "Palmeiras") is None
    assert triggers.rule_match_soon(cfg, {**match, "status": "live"}, "Palmeiras") is None


def test_cpu_needs_sustained_load_and_cooldown():
    cfg = _cfg(cpu_high={"threshold": 90, "minutes": 3})["cpu_high"]
    assert triggers.rule_cpu_high(cfg, 95, 1000.0) is None          # começou agora
    assert triggers.rule_cpu_high(cfg, 96, 1000.0 + 120) is None    # 2 min
    assert triggers.rule_cpu_high(cfg, 97, 1000.0 + 181) is not None  # 3 min seguidos
    assert triggers.rule_cpu_high(cfg, 97, 1000.0 + 400) is None    # dentro dos 30 min de intervalo
    assert triggers.rule_cpu_high(cfg, 50, 1000.0 + 500) is None    # baixou: zera a contagem


def test_water_behind_pace():
    cfg = _cfg(water_behind={"enabled": True, "deficit_ml": 500, "after_hour": 14})["water_behind"]
    status = {"goal_ml": 2000, "total_ml": 300, "goal_reached": False, "start_hour": 8, "end_hour": 22}
    now = datetime(2026, 10, 30, 15, 0, tzinfo=SP)  # 50% da janela -> esperado 1000 ml
    key, text = triggers.rule_water_behind(cfg, now, status)
    assert "700 ml" in text
    assert triggers.rule_water_behind(cfg, now, {**status, "total_ml": 900}) is None
    assert triggers.rule_water_behind(cfg, datetime(2026, 10, 30, 10, tzinfo=SP), status) is None


def test_same_alert_is_not_repeated():
    first = triggers._new(("rain:2026-10-30", "chuva"), "rain_tomorrow")
    again = triggers._new(("rain:2026-10-30", "chuva"), "rain_tomorrow")
    assert first and again is None


def test_check_all_uses_only_enabled_rules(monkeypatch):
    from modules import system_monitor, tools, water

    calls = []
    monkeypatch.setattr(tools, "_fetch_weather", lambda city: calls.append("weather") or None)
    monkeypatch.setattr(system_monitor, "snapshot", lambda: {"cpu_percent": 10})
    monkeypatch.setattr(water, "get_status", lambda: calls.append("water") or {})
    off = {k: {"enabled": False} for k in triggers.DEFAULTS}
    assert triggers.check_all(off, fan_enabled=True, team_id="palmeiras") == []
    assert calls == []


def test_trigger_validation():
    assert triggers.validate({"cpu_high": {"threshold": 95}}) is None
    assert "de 50 a 100" in triggers.validate({"cpu_high": {"threshold": 20}})
    assert "desconhecido" in triggers.validate({"nope": {}})
    assert triggers.validate({"rain_tomorrow": {"enabled": "sim"}})


def test_quiet_hours():
    assert triggers.is_quiet(datetime(2026, 10, 30, 23, tzinfo=SP))
    assert triggers.is_quiet(datetime(2026, 10, 30, 6, tzinfo=SP))
    assert not triggers.is_quiet(datetime(2026, 10, 30, 12, tzinfo=SP))


# ------------------------------------------------------------------ protocolos
def test_defaults_are_valid_and_found_without_accents():
    assert protocols.validate(protocols.DEFAULT_PROTOCOLS) is None
    key, proto = protocols.find("gravação", protocols.DEFAULT_PROTOCOLS)
    assert key == "gravacao"
    assert protocols.find("grava", protocols.DEFAULT_PROTOCOLS)[0] == "gravacao"
    assert protocols.find("inexistente", protocols.DEFAULT_PROTOCOLS) is None


def test_validation_rejects_unsafe_or_bad_steps():
    assert "ação inválida" in protocols.validate({"x": {"steps": [{"action": "delete", "value": "C:"}]}})
    assert protocols.validate({"x": {"steps": [{"action": "volume", "value": 150}]}})
    assert protocols.validate({"x": {"steps": [{"action": "playlist", "value": "https://youtube.com"}]}})
    assert protocols.validate({"x": {"steps": []}})


def test_run_executes_steps_in_order_and_reports_problems(monkeypatch):
    done = []

    async def fake_step(step):
        done.append(step["action"])
        return "não abri obs" if step["action"] == "open" else None

    monkeypatch.setattr(protocols, "_run_step", fake_step)
    monkeypatch.setattr(protocols, "_silence_later", lambda delay: asyncio.sleep(0))
    from modules import event_log

    monkeypatch.setattr(event_log, "add", lambda *a, **k: None)
    result = asyncio.run(protocols.run("gravacao", protocols.DEFAULT_PROTOCOLS))
    assert done == ["open", "volume"]  # "silent" fica para depois da fala; "say" não é passo de sistema
    assert result["label"] == "Gravação" and not result["ok"]
    assert "não abri obs" in result["reply"]


def test_voice_commands(monkeypatch):
    async def fake_run(name, user=None):
        return {"reply": f"rodou {name}"}

    monkeypatch.setattr(protocols, "run", fake_run)
    monkeypatch.setattr(protocols, "all_protocols", lambda user=None: protocols.DEFAULT_PROTOCOLS)
    assert asyncio.run(protocols.handle_voice("ativar protocolo trabalho")) == "rodou trabalho"
    assert asyncio.run(protocols.handle_voice("jarvis protocolo gravacao")) == "rodou gravacao"
    assert "Trabalho" in asyncio.run(protocols.handle_voice("quais sao os meus protocolos"))
    assert asyncio.run(protocols.handle_voice("abre o youtube")) is None


def test_protocol_routes_and_lock(client_factory=None):
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    import main
    from modules import access

    client = TestClient(main.app)
    access.reset_for_tests(access.UNLOCKED)
    try:
        data = client.get("/api/protocols").json()
        assert data["using_defaults"] in (True, False) and "focus" in data["actions"]
        assert "cpu_high" in client.get("/api/triggers").json()["triggers"]
        access.reset_for_tests(access.LOCKED)
    finally:
        access.reset_for_tests(access.LOCKED)


# ------------------------------------------------------------------ leitura de tela
def test_screen_intent():
    from modules import screen_assist

    for phrase in ("o que e esse erro na tela", "leia minha tela", "explica essa tela", "o que tem na tela"):
        assert screen_assist.wants_screen(phrase), phrase
    for phrase in ("tira um print", "bloqueia a tela", "aumenta o brilho da tela", "o que e uma tela oled"):
        assert not screen_assist.wants_screen(phrase), phrase


def test_screen_answer_uses_capture_and_llm(monkeypatch):
    from modules import prefs, screen_assist
    from services import llm_orchestrator

    monkeypatch.setattr(prefs, "get_all", lambda: {"screen_assist_enabled": True})
    monkeypatch.setattr(screen_assist, "capture_jpeg_b64", lambda: "IMG")
    seen = {}

    def fake_ask(prompt, image):
        seen.update(prompt=prompt, image=image)
        return "É um erro de permissão."

    monkeypatch.setattr(llm_orchestrator, "ask_with_image", fake_ask)
    assert asyncio.run(screen_assist.answer("o que é esse erro?")) == "É um erro de permissão."
    assert seen["image"] == "IMG" and "TELA" in seen["prompt"]
    monkeypatch.setattr(prefs, "get_all", lambda: {"screen_assist_enabled": False})
    assert "desligada" in asyncio.run(screen_assist.answer("o que é isso?"))


def test_screen_question_is_protected_when_locked():
    from modules import sentinel

    result = asyncio.run(sentinel.classify_and_answer("jarvis o que é esse erro na tela", "locked"))
    assert result.get("requires_unlock") is True

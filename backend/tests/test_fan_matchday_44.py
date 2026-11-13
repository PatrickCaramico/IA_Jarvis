"""V4.4: agenda real do Modo Torcedor (ESPN + Google Notícias, sem IA) e ligar sozinho no dia do jogo."""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from modules import prefs, sports_provider
from modules.sports_provider import SP_TZ


def _espn_event(event_id, when_utc, home_id, away_id, state="pre", name="STATUS_SCHEDULED", home_score=None, away_score=None, clock="0'"):
    def team(tid, side, score):
        names = {"2029": "Palmeiras", "4936": "Remo", "3454": "Vasco da Gama"}
        return {"homeAway": side, "team": {"id": tid, "displayName": names[tid], "shortDisplayName": names[tid]},
                "score": score if score is not None else {"$ref": "http://x"}}
    return {
        "id": event_id,
        "date": when_utc,
        "league": {"name": "Brazil Serie A", "slug": "bra.1"},
        "competitions": [{
            "venue": {"fullName": "Allianz Parque"},
            "status": {"displayClock": clock, "type": {"state": state, "name": name}},
            "competitors": [team(home_id, "home", home_score), team(away_id, "away", away_score)],
        }],
    }


@pytest.fixture
def fan_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(sports_provider, "CACHE_FILE", tmp_path / "fan_cache.json")
    monkeypatch.setattr(prefs, "_SETTINGS_PATH", tmp_path / "jarvis_settings.json")
    return tmp_path


def test_parse_espn_event_home_and_away():
    ev = _espn_event("1", "2026-11-05T22:30Z", "2029", "4936")
    m = sports_provider.parse_espn_event(ev, 2029)
    assert m["opponent"] == "Remo"
    assert m["home_away"] == "home"
    assert m["competition"] == "Brasileirão"
    assert m["date"].startswith("2026-11-05T19:30")  # horário de Brasília
    assert m["score"] == {"home": 0, "away": 0}  # placar como link ($ref) vira 0

    away = sports_provider.parse_espn_event(_espn_event("2", "2026-11-08T20:00Z", "3454", "2029"), 2029)
    assert away["opponent"] == "Vasco da Gama" and away["home_away"] == "away"
    assert sports_provider.parse_espn_event(_espn_event("3", "2026-11-08T20:00Z", "3454", "4936"), 2029) is None


def test_parse_live_score_and_goals():
    ev = _espn_event("9", "2026-11-05T22:30Z", "3454", "2029", state="in", name="STATUS_FIRST_HALF",
                     home_score="1", away_score={"value": 2.0}, clock="34'")
    m = sports_provider.parse_espn_event(ev, 2029)
    assert m["status"] == "live" and m["minute"] == "34'"
    assert m["score"] == {"home": 1, "away": 2}
    assert sports_provider.team_goals(m) == (2, 1)  # Palmeiras visitante


def test_google_news_matchday_parser():
    today = datetime(2026, 11, 5, 15, 0, tzinfo=SP_TZ)
    xml = b"""<rss><channel>
      <item><title>Palmeiras x Remo: onde assistir ao vivo e escalacoes - ESPN</title><pubDate>Thu, 05 Nov 2026 21:51:16 GMT</pubDate></item>
      <item><title>Onde vai passar Palmeiras x Remo pelo Brasileirao? - UOL</title><pubDate>Thu, 05 Nov 2026 16:30:00 GMT</pubDate></item>
      <item><title>Palmeiras x Remo Palpite - Onde assistir (05/11) - Trivela</title><pubDate>Thu, 05 Nov 2026 20:54:39 GMT</pubDate></item>
      <item><title>Palmeiras x Remo: onde assistir - LANCE!</title><pubDate>Wed, 04 Nov 2026 23:11:15 GMT</pubDate></item>
      <item><title>Corinthians x Santos: onde assistir</title><pubDate>Thu, 05 Nov 2026 12:00:00 GMT</pubDate></item>
    </channel></rss>"""
    found = sports_provider.parse_google_news_matchday(xml, "Palmeiras", today)
    assert found["match_today"] is True
    assert found["articles"] == 3  # a de ontem e a de outro time não contam
    assert found["opponent"] == "Remo"

    other_day = sports_provider.parse_google_news_matchday(xml, "Palmeiras", today + timedelta(days=3))
    assert other_day["match_today"] is False


def test_current_match_from_cache_is_match_day(fan_cache):
    now = datetime.now(SP_TZ)
    later = (now + timedelta(hours=2)).replace(microsecond=0)
    sports_provider.save_fan_cache({"schedule": {"palmeiras": {"fetched_at": now.isoformat(), "matches": [{
        "id": "espn_1", "espn_event_id": "1", "opponent": "Remo", "competition": "Brasileirão",
        "date": later.isoformat(), "time_known": True, "venue": "Allianz Parque", "home_away": "home",
        "status": "scheduled", "score": {"home": 0, "away": 0}, "minute": None,
    }]}}})
    m = sports_provider.get_current_or_next_match("palmeiras")
    assert m["opponent"] == "Remo"
    assert m["is_match_day"] is (later.date() == now.date())
    assert m["source"] == "espn"
    assert m["countdown"].startswith("Em ")


def test_google_only_match_has_no_time(fan_cache):
    now = datetime.now(SP_TZ)
    sports_provider.save_fan_cache({"google": {"palmeiras": {
        "match_today": True, "articles": 5, "opponent": "Remo", "date": now.date().isoformat(), "checked_at": now.isoformat(),
    }}})
    m = sports_provider.get_current_or_next_match("palmeiras")
    assert m["is_match_day"] is True
    assert m["time_known"] is False
    assert m["countdown"] == "Hoje · horário a confirmar"
    assert m["source"] == "google_news"


def test_no_data_is_not_a_match_day(fan_cache):
    m = sports_provider.get_current_or_next_match("palmeiras")
    assert m["status"] == "unknown"
    assert m["is_match_day"] is False
    assert sports_provider.get_schedule("palmeiras") == []
    assert sports_provider.create_match_reminder()["status"] == "error"


def test_yesterdays_live_match_does_not_hide_next_match(fan_cache, noon, monkeypatch):
    now = sports_provider._now_sp()
    old_live = {
        "id": "espn_old", "espn_event_id": "old", "opponent": "Remo", "competition": "Brasileirão",
        "date": (now - timedelta(days=1, hours=2)).isoformat(), "time_known": True, "home_away": "home",
        "status": "live", "score": {"home": 1, "away": 0}, "minute": "72'",
    }
    next_match = {
        "id": "espn_next", "espn_event_id": "next", "opponent": "Vasco da Gama", "competition": "Brasileirão",
        "date": (now + timedelta(days=2)).isoformat(), "time_known": True, "home_away": "away",
        "status": "scheduled", "score": {"home": 0, "away": 0}, "minute": None,
    }
    sports_provider.save_fan_cache({"schedule": {"palmeiras": {"matches": [old_live, next_match]}}})

    match = sports_provider.get_current_or_next_match("palmeiras")

    assert match["id"] == "espn_next"
    assert match["status"] == "scheduled"

    from fastapi.testclient import TestClient

    import main

    monkeypatch.setattr(sports_provider, "refresh", lambda *args, **kwargs: {})
    response = TestClient(main.app).get("/api/fan/match")
    assert response.json()["match"]["id"] == "espn_next"


def test_live_match_past_three_hour_window_reads_as_finished(fan_cache, noon):
    now = sports_provider._now_sp()
    old_live = {
        "id": "espn_old", "espn_event_id": "old", "opponent": "Remo", "competition": "Brasileirão",
        "date": (now - timedelta(hours=4)).isoformat(), "time_known": True, "home_away": "home",
        "status": "live", "score": {"home": 2, "away": 1}, "minute": "90'",
    }
    sports_provider.save_fan_cache({"schedule": {"palmeiras": {"matches": [old_live]}}})

    match = sports_provider.get_current_or_next_match("palmeiras")

    assert match["id"] == "espn_old"
    assert match["status"] == "finished"
    assert match["minute"] == "Fim"


def test_stale_live_match_schedule_is_rechecked_once(fan_cache, noon, monkeypatch):
    now = sports_provider._now_sp()
    old_live = {
        "id": "espn_old", "espn_event_id": "old", "opponent": "Remo", "competition": "Brasileirão",
        "date": (now - timedelta(days=1, hours=2)).isoformat(), "time_known": True, "home_away": "home",
        "status": "live", "score": {"home": 1, "away": 0}, "minute": "72'",
    }
    sports_provider.save_fan_cache({"schedule": {"palmeiras": {
        "fetched_at": now.isoformat(), "matches": [old_live],
    }}})
    schedule_calls = []
    monkeypatch.setattr(sports_provider, "_fetch_espn_schedule", lambda team_id: schedule_calls.append(team_id) or [old_live])
    monkeypatch.setattr(sports_provider, "_fetch_google_matchday", lambda team: {"match_today": False, "articles": 0})

    sports_provider.refresh("palmeiras")
    sports_provider.refresh("palmeiras")

    assert schedule_calls == [2029]


def test_score_change_detects_goal(fan_cache):
    now = datetime.now(SP_TZ)

    def store(home, away):
        sports_provider.save_fan_cache({**sports_provider.load_fan_cache(), "schedule": {"palmeiras": {"matches": [{
            "id": "espn_7", "espn_event_id": "7", "opponent": "Remo", "competition": "Brasileirão",
            "date": (now - timedelta(minutes=30)).isoformat(), "time_known": True, "home_away": "home",
            "status": "live", "score": {"home": home, "away": away}, "minute": "30'",
            "live_checked_at": now.isoformat(),
        }]}}})

    store(0, 0)
    assert sports_provider.detect_score_change() is None  # primeira leitura só registra
    store(1, 0)
    change = sports_provider.detect_score_change()
    assert change["kind"] == "goal" and change["ours"] == 1
    store(1, 1)
    assert sports_provider.detect_score_change()["kind"] == "conceded"
    assert sports_provider.detect_score_change() is None


def test_refresh_uses_espn_and_google(fan_cache, monkeypatch):
    calls = []
    now = datetime.now(SP_TZ)
    when = (now + timedelta(days=2)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")

    def fake_json(url, **kw):
        calls.append(url)
        return {"events": [_espn_event("5", when, "2029", "4936")]}

    def fake_bytes(url, **kw):
        calls.append(url)
        return b"<rss><channel></channel></rss>"

    monkeypatch.setattr(sports_provider.http_client, "get_json", fake_json)
    monkeypatch.setattr(sports_provider.http_client, "get_bytes", fake_bytes)
    done = sports_provider.refresh("palmeiras")
    assert done["schedule"] and done["google"]
    assert any("teams/2029/schedule" in c for c in calls)
    assert any("news.google.com" in c for c in calls)
    assert sports_provider.get_schedule("palmeiras")[0]["opponent"] == "Remo"

    calls.clear()
    sports_provider.refresh("palmeiras")  # dentro da validade: nada de rede
    assert calls == []


def test_auto_mode_turns_on_once_and_off_next_day(fan_cache, monkeypatch):
    from core import runtime, watchers

    sent = []

    async def fake_broadcast(event):
        sent.append(event)

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    monkeypatch.setattr(watchers, "_say", lambda text: None)
    prefs.update({"fan_mode_enabled": False, "fan_auto_on_match_day": True})
    match = {"is_match_day": True, "opponent": "Remo", "time_known": True,
             "date": datetime.now(SP_TZ).replace(hour=19, minute=30).isoformat(), "venue": "Allianz Parque"}

    asyncio.run(watchers._fan_auto_mode(prefs.get_all(), "palmeiras", match))
    assert prefs.get_all()["fan_mode_enabled"] is True
    assert sent[-1]["fan_auto"] is True and "Remo" in sent[-1]["notice"] and "19:30" in sent[-1]["notice"]

    # Desligou na mão no mesmo dia: não liga de novo
    prefs.update({"fan_mode_enabled": False})
    asyncio.run(watchers._fan_auto_mode(prefs.get_all(), "palmeiras", match))
    assert prefs.get_all()["fan_mode_enabled"] is False

    # Dia seguinte, sem jogo: desliga o que ele mesmo ligou
    prefs.update({"fan_mode_enabled": True})
    sports_provider.set_auto_state(activated_on="2000-01-01", by_auto=True)
    asyncio.run(watchers._fan_auto_mode(prefs.get_all(), "palmeiras", {"is_match_day": False}))
    assert prefs.get_all()["fan_mode_enabled"] is False


def test_parse_espn_details_events_stats_standing():
    summary = {
        "keyEvents": [
            {"type": {"type": "kickoff", "text": "Kickoff"}, "clock": {"displayValue": ""}},
            {"type": {"type": "goal", "text": "Goal"}, "clock": {"displayValue": "4'"}, "team": {"id": "2029"},
             "participants": [{"athlete": {"displayName": "Jhon Arias"}}, {"athlete": {"displayName": "Vitor Roque"}}]},
            {"type": {"type": "goal---own", "text": "Own Goal"}, "clock": {"displayValue": "30'"}, "team": {"id": "4936"},
             "participants": [{"athlete": {"displayName": "Zagueiro"}}]},
            {"type": {"type": "red-card", "text": "Red Card"}, "clock": {"displayValue": "60'"}, "team": {"id": "4936"},
             "participants": [{"athlete": {"displayName": "Volante"}}]},
            {"type": {"type": "yellow-card", "text": "Yellow Card"}, "clock": {"displayValue": "61'"}, "team": {"id": "2029"}},
        ],
        "boxscore": {"teams": [
            {"team": {"id": "2029"}, "statistics": [{"name": "possessionPct", "displayValue": "46.4"}, {"name": "totalShots", "displayValue": "3"}]},
            {"team": {"id": "4936"}, "statistics": [{"name": "possessionPct", "displayValue": "53.6"}, {"name": "foulsCommitted", "displayValue": "2"}]},
        ]},
        "standings": {"groups": [{"header": "Brazilian Serie A Standings", "standings": {"entries": [
            {"id": "2029", "stats": [{"name": "rank", "displayValue": "2"}, {"name": "points", "displayValue": "70"}, {"name": "gamesPlayed", "displayValue": "33"}]},
        ]}}]},
    }
    d = sports_provider.parse_espn_details(summary, 2029)
    assert [e["kind"] for e in d["events"]] == ["goal", "own_goal", "red_card"]  # amarelo e início não entram
    assert d["events"][0] == {"kind": "goal", "minute": "4'", "side": "ours", "player": "Jhon Arias",
                              "assist": "Vitor Roque", "penalty": False}
    assert d["stats"]["ours"] == {"possession": 46.4, "shots": 3.0}
    assert d["stats"]["theirs"] == {"possession": 53.6}
    assert d["standing"] == {"rank": 2, "points": 70, "played": 33, "table": "Brasileirão"}


@pytest.fixture
def noon(monkeypatch):
    """Relógio parado às 15h de hoje: um jogo "50 min atrás" nunca cai no dia anterior (rodar à meia-noite)."""
    fixed = datetime.now(SP_TZ).replace(hour=15, minute=0, second=0, microsecond=0)
    monkeypatch.setattr(sports_provider, "_now_sp", lambda: fixed)
    return fixed


def _store_match(status, minute, home=1, away=0):
    now = sports_provider._now_sp()
    sports_provider.save_fan_cache({**sports_provider.load_fan_cache(), "schedule": {"palmeiras": {"matches": [{
        "id": "espn_8", "espn_event_id": "8", "opponent": "Remo", "competition": "Brasileirão",
        "date": (now - timedelta(minutes=50)).isoformat(), "time_known": True, "home_away": "home",
        "status": status, "score": {"home": home, "away": away}, "minute": minute,
        "live_checked_at": now.isoformat(), "venue": "Allianz Parque",
    }]}}})


def test_moments_half_and_full_once(fan_cache, noon):
    _store_match("live", "30'")
    assert sports_provider.take_moments()[0] == []
    _store_match("live", "Intervalo")
    assert sports_provider.take_moments()[0] == ["half"]
    assert sports_provider.take_moments()[0] == []  # não repete
    _store_match("finished", "Fim")
    assert sports_provider.take_moments()[0] == ["full"]
    assert sports_provider.take_moments()[0] == []


def test_auto_mode_mid_game_speaks_once(fan_cache, monkeypatch, noon):
    """Ligar no meio do jogo: uma fala só, com o placar, e sem o grito repetido depois."""
    from core import runtime, watchers

    said = []

    async def fake_broadcast(event):
        pass

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    monkeypatch.setattr(watchers, "_say", said.append)
    prefs.update({"fan_mode_enabled": False, "fan_auto_on_match_day": True})
    _store_match("live", "19'", home=2, away=0)
    match = sports_provider.get_current_or_next_match()
    asyncio.run(watchers._fan_auto_mode(prefs.get_all(), "palmeiras", match))
    assert said == ["Bola rolando: Palmeiras 2 a 0 Remo, aos 19 minutos. Modo Torcedor ativado. Avante Palestra!"]
    assert sports_provider.should_trigger_shout() is False   # o grito já foi junto
    assert sports_provider.detect_score_change() is None     # gols antigos não são comemorados


def test_auto_mode_after_game_does_not_announce_end_again(fan_cache, monkeypatch, noon):
    from core import runtime, watchers

    async def fake_broadcast(event):
        pass

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    said = []
    monkeypatch.setattr(watchers, "_say", said.append)
    prefs.update({"fan_mode_enabled": False, "fan_auto_on_match_day": True})
    _store_match("finished", "Fim", home=3, away=1)
    asyncio.run(watchers._fan_auto_mode(prefs.get_all(), "palmeiras", sports_provider.get_current_or_next_match()))
    assert said[0].startswith("Hoje teve Palmeiras 3 a 1 Remo.")
    assert sports_provider.take_moments()[0] == []  # o "fim de jogo" já foi dito na ativação


def test_fan_toggle_route_works_locked_and_counts_as_manual(fan_cache, monkeypatch, credentials):
    """Botão do bloqueio: liga/desliga com a central bloqueada; escolha manual não é desfeita sozinha."""
    from fastapi.testclient import TestClient

    import main
    from core import runtime, watchers
    from modules import access

    async def fake_broadcast(event):
        pass

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    monkeypatch.setattr(watchers, "_say", lambda text: None)
    access.reset_for_tests(access.LOCKED)
    prefs.update({"fan_mode_enabled": False})
    client = TestClient(main.app)

    assert client.post("/api/fan/toggle", json={}).json()["fan_mode_enabled"] is True
    assert prefs.get_all()["fan_mode_enabled"] is True
    assert client.patch("/api/prefs", json={"fan_mode_enabled": False}).status_code == 403  # o resto continua travado

    # Ligado na mão: o "fim do dia" não desliga sozinho
    sports_provider.set_auto_state(activated_on="2000-01-01")
    asyncio.run(watchers._fan_auto_mode(prefs.get_all(), "palmeiras", {"is_match_day": False}))
    assert prefs.get_all()["fan_mode_enabled"] is True

    # Desligado na mão no dia do jogo: não religa
    assert client.post("/api/fan/toggle", json={"enabled": False}).json()["fan_mode_enabled"] is False
    asyncio.run(watchers._fan_auto_mode(prefs.get_all(), "palmeiras", {"is_match_day": True, "opponent": "Remo"}))
    assert prefs.get_all()["fan_mode_enabled"] is False


def test_manual_matchday_activation_turns_off_next_day(fan_cache, monkeypatch, noon):
    from fastapi.testclient import TestClient

    import main
    from core import runtime, watchers
    from modules import access

    async def fake_broadcast(event):
        sent.append(event)

    sent = []
    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    monkeypatch.setattr(watchers, "_say", lambda text: None)
    prefs.update({"fan_mode_enabled": False})
    now = sports_provider._now_sp()
    match = {
        "id": "espn_today", "espn_event_id": "today", "opponent": "Remo", "competition": "Brasileirão",
        "date": (now + timedelta(hours=2)).isoformat(), "time_known": True, "home_away": "home",
        "status": "scheduled", "score": {"home": 0, "away": 0}, "minute": None,
    }
    sports_provider.save_fan_cache({"schedule": {"palmeiras": {"matches": [match]}}})
    access.reset_for_tests(access.LOCKED)
    client = TestClient(main.app)

    assert client.post("/api/fan/toggle", json={"enabled": True}).json()["fan_mode_enabled"] is True
    assert sports_provider.auto_state()["activated_on_match_day"] is True

    monkeypatch.setattr(sports_provider, "_now_sp", lambda: now + timedelta(days=1))
    monkeypatch.setattr(runtime, "notify", lambda *args, **kwargs: None)
    asyncio.run(watchers._fan_auto_mode(prefs.get_all(), "palmeiras", {"is_match_day": False}))

    assert prefs.get_all()["fan_mode_enabled"] is False
    assert len([event for event in sent if "Modo Torcedor desligado" in event.get("notice", "")]) == 1
    assert "Próximo jogo:" in sent[-1]["notice"]
    asyncio.run(watchers._fan_auto_mode(prefs.get_all(), "palmeiras", {"is_match_day": False}))
    assert len([event for event in sent if "Modo Torcedor desligado" in event.get("notice", "")]) == 1


def test_manual_activation_without_matchday_remains_enabled(fan_cache, monkeypatch, noon):
    from fastapi.testclient import TestClient

    import main
    from core import runtime, watchers
    from modules import access

    async def fake_broadcast(event):
        pass

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    prefs.update({"fan_mode_enabled": False})
    access.reset_for_tests(access.LOCKED)
    client = TestClient(main.app)

    assert client.post("/api/fan/toggle", json={"enabled": True}).json()["fan_mode_enabled"] is True
    assert sports_provider.auto_state()["activated_on_match_day"] is False

    next_day = sports_provider._now_sp() + timedelta(days=1)
    monkeypatch.setattr(sports_provider, "_now_sp", lambda: next_day)
    asyncio.run(watchers._fan_auto_mode(prefs.get_all(), "palmeiras", {"is_match_day": False}))

    assert prefs.get_all()["fan_mode_enabled"] is True


def test_auto_pref_migrates_on(fan_cache):
    (fan_cache / "jarvis_settings.json").write_text('{"fan_auto_on_match_day": false}', encoding="utf-8")
    assert prefs.get_all()["fan_auto_on_match_day"] is True
    prefs.update({"fan_auto_on_match_day": False})  # depois da migração, a escolha do usuário vale
    assert prefs.get_all()["fan_auto_on_match_day"] is False


def test_adversary_logo_does_not_fallback_to_our_team(fan_cache, monkeypatch):
    monkeypatch.setattr(sports_provider, "LOGO_DIR", fan_cache / "fan_logos")
    monkeypatch.setattr(
        sports_provider,
        "get_current_or_next_match",
        lambda team_key: {"logos": {"ours": "https://a.espncdn.com/logo.png"}, "opponent": "Remo"},
    )
    downloads = []
    monkeypatch.setattr(
        sports_provider.http_client,
        "get_bytes",
        lambda url, **kwargs: downloads.append(url) or b"logo",
    )

    result = sports_provider.resolve_logo_path("palmeiras", "theirs")

    assert result is None
    assert downloads == []


def test_google_ignores_youth_women_and_daily_roundups():
    """V5: jogos da base, do feminino e listas "Jogos de hoje" não confirmam jogo do time principal."""
    today = datetime(2026, 11, 9, 15, 0, tzinfo=SP_TZ)
    xml = b"""<rss><channel>
      <item><title>Palmeiras x Santos AO VIVO: Paulista sub-20 (09/11) - Sporting News</title><pubDate>Mon, 09 Nov 2026 15:00:00 GMT</pubDate></item>
      <item><title>Jogos de hoje: Palmeiras x Santos e Corinthians x Palmeiras; veja onde assistir</title><pubDate>Mon, 09 Nov 2026 11:14:00 GMT</pubDate></item>
      <item><title>Segunda-feira tem Corinthians x Palmeiras sub-20; veja horarios</title><pubDate>Mon, 09 Nov 2026 16:20:00 GMT</pubDate></item>
      <item><title>Palmeiras x Flamengo pelo Brasileiro Feminino: onde assistir</title><pubDate>Mon, 09 Nov 2026 12:00:00 GMT</pubDate></item>
      <item><title>Palmeiras x Remo pelo Brasileirao: onde assistir ao vivo - Estadao</title><pubDate>Mon, 09 Nov 2026 05:00:00 GMT</pubDate></item>
    </channel></rss>"""
    found = sports_provider.parse_google_news_matchday(xml, "Palmeiras", today)
    assert found["articles"] == 1  # só a matéria do time principal conta
    assert found["match_today"] is False


def test_fresh_espn_schedule_wins_over_google(fan_cache):
    """V5: com a agenda da ESPN em dia e sem jogo hoje, o Google não inventa "jogo de hoje"."""
    now = datetime.now(SP_TZ)
    sports_provider.save_fan_cache({
        "schedule": {"palmeiras": {"fetched_at": now.isoformat(), "source": "espn", "matches": [{
            "id": "espn_next", "espn_event_id": "next", "opponent": "Cruzeiro", "competition": "Brasileirão",
            "date": (now + timedelta(days=9)).isoformat(), "time_known": True, "venue": "Mineirão",
            "home_away": "away", "status": "scheduled", "score": {"home": 0, "away": 0}, "minute": None,
        }]}},
        "google": {"palmeiras": {
            "match_today": True, "articles": 6, "opponent": "Remo", "date": now.date().isoformat(), "checked_at": now.isoformat(),
        }},
    })
    m = sports_provider.get_current_or_next_match("palmeiras")
    assert m["opponent"] == "Cruzeiro"
    assert m["is_match_day"] is False
    assert m["source"] == "espn"


def test_google_is_backup_when_espn_schedule_is_old(fan_cache):
    """Com a ESPN fora há mais de um dia, o Google continua valendo como reserva."""
    now = datetime.now(SP_TZ)
    sports_provider.save_fan_cache({
        "schedule": {"palmeiras": {"fetched_at": (now - timedelta(days=2)).isoformat(), "source": "espn", "matches": [{
            "id": "espn_next", "espn_event_id": "next", "opponent": "Cruzeiro", "competition": "Brasileirão",
            "date": (now + timedelta(days=9)).isoformat(), "time_known": True, "venue": "Mineirão",
            "home_away": "away", "status": "scheduled", "score": {"home": 0, "away": 0}, "minute": None,
        }]}},
        "google": {"palmeiras": {
            "match_today": True, "articles": 4, "opponent": "Remo", "date": now.date().isoformat(), "checked_at": now.isoformat(),
        }},
    })
    m = sports_provider.get_current_or_next_match("palmeiras")
    assert m["source"] == "google_news"
    assert m["is_match_day"] is True

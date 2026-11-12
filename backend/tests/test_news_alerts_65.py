"""V6.5: manchetes novas dos temas viram aviso no celular."""
from datetime import datetime

from modules import news_alerts as na

MARVEL = {"title": "Marvel", "query": "Marvel", "count": 3}


def items(*titles):
    return [{"title": t, "source": "G1"} for t in titles]


def test_first_time_only_memorizes():
    seen = {}
    assert na.pick_new(MARVEL, items("Filme A estreia - G1", "Série B"), seen) == []
    assert na.theme_key(MARVEL) in seen


def test_new_headlines_are_sent_once_and_capped():
    seen = {}
    na.pick_new(MARVEL, items("Filme A"), seen)
    fresh = na.pick_new(MARVEL, items("Filme C", "Filme A", "Série D", "Jogo E"), seen)
    assert [f["title"] for f in fresh] == ["Filme C", "Série D"]  # no máximo 2 por rodada
    assert na.pick_new(MARVEL, items("Filme C", "Série D"), seen) == []  # já avisadas


def test_same_headline_from_other_source_is_not_new():
    seen = {}
    na.pick_new(MARVEL, items("Thunderbolts bate recorde - G1"), seen)
    assert na.pick_new(MARVEL, items("Thunderbolts bate recorde - Omelete"), seen) == []


def test_quiet_hours_and_text():
    assert na.is_quiet(datetime(2026, 11, 12, 23, 0))
    assert na.is_quiet(datetime(2026, 11, 12, 6, 30))
    assert not na.is_quiet(datetime(2026, 11, 12, 14, 0))
    title, body = na.notice_text(MARVEL, {"title": "Filme A estreia - G1", "source": "G1"})
    assert title == "📰 Marvel" and body == "Filme A estreia · G1"


def test_check_once_respects_pref(monkeypatch):
    from modules import prefs

    monkeypatch.setattr(prefs, "get_all", lambda: {"news_notify_enabled": False})
    assert na.check_once(datetime(2026, 11, 12, 14, 0)) == []

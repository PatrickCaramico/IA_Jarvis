"""V6.8: ofensiva da água (dias seguidos batendo a meta)."""
from datetime import timedelta

from modules import water


def data_with(totals, goal=2000):
    now = water._now()
    days = {(now - timedelta(days=i)).strftime("%Y-%m-%d"): {"total_ml": t, "logs": []} for i, t in totals.items()}
    return {"goal_ml": goal, "days": days}


def test_counts_consecutive_days():
    s = water.streak(data_with({1: 2000, 2: 2500, 3: 2100, 4: 500, 5: 3000}))
    assert s == {"days": 3, "base": 3, "today_done": False, "best": 3}
    s = water.streak(data_with({0: 2000, 1: 2000, 2: 2000}))
    assert s["days"] == 3 and s["today_done"] and s["base"] == 2
    assert water.streak(data_with({0: 100, 2: 3000}))["days"] == 0  # ontem falhou: zerou


def test_voice_and_sentence():
    assert water.parse_water_command("Jarvis, qual minha ofensiva de água?") == ("streak", 0)
    assert water.parse_water_command("como está minha sequência de água") == ("streak", 0)
    assert "zerada" in water.streak_sentence({"days": 0, "base": 0, "today_done": False, "best": 0}, {"goal_ml": 2000, "total_ml": 0})
    text = water.streak_sentence({"days": 4, "base": 4, "today_done": False, "best": 9}, {"goal_ml": 2000, "total_ml": 1500})
    assert "4 dias" in text and "Faltam 500 ml" in text and "recorde é de 9" in text


def test_status_and_best_saved():
    for i in (3, 2, 1):
        day = (water._now() - timedelta(days=i)).strftime("%Y-%m-%d")
        data = water._load_data()
        data["days"][day] = {"total_ml": 2000, "logs": []}
        water._save_data(data)
    st = water.get_status()
    assert st["streak"] == 3 and st["streak_base"] == 3 and st["streak_today_done"] is False
    st = water.add_intake(2000)
    assert st["streak"] == 4 and st["streak_today_done"] is True
    assert water._load_data()["best_streak"] == 4

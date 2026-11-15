"""V8.1: guarda-roupa, temas de datas, missões e ofensiva (ideia 7)."""
from datetime import date, timedelta

import pytest

from modules import desk, desk_missions


def test_wardrobe_lock_and_migration():
    desk._save({**desk._load(), "avatar": {**desk._load()["avatar"], "acessorio": "coroa"}})
    av = desk._load()["avatar"]
    assert av["chapeu"] == "coroa" and av["acessorio"] == "nenhum"
    with pytest.raises(ValueError, match="Nível 3"):
        desk.update_config({"avatar": {"chapeu": "cartola"}})
    out = desk.update_config({"avatar": {"chapeu": "bone", "roupa": "cachecol", "temas": False}})
    assert out["avatar"]["chapeu"] == "bone" and out["avatar"]["roupa"] == "cachecol" and out["tema"] is None
    desk.add_xp_raw(300, "teste")  # nível 3
    assert desk.update_config({"avatar": {"chapeu": "cartola"}})["avatar"]["chapeu"] == "cartola"


def test_season_themes(monkeypatch):
    monkeypatch.setattr(desk, "game_day", lambda d: False)
    assert desk.season_theme(date(2026, 12, 20))["nome"] == "Natal"
    assert desk.season_theme(date(2026, 10, 31))["chapeu"] == "abobora"
    assert desk.season_theme(date(2026, 2, 17))["nome"] == "Carnaval"  # terça de Carnaval 2026
    assert desk.season_theme(date(2026, 6, 10)) is None
    monkeypatch.setattr(desk, "game_day", lambda d: True)
    assert desk.season_theme(date(2026, 6, 10))["roupa"] == "camisa"


def test_daily_missions_no_repeat_and_auto_complete():
    d1 = date(2026, 11, 16)
    v1 = desk_missions.view(d1)
    assert [i["tipo"] for i in v1["itens"]] == ["uso", "sobre", "bem"]
    v2 = desk_missions.view(d1 + timedelta(days=1))
    assert not {i["id"] for i in v1["itens"]} & {i["id"] for i in v2["itens"]}
    use = v2["itens"][0]
    for _ in range(use["meta"]):
        desk_missions.track(use["acao"], d1 + timedelta(days=1))
    v = desk_missions.view(d1 + timedelta(days=1))
    assert v["itens"][0]["feita"] and v["ofensiva"]["atual"] == 1 and v["ofensiva"]["feita_hoje"]


def test_wellbeing_and_answer_go_to_memory(monkeypatch):
    saved = []
    from modules import memory

    monkeypatch.setattr(memory, "remember", lambda text, **kw: saved.append(text) or {})
    day = date(2026, 11, 16)
    v = desk_missions.view(day)
    with pytest.raises(ValueError):
        desk_missions.mark_done(v["itens"][0]["id"], day)
    r = desk_missions.mark_done(v["itens"][2]["id"], day)
    assert r["xp"]["ganhou"] == 15 and r["missoes"]["feitas"] == 1
    q = v["itens"][1]
    desk_missions.answer(q["id"], "pizza", day)
    assert saved == [f"{q['rotulo']}: pizza"]
    assert q["id"] in desk_missions._load()["respondidas"]


def test_streak_with_shields():
    of = {"atual": 5, "recorde": 5, "ultimo_dia": "2026-11-10", "protetores": 1}
    assert desk_missions._streak_hit(of, date(2026, 11, 12)) is True  # pulou 1 dia: protetor segura
    assert of["atual"] == 6 and of["protetores"] == 0
    assert desk_missions._streak_hit(of, date(2026, 11, 15)) is False  # pulou 2 sem protetor: recomeça
    assert of["atual"] == 1 and of["recorde"] == 6


def test_weekly_shield_capped_and_unlock_toast():
    day = date(2026, 11, 16)
    st = desk_missions._empty()
    for k in range(4):
        desk_missions._roll_week(st, day + timedelta(weeks=k))
    assert st["ofensiva"]["protetores"] == 2
    st = desk_missions._ensure(desk_missions._load(), day)
    st["ofensiva"].update({"atual": 2, "recorde": 2, "ultimo_dia": (day - timedelta(days=1)).isoformat()})
    desk_missions._save(st)
    desk_missions.mark_done(st["itens"][2]["id"], day)
    novos = desk_missions.view(day)["novos"]
    assert {"ref": "olhos_forma:estrela", "nome": "olhos de estrela"} in novos
    desk_missions.seen()
    assert desk_missions.view(day)["novos"] == []


def test_voice_and_cloud():
    assert "missões" in desk_missions.handle_voice("quais sao minhas missoes")
    assert "ofensiva" in desk_missions.handle_voice("como esta minha ofensiva")
    assert desk_missions.handle_voice("abre o spotify") is None
    assert "missoes" in desk.cloud_summary()


def test_mission_routes():
    from fastapi.testclient import TestClient

    from main import app

    c = TestClient(app)
    v = c.get("/api/desk/missions").json()
    assert len(v["itens"]) == 3 and "ofensiva" in v
    assert c.post("/api/desk/missions/nada/done").status_code == 404
    assert c.post("/api/desk/missions/track/olho").status_code == 200
    assert c.post("/api/desk/missions/track/xyz").status_code == 400
    assert c.patch("/api/desk", json={"avatar": {"chapeu": "coroa"}}).status_code == 403

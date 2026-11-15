"""V8.0: Modo Desk: aparência, nível e XP, hábitos, copiados, memória em mapa."""
from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient

from modules import access, desk, memory


def _client():
    import main

    access.reset_for_tests(access.UNLOCKED)
    return TestClient(main.app)


def test_config_validates_everything():
    c = desk.update_config({"avatar": {"corpo": "#FF0000", "olhos": "vermelho", "expressao": "dormindo", "acessorio": "gorro"},
                            "cor": "#a3e635", "ilha": {"tamanho": "grande", "atalho": "Ctrl+Space!!"}})
    assert c["avatar"]["corpo"] == "#ff0000" and c["avatar"]["olhos"] == "#22d3ee"  # cor inválida ignorada
    assert c["avatar"]["expressao"] == "dormindo" and c["avatar"]["acessorio"] == "gorro"
    assert c["cor"] == "#a3e635" and c["ilha"]["tamanho"] == "grande" and c["ilha"]["atalho"] == "PageDown"


def test_levels_and_daily_caps():
    assert desk.level_info(0)["nivel"] == 1 and desk.level_info(99)["nivel"] == 1
    assert desk.level_info(100)["nivel"] == 2 and desk.level_info(299)["nivel"] == 2 and desk.level_info(300)["nivel"] == 3
    d = date(2026, 11, 15)
    gains = [desk.add_xp("tarefa", d) for _ in range(12)]
    assert sum(g["ganhou"] for g in gains if g) == 100 and gains[-1] is None  # teto do dia
    assert desk.add_xp("tarefa", d + timedelta(days=1))["ganhou"] == 10
    assert desk.add_xp("hackear", d) is None


def test_habits_streak_toggle_and_voice():
    desk.habit_add("Treinar", "🏋", "07:00")
    try:
        desk.habit_add("treinar")
        raise AssertionError("duplicado")
    except ValueError:
        pass
    t = date.today()
    for k in (2, 1):
        desk.habit_toggle("treinar", True, t - timedelta(days=k))
    h = desk.habits(t)["itens"][0]
    assert h["sequencia"] == 2 and not h["hoje"] and h["semana"][-3:] == [True, True, False]
    assert "Sequência de 3 dias" in desk.handle_voice("marquei o treino de hoje")
    assert desk.handle_voice("marquei a consulta") is None
    r = desk.habit_toggle("treinar", True, t)
    assert r["habito"]["sequencia"] == 3 and r["feitos_hoje"] == 1
    assert "1 de 1" in desk.handle_voice("como estao meus habitos")
    assert desk.habit_reminders(datetime.combine(t, datetime.min.time()).replace(hour=7)) == []  # já feito hoje
    desk.habit_toggle("treinar", False, t)
    assert desk.habit_reminders(datetime.combine(t, datetime.min.time()).replace(hour=7)) == ["Lembrete do hábito: Treinar."]


def test_clipboard_filters_secrets_and_dedupes():
    assert desk.clip_add("lista: arroz, feijão")
    assert not desk.clip_add("lista: arroz, feijão")  # repetido em seguida
    for secret in ("4111 1111 1111 1111", "Sup3r$enha!", "sk-abcdefghijklmnopqrstuvwxyz123456", "senha: 1234", "482913"):
        assert not desk.clip_add(secret), secret
    assert desk.clip_add("https://exemplo.com/artigo")
    assert [i["texto"] for i in desk.clips()["itens"]] == ["https://exemplo.com/artigo", "lista: arroz, feijão"]
    desk.clip_pause(True)
    assert not desk.clip_add("outra coisa")
    assert desk.clip_remove(None)["itens"] == []


def test_memory_map_groups_by_topic():
    memory.remember("Minha esposa se chama Ana")
    memory.remember("Eu gosto de rock dos anos 80")
    memory.remember("Tenho reunião com cliente toda segunda")
    memory.set_preference("cidade", "Campinas")
    m = desk.memory_map()
    names = {n["rotulo"] for n in m["nos"] if n["tipo"] == "assunto"}
    assert {"Pessoas", "Gostos", "Trabalho", "Casa"} <= names and m["total"] == 4
    assert all(any(link["para"] == n["id"] for link in m["ligacoes"]) for n in m["nos"] if n["id"] != "eu")


def test_routes():
    c = _client()
    assert c.patch("/api/desk", json={"cor": "#a855f7"}).json()["cor"] == "#a855f7"
    assert c.post("/api/desk/habits", json={"nome": "Ler 10 páginas", "icone": "📚"}).json()["total"] == 1
    hid = c.get("/api/desk/habits").json()["itens"][0]["id"]
    assert c.post(f"/api/desk/habits/{hid}/toggle", json={}).json()["feitos_hoje"] == 1
    assert c.get("/api/desk/xp").json()["xp"] >= 15
    assert c.post("/api/desk/habits", json={"nome": "x", "lembrete": "25:00"}).status_code == 400
    assert c.delete(f"/api/desk/habits/{hid}").json()["total"] == 0
    memory.remember("Meu cachorro se chama Thor")
    m = c.post("/api/desk/memory/forget", json={"texto": "Meu cachorro se chama Thor"}).json()
    assert m["apagadas"] == 1 and m["total"] == 0
    assert c.get("/api/desk/clips").json() == {"pausado": False, "itens": []}

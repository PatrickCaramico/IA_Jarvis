"""V8.8.0 (ideia 11): bloqueio do Modo Desk. A rota pública só mostra aparência e CONTAGENS (nada pessoal)."""
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from modules import access, reminders, tasks


def test_lockface_is_public_and_has_no_personal_text():
    import main

    access.reset_for_tests(access.LOCKED)
    c = TestClient(main.app)
    tasks.add_task("Ligar para o médico sobre o exame")
    reminders.add_reminder("Consulta secreta", datetime.now() + timedelta(minutes=30))
    r = c.get("/api/desk/lockface")
    assert r.status_code == 200
    d = r.json()
    assert {"avatar", "cor", "nome", "hora", "tarefas", "lembretes_hoje", "proximo_lembrete", "ofensiva"} <= set(d)
    assert d["tarefas"] >= 1 and isinstance(d["tarefas"], int)
    body = r.text.lower()
    assert "médico" not in body and "medico" not in body and "secreta" not in body  # só contagens
    # a regra de acesso: só a lockface é liberada com a tela bloqueada; tarefas, lembretes e a ilha continuam fechados
    assert access.is_allowed("GET", "/api/desk/lockface", access.LOCKED)
    for path in ("/api/tasks", "/api/reminders", "/api/desk/island", "/api/desk", "/api/memory"):
        assert not access.is_allowed("GET", path, access.LOCKED), path
    access.reset_for_tests(access.UNLOCKED)

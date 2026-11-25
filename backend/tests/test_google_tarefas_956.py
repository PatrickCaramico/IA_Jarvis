"""V9.5.6: 💡 Bloco de ideias <-> Google Tarefas (lista "Ideias JARVIS"). Google falso: nada sai do PC no teste."""
import pytest

from modules import google_calendar, google_tasks, ideas


class FakeGoogle:
    """Imita a API do Google Tarefas com as listas e tarefas em memória."""

    def __init__(self):
        self.lists, self.tasks, self.calls = [], {}, []

    def __call__(self, method, path, **kw):
        self.calls.append((method, path))
        body = kw.get("json") or {}
        if path == "/users/@me/lists" and method == "GET":
            return Resp({"items": self.lists})
        if path == "/users/@me/lists" and method == "POST":
            lst = {"id": f"L{len(self.lists) + 1}", "title": body["title"]}
            self.lists.append(lst)
            return Resp(lst)
        parts = path.split("/")  # /lists/{lid}/tasks[/{tid}]
        if method == "GET":
            return Resp({"items": list(self.tasks.values())})
        if method == "POST":
            tid = f"T{len(self.tasks) + 1}"
            self.tasks[tid] = {"id": tid, "status": "needsAction", **body}
            return Resp(self.tasks[tid])
        if method == "PATCH":
            self.tasks[parts[-1]].update(body)
            return Resp(self.tasks[parts[-1]])
        if method == "DELETE":
            self.tasks.pop(parts[-1], None)
            return Resp({})
        raise AssertionError(path)


class Resp:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


@pytest.fixture
def google(monkeypatch):
    fake = FakeGoogle()
    google_tasks._list_id_cache.clear()
    monkeypatch.setattr(google_tasks, "_req", fake)
    monkeypatch.setattr(google_tasks, "available", lambda: True)
    yield fake
    google_tasks._list_id_cache.clear()


def test_cria_a_lista_uma_vez_e_envia_a_ideia(google):
    idea = ideas.add_idea("Roteiro das lives", title="Aquecimento Orbes", project=True)
    tid = google_tasks.push(idea, google)
    assert google.lists == [{"id": "L1", "title": "Ideias JARVIS"}]
    assert google.tasks[tid]["title"] == "📌 Aquecimento Orbes" and google.tasks[tid]["notes"] == "Roteiro das lives"
    assert ideas.get_idea(idea["id"])["google_task_id"] == tid
    google_tasks.push(ideas.get_idea(idea["id"]), google)  # de novo: atualiza a mesma tarefa
    assert len(google.tasks) == 1 and len(google.lists) == 1


def test_editar_e_apagar_vao_para_o_google(google):
    idea = ideas.add_idea("texto", title="Ideia A")
    tid = google_tasks.push(idea, google)
    edited = ideas.update_idea(idea["id"], title="Ideia A2", project=True)
    google_tasks.push(edited, google)
    assert google.tasks[tid]["title"] == "📌 Ideia A2"
    google_tasks.remove(tid, google)
    assert tid not in google.tasks


def test_traz_o_que_foi_anotado_no_app(google):
    lid = google_tasks.list_id(google)
    google("POST", f"/lists/{lid}/tasks", json={"title": "📌 Canal no YouTube", "notes": "Série sobre o JARVIS"})
    google("POST", f"/lists/{lid}/tasks", json={"title": "Comprar microfone"})
    out = google_tasks.pull(google)
    assert out == {"novas": 2, "atualizadas": 0}
    by_title = {i["titulo"]: i for i in ideas.list_ideas()}
    assert by_title["Canal no YouTube"]["projeto"] is True and by_title["Comprar microfone"]["projeto"] is False
    assert google_tasks.pull(google) == {"novas": 0, "atualizadas": 0}  # não duplica


def test_concluida_no_google_sai_dos_projetos(google):
    idea = ideas.add_idea("x", title="Projeto velho", project=True)
    tid = google_tasks.push(idea, google)
    google.tasks[tid]["status"] = "completed"
    assert google_tasks.pull(google)["atualizadas"] == 1
    assert ideas.get_idea(idea["id"])["projeto"] is False  # continua no bloco, mas sai do briefing


def test_sem_permissao_de_tarefas_nao_tenta(monkeypatch):
    monkeypatch.setattr(google_calendar, "connected", lambda: True)
    monkeypatch.setattr(google_calendar, "granted_scopes", lambda: {"https://www.googleapis.com/auth/calendar.readonly"})
    assert google_tasks.available() is False  # conectou antes da 9.5.6: precisa conectar de novo
    assert google_tasks.safe(lambda: 1 / 0) is None  # nem chama
    monkeypatch.setattr(google_calendar, "granted_scopes", lambda: {google_calendar.TASKS_SCOPE})
    assert google_tasks.available() is True


def test_falha_do_google_nao_derruba(google, caplog):
    def boom(*a):
        raise RuntimeError("sem internet")

    assert google_tasks.safe(boom) is None
    assert "não consegui sincronizar" in caplog.text


def test_pedido_de_permissao_inclui_tarefas():
    assert google_calendar.TASKS_SCOPE in google_calendar._SCOPES


def test_ideia_por_tarefa():
    assert google_tasks.idea_from_task({"title": "📌 Projeto X", "notes": "n"}) == {"titulo": "Projeto X", "texto": "n", "projeto": True}
    assert google_tasks.idea_from_task({"title": "📌 Feito", "status": "completed"})["projeto"] is False
    assert google_tasks.task_body({"titulo": "A", "texto": "A", "projeto": False}) == {"title": "A", "notes": ""}

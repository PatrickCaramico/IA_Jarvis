"""V9.5.6: 💡 BLOCO DE IDEIAS (módulo, rotas, skills de voz, briefing) e o aviso de lembrete vencido."""
import asyncio
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from core.skills import registry, router
from modules import briefing, ideas, reminders


def run(coro):
    return asyncio.run(coro)


# ------------------------------------------------------------------ módulo
def test_anota_lista_edita_e_apaga():
    a = ideas.add_idea("App de receitas que reconhece ingredientes pela câmera", now=1)
    assert a["titulo"].startswith("App de receitas") and a["projeto"] is False
    b = ideas.add_idea("site do churrasco", title="Churrasco 2027", project=True, now=2)
    assert [i["id"] for i in ideas.list_ideas()] == [b["id"], a["id"]]  # projetos primeiro
    ideas.update_idea(a["id"], project=True, now=3)
    assert [i["id"] for i in ideas.projects()] == [a["id"], b["id"]]  # o mais recente primeiro
    assert ideas.delete_idea(b["id"]) and not ideas.delete_idea(999)
    with pytest.raises(ValueError):
        ideas.add_idea("   ")


def test_sem_projetos_marcados_usa_as_ideias_recentes():
    ideas.add_idea("ideia um", now=1)
    ideas.add_idea("ideia dois", now=2)
    assert [i["titulo"] for i in ideas.projects()] == ["ideia dois", "ideia um"]


def test_fala_do_briefing():
    assert ideas.briefing_speech([]) == ""
    assert ideas.briefing_speech([{"titulo": "A"}]) == "No seu bloco de ideias, o projeto do momento é A."
    assert ideas.briefing_speech([{"titulo": "A"}, {"titulo": "B"}, {"titulo": "C"}]) == \
        "No seu bloco de ideias, 3 projetos em andamento: A, B e C."


def test_briefing_le_os_projetos():
    assert briefing._ideas_segment() is None  # bloco vazio: fica de fora
    for t in ("Projeto Orbes", "Canal do YouTube", "App JARVIS no celular"):
        ideas.add_idea(t, title=t, project=True)
    seg = briefing._ideas_segment()
    assert seg["tab"] == "ideias" and seg["card"]["label"].startswith("PROJETOS")
    assert len(seg["card"]["items"]) == 3 and "3 projetos em andamento" in seg["speech"]


# ------------------------------------------------------------------ rotas
def test_rotas_do_bloco(monkeypatch):
    import main

    client = TestClient(main.app)
    monkeypatch.setattr("modules.access.is_restricted", lambda: False, raising=False)
    r = client.post("/api/ideas", json={"texto": "ideia pela central", "projeto": True})
    if r.status_code in (401, 403):
        pytest.skip("rotas protegidas exigem a central liberada neste ambiente de teste")
    assert r.status_code == 200
    idea = r.json()["idea"]
    assert client.get("/api/ideas").json()["ideas"][0]["id"] == idea["id"]
    assert client.patch(f"/api/ideas/{idea['id']}", json={"titulo": "Novo título"}).json()["idea"]["titulo"] == "Novo título"
    assert client.delete(f"/api/ideas/{idea['id']}").status_code == 200
    assert client.post("/api/ideas", json={"texto": ""}).status_code == 400


# ------------------------------------------------------------------ voz
@pytest.mark.parametrize("phrase, args", [
    ("anota uma ideia: app de receitas com a câmera", {"texto": "app de receitas com a câmera", "projeto": False}),
    ("Jarvis, tive uma ideia: um site para o churrasco", {"texto": "um site para o churrasco", "projeto": False}),
    ("nova ideia de projeto: Canal no YouTube", {"texto": "Canal no YouTube", "projeto": True}),
    ("anota um projeto, aplicativo de treino", {"texto": "aplicativo de treino", "projeto": True}),
])
def test_frases_de_anotar(real_skills, phrase, args):
    from modules.quick_replies import _norm

    sk, got = registry.match(_norm(phrase), phrase)
    assert sk.name == "anotar_ideia" and got == args


@pytest.mark.parametrize("phrase", ["quais sao meus projetos", "quais sao minhas ideias", "le minhas ideias"])
def test_frases_de_ler(real_skills, phrase):
    sk, _ = registry.match(phrase, phrase)
    assert sk.name == "ler_ideias"


@pytest.mark.parametrize("phrase", ["anota ai", "anota que eu preciso comprar pao", "qual a ideia disso",
                                    "minha agenda de hoje", "projeto trabalho"])
def test_frases_que_nao_sao_do_bloco(real_skills, phrase):
    hit = registry.match(phrase, phrase)
    assert hit is None or hit[0].name not in ("anotar_ideia", "ler_ideias")


def test_anotar_e_ler_por_voz(real_skills):
    r = run(router.try_fast_path("nova ideia de projeto: Canal no YouTube"))
    assert r.speech.startswith("Projeto anotado")
    assert ideas.list_ideas()[0]["titulo"] == "Canal no YouTube"
    r = run(router.try_fast_path("quais são meus projetos"))
    assert "Canal no YouTube" in r.speech and r.cards[0]["data"]["tag"] == "BLOCO DE IDEIAS"


def test_ler_bloco_vazio(real_skills):
    assert "vazio" in run(router.try_fast_path("quais são minhas ideias")).speech


# ------------------------------------------------------------------ lembrete vencido
def test_lembrete_vencido_abre_o_aviso_e_fala(monkeypatch):
    avisos, falas = [], []

    async def due(info):
        avisos.append(info)

    async def fala(text):
        falas.append(text)

    monkeypatch.setattr(reminders, "_due_hook", due)
    monkeypatch.setattr(reminders, "_announcer", fala)
    rem = reminders.add_reminder("ligar para a mãe", datetime(2020, 1, 1, 9, 0))
    run(reminders.check_pending_reminders())
    assert avisos and avisos[0]["id"] == rem["id"] and avisos[0]["atrasado"] is True
    assert falas == ["Atenção, lembrete das 01/01 às 09:00: ligar para a mãe."]
    run(reminders.check_pending_reminders())
    assert len(avisos) == 1  # uma vez só


def test_mensagem_no_horario_e_atrasada():
    alvo = datetime(2026, 11, 25, 14, 0)
    assert reminders.due_message("x", alvo, datetime(2026, 11, 25, 14, 1)) == "Atenção, lembrete: x."
    assert reminders.due_message("x", alvo, datetime(2026, 11, 25, 15, 0)) == "Atenção, lembrete das 14:00: x."


def test_adiar_pelo_aviso():
    rem = reminders.add_reminder("beber água", datetime(2020, 1, 1, 9, 0))
    novo = reminders.postpone_by_id(rem["id"], 10, now=datetime(2026, 11, 25, 14, 0))
    assert novo["data_hora"] == "2026-11-25 14:10" and novo["disparado"] is False
    assert reminders.postpone_by_id(999) is None


def test_data_invalida_vai_para_o_log(caplog):
    reminders._save_reminders([{"id": 1, "texto": "x", "data_hora": "amanhã", "disparado": False}])
    run(reminders.check_pending_reminders())
    assert "data inválida" in caplog.text

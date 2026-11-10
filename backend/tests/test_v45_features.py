"""V4.5 (última leva): memória de longo prazo, arquivos com confirmação, WhatsApp e finanças por voz."""
import asyncio
from datetime import datetime

from core import confirm, session
from modules import files, finances, memory, tools, whatsapp
from modules.finances import SP_TZ


def run(text):
    return asyncio.run(tools.run(text))


def test_memory_remember_recall_forget():
    assert "Guardado" in run("Lembre que eu treino às 18h")
    assert "Eu treino às 18h" in memory.facts()
    assert "treino às 18h" in run("o que você lembra de mim?")
    assert "esqueci 1" in run("esqueça o treino")
    assert memory.facts() == []


def test_memory_context_includes_previous_sessions(monkeypatch):
    memory.add_conversation("qual meu time?", "Palmeiras, senhor.")
    monkeypatch.setattr(memory, "_BOOT", "9999-12-31T00:00:00")  # tudo conta como sessão anterior
    assert "Conversas recentes de sessões anteriores" in memory.prompt_context()
    assert "qual meu time?" in memory.prompt_context()


def test_finances_by_voice():
    assert "R$ 45,00 em mercado" in run("gastei 45 reais no mercado")
    run("paguei 120 de luz")
    assert "Entrada de R$ 3.000,00" in run("recebi 3000 de salário")
    s = finances.summary("month", now=datetime.now(SP_TZ))
    assert s["spent"] == 165 and s["earned"] == 3000 and s["by_category"]["Contas"] == 120
    assert "R$ 165,00" in run("quanto eu gastei esse mês?")
    assert "Apaguei o último" in run("apaga o último gasto")
    assert finances.summary("month")["earned"] == 0


def test_whatsapp_needs_confirmation(monkeypatch):
    opened = []
    monkeypatch.setattr(whatsapp, "open_chat", lambda data: opened.append(data) or "aberto")
    session.pending_action = None
    assert "salvo" in run("salva o contato Ana 11 99999-8888")
    reply = run("manda uma mensagem no whatsapp para a Ana dizendo que eu chego às 8")
    assert "Posso abrir?" in reply and opened == []        # nada abre antes do "sim"
    assert asyncio.run(confirm.answer("sim")) == "aberto"
    assert opened[0]["phone"] == "5511999998888" and opened[0]["text"] == "eu chego às 8"


def test_files_trash_and_mkdir_need_confirmation(tmp_path, monkeypatch):
    desk = tmp_path / "Desktop"
    desk.mkdir()
    (desk / "rascunho.txt").write_text("x", encoding="utf-8")
    monkeypatch.setattr(files, "personal_roots", lambda: [desk])
    trashed = []
    monkeypatch.setattr(files, "send_to_trash", lambda path: trashed.append(path) or "foi para a Lixeira")
    session.pending_action = None
    files.remember([{"path": str(desk / "rascunho.txt"), "name": "rascunho.txt"}])
    assert "Diga sim" in run("manda o primeiro para a lixeira")
    assert trashed == []
    assert "Lixeira" in asyncio.run(confirm.answer("sim"))
    assert trashed == [str(desk / "rascunho.txt")]

    assert "Crio a pasta Projetos" in run("cria uma pasta projetos na área de trabalho")
    assert not (desk / "Projetos").exists()
    assert "criada" in asyncio.run(confirm.answer("sim"))
    assert (desk / "Projetos").is_dir()


def test_files_refuse_outside_personal_folders(tmp_path, monkeypatch):
    monkeypatch.setattr(files, "personal_roots", lambda: [tmp_path / "Desktop"])
    assert "Não posso" in files.move_to(str(tmp_path / "x.txt"), str(tmp_path / "Desktop"))
    assert "Só crio pastas" in files.make_folder(str(tmp_path / "fora" / "nova"))

"""V8.11 (Q8): "abre o X" desconhecido ou de sistema só abre depois do "sim" (skills/abrir_programa.py)."""
import asyncio

import pytest

from core import confirm, session, voice_route
from core.skills import registry
from modules import tools
from skills import abrir_programa as ap


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def opened(real_skills, monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(ap.subprocess, "Popen", lambda args, **kw: calls.append(args))
    exe = tmp_path / "editorx.exe"
    exe.write_text("", encoding="utf-8")
    monkeypatch.setattr(ap.shutil, "which", lambda name: str(exe) if name == "editorx" else None)
    monkeypatch.setattr(ap, "_app_paths", lambda exe_name: None)
    return calls, exe


def test_dangerous_names():
    assert ap.is_dangerous("cmd") and ap.is_dangerous("Windows PowerShell") and ap.is_dangerous("prompt de comando")
    assert ap.is_dangerous("meu terminal favorito", r"C:\Windows\System32\cmd.exe")
    assert ap.is_dangerous("editor do registro")
    assert not ap.is_dangerous("discord", r"C:\Users\x\AppData\Local\Discord\Update.exe")


def test_resolve_refuses_injection_and_paths(opened):
    assert ap.resolve("editorx") is not None
    assert ap.resolve("editorx & del c") is None
    assert ap.resolve("..\\editorx") is None and ap.resolve("c:/windows/editorx") is None
    assert ap.resolve("nao existe") is None


def test_unknown_program_asks_then_opens(opened):
    calls, exe = opened
    reply = run(tools.run("abre o editorx"))
    assert reply == "O Editorx não está nos seus atalhos. Abro o programa editorx.exe, senhor? Diga sim para confirmar."
    assert calls == []  # nada abriu antes do "sim"
    assert session.pending_action["data"]["name"] == "abrir_programa"
    assert run(confirm.answer("sim")) == "Iniciando Editorx, senhor."
    assert calls == [[str(exe)]]


def test_no_means_nothing_opens(opened):
    calls, _ = opened
    run(tools.run("abre o editorx"))
    assert run(confirm.answer("nao")) == "Certo, senhor. Não mexi em nada."
    assert calls == []


def test_remote_request_is_refused(opened):
    calls, _ = opened
    token = voice_route.set_remote(True)
    try:
        reply = run(tools.run("abre o editorx"))
    finally:
        voice_route.reset_remote(token)
    assert reply.startswith("Por segurança, só abro o Editorx") and session.pending_action is None and calls == []


def test_truly_unknown_still_says_so(opened):
    assert run(tools.run("abre o programinhaxyz")) == "Não conheço esse site. Adicione em Configurações > Meus Sites."


def test_dangerous_start_menu_shortcut_asks(opened, monkeypatch):
    started = []
    monkeypatch.setattr(tools.os, "name", "nt")
    monkeypatch.setattr(tools.os, "startfile", lambda p: started.append(p), raising=False)
    monkeypatch.setattr(tools, "_find_start_menu_app", lambda name, index=None: (
        ("windows powershell", r"C:\Menu\Windows PowerShell.lnk") if "powershell" in name else
        ("discord", r"C:\Menu\Discord.lnk") if "discord" in name else None))
    assert tools._try_open_smart("powershell") == (False, "ask", "Windows Powershell", r"C:\Menu\Windows PowerShell.lnk")
    assert started == []
    assert tools._try_open_smart("discord")[:2] == (True, "app")  # programa comum do Menu Iniciar abre direto
    assert started == [r"C:\Menu\Discord.lnk"]


def test_dangerous_question_wording(opened):
    reply = ap.offer("Windows Powershell", r"C:\Menu\Windows PowerShell.lnk", remote=False)
    assert reply.startswith("O Windows Powershell executa comandos no sistema. Abro mesmo assim")


def test_skill_checks_the_file_again(opened, tmp_path):
    from core.skills import executor
    from core.skills.base import SkillContext

    ctx = SkillContext(confirmed=True)
    bad = run(executor.execute("abrir_programa", {"caminho": str(tmp_path / "x.txt"), "nome": "X"}, ctx))
    assert bad.ok is False and "Não encontrei mais" in bad.speech


def test_not_offered_to_the_ai(real_skills):
    assert "abrir_programa" not in {s.name for s in registry.llm_skills()}
    assert registry.match("abre o editorx", "abre o editorx") is None  # sem frase própria

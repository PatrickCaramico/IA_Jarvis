"""V9.5.8: subida mais rápida e medida por etapa.

- o Iniciar-JARVIS.bat liga o backend direto com o pythonw (sem abrir o PowerShell, que levava segundos com o disco
  frio logo depois de entrar no Windows) e anota cada etapa em logs\\subida.log;
- o run_server.py aguenta o pythonw (sys.stdout/sys.stderr = None derrubavam o uvicorn ao montar o log);
- sem console para herdar, todo PowerShell aberto pelo backend precisa de CREATE_NO_WINDOW (senão pisca uma janela);
- o ligar.log diz quanto o Windows demorou para chamar o atalho da Inicialização.
"""
import ast
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import ligar_jarvis  # noqa: E402
import run_server  # noqa: E402

BAT = (ROOT / "Iniciar-JARVIS.bat").read_bytes().decode("latin-1")


# ------------------------------------------------------------------ run_server no pythonw
def test_pythonw_sem_saida_nao_derruba_o_uvicorn(monkeypatch):
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    run_server.ensure_streams()
    assert sys.stdout is not None and sys.stderr is not None
    import uvicorn.logging

    uvicorn.logging.DefaultFormatter()  # antes: AttributeError ('NoneType' object has no attribute 'isatty')
    print("vai para lugar nenhum")  # e não quebra


def test_com_console_nao_troca_a_saida(monkeypatch):
    out, err = io.StringIO(), io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "stderr", err)
    run_server.ensure_streams()
    assert sys.stdout is out and sys.stderr is err


def test_run_prepara_a_saida_antes_de_ligar(monkeypatch):
    seen = []
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(run_server, "main", lambda: seen.append(sys.stdout is not None))
    assert run_server.run() == 0
    assert seen == [True]


# ------------------------------------------------------------------ Iniciar-JARVIS.bat
def test_backend_sobe_com_o_pythonw_sem_powershell():
    lines = [ln.strip() for ln in BAT.replace("\r", "").split("\n")]
    start = next(i for i, ln in enumerate(lines) if ln.startswith('start "" /d "%BACKEND%"'))
    assert 'venv\\Scripts\\pythonw.exe" run_server.py --host %HOST% --port 8000' in lines[start]
    # a rede de casa continua valendo: a variável é definida logo antes, no mesmo bloco
    assert lines[start - 1] == 'set "JARVIS_NETWORK_MODE=%NETMODE%"'
    assert lines[start - 2] == 'if exist "%BACKEND%\\venv\\Scripts\\pythonw.exe" ('
    # sem o pythonw, o PowerShell de antes continua como reserva
    assert "-ArgumentList 'run_server.py --host %HOST% --port 8000'" in lines[start + 2]


def test_backend_sobe_depois_de_liberar_a_porta_e_antes_da_interface():
    kill = BAT.index("Get-NetTCPConnection -LocalPort 8000,8443")
    start = BAT.index('start "" /d "%BACKEND%"')
    front = BAT.index("serve_frontend.py --host")
    assert kill < start < front


def test_cada_etapa_fica_no_subida_log_em_ordem():
    marks = ["inicio do Iniciar-JARVIS.bat", "backend: ligando", "backend: disparado", "interface local: disparada",
             "ouvido e guardiao: disparados", "espera terminada", "fim"]
    pos = [BAT.index(f'subida.log" echo !date! !time! {m}') for m in marks]
    assert pos == sorted(pos)
    assert BAT.index("backend: ligando") < BAT.index('start "" /d "%BACKEND%"') < BAT.index("backend: disparado")
    assert "nao respondeu em 60 s: chamando o socorro" in BAT
    # o arquivo não cresce para sempre
    assert 'if exist "%ROOT%logs\\subida.log" for %%F' in BAT and "GTR 102400" in BAT


def test_marcas_usam_a_forma_segura_do_echo():
    """CLAUDE.md: nada de `echo texto%var%> arquivo` (o 2 do fim vira 2>). As marcas põem o >> na frente."""
    for ln in BAT.replace("\r", "").split("\n"):
        if "subida.log" in ln and "echo" in ln:
            assert ln.strip().startswith('>> "%ROOT%logs\\subida.log" echo') or ln.strip().startswith("if exist"), ln


# ------------------------------------------------------------------ PowerShell sem janela
def _powershell_calls_without_flags() -> list[str]:
    bad = []
    for path in (ROOT / "backend").rglob("*.py"):
        if any(part in path.parts for part in ("venv", "tests", "node_modules", "__pycache__")):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess"
                    and node.func.attr in {"run", "Popen", "call", "check_call", "check_output"}):
                continue
            if not node.args:
                continue
            first = ast.dump(node.args[0])
            names_powershell = "'powershell'" in first or "'powershell.exe'" in first
            has_flags = any(k.arg == "creationflags" or k.arg is None for k in node.keywords)
            if names_powershell and not has_flags:
                bad.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    return bad


def test_todo_powershell_do_backend_abre_sem_janela():
    assert _powershell_calls_without_flags() == []


# ------------------------------------------------------------------ ligar.log
def test_anotacao_do_atalho_da_inicializacao():
    note = ligar_jarvis.logon_note(now=1000.0, boot=900.0, logon=970.0)
    assert note == "Atalho da Inicialização chamado (30 s depois de entrar no Windows; 100 s depois de ligar o PC)."
    assert ligar_jarvis.logon_note(now=1000.0, boot=None, logon=None) == "Atalho da Inicialização chamado."
    # hora do relógio voltou (ou explorer reiniciado depois): não inventa número negativo
    assert ligar_jarvis.logon_note(now=1000.0, boot=900.0, logon=1200.0) == (
        "Atalho da Inicialização chamado (100 s depois de ligar o PC).")


def test_logon_anota_antes_de_esperar(monkeypatch, tmp_path):
    order = []
    monkeypatch.setattr(ligar_jarvis, "ROOT", tmp_path)
    monkeypatch.setattr(ligar_jarvis, "logon_times", lambda: (900.0, 970.0))
    monkeypatch.setattr(ligar_jarvis.log, "info", lambda msg, *a: order.append(msg % a if a else msg))
    monkeypatch.setattr(ligar_jarvis.time, "sleep", lambda s: order.append(f"sleep {s}"))
    monkeypatch.setattr(ligar_jarvis, "backend_up", lambda timeout=2.0: True)
    assert ligar_jarvis.main(["--logon"]) == 0
    assert order[0].startswith("Atalho da Inicialização chamado (")
    assert order[1] == f"sleep {ligar_jarvis.LOGON_DELAY_S}"


def test_sem_logon_nao_anota(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(ligar_jarvis, "ROOT", tmp_path)
    monkeypatch.setattr(ligar_jarvis, "logon_times", lambda: calls.append("lido") or (None, None))
    monkeypatch.setattr(ligar_jarvis, "backend_up", lambda timeout=2.0: True)
    assert ligar_jarvis.main([]) == 0
    assert calls == []


def test_logon_times_nunca_quebra(monkeypatch):
    import psutil

    def boom(*a, **k):
        raise RuntimeError("sem acesso")

    monkeypatch.setattr(psutil, "process_iter", boom)
    boot, logon = ligar_jarvis.logon_times()
    assert logon is None

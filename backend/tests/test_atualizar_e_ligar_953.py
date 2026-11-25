"""V9.5.3: ⟳ ATUALIZAR E LIGAR na tela "Reconectando". Com o JARVIS do PC fora do ar, a central não tinha como
atualizar; agora o atalho jarvis://atualizar faz o PC baixar a versão nova antes de ligar, e o socorro da subida
também procura uma versão corrigida quando a atual não liga."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import ligar_jarvis  # noqa: E402
import socorro_subida as socorro  # noqa: E402

from modules import launcher_protocol  # noqa: E402

BAT = (ROOT / "Iniciar-JARVIS.bat").read_bytes().decode("utf-8")
INSTALL = (ROOT / "Instalar-Botao-Ligar.bat").read_bytes().decode("utf-8")


def test_endereco_do_atalho_so_escolhe_entre_duas_opcoes():
    assert ligar_jarvis.mode_from_url("jarvis://atualizar") == "atualizar"
    assert ligar_jarvis.mode_from_url("JARVIS://Atualizar/") == "atualizar"
    assert ligar_jarvis.mode_from_url("jarvis://iniciar") == "site"
    assert ligar_jarvis.mode_from_url('jarvis://x" & del C:\\ "') == "site"  # nada vira comando
    assert ligar_jarvis.mode_from_url("") == "site"
    bat = Path("C:/J/Iniciar-JARVIS.bat")
    assert ligar_jarvis.start_command(bat, "atualizar") == ["cmd.exe", "/c", str(bat), "atualizar"]
    assert ligar_jarvis.start_command(bat, "qualquer") == ["cmd.exe", "/c", str(bat), "site"]


def test_atualizar_liga_mesmo_com_o_jarvis_no_ar(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(ligar_jarvis, "ROOT", tmp_path)
    monkeypatch.setattr(ligar_jarvis, "backend_up", lambda timeout=2.0: True)
    monkeypatch.setattr(ligar_jarvis, "start_hidden", lambda bat=None, mode="site": calls.append(mode) or True)
    assert ligar_jarvis.main(["--url", "jarvis://atualizar"]) == 0
    assert ligar_jarvis.main(["--url", "jarvis://iniciar"]) == 0  # já no ar: só ligar não faz nada
    assert calls == ["atualizar"]


def test_atalho_antigo_vira_o_novo_e_so_o_do_jarvis():
    pyw = Path("C:/J/backend/venv/Scripts/pythonw.exe")
    wanted = launcher_protocol.wanted_command(pyw, Path("C:/J"))
    assert wanted.endswith('--url "%1"') and "ligar_jarvis.py" in wanted
    old = '"C:\\Windows\\system32\\cmd.exe" /c ""C:\\J\\Iniciar-JARVIS.bat" site"'
    assert launcher_protocol.needs_update(old, wanted) is True
    assert launcher_protocol.needs_update(wanted, wanted) is False
    assert launcher_protocol.needs_update('"C:\\outro\\app.exe" "%1"', wanted) is False  # de outro programa
    assert launcher_protocol.needs_update(None, wanted) is False  # não instalado: não cria sozinho


def test_fora_do_windows_nao_mexe(monkeypatch):
    monkeypatch.setattr(launcher_protocol.os, "name", "posix")
    assert launcher_protocol.refresh() == "skip"


def test_socorro_baixa_versao_corrigida_quando_a_atual_nao_liga():
    calls = []
    waits = iter([False, True])
    result = socorro.rescue(
        "0.0.0.0", "true", up=lambda: False, wait=lambda s: next(waits), crash=lambda: "ValueError: defeito",
        install=lambda py: calls.append("install") or True, start=lambda py, h, n: calls.append("start"),
        python=Path("py"), update=lambda: calls.append("update") or True)
    assert result == "updated"
    assert calls == ["update", "install", "start"]


def test_bat_modo_atualizar_baixa_antes_das_dependencias():
    assert 'if /i "%~1"=="atualizar" (' in BAT
    i_update = BAT.index('scripts\\atualizar_jarvis.py"')
    assert i_update < BAT.index("---------- 2. Dependencias do Backend")
    assert BAT.count("\r\n") == BAT.count("\n")


def test_instalador_passa_o_endereco_literal():
    assert "--url \\\"%%1\\\"" in INSTALL  # no .bat, %%1 vira o %1 que o Windows troca pelo endereço
    assert "ligar_jarvis.py" in INSTALL
    assert INSTALL.count("\r\n") == INSTALL.count("\n")

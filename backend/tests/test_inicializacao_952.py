"""V9.5.2: inicialização mais confiável. Antes, se o JARVIS caía ao ligar (biblioteca nova de uma atualização,
porta presa), ficava fora do ar em silêncio: o .bat só conferia 3 bibliotecas, o erro não ia para nenhum log e o
guardião só religava quem já tinha estado no ar."""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "backend"))

import guardiao  # noqa: E402
import run_server  # noqa: E402
import socorro_subida as socorro  # noqa: E402

BAT = (ROOT / "Iniciar-JARVIS.bat").read_bytes().decode("utf-8")


# ------------------------------------------------------------------ o motivo da queda fica registrado
def test_queda_ao_ligar_vai_para_o_log(tmp_path, monkeypatch):
    log = tmp_path / "logs" / "backend-erro.log"

    def boom():
        raise ModuleNotFoundError("No module named 'biblioteca_nova'")

    monkeypatch.setattr(run_server, "CRASH_LOG", log)
    monkeypatch.setattr(run_server, "main", boom)
    real = run_server.record_crash
    monkeypatch.setattr(run_server, "record_crash", lambda text: real(text, log))
    assert run_server.run() == 1
    text = log.read_text(encoding="utf-8")
    assert "o JARVIS caiu ao ligar" in text and "biblioteca_nova" in text


def test_porta_ocupada_tambem_fica_registrada(tmp_path, monkeypatch):
    log = tmp_path / "backend-erro.log"
    real = run_server.record_crash
    monkeypatch.setattr(run_server, "record_crash", lambda text: real(text, log))

    def exit1():
        raise SystemExit(1)

    monkeypatch.setattr(run_server, "main", exit1)
    assert run_server.run() == 1
    assert "porta 8000 ocupada" in log.read_text(encoding="utf-8")


# ------------------------------------------------------------------ o socorro entende o motivo
def test_diagnostico_da_queda():
    assert socorro.diagnose("ModuleNotFoundError: No module named 'x'") == "deps"
    assert socorro.diagnose("ImportError: cannot import name") == "deps"
    assert socorro.diagnose("OSError: [WinError 10048] endereço já em uso") == "port"
    assert socorro.diagnose("Saiu com o código 1 (porta 8000 ocupada ou erro ao abrir o servidor).") == "port"
    assert socorro.diagnose("ValueError: algo") == "other"
    assert socorro.diagnose("") is None


def test_le_so_a_ultima_queda_e_se_for_recente(tmp_path):
    log = tmp_path / "backend-erro.log"
    log.write_text("\n===== 2026-11-20 10:00:00 o JARVIS caiu ao ligar =====\nvelho\n"
                   "\n===== 2026-11-25 09:00:00 o JARVIS caiu ao ligar =====\nModuleNotFoundError: novo\n", encoding="utf-8")
    last = socorro.last_crash(log)
    assert "novo" in last and "velho" not in last
    assert socorro.last_crash(log, now=time.time() + socorro.RECENT_S + 5) == ""  # antigo: não vale
    assert socorro.last_crash(tmp_path / "nao-existe.log") == ""


def _rescue(**kw):
    calls = []
    base = dict(up=lambda: False, wait=lambda s: False, crash=lambda: "",
                install=lambda py: calls.append("install") or True,
                start=lambda py, h, n: calls.append(("start", h, n)), python=Path("py"),
                update=lambda: calls.append("update") and False)
    base.update(kw)
    return socorro.rescue("0.0.0.0", "true", **base), calls


def test_socorro_ja_no_ar_nao_faz_nada():
    assert _rescue(up=lambda: True)[0] == "ok"


def test_socorro_so_demorando():
    assert _rescue(wait=lambda s: True)[0] == "slow-ok"


def test_socorro_instala_o_que_falta_e_liga_de_novo():
    waits = iter([False, True])
    result, calls = _rescue(wait=lambda s: next(waits), crash=lambda: "ModuleNotFoundError: No module named 'x'")
    assert result == "fixed"
    assert calls == ["install", ("start", "0.0.0.0", "true")]


def test_socorro_nao_instala_sem_motivo():
    result, calls = _rescue(crash=lambda: "ValueError: outra coisa")
    assert result == "other" and calls == ["update"]  # V9.5.3: procurou versão nova, não havia
    assert _rescue()[0] == "down"
    assert _rescue(crash=lambda: "WinError 10048")[0] == "port"


# ------------------------------------------------------------------ o guardião religa quem nunca respondeu
def test_guardiao_religa_quem_caiu_logo_ao_subir():
    g = guardiao.Guardian(started=1000.0)
    assert g.should_revive(False, 1000.0 + 10, starting_age=5) is False  # Iniciar trabalhando
    assert g.should_revive(False, 1000.0 + guardiao.NEVER_UP_S - 1, None) is False
    assert g.should_revive(False, 1000.0 + guardiao.NEVER_UP_S, None) is True  # nunca respondeu: religa
    assert g.should_revive(False, 1000.0 + guardiao.NEVER_UP_S + 10, None) is False  # dá tempo para subir


def test_guardiao_continua_respeitando_o_teto():
    g = guardiao.Guardian(started=0.0)
    t, revived = 0.0, []
    for _ in range(360):
        if g.should_revive(False, t, None):
            revived.append(t)
        t += guardiao.CHECK_EVERY_S
    assert len(revived) == guardiao.MAX_PER_HOUR


# ------------------------------------------------------------------ o .bat
def test_bat_instala_quando_o_requirements_muda():
    assert 'certutil -hashfile "%BACKEND%\\requirements.txt" SHA256' in BAT
    assert 'if defined REQ_SUM if not "%REQ_SUM%"=="%REQ_OLD%" set "NEED_PIP=1"' in BAT
    assert 'if defined REQ_SUM (> "%BACKEND%\\venv\\.jarvis-req.sha" echo %REQ_SUM%)' in BAT


def test_bat_chama_o_socorro_quando_nao_responde():
    i = BAT.index("Abre o painel assim que backend e frontend responderem")
    rest = BAT[i:]
    assert 'scripts\\socorro_subida.py" "%HOST%" "%NETMODE%"' in rest
    assert rest.index("socorro_subida.py") < rest.index('del "%ROOT%logs\\iniciando.flag"')  # ainda "ligando"


def test_bat_continua_crlf():
    assert BAT.count("\r\n") == BAT.count("\n")

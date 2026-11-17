"""V8.10.0 (ideia 13): varredura do PC lento."""
import os
import time

import pytest

from modules import access, pc_scan


@pytest.mark.parametrize("text", [
    "meu note está lento", "o PC está travando muito", "Jarvis, o computador está pesado hoje",
    "meu notebook ta muito devagar", "roda uma varredura", "otimiza o pc", "tá lento o meu pc",
])
def test_frases_que_disparam(text):
    assert pc_scan.is_slow_request(text)


@pytest.mark.parametrize("text", [
    "o jarvis está lento", "abre o youtube", "a internet está lenta", "toca uma música lenta",
    "otimiza o jarvis", "qual a previsão do tempo",
])
def test_frases_que_nao_disparam(text):
    assert not pc_scan.is_slow_request(text)


def _top(label="Google Chrome", name="chrome.exe", mem=40.0, cpu=5.0):
    return [{"name": name, "label": label, "count": 12, "mem_mb": 6000, "mem_percent": mem, "cpu_percent": cpu, "protected": False}]


def test_diagnostico_memoria_cheia_aponta_o_culpado_e_oferece_fechar():
    d = pc_scan.diagnose({"ram_percent": 92, "cpu_percent": 20, "disk_percent": 50, "top": _top(), "temp_bytes": 0})
    assert d["verdict"] == "fail"
    assert d["speech"].startswith("A memória está quase cheia: 92%") and "Google Chrome (40%)" in d["speech"]
    assert d["fixes"] == ["fechar"]


def test_diagnostico_cpu_disco_lixeira_ligado_inicializacao_bateria():
    d = pc_scan.diagnose({"ram_percent": 50, "cpu_percent": 95, "disk_percent": 93, "disk_free_gb": 8.4,
                          "top": _top(cpu=60), "temp_bytes": 900 * 1024 ** 2, "recycle_bytes": 3 * 1024 ** 3,
                          "uptime_days": 6.2, "startup": 14, "battery": {"percent": 20, "plugged": False}})
    ids = [f["id"] for f in d["findings"]]
    assert ids[:2] == ["cpu", "disco"] and {"temp", "lixeira", "ligado", "inicializacao", "bateria"} <= set(ids)
    assert "Google Chrome está usando 60%" in d["findings"][0]["text"]
    assert set(d["fixes"]) == {"fechar", "temporarios", "lixeira"}
    assert "Posso arrumar pelos botões" in d["speech"]


def test_diagnostico_tudo_tranquilo():
    d = pc_scan.diagnose({"ram_percent": 40, "cpu_percent": 10, "disk_percent": 40, "top": _top(), "temp_bytes": 0,
                          "uptime_days": 0.5, "startup": 3})
    assert d["verdict"] == "ok" and d["fixes"] == [] and d["findings"] == []
    assert "tranquilos" in d["speech"]


def test_nunca_fecha_programas_do_windows_nem_o_jarvis(monkeypatch):
    r = pc_scan.close_programs(["explorer.exe", "svchost.exe", "python.exe", "pythonw.exe", "msedgewebview2.exe"])
    assert r["closed"] == [] and set(r["blocked"]) == {"explorer.exe", "svchost.exe", "python.exe", "pythonw.exe", "msedgewebview2.exe"}


def test_limpa_so_temporarios_antigos(tmp_path):
    velho, novo = tmp_path / "velho.tmp", tmp_path / "sub" / "novo.tmp"
    novo.parent.mkdir()
    velho.write_bytes(b"x" * 2048)
    novo.write_bytes(b"y" * 100)
    old = time.time() - 3 * 86400
    os.utime(velho, (old, old))
    r = pc_scan.clean_temp(tmp_path)
    assert r["removed"] == 1 and r["freed_bytes"] == 2048
    assert not velho.exists() and novo.exists()


def test_varredura_roda_e_tem_o_formato_esperado():
    d = pc_scan.scan()
    for k in ("cpu_percent", "ram_percent", "disk_percent", "top", "findings", "fixes", "speech", "verdict", "temp_bytes"):
        assert k in d
    assert all(not p["protected"] for p in d["top"])


def test_rotas_ficam_fechadas_com_a_central_bloqueada():
    assert not access.is_allowed("GET", "/api/pc/scan", access.LOCKED)
    assert not access.is_allowed("POST", "/api/pc/fix", access.LOCKED)


def test_rota_de_correcao_recusa_acao_desconhecida():
    from fastapi.testclient import TestClient
    from main import app

    c = TestClient(app)
    assert c.post("/api/pc/fix", json={"acao": "formatar"}).status_code == 400
    assert c.post("/api/pc/fix", json={"acao": "fechar", "nomes": []}).status_code == 400


def test_pedido_novo_corta_a_fala_da_resposta_anterior(monkeypatch):
    """V8.10.0: falando a resposta final, um pedido novo interrompe a fala (antes: 409 e o comando se perdia)."""
    import asyncio

    from core import session, speech
    from modules import tts

    stopped = []
    monkeypatch.setattr(tts, "stop_playback", lambda: stopped.append(1))
    monkeypatch.setattr(tts, "clear_prefetch", lambda: None)

    async def fake_play(text, on_playback_start=None):
        await asyncio.sleep(30)

    monkeypatch.setattr(speech, "generate_and_play_speech", fake_play)
    monkeypatch.setattr(speech.prefs, "is_silent_mode", lambda: False)

    async def go():
        session.busy = True
        task = asyncio.create_task(speech.speak("uma resposta bem comprida"))
        await asyncio.sleep(0.05)
        assert speech.only_speaking()
        await speech.interrupt()
        await asyncio.sleep(0.05)
        assert task.cancelled() and not session.busy and stopped
        assert not speech.only_speaking()

    asyncio.run(go())


def test_falas_intermediarias_nao_contam_como_resposta_final():
    from core import speech

    assert not speech.only_speaking()
    src = open(speech.__file__, encoding="utf-8").read()
    assert "if release_busy and current is not None:" in src


def test_abrir_programa_pelo_menu_iniciar_sem_powershell(tmp_path):
    """V8.10.0: "abre o discord" acha o atalho do Menu Iniciar na hora (antes: PowerShell com 2 s de limite)."""
    from modules import tools

    progs = tmp_path / "Programs"
    (progs / "Discord Inc").mkdir(parents=True)
    (progs / "Discord Inc" / "Discord.lnk").write_text("x")
    (progs / "Microsoft Teams (work or school).lnk").write_text("x")
    (progs / "Uninstall Discord.lnk").write_text("x")
    (progs / "Visual Studio Code.lnk").write_text("x")
    (progs / "notas.txt").write_text("x")
    idx = tools._start_menu_index([progs])
    assert "uninstall discord" not in idx and "notas" not in idx
    assert tools._find_start_menu_app("discord", idx)[0] == "discord"
    assert tools._find_start_menu_app("Visual Studio", idx)[0] == "visual studio code"
    assert tools._find_start_menu_app("visualstudiocode", idx)[0] == "visual studio code"
    assert tools._find_start_menu_app("teams", idx)[0].startswith("microsoft teams")
    assert tools._find_start_menu_app("photoshop", idx) is None
    assert tools._find_start_menu_app("x", idx) is None

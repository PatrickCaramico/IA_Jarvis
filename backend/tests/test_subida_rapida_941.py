"""V9.4.1: o JARVIS liga mais rápido — OpenCV, numpy e pygame não seguram mais a subida do backend, o .bat não abre
o PowerShell à toa e a subida registra quanto tempo cada etapa levou."""
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from core import startup_timing
from core.lazy import LazyModule, warm

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent


def test_backend_import_does_not_load_heavy_libs():
    # num interpretador limpo, como na subida de verdade
    code = "import sys, main; print(','.join(m for m in ('cv2', 'pygame', 'numpy') if m in sys.modules))"
    out = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, capture_output=True, text=True, timeout=120, check=True)
    assert out.stdout.strip() == ""  # nenhuma das três carregou


def test_lazy_module_loads_on_first_use_and_can_be_patched(monkeypatch):
    m = LazyModule("json")
    assert not m.loaded and "ainda não carregado" in repr(m)
    assert m.dumps({"a": 1}) == '{"a": 1}' and m.loaded
    monkeypatch.setattr(m, "dumps", lambda obj: "falso")
    assert m.dumps({}) == "falso"
    other = LazyModule("base64")
    warm(other)
    assert other.loaded


def test_face_and_tts_still_use_the_real_libraries():
    from modules import face, tts

    assert face.cv2.IMREAD_COLOR is not None and face.np.uint8 is not None
    assert hasattr(tts.pygame, "mixer")


def test_startup_timing_measure():
    info = startup_timing.measure(now=1_000_100.0, process_start=1_000_090.0, boot=1_000_000.0)
    assert info["process_to_ready_s"] == 10.0 and info["windows_to_process_s"] == 90.0
    # o Windows ligou há dias: não confunde com a subida
    info = startup_timing.measure(now=1_000_100.0, process_start=1_000_090.0, boot=1_000_090.0 - 86400)
    assert "windows_to_process_s" not in info
    assert startup_timing.measure(now=1_000_100.0)["ready_at"]


def test_health_reports_startup(isolated_data):
    import main

    with TestClient(main.app) as client:
        st = client.get("/api/health").json()["startup"]
    assert "ready_at" in st and st.get("process_to_ready_s", 0) >= 0


def test_bat_starts_backend_without_powershell_when_nothing_is_running():
    bat = (ROOT / "Iniciar-JARVIS.bat").read_text(encoding="latin-1")
    netstat = bat.index("netstat -ano -p tcp")
    kill = bat.index("Get-NetTCPConnection -LocalPort 8000,8443")
    start = bat.index("run_server.py --host")
    assert netstat < kill < start  # o PowerShell de encerrar só roda se a porta estiver ocupada
    assert "if not errorlevel 1 (" in bat[netstat:kill]
    assert bat.index("m.version('edge-tts')") > start  # a conferência da voz ficou para depois de ligar

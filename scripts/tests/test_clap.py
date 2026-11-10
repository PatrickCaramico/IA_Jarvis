"""Testes do detector de palmas (Python) e do Ouvinte de Palmas (seção 15).

Rodar na raiz do projeto: python -m pytest scripts/tests
"""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import clap_detector  # noqa: E402
import clap_launcher  # noqa: E402

FIXTURES = json.loads((HERE.parents[1] / "tests" / "fixtures" / "clap_sequences.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("seq", FIXTURES["sequences"], ids=lambda s: s["name"])
def test_shared_sequences(seq):
    assert clap_detector.count_doubles(seq, FIXTURES["frame_ms"]) == seq["expect"]


def test_sensitivity_params():
    assert clap_detector.sensitivity_params(1) == (12, 0.12)
    f, m = clap_detector.sensitivity_params(10)
    assert f == 3 and abs(m - 0.02) < 1e-9


def test_invalid_input_does_not_crash():
    det = clap_detector.ClapDetector()
    assert det.process(float("nan"), 0) is None
    assert det.process("x", 10) is None


@pytest.mark.parametrize("up,clients,expected", [
    (False, None, clap_launcher.START),
    (True, 0, clap_launcher.OPEN_PANEL),
    (True, None, clap_launcher.OPEN_PANEL),
    (True, 1, clap_launcher.NOTHING),
    (True, 3, clap_launcher.NOTHING),
])
def test_decide_action(up, clients, expected):
    assert clap_launcher.decide_action(up, clients) == expected


def test_probe_with_simulated_backend():
    def offline(url):
        return None

    def online_no_page(url):
        return {"status": "ok"} if url.endswith("/api/health") else {"clients": 0}

    def online_with_page(url):
        return {"status": "ok"} if url.endswith("/api/health") else {"clients": 2}

    assert clap_launcher.probe(offline) == (False, None)
    assert clap_launcher.decide_action(*clap_launcher.probe(online_no_page)) == clap_launcher.OPEN_PANEL
    assert clap_launcher.decide_action(*clap_launcher.probe(online_with_page)) == clap_launcher.NOTHING


def test_bat_command_passes_wake():
    cmd = clap_launcher.bat_command(clap_launcher.START)
    assert cmd[-2].endswith("Iniciar-JARVIS.bat") and cmd[-1] == "wake"
    assert clap_launcher.bat_command(clap_launcher.OPEN_PANEL)[-2].endswith("Abrir-Painel.bat")
    assert clap_launcher.bat_command(clap_launcher.NOTHING) is None


def test_wait_backend_gives_up():
    calls = []
    assert clap_launcher.wait_backend(0.05, fetch=lambda u: None, sleep=lambda s: calls.append(s)) is False
    assert clap_launcher.wait_backend(5, fetch=lambda u: {"status": "ok"}, sleep=lambda s: None) is True


def test_config_created_with_defaults(tmp_path):
    path = tmp_path / "clap_launcher.json"
    cfg = clap_launcher.load_config(path)
    assert path.exists() and cfg["cooldown_s"] == 30 and cfg["sensitivity"] == 5
    path.write_text(json.dumps({"sensitivity": 42, "intruso": 1}), encoding="utf-8")
    cfg = clap_launcher.load_config(path)
    assert cfg["sensitivity"] == 10 and "intruso" not in cfg


def test_energy_meter_highpass_rejects_low_frequency():
    np = pytest.importorskip("numpy")
    sr = 48000
    t = np.arange(4800) / sr
    meter = clap_launcher.EnergyMeter(sr, 1000)
    low = meter.rms(0.5 * np.sin(2 * np.pi * 100 * t))
    meter2 = clap_launcher.EnergyMeter(sr, 1000)
    high = meter2.rms(0.5 * np.sin(2 * np.pi * 4000 * t))
    assert high > 4 * low


def test_listener_fires_on_double_clap_energy():
    listener = clap_launcher.Listener(dict(clap_launcher.DEFAULT_CONFIG), test_mode=True)
    seq = next(s for s in FIXTURES["sequences"] if s["name"] == "duas_palmas_300ms")
    for e, t in clap_detector.expand_sequence(seq):
        if listener.detector.process(e, t) == "double":
            listener.fired.set()
    assert listener.fired.is_set()

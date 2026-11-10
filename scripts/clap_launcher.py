"""Ouvinte de Palmas do JARVIS (seção 15): 2 palmas com o JARVIS fechado ligam tudo e já
iniciam o escaneamento facial.

Uso (na pasta do projeto):
    python scripts/clap_launcher.py --list-devices   # lista os microfones
    python scripts/clap_launcher.py --test           # mostra nível e detecções (não abre nada)
    python scripts/clap_launcher.py                  # modo normal (os .bat usam pythonw.exe)

Comportamento ao detectar 2 palmas:
    backend desligado                -> Iniciar-JARVIS.bat wake
    backend ligado e nenhuma página  -> Abrir-Painel.bat wake
    backend ligado e página aberta   -> nada (a página trata as palmas)

Privacidade: o áudio é processado em memória (só a energia de cada quadro). Nada é gravado.
O log (logs/clap_launcher.log) registra apenas horários de disparos e avisos.
Segurança: a palma só INICIA o escaneamento; sem o rosto reconhecido nada é liberado.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from clap_detector import ClapDetector  # noqa: E402

CONFIG_PATH = ROOT / "data" / "clap_launcher.json"
LOG_PATH = ROOT / "logs" / "clap_launcher.log"
BACKEND = "http://127.0.0.1:8000"

DEFAULT_CONFIG = {
    "device": None,            # índice ou nome do microfone (None = padrão do Windows)
    "sensitivity": 5,          # 1 a 10
    "min_gap_ms": 120,         # intervalo mínimo entre as 2 palmas
    "max_gap_ms": 800,         # intervalo máximo entre as 2 palmas
    "cooldown_s": 30,          # espera após um disparo (o JARVIS demora para subir)
    "presence_interval_s": 5,  # intervalo de consulta a /api/health e /api/presence
    "startup_timeout_s": 60,   # desiste de esperar o backend após esse tempo
    "retry_device_s": 30,      # tenta abrir o microfone de novo após falha
    "beep": True,              # bipe curto do Windows ao disparar
    "highpass_hz": 1000,
    "frame_ms": 10,
}

log = logging.getLogger("jarvis.clap_launcher")


# ------------------------------------------------------------------ configuração e log
def load_config(path: Path = CONFIG_PATH) -> dict:
    """Lê data/clap_launcher.json; cria com os valores padrão se não existir."""
    cfg = dict(DEFAULT_CONFIG)
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                cfg.update({k: v for k, v in data.items() if k in DEFAULT_CONFIG})
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False), encoding="utf-8")
    except (OSError, ValueError) as exc:
        log.warning("Configuração inválida (%s); usando padrões.", exc)
    cfg["sensitivity"] = min(10, max(1, int(cfg.get("sensitivity") or 5)))
    return cfg


def setup_logging(to_console: bool) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [RotatingFileHandler(LOG_PATH, maxBytes=512 * 1024, backupCount=2, encoding="utf-8")]
    if to_console:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", handlers=handlers)


# ------------------------------------------------------------------ decisão (testável)
START, OPEN_PANEL, NOTHING = "start", "open_panel", "nothing"


def decide_action(backend_up: bool, clients: Optional[int]) -> str:
    """O que fazer ao detectar 2 palmas."""
    if not backend_up:
        return START
    if clients is None or clients <= 0:
        return OPEN_PANEL
    return NOTHING


def _get_json(url: str, timeout: float = 2.0) -> Optional[dict]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 - só 127.0.0.1
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return None


def probe(fetch: Callable[[str], Optional[dict]] = _get_json) -> tuple[bool, Optional[int]]:
    """(backend respondendo?, número de páginas abertas)."""
    health = fetch(f"{BACKEND}/api/health")
    if not health:
        return False, None
    presence = fetch(f"{BACKEND}/api/presence")
    clients = presence.get("clients") if isinstance(presence, dict) else None
    return True, clients if isinstance(clients, int) else None


def bat_command(action: str) -> Optional[list[str]]:
    name = {START: "Iniciar-JARVIS.bat", OPEN_PANEL: "Abrir-Painel.bat"}.get(action)
    if not name:
        return None
    return ["cmd.exe", "/c", str(ROOT / name), "wake"]


def run_action(action: str) -> bool:
    cmd = bat_command(action)
    if not cmd:
        return False
    flags = 0
    if os.name == "nt":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        subprocess.Popen(cmd, cwd=str(ROOT), creationflags=flags)  # noqa: S603 - comando fixo do projeto
        return True
    except OSError as exc:
        log.error("Não consegui executar %s: %s", cmd[2], exc)
        return False


def wait_backend(timeout_s: float, fetch: Callable[[str], Optional[dict]] = _get_json,
                 sleep: Callable[[float], None] = time.sleep) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if fetch(f"{BACKEND}/api/health"):
            return True
        sleep(2)
    return False


def beep() -> None:
    try:
        import winsound  # só existe no Windows
        winsound.Beep(1200, 120)
    except Exception:  # noqa: BLE001
        pass


# ------------------------------------------------------------------ áudio
class EnergyMeter:
    """Filtro passa-alta de 1ª ordem + RMS por bloco (numpy)."""

    def __init__(self, samplerate: int, cutoff_hz: float) -> None:
        import math
        rc = 1.0 / (2 * math.pi * cutoff_hz)
        dt = 1.0 / samplerate
        self.a = rc / (rc + dt)
        self.prev_x = 0.0
        self.prev_y = 0.0

    def rms(self, block) -> float:
        import numpy as np
        x = np.asarray(block, dtype=np.float64).reshape(-1)
        if x.size == 0:
            return 0.0
        y = np.empty_like(x)
        a, px, py = self.a, self.prev_x, self.prev_y
        for i in range(x.size):  # blocos de ~480 amostras: barato
            py = a * (py + x[i] - px)
            px = x[i]
            y[i] = py
        self.prev_x, self.prev_y = px, py
        return float(np.sqrt(np.mean(y * y)))


def list_devices() -> int:
    try:
        import sounddevice as sd
    except ImportError:
        print("A biblioteca 'sounddevice' não está instalada. Rode: pip install -r scripts/requirements-clap.txt")
        return 1
    print("Microfones disponíveis (use o número em data/clap_launcher.json, campo \"device\"):\n")
    for idx, dev in enumerate(sd.query_devices()):
        if dev.get("max_input_channels", 0) > 0:
            default = " (padrão)" if idx == sd.default.device[0] else ""
            print(f"  [{idx}] {dev['name']}{default}")
    return 0


class Listener:
    def __init__(self, cfg: dict, test_mode: bool = False) -> None:
        self.cfg = cfg
        self.test_mode = test_mode
        self.detector = ClapDetector(cfg["sensitivity"], {
            "min_gap_ms": cfg["min_gap_ms"], "max_gap_ms": cfg["max_gap_ms"],
            "cooldown_ms": 3000 if test_mode else int(cfg["cooldown_s"] * 1000),
        })
        self.paused = threading.Event()
        self.stop = threading.Event()
        self.fired = threading.Event()
        self.level = 0.0
        self.t0 = time.monotonic()

    def on_block(self, energy: float) -> None:
        self.level = energy
        t_ms = (time.monotonic() - self.t0) * 1000.0
        if self.detector.process(energy, t_ms) == "double":
            self.fired.set()

    def presence_loop(self) -> None:
        """Pausa a escuta enquanto houver página do JARVIS aberta (evita 2 detectores no microfone)."""
        while not self.stop.is_set():
            up, clients = probe()
            if up and clients and clients > 0:
                if not self.paused.is_set():
                    log.info("Página do JARVIS aberta: escuta pausada.")
                self.paused.set()
            else:
                if self.paused.is_set():
                    log.info("Nenhuma página aberta: escuta retomada.")
                self.paused.clear()
            self.stop.wait(self.cfg["presence_interval_s"])

    def handle_fire(self) -> None:
        log.info("Palma dupla detectada.")
        if self.cfg.get("beep", True):
            beep()
        if self.test_mode:
            print("\n>>> PALMA DUPLA DETECTADA <<<")
            return
        up, clients = probe()
        action = decide_action(up, clients)
        if action == NOTHING:
            log.info("Página já aberta: nada a fazer.")
            return
        log.info("Ação: %s", "iniciar o JARVIS" if action == START else "abrir o painel")
        if run_action(action) and action == START:
            if not wait_backend(self.cfg["startup_timeout_s"]):
                log.warning("O backend não respondeu em %ss; desisti de esperar.", self.cfg["startup_timeout_s"])

    def run(self) -> int:
        try:
            import sounddevice as sd
        except ImportError:
            log.error("Biblioteca 'sounddevice' ausente. Rode: pip install -r scripts/requirements-clap.txt")
            print("Instale as dependências: pip install -r scripts/requirements-clap.txt")
            return 1
        if not self.test_mode:
            threading.Thread(target=self.presence_loop, daemon=True).start()
        while not self.stop.is_set():
            if self.paused.is_set():
                self.stop.wait(1)
                continue
            try:
                device = self.cfg.get("device")
                info = sd.query_devices(device, "input")
                samplerate = int(info.get("default_samplerate") or 48000)
                block = max(64, int(samplerate * self.cfg["frame_ms"] / 1000))
                meter = EnergyMeter(samplerate, float(self.cfg["highpass_hz"]))

                def callback(indata, frames, time_info, status):  # noqa: ARG001
                    self.on_block(meter.rms(indata[:, 0]))

                with sd.InputStream(device=device, channels=1, samplerate=samplerate, blocksize=block,
                                    dtype="float32", callback=callback):
                    log.info("Ouvindo o microfone (%s).", info.get("name"))
                    self.detector.reset()
                    while not self.stop.is_set() and not self.paused.is_set():
                        if self.fired.wait(0.1):
                            self.fired.clear()
                            self.handle_fire()
                        if self.test_mode:
                            bars = int(min(1.0, self.level * 8) * 40)
                            sys.stdout.write("\r nível " + "#" * bars + " " * (40 - bars) + f" {self.level:.3f} ")
                            sys.stdout.flush()
                # stream fechado aqui: microfone liberado enquanto a página está aberta
            except KeyboardInterrupt:
                break
            except Exception as exc:  # noqa: BLE001 - microfone ocupado/exclusivo, desconectado etc.
                log.error("Falha ao abrir o microfone (%s). Nova tentativa em %ss.", exc, self.cfg["retry_device_s"])
                self.stop.wait(self.cfg["retry_device_s"])
        return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Ouvinte de Palmas do JARVIS")
    parser.add_argument("--list-devices", "-list-devices", action="store_true", help="lista os microfones")
    parser.add_argument("--test", "-test", action="store_true", help="mostra o nível e as detecções, sem abrir nada")
    args = parser.parse_args(argv)
    if args.list_devices:
        return list_devices()
    setup_logging(to_console=args.test or sys.stdout is not None and sys.stdout.isatty())
    cfg = load_config()
    log.info("Ouvinte de Palmas iniciado (sensibilidade %s).", cfg["sensitivity"])
    try:
        return Listener(cfg, test_mode=args.test).run()
    finally:
        log.info("Ouvinte de Palmas encerrado.")


if __name__ == "__main__":
    sys.exit(main())

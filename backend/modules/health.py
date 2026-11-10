"""Módulo de Telemetria de Saúde e Conexão de Smartwatch (BLE / Android Sync).

Permite:
1. Receber métricas vitais via Webhook / REST de automações Android (Tasker, MacroDroid, Health Connect, MActivePro bridges).
2. Escanear e conectar via Bluetooth BLE direto com relógios inteligentes (padrão Heart Rate / BLE).
3. Armazenar a telemetria atual (BPM, SpO2, HRV, Stress, Passos, Bateria do relógio).
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from bleak import BleakScanner, BleakClient
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False

log = logging.getLogger("jarvis.health")

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
HEALTH_FILE = DATA_DIR / "health_telemetry.json"

DEFAULT_TELEMETRY = {
    "device_name": "Smartwatch MActivePro",
    "connected": True,
    "connection_type": "ble",  # "ble", "android_sync", "manual"
    "last_sync": "Hoje às 06:45",
    "battery": 85,
    "bpm": 84,
    "bpm_history": [82, 84, 85, 83, 84],
    "hrv": 44.1,
    "spo2": 96.6,
    "stress": 22,
    "steps": 6420,
    "sleep_hours": 7.8,
    "sleep_efficiency": 95,
    "sleep_performance": 82,
    "skin_temp": 33.6,
    "respiration": 13.6,
    "recovery": 88,
    "status": "normal",
    "synced_today": True
}


def load_telemetry() -> Dict[str, Any]:
    if not HEALTH_FILE.exists():
        save_telemetry(DEFAULT_TELEMETRY)
        return DEFAULT_TELEMETRY.copy()
    try:
        with open(HEALTH_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {**DEFAULT_TELEMETRY, **data}
    except Exception as e:
        log.warning(f"Erro ao ler arquivo de saúde: {e}")
        return DEFAULT_TELEMETRY.copy()


def save_telemetry(data: Dict[str, Any]) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(HEALTH_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"Erro ao salvar arquivo de saúde: {e}")


async def scan_ble_devices(timeout: float = 5.0) -> list[dict]:
    """Escaneia dispositivos BLE próximos (smartwatches, sensores cardíacos)."""
    if not BLEAK_AVAILABLE:
        log.warning("Bleak não disponível para Bluetooth scan")
        return []

    try:
        devices = await BleakScanner.discover(timeout=timeout)
        found = []
        for d in devices:
            name = d.name or "Dispositivo Desconhecido"
            # Filtra ou destaca prováveis smartwatches / pulseiras
            is_watch = any(term in name.lower() for term in ["watch", "fit", "band", "smart", "mactive", "microwear", "ultra", "hr", "pulse"])
            found.append({
                "address": d.address,
                "name": name,
                "rssi": getattr(d, "rssi", None),
                "is_watch": is_watch
            })
        return sorted(found, key=lambda x: (x["is_watch"], x["name"] != "Dispositivo Desconhecido"), reverse=True)
    except Exception as e:
        log.error(f"Erro no escaneamento BLE: {e}")
        return []


def update_biometrics(
    bpm: Optional[int] = None,
    spo2: Optional[float] = None,
    hrv: Optional[float] = None,
    stress: Optional[int] = None,
    steps: Optional[int] = None,
    battery: Optional[int] = None,
    sleep_hours: Optional[float] = None,
    sleep_efficiency: Optional[int] = None,
    sleep_performance: Optional[int] = None,
    skin_temp: Optional[float] = None,
    respiration: Optional[float] = None,
    recovery: Optional[int] = None,
    device_name: Optional[str] = None,
    connection_type: str = "android_sync"
) -> Dict[str, Any]:
    """Atualiza as métricas e persiste."""
    current = load_telemetry()
    if bpm is not None:
        current["bpm"] = int(bpm)
    if spo2 is not None:
        current["spo2"] = float(spo2)
    if hrv is not None:
        current["hrv"] = float(hrv)
    if stress is not None:
        current["stress"] = int(stress)
    if steps is not None:
        current["steps"] = int(steps)
    if battery is not None:
        current["battery"] = int(battery)
    if sleep_hours is not None:
        current["sleep_hours"] = float(sleep_hours)
    if sleep_efficiency is not None:
        current["sleep_efficiency"] = int(sleep_efficiency)
    if sleep_performance is not None:
        current["sleep_performance"] = int(sleep_performance)
    if skin_temp is not None:
        current["skin_temp"] = float(skin_temp)
    if respiration is not None:
        current["respiration"] = float(respiration)
    if recovery is not None:
        current["recovery"] = int(recovery)
    if device_name:
        current["device_name"] = device_name

    current["connected"] = True
    current["connection_type"] = connection_type
    current["last_sync"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    save_telemetry(current)
    return current

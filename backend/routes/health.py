"""Rotas de saúde: biometria e relógios Bluetooth."""

from fastapi import Query
from pydantic import BaseModel
from modules import health as health_module
from modules import access
from fastapi import APIRouter
from core import runtime, speech

router = APIRouter()


class BiometricsUpdateRequest(BaseModel):
    bpm: int | None = None
    spo2: float | None = None
    hrv: float | None = None
    stress: int | None = None
    steps: int | None = None
    battery: int | None = None
    sleep_hours: float | None = None
    sleep_efficiency: int | None = None
    sleep_performance: int | None = None
    skin_temp: float | None = None
    respiration: float | None = None
    recovery: int | None = None
    device_name: str | None = None
    speak_confirmation: bool = True


@router.get("/api/health/biometrics")
async def get_health_biometrics() -> dict:
    """Retorna os dados biométricos atuais persistidos."""
    return health_module.load_telemetry()


@router.post("/api/health/biometrics")
async def update_health_biometrics(req: BiometricsUpdateRequest) -> dict:
    """Atualiza a telemetria do smartwatch recebida via Android Sync / Webhook ou BLE."""
    updated = health_module.update_biometrics(
        bpm=req.bpm,
        spo2=req.spo2,
        hrv=req.hrv,
        stress=req.stress,
        steps=req.steps,
        battery=req.battery,
        sleep_hours=req.sleep_hours,
        sleep_efficiency=req.sleep_efficiency,
        sleep_performance=req.sleep_performance,
        skin_temp=req.skin_temp,
        respiration=req.respiration,
        recovery=req.recovery,
        device_name=req.device_name,
        connection_type="android_sync",
    )

    # Notifica via WebSocket em tempo real para os modais e widgets abertos
    await runtime.manager.broadcast({"type": "health_telemetry_updated", "data": updated})

    # Confirmação vocal do Jarvis se solicitado (nunca com a central bloqueada: são dados de saúde)
    if req.speak_confirmation and not access.is_restricted():
        bpm_str = f"{updated['bpm']} batimentos por minuto" if updated.get("bpm") else ""
        msg = f"Sinais vitais do relógio sincronizados com sucesso, senhor. Deu bom! Batimentos em {bpm_str} e oxigenação em {updated.get('spo2', 98)} porcento."
        runtime.track(speech.speak(msg, release_busy=True))

    return {"status": "ok", "telemetry": updated}


@router.get("/api/health/ble-scan")
async def scan_ble_smartwatches(timeout: float = 4.0) -> dict:
    """Escaneia o ambiente Bluetooth buscando relógios ou sensores BLE."""
    devices = await health_module.scan_ble_devices(timeout=timeout)
    return {"devices": devices}


@router.post("/api/health/connect-ble")
async def connect_ble_device(address: str = Query(...), name: str = Query("Smartwatch")) -> dict:
    """Conecta ou associa um dispositivo Bluetooth escaneado."""
    updated = health_module.update_biometrics(device_name=name, connection_type="ble")
    await runtime.manager.broadcast({"type": "health_telemetry_updated", "data": updated})
    runtime.track(
        speech.speak(
            f"Dispositivo Bluetooth {name} pareado com o sistema Jarvis. Sinais vitais ativos, senhor.",
            release_busy=True,
        )
    )
    return {"status": "connected", "telemetry": updated}

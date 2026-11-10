"""Coleta métricas locais sem assumir que sensores estejam disponíveis."""
import os
import platform
import shutil
import time
from datetime import datetime

_CACHE_TTL_SECONDS = 5.0
_cache = None
_cache_time = 0.0


def snapshot() -> dict:
    global _cache, _cache_time
    now = time.monotonic()
    if _cache is not None and now - _cache_time < _CACHE_TTL_SECONDS:
        return {**_cache, "timestamp": datetime.now().isoformat(timespec="seconds")}

    result = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "platform": platform.system(),
        "cpu_percent": None,
        "ram_percent": None,
        "gpu": "Indisponível",
        "network": "Disponível",
        "temperature": "Indisponível",
        "processes": None,
    }
    try:
        import psutil
        result["cpu_percent"] = psutil.cpu_percent(interval=0.15)
        result["ram_percent"] = psutil.virtual_memory().percent
        result["processes"] = len(psutil.pids())
        result["network"] = "Disponível" if psutil.net_if_stats() else "Indisponível"
        try:
            temps = psutil.sensors_temperatures() if hasattr(psutil, "sensors_temperatures") else {}
            if temps:
                first = next(iter(temps.values()), [])
                if first:
                    result["temperature"] = round(first[0].current, 1)
        except (NotImplementedError, OSError):
            pass
    except (ImportError, OSError, AttributeError):
        result["cpu_percent"] = None
        result["ram_percent"] = None
    result["disk_free_gb"] = round(shutil.disk_usage(os.getcwd()).free / (1024 ** 3), 1)
    _cache = result
    _cache_time = now
    return result

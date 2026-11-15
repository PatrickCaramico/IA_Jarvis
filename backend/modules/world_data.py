"""V7.11: OLHO DE DEUS com dados reais (ideia 4 do documento de atualização).

Camadas, todas de fontes públicas e gratuitas, sem chave:
- chuva: quadros do radar (RainViewer) + previsão da cidade (Open-Meteo);
- voos: aviões perto da cidade (ADS-B público: adsb.lol, com airplanes.live de reserva);
- terremotos: últimas 24 h no mundo (USGS);
- queimadas: focos no Brasil nas últimas 24 h (INPE);
- iss: posição, órbita e passagens visíveis (TLE do CelesTrak + modules/orbit.py).

Cada fonte tem cache curto (para não pesar nem ser bloqueado). Os avisos automáticos (chuva forte chegando,
queimada/terremoto perto, ISS visível) rodam no PC e cada um pode ser desligado.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import math
import threading
from datetime import datetime, timedelta, timezone

from config import settings
from modules import orbit
from services import http_client

log = logging.getLogger("jarvis.world")

USGS = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
RAINVIEWER = "https://api.rainviewer.com/public/weather-maps.json"
OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
FLIGHTS = ("https://api.adsb.lol/v2/point/{lat:.4f}/{lon:.4f}/{nm}", "https://api.airplanes.live/v2/point/{lat:.4f}/{lon:.4f}/{nm}")
INPE = "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil/focos_diario_br_{d}.csv"
CELESTRAK = "https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=TLE"

LAYERS = ("chuva", "voos", "terremotos", "queimadas", "iss")
FLIGHT_RADIUS_KM = 150
NEAR_KM = 50
STRONG_RAIN_MM15 = 1.25  # 1,25 mm em 15 min = 5 mm/h: chuva forte
_TLE_PATH = settings.DATA_DIR / "olho_tle.json"
_PREFS_PATH = settings.DATA_DIR / "olho_avisos.json"
ALERT_KINDS = ("chuva", "perto", "iss")
_lock = threading.RLock()
# América do Sul (para "terremoto forte no Brasil e vizinhos")
SOUTH_AMERICA = (-56.0, 13.5, -82.0, -34.0)


def km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371.0 * 2 * math.asin(min(1.0, math.sqrt(h)))


def _f(v) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- terremotos
def parse_quakes(data: dict, lat: float | None = None, lon: float | None = None) -> list[dict]:
    out = []
    for f in (data or {}).get("features") or []:
        p, g = f.get("properties") or {}, (f.get("geometry") or {}).get("coordinates") or []
        if len(g) < 2 or _f(g[0]) is None or _f(g[1]) is None:
            continue
        mag = _f(p.get("mag"))
        if mag is None:
            continue
        q = {"id": str(f.get("id") or p.get("code") or ""), "lat": round(g[1], 3), "lon": round(g[0], 3),
             "prof_km": round(_f(g[2]) or 0) if len(g) > 2 else None, "mag": round(mag, 1),
             "lugar": str(p.get("place") or "")[:120],
             "quando": datetime.fromtimestamp((_f(p.get("time")) or 0) / 1000, timezone.utc).isoformat(),
             "url": str(p.get("url") or "")}
        if lat is not None:
            q["dist_km"] = round(km(lat, lon, q["lat"], q["lon"]))
        out.append(q)
    out.sort(key=lambda q: -q["mag"])
    return out[:500]


def quakes(lat=None, lon=None) -> dict:
    items = parse_quakes(http_client.get_json(USGS, timeout=12, ttl=300), lat, lon)
    return {"itens": items, "total": len(items), "fortes": sum(1 for q in items if q["mag"] >= 5),
            "maior": items[0] if items else None, "atualizado": _now().isoformat(), "fonte": "USGS"}


# --------------------------------------------------------------------------- voos
def parse_flights(data: dict, lat: float, lon: float) -> list[dict]:
    out = []
    for a in (data or {}).get("ac") or (data or {}).get("aircraft") or []:
        la, lo = _f(a.get("lat")), _f(a.get("lon"))
        if la is None or lo is None:
            continue
        alt = a.get("alt_baro", a.get("alt_geom"))
        ground = alt == "ground"
        alt_ft = 0 if ground else _f(alt)
        gs = _f(a.get("gs"))
        out.append({
            "id": str(a.get("hex") or "")[:8], "voo": str(a.get("flight") or "").strip()[:10],
            "matricula": str(a.get("r") or "")[:10], "modelo": str(a.get("t") or "")[:10],
            "lat": round(la, 4), "lon": round(lo, 4),
            "alt_m": round(alt_ft * 0.3048) if alt_ft is not None else None, "solo": ground,
            "vel_kmh": round(gs * 1.852) if gs is not None else None, "rumo": round(_f(a.get("track")) or 0),
            "dist_km": round(km(lat, lon, la, lo), 1),
        })
    out.sort(key=lambda f: f["dist_km"])
    return out[:300]


def flights(lat: float, lon: float) -> dict:
    nm = round(FLIGHT_RADIUS_KM / 1.852)
    last: Exception | None = None
    for url in FLIGHTS:
        try:
            data = http_client.get_json(url.format(lat=lat, lon=lon, nm=nm), timeout=10, ttl=12)
            items = parse_flights(data, lat, lon)
            return {"itens": items, "total": len(items), "no_ar": sum(1 for f in items if not f["solo"]),
                    "raio_km": FLIGHT_RADIUS_KM, "atualizado": _now().isoformat(), "fonte": "ADS-B público"}
        except Exception as exc:  # noqa: BLE001 - tenta a reserva
            last = exc
    raise last or RuntimeError("sem dados de voos")


# --------------------------------------------------------------------------- queimadas
def parse_fires(text: str, now: datetime | None = None) -> list[dict]:
    now = now or _now()
    rows = csv.DictReader(io.StringIO(text or ""))
    out = []
    for r in rows:
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
        la, lo = _f(r.get("lat") or r.get("latitude")), _f(r.get("lon") or r.get("longitude"))
        if la is None or lo is None:
            continue
        quando = r.get("data_hora_gmt") or r.get("datahora") or ""
        try:
            t = datetime.fromisoformat(quando.replace("/", "-").replace(" ", "T")[:19]).replace(tzinfo=timezone.utc)
        except ValueError:
            t = None
        if t and now - t > timedelta(hours=24):
            continue
        out.append({"lat": round(la, 4), "lon": round(lo, 4), "quando": t.isoformat() if t else "",
                    "municipio": (r.get("municipio") or "").title()[:60], "estado": (r.get("estado") or "").title()[:30],
                    "bioma": r.get("bioma", "")[:20], "frp": _f(r.get("frp"))})
    return out


def _fire_files(now: datetime) -> list[str]:
    br = now - timedelta(hours=3)
    return [INPE.format(d=(br - timedelta(days=k)).strftime("%Y%m%d")) for k in (0, 1)]


def fires(lat: float | None = None, lon: float | None = None, limit: int = 4000) -> dict:
    now = _now()
    items: list[dict] = []
    seen = set()
    ok = False
    for url in _fire_files(now):
        try:
            raw = http_client.get_bytes(url, timeout=20, ttl=900)
        except Exception as exc:  # noqa: BLE001 - o arquivo de hoje pode ainda não existir
            log.info("Queimadas: %s indisponível (%s)", url, exc)
            continue
        ok = True
        for f in parse_fires(raw.decode("utf-8", "replace"), now):
            key = (f["lat"], f["lon"], f["quando"])
            if key not in seen:
                seen.add(key)
                items.append(f)
    if not ok:
        raise RuntimeError("sem dados de queimadas")
    near = []
    if lat is not None:
        for f in items:
            f["dist_km"] = round(km(lat, lon, f["lat"], f["lon"]))
        items.sort(key=lambda f: f["dist_km"])
        near = [f for f in items if f["dist_km"] <= NEAR_KM]
    total = len(items)
    if total > limit:  # mantém os mais próximos e uma amostra do resto (o celular aguenta menos pontos)
        head = items[: limit // 2]
        rest = items[limit // 2:]
        step = len(rest) / (limit - len(head))
        items = head + [rest[int(i * step)] for i in range(limit - len(head))]
    return {"itens": items, "total": total, "perto": len(near), "perto_km": NEAR_KM,
            "mais_perto": near[0] if near else (items[0] if items and lat is not None else None),
            "atualizado": now.isoformat(), "fonte": "INPE"}


# --------------------------------------------------------------------------- chuva
def parse_radar(data: dict) -> dict:
    host = str((data or {}).get("host") or "https://tilecache.rainviewer.com")
    frames = [{"time": int(f["time"]), "path": str(f["path"])}
              for f in ((data or {}).get("radar") or {}).get("past") or [] if f.get("time") and f.get("path")]
    return {"host": host, "quadros": frames[-13:]}


def parse_forecast(data: dict) -> dict:
    m15 = (data or {}).get("minutely_15") or {}
    hourly = (data or {}).get("hourly") or {}
    prox = [{"hora": t[11:16], "t": t, "mm": round(_f(v) or 0, 1)}
            for t, v in zip(m15.get("time") or [], m15.get("precipitation") or [])]
    horas = []
    for i, t in enumerate(hourly.get("time") or []):
        def at(key, i=i):
            vals = hourly.get(key) or []
            return _f(vals[i]) if i < len(vals) else None
        horas.append({"hora": t[11:16], "t": t, "mm": round(at("precipitation") or 0, 1),
                      "prob": at("precipitation_probability"), "nuvens": at("cloud_cover")})
    return {"prox": prox, "horas": horas, "offset": _f((data or {}).get("utc_offset_seconds"))}


def rain_text(fc: dict, local_now: str = "") -> dict:
    """Resumo falado: quando a chuva começa e se é forte (as próximas 3 horas)."""
    slots = [s for s in fc.get("prox") or [] if not local_now or s["t"] >= local_now[:16]][:12]
    first = next((s for s in slots if s["mm"] >= 0.2), None)
    strong = next((s for s in slots if s["mm"] >= STRONG_RAIN_MM15), None)
    if strong:
        mins = _minutes_until(strong["t"], local_now)
        return {"texto": f"Chuva forte por volta das {strong['hora']}", "forte": True, "minutos": mins, "hora": strong["hora"]}
    if first:
        return {"texto": f"Chuva fraca por volta das {first['hora']}", "forte": False,
                "minutos": _minutes_until(first["t"], local_now), "hora": first["hora"]}
    horas = fc.get("horas") or []
    later = next((h for h in horas[:12] if (not local_now or h["t"] >= local_now[:13]) and (h["prob"] or 0) >= 60 and h["mm"] >= 0.5), None)
    if later:
        return {"texto": f"Sem chuva nas próximas 3 h; chance de chuva às {later['hora']}", "forte": False, "minutos": None, "hora": later["hora"]}
    return {"texto": "Sem chuva nas próximas 3 h", "forte": False, "minutos": None, "hora": None}


def _minutes_until(t: str, local_now: str) -> int | None:
    try:
        return max(0, round((datetime.fromisoformat(t) - datetime.fromisoformat(local_now[:16])).total_seconds() / 60))
    except ValueError:
        return None


def forecast(lat: float, lon: float) -> dict:
    return parse_forecast(http_client.get_json(OPEN_METEO, params={
        "latitude": round(lat, 3), "longitude": round(lon, 3), "minutely_15": "precipitation",
        "forecast_minutely_15": 16, "hourly": "precipitation,precipitation_probability,cloud_cover",
        "forecast_days": 4, "timezone": "auto"}, timeout=10, ttl=600))


def _local_now(offset_s: float | None) -> str:
    """A hora local da cidade (o Open-Meteo manda o fuso em segundos; sem isso, a hora do PC)."""
    if offset_s is None:
        return datetime.now().strftime("%Y-%m-%dT%H:%M")
    return (_now() + timedelta(seconds=offset_s)).strftime("%Y-%m-%dT%H:%M")


def rain(lat: float, lon: float) -> dict:
    out: dict = {"atualizado": _now().isoformat(), "fonte": "RainViewer + Open-Meteo"}
    try:
        out["radar"] = parse_radar(http_client.get_json(RAINVIEWER, timeout=10, ttl=300))
    except Exception as exc:  # noqa: BLE001 - sem radar, a previsão segue
        log.info("Radar indisponível: %s", exc)
        out["radar"] = None
    fc = forecast(lat, lon)
    out["previsao"] = {"prox": fc["prox"], "horas": fc["horas"][:24]}
    out["resumo"] = rain_text(fc, _local_now(fc["offset"]))
    return out


# --------------------------------------------------------------------------- estação espacial
def _tle() -> dict:
    with _lock:
        cached = {}
        try:
            cached = json.loads(_TLE_PATH.read_text(encoding="utf-8")) if _TLE_PATH.exists() else {}
        except (OSError, ValueError):
            cached = {}
        fetched = _f(cached.get("baixado")) or 0
        if cached.get("tle") and _now().timestamp() - fetched < 6 * 3600:
            return cached["tle"]
        try:
            tle = orbit.parse_tle(http_client.get_bytes(CELESTRAK, timeout=12).decode("utf-8", "replace"))
        except Exception as exc:  # noqa: BLE001 - usa o TLE guardado (vale por alguns dias)
            log.info("TLE indisponível: %s", exc)
            tle = None
        if tle:
            _TLE_PATH.parent.mkdir(parents=True, exist_ok=True)
            _TLE_PATH.write_text(json.dumps({"tle": tle, "baixado": _now().timestamp()}), encoding="utf-8")
            return tle
        if cached.get("tle"):
            return cached["tle"]
        raise RuntimeError("sem dados da Estação Espacial")


def iss(lat: float | None = None, lon: float | None = None, clouds: dict | None = None, tle: dict | None = None,
        now: datetime | None = None, light: bool = False) -> dict:
    tle = tle or _tle()
    now = now or _now()
    out = {"agora": orbit.position(tle, now), "trilha": orbit.track(tle, now), "atualizado": now.isoformat(),
           "fonte": "CelesTrak", "passagens": []}
    if lat is not None and not light:
        if clouds is None:
            try:
                clouds = {h["t"][:13]: h["nuvens"] for h in forecast(lat, lon)["horas"]}
            except Exception:  # noqa: BLE001 - sem previsão de nuvens
                clouds = {}
        tz = None
        for p in orbit.passes(tle, lat, lon, now):
            start = datetime.fromisoformat(p["inicio"])
            if tz is None:
                tz = _tz_offset(lon)
            local = start + tz
            p["hora"] = local.strftime("%H:%M")
            p["dia"] = local.strftime("%d/%m")
            p["nuvens"] = clouds.get(local.strftime("%Y-%m-%dT%H"))
            out["passagens"].append(p)
    return out


def _tz_offset(lon: float) -> timedelta:
    """Fuso do PC (a cidade do JARVIS é a de casa)."""
    off = datetime.now().astimezone().utcoffset()
    return off if off is not None else timedelta(hours=round(lon / 15))


# --------------------------------------------------------------------------- casa e resumo
def home() -> dict | None:
    """A cidade do JARVIS (a mesma do clima)."""
    from modules import tools

    city = (settings.WEATHER_CITY or "").strip()
    if not city:
        return None
    try:
        r = tools._fetch_weather(city)
    except Exception:  # noqa: BLE001
        return None
    d = (r or {}).get("data") or {}
    if d.get("latitude") is None:
        return None
    return {"lat": d["latitude"], "lon": d["longitude"], "nome": r.get("place") or city}


def layer(name: str, lat: float | None, lon: float | None, limit: int = 4000, light: bool = False) -> dict:
    if name not in LAYERS:
        raise ValueError("camada desconhecida")
    if lat is None and name in ("chuva", "voos"):
        h = home()
        if not h:
            raise ValueError("Sem a cidade: configure a cidade do clima.")
        lat, lon = h["lat"], h["lon"]
    if name == "terremotos":
        return quakes(lat, lon)
    if name == "voos":
        return flights(lat, lon)
    if name == "queimadas":
        return fires(lat, lon, limit=max(200, min(limit, 6000)))
    if name == "chuva":
        return rain(lat, lon)
    return iss(lat, lon, light=light)


def summary(lat: float, lon: float) -> dict:
    """A faixa "o que está acontecendo" do topo do globo."""
    from concurrent.futures import ThreadPoolExecutor

    jobs = {"chuva": lambda: rain(lat, lon)["resumo"],
            "voos": lambda: {k: v for k, v in flights(lat, lon).items() if k != "itens"},
            "terremotos": lambda: {k: v for k, v in quakes(lat, lon).items() if k != "itens"},
            "queimadas": lambda: {k: v for k, v in fires(lat, lon, limit=1).items() if k != "itens"},
            "iss": lambda: {"passagens": iss(lat, lon)["passagens"][:3]}}
    out: dict = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {name: pool.submit(fn) for name, fn in jobs.items()}
        for name, fut in futures.items():
            try:
                out[name] = fut.result()
            except Exception as exc:  # noqa: BLE001 - uma fonte fora do ar não derruba o resumo
                log.info("Resumo do Olho de Deus sem %s: %s", name, exc)
                out[name] = None
    parts = summary_parts(out)
    out["texto"] = " · ".join(parts)
    return out


def summary_parts(s: dict) -> list[str]:
    parts = []
    if s.get("chuva"):
        parts.append(s["chuva"]["texto"])
    if s.get("voos"):
        parts.append(f"{s['voos']['no_ar']} voos por perto")
    if s.get("terremotos"):
        n = s["terremotos"]["fortes"]
        parts.append(f"{n} terremoto{'s' if n != 1 else ''} forte{'s' if n != 1 else ''} hoje" if n else "nenhum terremoto forte hoje")
    if s.get("queimadas") is not None and s["queimadas"].get("perto") is not None:
        n = s["queimadas"]["perto"]
        parts.append(f"{n} foco{'s' if n != 1 else ''} de queimada a menos de {NEAR_KM} km" if n else "sem queimadas por perto")
    pas = (s.get("iss") or {}).get("passagens") or []
    if pas:
        parts.append(f"ISS passa visível {'hoje' if pas[0]['dia'] == datetime.now().strftime('%d/%m') else 'em ' + pas[0]['dia']} às {pas[0]['hora']}")
    return parts


# --------------------------------------------------------------------------- avisos
def prefs() -> dict:
    try:
        data = json.loads(_PREFS_PATH.read_text(encoding="utf-8")) if _PREFS_PATH.exists() else {}
    except (OSError, ValueError):
        data = {}
    data.setdefault("ligados", {})
    for k in ALERT_KINDS:
        data["ligados"].setdefault(k, True)
    data.setdefault("enviados", {})
    return data


def set_prefs(changes: dict) -> dict:
    with _lock:
        data = prefs()
        for k in ALERT_KINDS:
            if k in changes:
                data["ligados"][k] = bool(changes[k])
        _save_prefs(data)
        return data["ligados"]


def _save_prefs(data: dict) -> None:
    cut = _now().timestamp() - 7 * 86400
    data["enviados"] = {k: v for k, v in data["enviados"].items() if v > cut}
    _PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _PREFS_PATH.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def alerts(now: datetime | None = None, where: dict | None = None, sources: dict | None = None) -> list[str]:
    """Os avisos que devem sair agora (cada um uma vez). `sources` permite testar sem internet."""
    now = now or _now()
    with _lock:
        data = prefs()
        on = data["ligados"]
        sent = data["enviados"]
        where = where or home()
        if not where:
            return []
        lat, lon, city = where["lat"], where["lon"], where.get("nome") or "sua cidade"
        src = sources or {}
        out: list[str] = []
        ts = now.timestamp()

        def once(key: str, text: str, gap_h: float = 0) -> None:
            prev = sent.get(key)
            if prev and (not gap_h or ts - prev < gap_h * 3600):
                return
            sent[key] = ts
            out.append(text)

        if on["chuva"]:
            try:
                r = src["chuva"] if "chuva" in src else rain(lat, lon)["resumo"]
                if r.get("forte") and r.get("minutos") is not None and r["minutos"] <= 45:
                    quando = "agora" if r["minutos"] <= 5 else f"em uns {max(5, round(r['minutos'] / 5) * 5)} minutos"
                    once("chuva", f"Senhor, chuva forte chegando em {city} {quando}.", gap_h=3)
            except Exception as exc:  # noqa: BLE001
                log.info("Aviso de chuva sem dados: %s", exc)
        if on["perto"]:
            try:
                f = src["queimadas"] if "queimadas" in src else fires(lat, lon, limit=1)
                if f.get("perto"):
                    once(f"fogo:{now.astimezone():%Y-%m-%d}", f"Atenção: {f['perto']} focos de queimada a menos de {NEAR_KM} km de {city}.")
            except Exception as exc:  # noqa: BLE001
                log.info("Aviso de queimada sem dados: %s", exc)
            try:
                qs = src["terremotos"] if "terremotos" in src else quakes(lat, lon)["itens"]
                s, n, w, e = SOUTH_AMERICA
                for q in qs:
                    if q["mag"] >= 5 and s <= q["lat"] <= n and w <= q["lon"] <= e:
                        once(f"sismo:{q['id']}", f"Terremoto de força {str(q['mag']).replace('.', ',')} registrado: {q['lugar']}.")
            except Exception as exc:  # noqa: BLE001
                log.info("Aviso de terremoto sem dados: %s", exc)
        if on["iss"]:
            try:
                ps = src["iss"] if "iss" in src else iss(lat, lon, now=now)["passagens"]
                for p in ps:
                    mins = (datetime.fromisoformat(p["inicio"]) - now).total_seconds() / 60
                    clear = p.get("nuvens") is None or p["nuvens"] < 50
                    if 0 <= mins <= 12 and clear:
                        once(f"iss:{p['inicio'][:16]}", f"Senhor, a Estação Espacial passa visível em {max(1, round(mins))} minutos, "
                                                         f"às {p['hora']}, do {p['de']} para o {p['para']}. Olhe para o céu!")
            except Exception as exc:  # noqa: BLE001
                log.info("Aviso da ISS sem dados: %s", exc)
        if out:
            _save_prefs(data)
        return out


async def alerts_loop(interval: float = 300) -> None:
    """A cada 5 min, das 6h às 23h: chuva forte chegando, queimada/terremoto perto e ISS visível."""
    import asyncio

    from core import speech

    await asyncio.sleep(60)
    while True:
        try:
            if 6 <= datetime.now().hour < 23:
                for text in await asyncio.to_thread(alerts):
                    await speech.announce(text)
        except Exception:  # noqa: BLE001 - um aviso ruim não para os próximos
            log.exception("Avisos do Olho de Deus falharam")
        await asyncio.sleep(interval)

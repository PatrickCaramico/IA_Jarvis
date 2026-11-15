"""V7.11: órbita da Estação Espacial (ISS) a partir do TLE público (CelesTrak), sem bibliotecas extras.

Propagação kepleriana com as correções seculares do achatamento da Terra (J2) e o arrasto do próprio TLE.
Para a ISS isso fica a poucas dezenas de km da posição real em 1 a 3 dias: bom para o globo e para
"quando ela passa visível na minha cidade" (erro de segundos a 1 minuto). O mesmo cálculo existe em
JavaScript na nuvem (netlify/nuvem/world.mjs), para funcionar igual fora de casa.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

MU = 398600.4418  # km³/s²
RE = 6378.137  # km
J2 = 1.08262668e-3
DEG = math.pi / 180
COMPASS = ("N", "NE", "L", "SE", "S", "SO", "O", "NO")


def parse_tle(text: str) -> dict | None:
    lines = [ln.rstrip() for ln in str(text or "").splitlines() if ln.strip()]
    l1 = next((ln for ln in lines if ln.startswith("1 ")), None)
    l2 = next((ln for ln in lines if ln.startswith("2 ")), None)
    if not l1 or not l2 or len(l1) < 64 or len(l2) < 63:
        return None
    try:
        yy, doy = int(l1[18:20]), float(l1[20:32])
        year = 2000 + yy if yy < 57 else 1900 + yy
        epoch = datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=doy - 1)
        ndot = float(l1[33:43])  # rev/dia² (já é n'/2)
        return {
            "name": next((ln.strip() for ln in lines if not ln.startswith(("1 ", "2 "))), "ISS"),
            "epoch": epoch.isoformat(),
            "inc": float(l2[8:16]), "raan": float(l2[17:25]), "ecc": float("0." + l2[26:33].strip()),
            "argp": float(l2[34:42]), "ma": float(l2[43:51]), "mm": float(l2[52:63]), "ndot": ndot,
            "line1": l1, "line2": l2,
        }
    except ValueError:
        return None


def _jd(t: datetime) -> float:
    return t.timestamp() / 86400.0 + 2440587.5


def gmst(t: datetime) -> float:
    d = _jd(t) - 2451545.0
    return ((280.46061837 + 360.98564736629 * d) % 360) * DEG


def _brouwer(n0: float, e: float, inc: float) -> tuple[float, float]:
    """O movimento médio do TLE é o de Kozai (o do SGP4): recupera o de Brouwer (menos erro ao longo da órbita)."""
    a1 = (MU / n0 ** 2) ** (1 / 3) / RE
    d1 = 0.75 * J2 * (3 * math.cos(inc) ** 2 - 1) / (1 - e * e) ** 1.5 / a1 ** 2
    a0 = a1 * (1 - d1 / 3 - d1 ** 2 - 134 / 81 * d1 ** 3)
    n = n0 / (1 + d1 * (a1 / a0) ** 2)
    return n, (MU / n ** 2) ** (1 / 3)


def eci(tle: dict, t: datetime) -> tuple[float, float, float]:
    """Posição (km) no referencial inercial no instante t."""
    epoch = datetime.fromisoformat(tle["epoch"])
    dt_days = (t - epoch).total_seconds() / 86400.0
    e, inc = tle["ecc"], tle["inc"] * DEG
    n, a = _brouwer(tle["mm"] * 2 * math.pi / 86400.0, e, inc)
    p = a * (1 - e * e)
    k = 1.5 * J2 * (RE / p) ** 2 * n * 86400.0  # rad/dia
    cos_i, sin_i = math.cos(inc), math.sin(inc)
    raan = tle["raan"] * DEG - k * cos_i * dt_days
    argp = tle["argp"] * DEG + k * (2 - 2.5 * sin_i ** 2) * dt_days
    m = (tle["ma"] * DEG + (n * 86400.0 + 0.5 * k * math.sqrt(1 - e * e) * (3 * cos_i ** 2 - 1)) * dt_days
         + 2 * math.pi * tle["ndot"] * dt_days ** 2)
    m %= 2 * math.pi
    ea = m
    for _ in range(8):
        ea -= (ea - e * math.sin(ea) - m) / (1 - e * math.cos(ea))
    nu = 2 * math.atan2(math.sqrt(1 + e) * math.sin(ea / 2), math.sqrt(1 - e) * math.cos(ea / 2))
    r = a * (1 - e * math.cos(ea))
    u = argp + nu
    cu, su, co, so = math.cos(u), math.sin(u), math.cos(raan), math.sin(raan)
    return (r * (co * cu - so * su * cos_i), r * (so * cu + co * su * cos_i), r * su * sin_i)


def geodetic(x: float, y: float, z: float, t: datetime) -> dict:
    g = gmst(t)
    lon = (math.atan2(y, x) - g + math.pi) % (2 * math.pi) - math.pi
    r = math.sqrt(x * x + y * y + z * z)
    lat = math.asin(z / r)
    return {"lat": round(lat / DEG, 4), "lon": round(lon / DEG, 4), "alt_km": round(r - RE, 1)}


def position(tle: dict, t: datetime) -> dict:
    x, y, z = eci(tle, t)
    out = geodetic(x, y, z, t)
    n = tle["mm"] * 2 * math.pi / 86400.0
    a = (MU / n ** 2) ** (1 / 3)
    out["vel_kmh"] = round(math.sqrt(MU * (2 / math.sqrt(x * x + y * y + z * z) - 1 / a)) * 3600)
    return out


def track(tle: dict, t: datetime, minutes: int = 46, step: int = 2) -> list[list[float]]:
    pts = []
    for k in range(-minutes, minutes + 1, step):
        p = position(tle, t + timedelta(minutes=k))
        pts.append([p["lon"], p["lat"]])
    return pts


def _observer(lat: float, lon: float, t: datetime) -> tuple[float, float, float]:
    th = gmst(t) + lon * DEG
    la = lat * DEG
    return (RE * math.cos(la) * math.cos(th), RE * math.cos(la) * math.sin(th), RE * math.sin(la))


def _look(target, lat: float, lon: float, t: datetime) -> tuple[float, float]:
    """Elevação e azimute (graus) de um ponto ECI visto do observador."""
    ox, oy, oz = _observer(lat, lon, t)
    dx, dy, dz = target[0] - ox, target[1] - oy, target[2] - oz
    th, la = gmst(t) + lon * DEG, lat * DEG
    s = math.sin(la) * math.cos(th) * dx + math.sin(la) * math.sin(th) * dy - math.cos(la) * dz
    e = -math.sin(th) * dx + math.cos(th) * dy
    zt = math.cos(la) * math.cos(th) * dx + math.cos(la) * math.sin(th) * dy + math.sin(la) * dz
    rng = math.sqrt(s * s + e * e + zt * zt)
    el = math.asin(zt / rng) / DEG
    az = (math.atan2(e, -s) / DEG) % 360
    return el, az


def sun_eci(t: datetime) -> tuple[float, float, float]:
    """Direção do Sol (vetor unitário) — fórmula de baixa precisão do Almanaque."""
    d = _jd(t) - 2451545.0
    g = (357.529 + 0.98560028 * d) * DEG
    q = 280.459 + 0.98564736 * d
    lam = (q + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g)) * DEG
    eps = (23.439 - 0.00000036 * d) * DEG
    return (math.cos(lam), math.cos(eps) * math.sin(lam), math.sin(eps) * math.sin(lam))


def sunlit(r, s) -> bool:
    dot = r[0] * s[0] + r[1] * s[1] + r[2] * s[2]
    if dot > 0:
        return True
    perp = math.sqrt(max(0.0, r[0] ** 2 + r[1] ** 2 + r[2] ** 2 - dot * dot))
    return perp > RE


def sun_elevation(lat: float, lon: float, t: datetime) -> float:
    s = sun_eci(t)
    au = 149597870.7
    return _look((s[0] * au, s[1] * au, s[2] * au), lat, lon, t)[0]


def compass(az: float) -> str:
    return COMPASS[int(((az % 360) + 22.5) // 45) % 8]


def passes(tle: dict, lat: float, lon: float, start: datetime, hours: int = 72, step: int = 20,
           min_el: float = 10.0, limit: int = 6) -> list[dict]:
    """Passagens VISÍVEIS: ISS acima de 10°, iluminada pelo Sol e o céu do observador escuro (Sol < -6°)."""
    out: list[dict] = []
    cur = None
    t = start
    end = start + timedelta(hours=hours)
    while t <= end and len(out) < limit:
        r = eci(tle, t)
        el, az = _look(r, lat, lon, t)
        ok = el >= min_el and sunlit(r, sun_eci(t)) and sun_elevation(lat, lon, t) < -6
        if ok:
            if cur is None:
                cur = {"inicio": t, "az_ini": az, "max_el": el, "fim": t, "az_fim": az}
            cur["fim"], cur["az_fim"] = t, az
            cur["max_el"] = max(cur["max_el"], el)
        elif cur is not None:
            out.append(_pass(cur))
            cur = None
        # longe do horizonte: pula mais rápido
        t += timedelta(seconds=step if el > -25 else step * 6)
    if cur is not None and len(out) < limit:
        out.append(_pass(cur))
    return out


def _pass(c: dict) -> dict:
    dur = max(1, round((c["fim"] - c["inicio"]).total_seconds() / 60))
    return {"inicio": c["inicio"].isoformat(), "fim": c["fim"].isoformat(), "minutos": dur,
            "max_el": round(c["max_el"]), "de": compass(c["az_ini"]), "para": compass(c["az_fim"])}

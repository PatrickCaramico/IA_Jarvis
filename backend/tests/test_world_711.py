"""V7.11: Olho de Deus com dados reais (fontes públicas), órbita da ISS e avisos."""
from datetime import datetime, timedelta, timezone

from modules import orbit, world_data

TLE = ("ISS (ZARYA)\n"
       "1 25544U 98067A   08264.51782528 -.00002182  00000-0 -11606-4 0  2927\n"
       "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537\n")


def test_parse_tle_and_position_close_to_sgp4():
    t = orbit.parse_tle(TLE)
    assert t and t["inc"] == 51.6416 and abs(t["mm"] - 15.72125391) < 1e-6
    ep = datetime.fromisoformat(t["epoch"])
    # valores do SGP4 oficial (biblioteca sgp4) para este TLE: a propagação fica a ~10 km em 3 dias
    p1 = orbit.position(t, ep + timedelta(hours=1))
    assert abs(p1["lat"] - -21.96) < 0.3 and abs(p1["lon"] - 27.42) < 0.3
    assert 340 < p1["alt_km"] < 370 and 27000 < p1["vel_kmh"] < 28500
    assert orbit.parse_tle("lixo") is None


def test_iss_visible_passes():
    t = orbit.parse_tle(TLE)
    ep = datetime.fromisoformat(t["epoch"])
    ps = orbit.passes(t, -23.55, -46.63, ep, hours=72)
    assert ps and ps[0]["inicio"].startswith("2008-09-22T07:3")
    assert all(p["max_el"] >= 10 and p["de"] in orbit.COMPASS for p in ps)
    out = world_data.iss(-23.55, -46.63, clouds={}, tle=t, now=ep)
    assert out["agora"]["lat"] and len(out["trilha"]) > 40 and out["passagens"][0]["hora"]
    light = world_data.iss(-23.55, -46.63, tle=t, now=ep, light=True)
    assert light["passagens"] == []


def test_quakes_flights_fires_parsers():
    usgs = {"features": [
        {"id": "a", "properties": {"mag": 5.4, "place": "Chile", "time": 1763200000000, "url": "u"}, "geometry": {"coordinates": [-70.1, -30.2, 33]}},
        {"id": "b", "properties": {"mag": None}, "geometry": {"coordinates": [0, 0]}},
        {"id": "c", "properties": {"mag": 2.1, "place": "Alaska", "time": 1763200000000}, "geometry": {"coordinates": [-150, 61, 10]}},
    ]}
    q = world_data.parse_quakes(usgs, -23.55, -46.63)
    assert [x["id"] for x in q] == ["a", "c"] and q[0]["prof_km"] == 33 and q[0]["dist_km"] > 2000
    ac = {"ac": [
        {"hex": "e48a1b", "flight": "GLO1234 ", "t": "B738", "r": "PR-GXA", "lat": -23.6, "lon": -46.7, "alt_baro": 10000, "gs": 300, "track": 90},
        {"hex": "e48a1c", "lat": -23.43, "lon": -46.47, "alt_baro": "ground", "gs": 10},
        {"hex": "zz"},
    ]}
    f = world_data.parse_flights(ac, -23.55, -46.63)
    assert len(f) == 2 and f[0]["voo"] == "GLO1234" and f[0]["alt_m"] == 3048 and f[0]["vel_kmh"] == 556
    assert f[1]["solo"] is True
    now = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)
    csv = ("id,lat,lon,data_hora_gmt,satelite,municipio,estado,pais,bioma,frp\n"
           "1,-23.70,-46.80,2026-11-15 10:00:00,AQUA,SAO PAULO,SAO PAULO,Brasil,Mata Atlantica,12.5\n"
           "2,-10.0,-55.0,2026-11-15 09:00:00,AQUA,SINOP,MATO GROSSO,Brasil,Amazonia,30\n"
           "3,-10.0,-55.0,2026-11-13 09:00:00,AQUA,VELHO,MATO GROSSO,Brasil,Amazonia,30\n"
           "x,,,,\n")
    fs = world_data.parse_fires(csv, now)
    assert len(fs) == 2 and fs[0]["municipio"] == "Sao Paulo"


def test_rain_summary_text():
    fc = world_data.parse_forecast({"timezone": "America/Sao_Paulo",
                                    "minutely_15": {"time": ["2026-11-15T14:00", "2026-11-15T14:15", "2026-11-15T14:30"], "precipitation": [0, 0.3, 2.0]},
                                    "hourly": {"time": ["2026-11-15T14:00"], "precipitation": [2.3], "precipitation_probability": [80], "cloud_cover": [90]}})
    r = world_data.rain_text(fc, "2026-11-15T14:00")
    assert r["forte"] is True and r["minutos"] == 30 and r["hora"] == "14:30"
    dry = world_data.rain_text(world_data.parse_forecast({"minutely_15": {"time": ["2026-11-15T14:00"], "precipitation": [0]}}), "2026-11-15T14:00")
    assert dry["texto"] == "Sem chuva nas próximas 3 h" and dry["forte"] is False
    radar = world_data.parse_radar({"host": "https://h", "radar": {"past": [{"time": 1, "path": "/v2/radar/1"}, {"path": "x"}]}})
    assert radar == {"host": "https://h", "quadros": [{"time": 1, "path": "/v2/radar/1"}]}


def test_summary_parts():
    today = datetime.now().strftime("%d/%m")
    parts = world_data.summary_parts({"chuva": {"texto": "Sem chuva nas próximas 3 h"}, "voos": {"no_ar": 42},
                                      "terremotos": {"fortes": 3}, "queimadas": {"perto": 0},
                                      "iss": {"passagens": [{"dia": today, "hora": "19:42"}]}})
    assert parts == ["Sem chuva nas próximas 3 h", "42 voos por perto", "3 terremotos fortes hoje",
                     "sem queimadas por perto", "ISS passa visível hoje às 19:42"]


def test_alerts_once_and_switchable(monkeypatch):
    where = {"lat": -23.55, "lon": -46.63, "nome": "São Paulo"}
    now = datetime(2026, 11, 15, 20, tzinfo=timezone.utc)
    # V8.11: o relógio do teste fica parado. _save_prefs descarta avisos com mais de 7 dias pelo relógio REAL;
    # a partir de 22/11/2026 20:00 os avisos "de hoje" do teste viravam antigos e o teste quebrava sozinho.
    monkeypatch.setattr(world_data, "_now", lambda: now + timedelta(hours=3))
    src = {"chuva": {"forte": True, "minutos": 30},
           "queimadas": {"perto": 3},
           "terremotos": [{"id": "q1", "mag": 5.6, "lat": -30, "lon": -71, "lugar": "Chile"},
                          {"id": "q2", "mag": 6.0, "lat": 35, "lon": 139, "lugar": "Japão"}],
           "iss": [{"inicio": (now + timedelta(minutes=10)).isoformat(), "hora": "17:10", "de": "NO", "para": "SE", "nuvens": 10}]}
    out = world_data.alerts(now, where, src)
    assert len(out) == 4
    assert "chuva forte" in out[0] and "em uns 30 minutos" in out[0]
    assert any("Chile" in t for t in out) and not any("Japão" in t for t in out)
    assert any("Estação Espacial" in t for t in out)
    assert world_data.alerts(now + timedelta(minutes=5), where, src) == []  # cada aviso sai uma vez
    world_data.set_prefs({"chuva": False, "iss": False})
    assert world_data.prefs()["ligados"] == {"chuva": False, "perto": True, "iss": False}
    later = now + timedelta(hours=2)
    assert world_data.alerts(later, where, {**src, "iss": []}) == []  # chuva desligada; fogo já avisado hoje


def test_world_routes(monkeypatch):
    from fastapi.testclient import TestClient

    import main

    client = TestClient(main.app)
    monkeypatch.setattr(world_data, "quakes", lambda lat=None, lon=None: {"itens": [], "total": 0, "fortes": 0})
    r = client.get("/api/world/terremotos")
    assert r.status_code == 200 and r.json()["total"] == 0
    assert client.get("/api/world/naves").status_code == 404
    assert client.get("/api/world/terremotos?lat=200&lon=0").status_code == 400

    def boom(*a, **k):
        raise RuntimeError("fora do ar")

    monkeypatch.setattr(world_data, "flights", boom)
    r = client.get("/api/world/voos?lat=-23.5&lon=-46.6")
    assert r.status_code == 502 and "não respondeu" in r.json()["detail"]
    r = client.post("/api/world/alerts", json={"perto": False})
    assert r.json()["ligados"]["perto"] is False
    assert client.get("/api/world/alerts").json()["ligados"]["perto"] is False


def test_launches_parser_v22_and_v23():
    v22 = {"results": [{"id": "a1", "name": "Falcon 9 | Bandwagon 6", "net": "2026-11-04T08:04:00Z", "status": {"abbrev": "Success"},
                        "rocket": {"configuration": {"full_name": "Falcon 9 Block 5"}}, "launch_service_provider": {"name": "SpaceX"},
                        "mission": {"name": "Bandwagon 6", "description": "Rideshare", "orbit": {"name": "Low Earth Orbit"}},
                        "pad": {"name": "SLC-40", "latitude": "28.56", "longitude": "-80.57", "location": {"name": "Cape Canaveral", "country_code": "USA"}},
                        "image": "https://img/x.jpg", "vidURLs": [{"url": "https://youtube.com/w"}], "infoURLs": [], "probability": 95},
                       {"id": "sem-base", "pad": {}}]}
    v23 = {"results": [{"id": "b2", "name": "Long March 5", "net": "2026-11-20T10:00:00Z", "status": {"abbrev": "Go"},
                        "pad": {"latitude": 19.6, "longitude": 110.9, "country": {"name": "China"}}, "image": {"image_url": "https://img/y.jpg"}}]}
    a = world_data.parse_launches(v22, "recente")
    b = world_data.parse_launches(v23, "proximo")
    assert len(a) == 1 and a[0]["situacao"] == "sucesso" and a[0]["video"] == "https://youtube.com/w" and a[0]["lat"] == 28.56
    assert b[0]["situacao"] == "confirmado" and b[0]["foto"] == "https://img/y.jpg" and b[0]["pais"] == "China"

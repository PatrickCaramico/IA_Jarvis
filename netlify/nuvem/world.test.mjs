import { test } from "node:test";
import assert from "node:assert/strict";
import { clearCache, parseFires, parseFlights, parseQuakes, parseTle, passes, position, rainText, parseForecast, worldLayer, worldSummary } from "./world.mjs";

const TLE = "ISS (ZARYA)\n1 25544U 98067A   08264.51782528 -.00002182  00000-0 -11606-4 0  2927\n2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537\n";

function memStore() {
  const m = new Map();
  return { get: async (k) => m.get(k), set: async (k, v) => m.set(k, v) };
}

test("V7.11 nuvem: a órbita da ISS dá o mesmo resultado do PC", () => {
  const t = parseTle(TLE);
  const ep = Date.parse(t.epoch);
  // mesmos números de backend/modules/orbit.py (test_world_711)
  assert.deepEqual(position(t, ep + 3600e3).lat, -21.9611);
  assert.deepEqual(position(t, ep + 3600e3).lon, 27.4162);
  const p = passes(t, -23.55, -46.63, ep);
  assert.equal(p[0].inicio.slice(0, 16), "2008-09-22T07:35");
  assert.equal(p[1].max_el, 52);
});

test("V7.11 nuvem: leitores das fontes", () => {
  const q = parseQuakes({ features: [{ id: "a", properties: { mag: 5.4, place: "Chile", time: 1 }, geometry: { coordinates: [-70.1, -30.2, 33] } }, { id: "b", properties: { mag: null }, geometry: { coordinates: [0, 0] } }] }, -23.55, -46.63);
  assert.equal(q.length, 1);
  assert.equal(q[0].prof_km, 33);
  const f = parseFlights({ ac: [{ hex: "e48a1b", flight: "GLO1234 ", lat: -23.6, lon: -46.7, alt_baro: 10000, gs: 300, track: 90 }, { hex: "x", lat: -23.4, lon: -46.4, alt_baro: "ground" }] }, -23.55, -46.63);
  assert.equal(f[0].alt_m, 3048);
  assert.equal(f[0].vel_kmh, 556);
  assert.equal(f[1].solo, true);
  const now = Date.parse("2026-11-15T12:00:00Z");
  const fires = parseFires("id,lat,lon,data_hora_gmt,municipio,estado,bioma,frp\n1,-23.7,-46.8,2026-11-15 10:00:00,SAO PAULO,SAO PAULO,Mata,12\n2,-10,-55,2026-11-13 09:00:00,VELHO,MT,Amazonia,1\n", now);
  assert.equal(fires.length, 1);
  assert.equal(fires[0].municipio, "Sao Paulo");
  const fc = parseForecast({ minutely_15: { time: ["2026-11-15T14:00", "2026-11-15T14:30"], precipitation: [0, 2] } });
  assert.deepEqual(rainText(fc, "2026-11-15T14:00"), { texto: "Chuva forte por volta das 14:30", forte: true, minutos: 30, hora: "14:30" });
});

test("V7.11 nuvem: camadas, reserva de voos e resumo", async () => {
  clearCache();
  const store = memStore();
  const calls = [];
  const fetchFn = async (url) => {
    calls.push(url);
    const ok = (body, text = false) => ({ ok: true, status: 200, json: async () => body, text: async () => (text ? body : JSON.stringify(body)) });
    if (url.includes("adsb.lol")) return { ok: false, status: 503 };
    if (url.includes("airplanes.live")) return ok({ ac: [{ hex: "a", lat: -23.6, lon: -46.7, alt_baro: 9000 }] });
    if (url.includes("usgs")) return ok({ features: [] });
    if (url.includes("celestrak")) return ok(TLE, true);
    if (url.includes("inpe")) return ok("lat,lon,data_hora_gmt\n-23.6,-46.7,2008-09-22 06:00:00\n", true);
    if (url.includes("rainviewer")) return ok({ host: "https://h", radar: { past: [{ time: 1, path: "/p" }] } });
    if (url.includes("open-meteo")) return ok({ minutely_15: { time: [], precipitation: [] }, hourly: { time: [] } });
    return { ok: false, status: 404 };
  };
  const nowMs = Date.parse("2008-09-22T07:00:00Z");
  const v = await worldLayer("voos", { lat: -23.55, lon: -46.63, store, fetchFn, nowMs });
  assert.equal(v.no_ar, 1);
  assert.ok(calls.some((u) => u.includes("airplanes.live")));
  const iss = await worldLayer("iss", { lat: -23.55, lon: -46.63, store, fetchFn, nowMs });
  assert.ok(iss.passagens.length >= 1);
  assert.ok((await store.get("olho_tle")).tle); // o TLE fica guardado (CelesTrak pede poucas consultas)
  const light = await worldLayer("iss", { lat: -23.55, lon: -46.63, light: true, store, fetchFn, nowMs });
  assert.deepEqual(light.passagens, []);
  await assert.rejects(worldLayer("naves", { store, fetchFn, nowMs }), /Camada desconhecida/);
  const s = await worldSummary({ lat: -23.55, lon: -46.63, store, fetchFn, nowMs });
  assert.match(s.texto, /1 voos por perto · nenhum terremoto forte hoje · 1 foco de queimada a menos de 50 km/);
});

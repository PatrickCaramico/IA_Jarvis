// JARVIS · modo nuvem (V7.11): OLHO DE DEUS fora de casa. Mesmas camadas e mesmo formato do PC
// (backend/modules/world_data.py e backend/modules/orbit.py), todas de fontes públicas, sem chave.
// Os avisos automáticos saem do PC; aqui é só o que a tela mostra.

const USGS = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson";
const RAINVIEWER = "https://api.rainviewer.com/public/weather-maps.json";
const OPEN_METEO = "https://api.open-meteo.com/v1/forecast";
const FLIGHTS = ["https://api.adsb.lol/v2/point", "https://api.airplanes.live/v2/point"];
const INPE = "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil/focos_diario_br_";
const CELESTRAK = "https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=TLE";
export const LAYERS = ["chuva", "voos", "terremotos", "queimadas", "iss", "lancamentos"];
const LAUNCHES = ["https://ll.thespacedevs.com/2.2.0/launch/", "https://ll.thespacedevs.com/2.3.0/launches/"];
const LAUNCH_STATUS = { go: "confirmado", tbd: "a confirmar", tbc: "a confirmar", success: "sucesso", failure: "falhou", "partial failure": "falha parcial", "in flight": "em voo", hold: "em espera" };
const FLIGHT_RADIUS_KM = 150;
const NEAR_KM = 50;
const STRONG_RAIN_MM15 = 1.25;
const TZ = "America/Sao_Paulo";

const memo = new Map();
async function cached(key, ttlMs, fn, nowMs) {
  const hit = memo.get(key);
  if (hit && hit.exp > nowMs) return hit.value;
  const value = await fn();
  if (memo.size > 64) memo.clear();
  memo.set(key, { exp: nowMs + ttlMs, value });
  return value;
}

export function clearCache() {
  memo.clear();
}

async function getJson(fetchFn, url, timeoutMs = 10_000) {
  const res = await fetchFn(url, { signal: AbortSignal.timeout(timeoutMs), headers: { "User-Agent": "JarvisAssistant" } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function getText(fetchFn, url, timeoutMs = 15_000) {
  const res = await fetchFn(url, { signal: AbortSignal.timeout(timeoutMs), headers: { "User-Agent": "JarvisAssistant" } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.text();
}

export function km(lat1, lon1, lat2, lon2) {
  const r = Math.PI / 180;
  const dp = (lat2 - lat1) * r;
  const dl = (lon2 - lon1) * r;
  const h = Math.sin(dp / 2) ** 2 + Math.cos(lat1 * r) * Math.cos(lat2 * r) * Math.sin(dl / 2) ** 2;
  return 6371 * 2 * Math.asin(Math.min(1, Math.sqrt(h)));
}

const num = (v) => {
  const x = typeof v === "number" ? v : v == null || v === "" ? NaN : Number(v);
  return Number.isFinite(x) ? x : null;
};
const round = (v, d = 0) => Math.round(v * 10 ** d) / 10 ** d;

// --------------------------------------------------------------------------- terremotos
export function parseQuakes(data, lat = null, lon = null) {
  const out = [];
  for (const f of data?.features || []) {
    const p = f.properties || {};
    const g = f.geometry?.coordinates || [];
    const mag = num(p.mag);
    if (g.length < 2 || num(g[0]) == null || num(g[1]) == null || mag == null) continue;
    const q = {
      id: String(f.id || p.code || ""), lat: round(g[1], 3), lon: round(g[0], 3),
      prof_km: g.length > 2 ? Math.round(num(g[2]) || 0) : null, mag: round(mag, 1),
      lugar: String(p.place || "").slice(0, 120), quando: new Date(num(p.time) || 0).toISOString(), url: String(p.url || ""),
    };
    if (lat != null) q.dist_km = Math.round(km(lat, lon, q.lat, q.lon));
    out.push(q);
  }
  return out.sort((a, b) => b.mag - a.mag).slice(0, 500);
}

async function quakes(fetchFn, lat, lon, nowMs) {
  const items = parseQuakes(await cached("usgs", 300_000, () => getJson(fetchFn, USGS, 12_000), nowMs), lat, lon);
  return { itens: items, total: items.length, fortes: items.filter((q) => q.mag >= 5).length, maior: items[0] || null, atualizado: new Date(nowMs).toISOString(), fonte: "USGS" };
}

// --------------------------------------------------------------------------- voos
export function parseFlights(data, lat, lon) {
  const out = [];
  for (const a of data?.ac || data?.aircraft || []) {
    const la = num(a.lat);
    const lo = num(a.lon);
    if (la == null || lo == null) continue;
    const alt = a.alt_baro ?? a.alt_geom;
    const ground = alt === "ground";
    const altFt = ground ? 0 : num(alt);
    const gs = num(a.gs);
    out.push({
      id: String(a.hex || "").slice(0, 8), voo: String(a.flight || "").trim().slice(0, 10),
      matricula: String(a.r || "").slice(0, 10), modelo: String(a.t || "").slice(0, 10),
      lat: round(la, 4), lon: round(lo, 4), alt_m: altFt != null ? Math.round(altFt * 0.3048) : null, solo: ground,
      vel_kmh: gs != null ? Math.round(gs * 1.852) : null, rumo: Math.round(num(a.track) || 0), dist_km: round(km(lat, lon, la, lo), 1),
    });
  }
  return out.sort((a, b) => a.dist_km - b.dist_km).slice(0, 300);
}

async function flights(fetchFn, lat, lon, nowMs) {
  const nm = Math.round(FLIGHT_RADIUS_KM / 1.852);
  let last = null;
  for (const base of FLIGHTS) {
    try {
      const data = await cached(`${base}${lat.toFixed(2)}${lon.toFixed(2)}`, 12_000, () => getJson(fetchFn, `${base}/${lat.toFixed(4)}/${lon.toFixed(4)}/${nm}`), nowMs);
      const items = parseFlights(data, lat, lon);
      return { itens: items, total: items.length, no_ar: items.filter((f) => !f.solo).length, raio_km: FLIGHT_RADIUS_KM, atualizado: new Date(nowMs).toISOString(), fonte: "ADS-B público" };
    } catch (err) {
      last = err;
    }
  }
  throw last || new Error("sem voos");
}

// --------------------------------------------------------------------------- queimadas
export function parseFires(text, nowMs) {
  const lines = String(text || "").split(/\r?\n/).filter((l) => l.trim());
  if (!lines.length) return [];
  const head = lines[0].split(",").map((h) => h.trim().toLowerCase());
  const col = (...names) => names.map((n) => head.indexOf(n)).find((i) => i >= 0) ?? -1;
  const iLat = col("lat", "latitude");
  const iLon = col("lon", "longitude");
  const iT = col("data_hora_gmt", "datahora");
  const iM = col("municipio");
  const iE = col("estado");
  const iB = col("bioma");
  const iF = col("frp");
  const out = [];
  for (const line of lines.slice(1)) {
    const c = line.split(",");
    const la = num(c[iLat]);
    const lo = num(c[iLon]);
    if (la == null || lo == null) continue;
    const raw = iT >= 0 ? String(c[iT] || "").trim() : "";
    const t = raw ? Date.parse(`${raw.replace(/\//g, "-").replace(" ", "T").slice(0, 19)}Z`) : NaN;
    if (Number.isFinite(t) && nowMs - t > 24 * 3600_000) continue;
    const title = (s) => String(s || "").trim().toLowerCase().replace(/(^|\s)\S/g, (m) => m.toUpperCase());
    out.push({
      lat: round(la, 4), lon: round(lo, 4), quando: Number.isFinite(t) ? new Date(t).toISOString() : "",
      municipio: title(c[iM]).slice(0, 60), estado: title(c[iE]).slice(0, 30), bioma: String(c[iB] || "").trim().slice(0, 20), frp: num(c[iF]),
    });
  }
  return out;
}

function ymd(ms) {
  return new Date(ms - 3 * 3600_000).toISOString().slice(0, 10).replace(/-/g, "");
}

async function fires(fetchFn, lat, lon, nowMs, limit = 4000) {
  const seen = new Set();
  let items = [];
  let ok = false;
  for (const k of [0, 1]) {
    const day = ymd(nowMs - k * 86400_000);
    try {
      const text = await cached(`inpe${day}`, 900_000, () => getText(fetchFn, `${INPE}${day}.csv`, 20_000), nowMs);
      ok = true;
      for (const f of parseFires(text, nowMs)) {
        const key = `${f.lat},${f.lon},${f.quando}`;
        if (!seen.has(key)) {
          seen.add(key);
          items.push(f);
        }
      }
    } catch {
      /* o arquivo de hoje pode ainda não existir */
    }
  }
  if (!ok) throw new Error("sem queimadas");
  let near = [];
  if (lat != null) {
    for (const f of items) f.dist_km = Math.round(km(lat, lon, f.lat, f.lon));
    items.sort((a, b) => a.dist_km - b.dist_km);
    near = items.filter((f) => f.dist_km <= NEAR_KM);
  }
  const total = items.length;
  if (total > limit) {
    const head = items.slice(0, Math.floor(limit / 2));
    const rest = items.slice(head.length);
    const step = rest.length / (limit - head.length);
    items = head.concat(Array.from({ length: limit - head.length }, (_, i) => rest[Math.floor(i * step)]));
  }
  return { itens: items, total, perto: near.length, perto_km: NEAR_KM, mais_perto: near[0] || (lat != null ? items[0] || null : null), atualizado: new Date(nowMs).toISOString(), fonte: "INPE" };
}

// --------------------------------------------------------------------------- chuva
export function parseRadar(data) {
  const host = String(data?.host || "https://tilecache.rainviewer.com");
  const frames = (data?.radar?.past || []).filter((f) => f.time && f.path).map((f) => ({ time: Number(f.time), path: String(f.path) }));
  return { host, quadros: frames.slice(-13) };
}

export function parseForecast(data) {
  const m = data?.minutely_15 || {};
  const h = data?.hourly || {};
  const prox = (m.time || []).map((t, i) => ({ hora: t.slice(11, 16), t, mm: round(num(m.precipitation?.[i]) || 0, 1) }));
  const horas = (h.time || []).map((t, i) => ({
    hora: t.slice(11, 16), t, mm: round(num(h.precipitation?.[i]) || 0, 1),
    prob: num(h.precipitation_probability?.[i]), nuvens: num(h.cloud_cover?.[i]),
  }));
  return { prox, horas, tz: data?.timezone || "" };
}

function minutesUntil(t, localNow) {
  const a = Date.parse(`${t}:00Z`);
  const b = Date.parse(`${localNow.slice(0, 16)}:00Z`);
  return Number.isFinite(a) && Number.isFinite(b) ? Math.max(0, Math.round((a - b) / 60_000)) : null;
}

export function rainText(fc, localNow = "") {
  const slots = (fc.prox || []).filter((s) => !localNow || s.t >= localNow.slice(0, 16)).slice(0, 12);
  const strong = slots.find((s) => s.mm >= STRONG_RAIN_MM15);
  if (strong) return { texto: `Chuva forte por volta das ${strong.hora}`, forte: true, minutos: minutesUntil(strong.t, localNow), hora: strong.hora };
  const first = slots.find((s) => s.mm >= 0.2);
  if (first) return { texto: `Chuva fraca por volta das ${first.hora}`, forte: false, minutos: minutesUntil(first.t, localNow), hora: first.hora };
  const later = (fc.horas || []).slice(0, 12).find((x) => (!localNow || x.t >= localNow.slice(0, 13)) && (x.prob || 0) >= 60 && x.mm >= 0.5);
  if (later) return { texto: `Sem chuva nas próximas 3 h; chance de chuva às ${later.hora}`, forte: false, minutos: null, hora: later.hora };
  return { texto: "Sem chuva nas próximas 3 h", forte: false, minutos: null, hora: null };
}

function localStamp(ms, tz = TZ) {
  const p = Object.fromEntries(new Intl.DateTimeFormat("en-CA", { timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" })
    .formatToParts(new Date(ms)).map((x) => [x.type, x.value]));
  return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}`;
}

async function forecast(fetchFn, lat, lon, nowMs) {
  const q = `?latitude=${lat.toFixed(3)}&longitude=${lon.toFixed(3)}&minutely_15=precipitation&forecast_minutely_15=16`
    + "&hourly=precipitation,precipitation_probability,cloud_cover&forecast_days=4&timezone=auto";
  return parseForecast(await cached(`om${q}`, 600_000, () => getJson(fetchFn, OPEN_METEO + q), nowMs));
}

async function rain(fetchFn, lat, lon, nowMs) {
  let radar = null;
  try {
    radar = parseRadar(await cached("rv", 300_000, () => getJson(fetchFn, RAINVIEWER), nowMs));
  } catch {
    radar = null;
  }
  const fc = await forecast(fetchFn, lat, lon, nowMs);
  let tz = TZ;
  try {
    localStamp(nowMs, fc.tz || TZ);
    tz = fc.tz || TZ;
  } catch {
    tz = TZ;
  }
  return { atualizado: new Date(nowMs).toISOString(), fonte: "RainViewer + Open-Meteo", radar, previsao: { prox: fc.prox, horas: fc.horas.slice(0, 24) }, resumo: rainText(fc, localStamp(nowMs, tz)) };
}

// --------------------------------------------------------------------------- órbita da ISS (igual a backend/modules/orbit.py)
const MU = 398600.4418;
const RE = 6378.137;
const J2 = 1.08262668e-3;
const DEG = Math.PI / 180;
const COMPASS = ["N", "NE", "L", "SE", "S", "SO", "O", "NO"];

export function parseTle(text) {
  const lines = String(text || "").split(/\r?\n/).map((l) => l.trimEnd()).filter((l) => l.trim());
  const l1 = lines.find((l) => l.startsWith("1 "));
  const l2 = lines.find((l) => l.startsWith("2 "));
  if (!l1 || !l2 || l1.length < 64 || l2.length < 63) return null;
  const yy = Number(l1.slice(18, 20));
  const doy = Number(l1.slice(20, 32));
  const vals = [l2.slice(8, 16), l2.slice(17, 25), `0.${l2.slice(26, 33).trim()}`, l2.slice(34, 42), l2.slice(43, 51), l2.slice(52, 63), l1.slice(33, 43)].map(Number);
  if (![yy, doy, ...vals].every(Number.isFinite)) return null;
  const year = yy < 57 ? 2000 + yy : 1900 + yy;
  const epoch = Date.UTC(year, 0, 1) + (doy - 1) * 86400_000;
  const [inc, raan, ecc, argp, ma, mm, ndot] = vals;
  return { epoch: new Date(epoch).toISOString(), inc, raan, ecc, argp, ma, mm, ndot, line1: l1, line2: l2 };
}

const jd = (ms) => ms / 86400_000 + 2440587.5;
const gmst = (ms) => (((280.46061837 + 360.98564736629 * (jd(ms) - 2451545)) % 360) + 360) % 360 * DEG;

function brouwer(n0, e, inc) {
  const a1 = (MU / n0 ** 2) ** (1 / 3) / RE;
  const d1 = (0.75 * J2 * (3 * Math.cos(inc) ** 2 - 1)) / (1 - e * e) ** 1.5 / a1 ** 2;
  const a0 = a1 * (1 - d1 / 3 - d1 ** 2 - (134 / 81) * d1 ** 3);
  const n = n0 / (1 + d1 * (a1 / a0) ** 2);
  return [n, (MU / n ** 2) ** (1 / 3)];
}

export function eci(tle, ms) {
  const dt = (ms - Date.parse(tle.epoch)) / 86400_000;
  const e = tle.ecc;
  const inc = tle.inc * DEG;
  const [n, a] = brouwer((tle.mm * 2 * Math.PI) / 86400, e, inc);
  const p = a * (1 - e * e);
  const k = 1.5 * J2 * (RE / p) ** 2 * n * 86400;
  const ci = Math.cos(inc);
  const si = Math.sin(inc);
  const raan = tle.raan * DEG - k * ci * dt;
  const argp = tle.argp * DEG + k * (2 - 2.5 * si ** 2) * dt;
  let m = tle.ma * DEG + (n * 86400 + 0.5 * k * Math.sqrt(1 - e * e) * (3 * ci ** 2 - 1)) * dt + 2 * Math.PI * tle.ndot * dt ** 2;
  m = ((m % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
  let E = m;
  for (let i = 0; i < 8; i += 1) E -= (E - e * Math.sin(E) - m) / (1 - e * Math.cos(E));
  const nu = 2 * Math.atan2(Math.sqrt(1 + e) * Math.sin(E / 2), Math.sqrt(1 - e) * Math.cos(E / 2));
  const r = a * (1 - e * Math.cos(E));
  const u = argp + nu;
  const [cu, su, co, so] = [Math.cos(u), Math.sin(u), Math.cos(raan), Math.sin(raan)];
  return [r * (co * cu - so * su * ci), r * (so * cu + co * su * ci), r * su * si];
}

export function position(tle, ms) {
  const [x, y, z] = eci(tle, ms);
  const r = Math.hypot(x, y, z);
  let lon = Math.atan2(y, x) - gmst(ms);
  lon = ((((lon + Math.PI) % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI)) - Math.PI;
  const [, a] = brouwer((tle.mm * 2 * Math.PI) / 86400, tle.ecc, tle.inc * DEG);
  return { lat: round(Math.asin(z / r) / DEG, 4), lon: round(lon / DEG, 4), alt_km: round(r - RE, 1), vel_kmh: Math.round(Math.sqrt(MU * (2 / r - 1 / a)) * 3600) };
}

export function track(tle, ms, minutes = 46, step = 2) {
  const pts = [];
  for (let k = -minutes; k <= minutes; k += step) {
    const p = position(tle, ms + k * 60_000);
    pts.push([p.lon, p.lat]);
  }
  return pts;
}

function look(target, lat, lon, ms) {
  const th = gmst(ms) + lon * DEG;
  const la = lat * DEG;
  const o = [RE * Math.cos(la) * Math.cos(th), RE * Math.cos(la) * Math.sin(th), RE * Math.sin(la)];
  const [dx, dy, dz] = [target[0] - o[0], target[1] - o[1], target[2] - o[2]];
  const s = Math.sin(la) * Math.cos(th) * dx + Math.sin(la) * Math.sin(th) * dy - Math.cos(la) * dz;
  const e = -Math.sin(th) * dx + Math.cos(th) * dy;
  const zt = Math.cos(la) * Math.cos(th) * dx + Math.cos(la) * Math.sin(th) * dy + Math.sin(la) * dz;
  const rng = Math.hypot(s, e, zt);
  return [Math.asin(zt / rng) / DEG, (((Math.atan2(e, -s) / DEG) % 360) + 360) % 360];
}

function sunEci(ms) {
  const d = jd(ms) - 2451545;
  const g = (357.529 + 0.98560028 * d) * DEG;
  const q = 280.459 + 0.98564736 * d;
  const lam = (q + 1.915 * Math.sin(g) + 0.02 * Math.sin(2 * g)) * DEG;
  const eps = (23.439 - 0.00000036 * d) * DEG;
  return [Math.cos(lam), Math.cos(eps) * Math.sin(lam), Math.sin(eps) * Math.sin(lam)];
}

function sunlit(r, s) {
  const dot = r[0] * s[0] + r[1] * s[1] + r[2] * s[2];
  if (dot > 0) return true;
  return Math.sqrt(Math.max(0, r[0] ** 2 + r[1] ** 2 + r[2] ** 2 - dot * dot)) > RE;
}

const compass = (az) => COMPASS[Math.floor((((az % 360) + 360) % 360 + 22.5) / 45) % 8];

export function passes(tle, lat, lon, startMs, hours = 72, step = 20, minEl = 10, limit = 6) {
  const out = [];
  let cur = null;
  const end = startMs + hours * 3600_000;
  const close = () => {
    out.push({
      inicio: new Date(cur.ini).toISOString(), fim: new Date(cur.fim).toISOString(),
      minutos: Math.max(1, Math.round((cur.fim - cur.ini) / 60_000)), max_el: Math.round(cur.max),
      de: compass(cur.azIni), para: compass(cur.azFim),
    });
    cur = null;
  };
  for (let t = startMs; t <= end && out.length < limit;) {
    const r = eci(tle, t);
    const [el, az] = look(r, lat, lon, t);
    const s = sunEci(t);
    const ok = el >= minEl && sunlit(r, s) && look([s[0] * 1.496e8, s[1] * 1.496e8, s[2] * 1.496e8], lat, lon, t)[0] < -6;
    if (ok) {
      if (!cur) cur = { ini: t, azIni: az, max: el, fim: t, azFim: az };
      cur.fim = t;
      cur.azFim = az;
      cur.max = Math.max(cur.max, el);
    } else if (cur) close();
    t += (el > -25 ? step : step * 6) * 1000;
  }
  if (cur && out.length < limit) close();
  return out;
}

async function tleFrom(store, fetchFn, nowMs) {
  const saved = (await store.get("olho_tle")) || null;
  if (saved?.tle && nowMs - saved.baixado < 6 * 3600_000) return saved.tle;
  try {
    const tle = parseTle(await getText(fetchFn, CELESTRAK, 12_000));
    if (tle) {
      await store.set("olho_tle", { tle, baixado: nowMs });
      return tle;
    }
  } catch {
    /* usa o guardado */
  }
  if (saved?.tle) return saved.tle;
  throw new Error("sem TLE");
}

async function iss(store, fetchFn, lat, lon, nowMs, light = false) {
  const tle = await tleFrom(store, fetchFn, nowMs);
  const out = { agora: position(tle, nowMs), trilha: track(tle, nowMs), atualizado: new Date(nowMs).toISOString(), fonte: "CelesTrak", passagens: [] };
  if (lat != null && !light) {
    let clouds = {};
    try {
      clouds = Object.fromEntries((await forecast(fetchFn, lat, lon, nowMs)).horas.map((h) => [h.t.slice(0, 13), h.nuvens]));
    } catch {
      clouds = {};
    }
    for (const p of passes(tle, lat, lon, nowMs)) {
      const local = localStamp(Date.parse(p.inicio));
      out.passagens.push({ ...p, hora: local.slice(11, 16), dia: `${local.slice(8, 10)}/${local.slice(5, 7)}`, nuvens: clouds[local.slice(0, 13)] ?? null });
    }
  }
  return out;
}

// --------------------------------------------------------------------------- lançamentos (igual a world_data.launches)
const urlOf = (v) => {
  const u = String((v && typeof v === "object" ? v.image_url || v.url : v) || "");
  return u.startsWith("https://") ? u : "";
};

export function parseLaunches(data, kind) {
  const out = [];
  for (const r of data?.results || []) {
    const pad = r.pad || {};
    const la = num(pad.latitude);
    const lo = num(pad.longitude);
    if (la == null || lo == null) continue;
    const st = r.status || {};
    const key = String(st.abbrev || st.name || "").trim().toLowerCase();
    const mission = r.mission || {};
    const rocket = r.rocket?.configuration || {};
    const loc = pad.location || {};
    out.push({
      id: String(r.id || "").slice(0, 40), nome: String(r.name || "").slice(0, 120), quando: String(r.net || ""),
      janela: [String(r.window_start || ""), String(r.window_end || "")],
      situacao: LAUNCH_STATUS[key] || String(st.name || "").slice(0, 30).toLowerCase(), status: key,
      foguete: String(rocket.full_name || rocket.name || "").slice(0, 60), empresa: String(r.launch_service_provider?.name || "").slice(0, 60),
      missao: String(mission.name || "").slice(0, 80), descricao: String(mission.description || "").slice(0, 600), orbita: String(mission.orbit?.name || "").slice(0, 40),
      base: String(pad.name || "").slice(0, 80), local: String(loc.name || "").slice(0, 80), pais: String(pad.country?.name || loc.country_code || "").slice(0, 40),
      lat: round(la, 4), lon: round(lo, 4), foto: urlOf(r.image),
      video: (r.vidURLs || []).map(urlOf).find(Boolean) || "", site: (r.infoURLs || []).map(urlOf).find(Boolean) || "",
      ao_vivo: Boolean(r.webcast_live), chance: num(r.probability), tipo: kind,
    });
  }
  return out;
}

async function launches(fetchFn, nowMs) {
  const items = [];
  let ok = false;
  for (const [kind, label, limit] of [["upcoming", "proximo", 12], ["previous", "recente", 8]]) {
    for (const base of LAUNCHES) {
      try {
        const data = await cached(`ll${base}${kind}`, 1800_000, () => getJson(fetchFn, `${base}${kind}/?limit=${limit}&mode=detailed`, 15_000), nowMs);
        items.push(...parseLaunches(data, label));
        ok = true;
        break;
      } catch {
        /* tenta a outra versão */
      }
    }
  }
  if (!ok) throw new Error("sem lançamentos");
  const prox = items.filter((i) => i.tipo === "proximo").sort((a, b) => a.quando.localeCompare(b.quando));
  return { itens: items, total: items.length, proximo: prox[0] || null, atualizado: new Date(nowMs).toISOString(), fonte: "The Space Devs" };
}

// --------------------------------------------------------------------------- entrada
export async function worldLayer(name, { lat = null, lon = null, limit = 4000, light = false, store, fetchFn = fetch, nowMs = Date.now() }) {
  if (!LAYERS.includes(name)) throw Object.assign(new Error("Camada desconhecida."), { status: 404 });
  if (lat == null && (name === "chuva" || name === "voos")) throw Object.assign(new Error("Informe a cidade (lat e lon)."), { status: 400 });
  if (name === "terremotos") return quakes(fetchFn, lat, lon, nowMs);
  if (name === "lancamentos") return launches(fetchFn, nowMs);
  if (name === "voos") return flights(fetchFn, lat, lon, nowMs);
  if (name === "queimadas") return fires(fetchFn, lat, lon, nowMs, Math.max(200, Math.min(limit, 6000)));
  if (name === "chuva") return rain(fetchFn, lat, lon, nowMs);
  return iss(store, fetchFn, lat, lon, nowMs, light);
}

export function summaryParts(s, todayDm) {
  const parts = [];
  if (s.chuva) parts.push(s.chuva.texto);
  if (s.voos) parts.push(`${s.voos.no_ar} voos por perto`);
  if (s.terremotos) {
    const n = s.terremotos.fortes;
    parts.push(n ? `${n} terremoto${n !== 1 ? "s" : ""} forte${n !== 1 ? "s" : ""} hoje` : "nenhum terremoto forte hoje");
  }
  if (s.queimadas && s.queimadas.perto != null) {
    const n = s.queimadas.perto;
    parts.push(n ? `${n} foco${n !== 1 ? "s" : ""} de queimada a menos de ${NEAR_KM} km` : "sem queimadas por perto");
  }
  const p = s.iss?.passagens || [];
  if (p.length) parts.push(`ISS passa visível ${p[0].dia === todayDm ? "hoje" : `em ${p[0].dia}`} às ${p[0].hora}`);
  return parts;
}

export async function worldSummary({ lat, lon, store, fetchFn = fetch, nowMs = Date.now() }) {
  const strip = (o) => (o ? Object.fromEntries(Object.entries(o).filter(([k]) => k !== "itens")) : null);
  const run = async (fn) => {
    try {
      return await fn();
    } catch {
      return null;
    }
  };
  const [chuva, voos, terremotos, queimadas, issOut] = await Promise.all([
    run(async () => (await rain(fetchFn, lat, lon, nowMs)).resumo),
    run(() => flights(fetchFn, lat, lon, nowMs)),
    run(() => quakes(fetchFn, lat, lon, nowMs)),
    run(() => fires(fetchFn, lat, lon, nowMs, 1)),
    run(async () => ({ passagens: (await iss(store, fetchFn, lat, lon, nowMs)).passagens.slice(0, 3) })),
  ]);
  const out = { chuva, voos: strip(voos), terremotos: strip(terremotos), queimadas: strip(queimadas), iss: issOut };
  const today = localStamp(nowMs);
  out.texto = summaryParts(out, `${today.slice(8, 10)}/${today.slice(5, 7)}`).join(" · ");
  return out;
}

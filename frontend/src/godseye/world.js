// V7.11: OLHO DE DEUS com dados reais. Camadas, textos falados e comandos de voz (sem React: testável com node).

export const LAYERS = [
  { id: "chuva", label: "Radar de chuva", icon: "☁", color: "#60a5fa", refresh: 300_000 },
  { id: "voos", label: "Voos ao vivo", icon: "✈", color: "#facc15", refresh: 15_000 },
  { id: "terremotos", label: "Terremotos 24 h", icon: "🌎", color: "#fb7185", refresh: 300_000 },
  { id: "queimadas", label: "Queimadas 24 h", icon: "🔥", color: "#fb923c", refresh: 900_000 },
  { id: "iss", label: "Estação Espacial", icon: "🛰", color: "#e879f9", refresh: 10_000 },
  { id: "lancamentos", label: "Lançamentos de foguetes", icon: "🚀", color: "#f43f5e", refresh: 1_800_000 },
];
export const LAYER_IDS = LAYERS.map((l) => l.id);

export const ALERTS = [
  { id: "chuva", label: "Chuva forte chegando" },
  { id: "perto", label: "Queimada ou terremoto perto" },
  { id: "iss", label: "Estação Espacial visível" },
];

const pt = (n) => String(n).replace(".", ",");
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;

/** O número curto que aparece ao lado de cada camada. */
export function layerValue(id, data) {
  if (!data) return "—";
  if (id === "chuva") return data.resumo?.forte ? "FORTE" : data.resumo?.minutos != null ? "chuva" : "seco";
  if (id === "voos") return String(data.no_ar ?? data.total ?? 0);
  if (id === "terremotos") return String(data.total ?? 0);
  if (id === "queimadas") return data.perto ? `${data.perto} perto` : String(data.total ?? 0);
  if (id === "iss") return data.agora ? `${Math.round(data.agora.alt_km)} km` : "—";
  if (id === "lancamentos") return data.proximo ? relTime(data.proximo.quando) : String(data.total ?? 0);
  return "—";
}

export function isToday(dm, now = new Date()) {
  return dm === `${String(now.getDate()).padStart(2, "0")}/${String(now.getMonth() + 1).padStart(2, "0")}`;
}

/** A resposta falada para "tem terremoto hoje?", "vai chover?" etc. */
export function speakFor(id, data, city = "sua cidade", now = new Date()) {
  if (!data) return "Não consegui os dados agora, senhor. Tente em instantes.";
  if (id === "terremotos") {
    if (!data.total) return "Nenhum terremoto registrado nas últimas 24 horas.";
    const m = data.maior || data.itens?.[0];
    return `${plural(data.total, "terremoto", "terremotos")} nas últimas 24 horas, ${data.fortes} de força 5 ou mais. O maior foi de ${pt(m.mag)}, ${m.lugar}.`;
  }
  if (id === "voos") return `${plural(data.no_ar ?? 0, "avião voando", "aviões voando")} num raio de ${data.raio_km || 150} quilômetros de ${city} agora.`;
  if (id === "queimadas") {
    if (data.perto) return `Atenção: ${plural(data.perto, "foco", "focos")} de queimada a menos de ${data.perto_km || 50} quilômetros de ${city} nas últimas 24 horas.`;
    const far = data.mais_perto ? ` O mais próximo está a ${data.mais_perto.dist_km} quilômetros, em ${data.mais_perto.municipio || "outro município"}.` : "";
    return `Nenhuma queimada a menos de ${data.perto_km || 50} quilômetros de ${city}. ${plural(data.total ?? 0, "foco", "focos")} no Brasil nas últimas 24 horas.${far}`;
  }
  if (id === "chuva") return `${data.resumo?.texto || "Sem dados de chuva"} em ${city}.`;
  if (id === "lancamentos") {
    const p = data.proximo;
    if (!p) return "Não encontrei lançamentos marcados agora.";
    return `O próximo lançamento é ${p.missao || p.nome}, num ${p.foguete || "foguete"}${p.empresa ? ` da ${p.empresa}` : ""}, ${relTime(p.quando, now, true)}${p.local ? `, saindo de ${p.local}` : ""}.`;
  }
  if (id === "iss") {
    const p = data.passagens?.[0];
    if (!p) return "A Estação Espacial não passa visível no seu céu nos próximos 3 dias.";
    const nuv = p.nuvens != null ? ` Céu com ${Math.round(p.nuvens)}% de nuvens.` : "";
    return `A Estação Espacial passa visível ${isToday(p.dia, now) ? "hoje" : `dia ${p.dia}`} às ${p.hora}, do ${p.de} para o ${p.para}, por ${plural(p.minutos, "minuto", "minutos")}, a ${p.max_el} graus de altura.${nuv}`;
  }
  return "";
}

/** "mostra os voos agora", "tem terremoto hoje?", "vai chover?", "quando a estação espacial passa?" (texto já normalizado). */
export function worldIntent(n) {
  const t = ` ${String(n || "")} `;
  if (/\b(lancamentos?|foguetes?|spacex|falcon)\b/.test(t) && !/\b(lancamento de (nota|gasto|despesa))\b/.test(t)) return { layer: "lancamentos", ask: true };
  if (/\b(estacao espacial|\biss\b)/.test(t)) return { layer: "iss", ask: /\b(quando|que horas|passa|vai passar|onde)\b/.test(t) };
  if (/\b(voos?|avi(ao|oes)|aeronaves?)\b/.test(t) && /\b(mostra|mostre|mostrar|ver|veja|quantos|tem|abre|abra|agora|passando|em cima)\b/.test(t)) return { layer: "voos", ask: true };
  if (/\b(terremotos?|sismos?|abalos? sismicos?)\b/.test(t)) return { layer: "terremotos", ask: true };
  if (/\b(queimadas?|incendios?|focos? de (fogo|incendio|queimada))\b/.test(t)) return { layer: "queimadas", ask: true };
  if (/\b(radar de chuva|radar do tempo)\b/.test(t) || (/\b(mostra|mostre|mostrar|abre|abra)\b/.test(t) && /\bchuva\b/.test(t))) return { layer: "chuva", ask: true };
  return null;
}

// --------------------------------------------------------------------------- GeoJSON para o globo
const fc = (features) => ({ type: "FeatureCollection", features });
const point = (lon, lat, props) => ({ type: "Feature", geometry: { type: "Point", coordinates: [lon, lat] }, properties: props });

export function quakesGeo(data) {
  return fc((data?.itens || []).map((q) => point(q.lon, q.lat, { kind: "terremotos", id: q.id, mag: q.mag, lugar: q.lugar, quando: q.quando, prof_km: q.prof_km, dist_km: q.dist_km ?? null })));
}

export function firesGeo(data) {
  return fc((data?.itens || []).map((f, i) => point(f.lon, f.lat, { kind: "queimadas", id: `f${i}`, municipio: f.municipio, estado: f.estado, bioma: f.bioma, quando: f.quando, frp: f.frp, dist_km: f.dist_km ?? null })));
}

export function flightsGeo(data) {
  return fc((data?.itens || []).filter((f) => !f.solo).map((f) => point(f.lon, f.lat, {
    kind: "voos", id: f.id, voo: f.voo || f.matricula || f.id, modelo: f.modelo, matricula: f.matricula, alt_m: f.alt_m, vel_kmh: f.vel_kmh, rumo: f.rumo, dist_km: f.dist_km,
  })));
}

/** A trilha da ISS cortada onde cruza a linha de data (senão o globo desenha uma linha atravessando o mundo). */
export function launchesGeo(data) {
  return fc((data?.itens || []).map((l) => point(l.lon, l.lat, { kind: "lancamentos", id: l.id, tipo: l.tipo, ao_vivo: l.ao_vivo })));
}

/** "em 3 dias", "há 11 dias", "em 2 h 10 min". */
export function relTime(iso, now = new Date(), long = false) {
  const t = Date.parse(iso);
  if (!Number.isFinite(t)) return "";
  const diff = t - now.getTime();
  const abs = Math.abs(diff);
  const min = Math.round(abs / 60_000);
  let txt;
  if (min < 60) txt = `${min} min`;
  else if (min < 48 * 60) txt = `${Math.floor(min / 60)} h${min % 60 ? ` ${min % 60} min` : ""}`;
  else txt = `${Math.round(min / 1440)} dias`;
  if (long) txt = txt.replace(/\bh\b/, "horas").replace("min", "minutos");
  return diff >= 0 ? `em ${txt}` : `há ${txt}`;
}

export function issTrack(data) {
  const lines = [];
  let cur = [];
  for (const p of data?.trilha || []) {
    const prev = cur[cur.length - 1];
    if (prev && Math.abs(p[0] - prev[0]) > 180) {
      lines.push(cur);
      cur = [];
    }
    cur.push(p);
  }
  if (cur.length) lines.push(cur);
  return fc(lines.filter((l) => l.length > 1).map((coordinates) => ({ type: "Feature", geometry: { type: "LineString", coordinates }, properties: {} })));
}

export function radarTiles(radar, frame) {
  return `${radar.host}${frame.path}/256/{z}/{x}/{y}/2/1_1.png`;
}

export function fmtTime(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

/** Linhas do cartão de um ponto tocado no globo. */
export function pickCard(p, launchList = []) {
  if (!p) return null;
  const dist = p.dist_km != null && p.dist_km !== "null" ? `${p.dist_km} km de você` : null;
  if (p.kind === "terremotos") return { icon: "🌎", title: `Terremoto ${pt(p.mag)}`, lines: [p.lugar, fmtTime(p.quando), p.prof_km != null ? `${p.prof_km} km de profundidade` : null, dist] };
  if (p.kind === "queimadas") return { icon: "🔥", title: "Foco de queimada", lines: [[p.municipio, p.estado].filter(Boolean).join(" · "), p.bioma, fmtTime(p.quando), dist] };
  if (p.kind === "voos") {
    return { icon: "✈", title: `Voo ${p.voo}`, lines: [[p.modelo, p.matricula].filter(Boolean).join(" · "), p.alt_m != null ? `${Number(p.alt_m).toLocaleString("pt-BR")} m de altitude` : null, p.vel_kmh != null ? `${p.vel_kmh} km/h · rumo ${p.rumo}°` : null, dist] };
  }
  if (p.kind === "lancamentos") {
    const l = (launchList || []).find((x) => x.id === p.id);
    if (!l) return null;
    const when = fmtTime(l.quando);
    return {
      icon: "🚀", title: l.missao || l.nome, subtitle: [l.foguete, l.empresa].filter(Boolean).join(" · "),
      badge: l.ao_vivo ? "AO VIVO" : l.situacao, badgeKind: /sucesso/.test(l.situacao) ? "ok" : /falh/.test(l.situacao) ? "bad" : "info",
      image: l.foto, hero: l.tipo === "proximo" ? "Próximo lançamento" : "Lançado", heroSub: relTime(l.quando),
      text: l.descricao,
      lines: [when ? `Quando: ${when}` : null, l.orbita ? `Órbita: ${l.orbita}` : null, l.base ? `Base: ${l.base}` : null, l.local ? `Local: ${l.local}` : null, l.chance != null ? `Tempo bom: ${l.chance}%` : null],
      links: [l.video && { label: l.ao_vivo ? "▶ AO VIVO" : "▶ ASSISTIR", url: l.video }, l.site && { label: "↗ SITE", url: l.site }].filter(Boolean),
    };
  }
  if (p.kind === "iss") return { icon: "🛰", title: "Estação Espacial (ISS)", lines: [`${Math.round(p.alt_km)} km de altitude`, `${Number(p.vel_kmh).toLocaleString("pt-BR")} km/h`, "uma volta na Terra a cada ~92 minutos"] };
  return null;
}

/** A faixa "o que está acontecendo" (com as camadas que já chegaram). */
export function summaryText(data, now = new Date()) {
  const parts = [];
  if (data.chuva?.resumo) parts.push(data.chuva.resumo.texto);
  if (data.voos) parts.push(`${data.voos.no_ar ?? 0} voos por perto`);
  if (data.terremotos) {
    const n = data.terremotos.fortes || 0;
    parts.push(n ? `${n} terremoto${n !== 1 ? "s" : ""} forte${n !== 1 ? "s" : ""} hoje` : "nenhum terremoto forte hoje");
  }
  if (data.queimadas && data.queimadas.perto != null) {
    const n = data.queimadas.perto;
    parts.push(n ? `${n} foco${n !== 1 ? "s" : ""} de queimada a menos de ${data.queimadas.perto_km || 50} km` : "sem queimadas por perto");
  }
  const p = data.iss?.passagens?.[0];
  if (p) parts.push(`ISS passa visível ${isToday(p.dia, now) ? "hoje" : `em ${p.dia}`} às ${p.hora}`);
  return parts.join(" · ");
}

export function layerUrl(id, where, { lite = false, light = false } = {}) {
  const q = new URLSearchParams();
  if (where) {
    q.set("lat", String(Number(where.lat).toFixed(4)));
    q.set("lon", String(Number(where.lon).toFixed(4)));
  }
  if (id === "queimadas") q.set("limit", lite ? "1500" : "4000");
  if (id === "iss" && light) q.set("leve", "1");
  return `/api/world/${id}?${q}`;
}

/** Para a voz: busca a camada perto de casa e devolve o texto da resposta. */
export async function askWorld(api, id) {
  let home = null;
  try {
    home = (await api("/api/world/home"))?.home || null;
  } catch {
    home = null;
  }
  try {
    const data = await api(layerUrl(id, home), { timeout: 30_000 });
    return speakFor(id, data, home?.nome || "sua cidade");
  } catch {
    return speakFor(id, null);
  }
}

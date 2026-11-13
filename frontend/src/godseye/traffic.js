// V6.9: trânsito ao vivo no Olho de Deus (mapa ao vivo do Waze, embutido).
// O mapa é a página pública de incorporação do Waze; a busca de lugares usa o OpenStreetMap
// (endereço, CEP, bairro) e o Open-Meteo (nome de cidade) como reserva. Nada disso pede chave.

export const DEFAULT_CENTER = { lat: -23.5505, lon: -46.6333, label: "São Paulo" };

export function wazeEmbedUrl({ lat, lon }, zoom = 13) {
  const z = Math.max(3, Math.min(17, Math.round(zoom)));
  return `https://embed.waze.com/iframe?zoom=${z}&lat=${lat.toFixed(5)}&lon=${lon.toFixed(5)}&ct=livemap`;
}

// "Ir até lá" no app do Waze (ou no site, se o app não estiver instalado)
export function wazeNavigateUrl({ lat, lon }) {
  return `https://waze.com/ul?ll=${lat.toFixed(5)}%2C${lon.toFixed(5)}&navigate=yes`;
}

const CEP = /^\d{5}-?\d{3}$/;

export async function geocode(query, fetchFn = fetch) {
  const q = String(query || "").trim();
  if (!q) return null;
  try {
    const res = await fetchFn(`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&accept-language=pt-BR&q=${encodeURIComponent(CEP.test(q) ? `${q}, Brasil` : q)}`);
    const hit = res.ok ? (await res.json())[0] : null;
    if (hit) return { lat: Number(hit.lat), lon: Number(hit.lon), label: shortLabel(hit.display_name) || q };
  } catch {
    /* tenta o Open-Meteo */
  }
  try {
    const res = await fetchFn(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(q)}&count=1&language=pt&format=json`);
    const hit = res.ok ? (await res.json()).results?.[0] : null;
    if (hit) return { lat: hit.latitude, lon: hit.longitude, label: [hit.name, hit.admin1].filter(Boolean).join(", ") };
  } catch {
    /* sem resultado */
  }
  return null;
}

export function shortLabel(displayName) {
  return String(displayName || "").split(",").map((p) => p.trim()).filter(Boolean).slice(0, 2).join(", ");
}

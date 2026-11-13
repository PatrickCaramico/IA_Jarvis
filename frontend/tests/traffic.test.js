// V6.9: trânsito ao vivo do Olho de Deus (node --test frontend/tests)
import { test } from "node:test";
import assert from "node:assert/strict";
import { geocode, shortLabel, wazeEmbedUrl, wazeNavigateUrl } from "../src/godseye/traffic.js";

test("monta o mapa ao vivo do Waze e o link de navegação", () => {
  assert.equal(wazeEmbedUrl({ lat: -23.5505, lon: -46.6333 }, 30), "https://embed.waze.com/iframe?zoom=17&lat=-23.55050&lon=-46.63330&ct=livemap");
  assert.equal(wazeNavigateUrl({ lat: -22.9, lon: -43.2 }), "https://waze.com/ul?ll=-22.90000%2C-43.20000&navigate=yes");
});

test("busca no OpenStreetMap e cai no Open-Meteo quando não acha", async () => {
  const osm = async () => new Response(JSON.stringify([{ lat: "-23.56", lon: "-46.65", display_name: "Avenida Paulista, Bela Vista, São Paulo" }]));
  assert.deepEqual(await geocode("Av Paulista", osm), { lat: -23.56, lon: -46.65, label: "Avenida Paulista, Bela Vista" });
  const calls = [];
  const fallback = async (url) => {
    calls.push(url);
    return url.includes("nominatim")
      ? new Response("[]")
      : new Response(JSON.stringify({ results: [{ latitude: -22.9, longitude: -47.06, name: "Campinas", admin1: "São Paulo" }] }));
  };
  assert.deepEqual(await geocode("Campinas", fallback), { lat: -22.9, lon: -47.06, label: "Campinas, São Paulo" });
  assert.equal(calls.length, 2);
  assert.equal(await geocode("  "), null);
  assert.equal(shortLabel(""), "");
});

import { test } from "node:test";
import assert from "node:assert/strict";
import { flightsGeo, issTrack, layerUrl, layerValue, pickCard, speakFor, summaryText, worldIntent } from "../src/godseye/world.js";

test("V7.11: comandos de voz do Olho de Deus", () => {
  assert.deepEqual(worldIntent("mostra os voos agora"), { layer: "voos", ask: true });
  assert.equal(worldIntent("tem terremoto hoje?").layer, "terremotos");
  assert.equal(worldIntent("tem queimada perto?").layer, "queimadas");
  assert.equal(worldIntent("quando a estacao espacial passa?").layer, "iss");
  assert.equal(worldIntent("mostra o radar de chuva").layer, "chuva");
  assert.equal(worldIntent("vai chover amanha?"), null); // continua com o clima
  assert.equal(worldIntent("comprei passagem de aviao"), null);
});

test("V7.11: respostas faladas e resumo", () => {
  const now = new Date(2026, 10, 15, 18, 0);
  assert.match(speakFor("terremotos", { total: 12, fortes: 2, maior: { mag: 6.1, lugar: "Chile" } }), /12 terremotos .* 2 de força 5 .* 6,1, Chile/);
  assert.match(speakFor("voos", { no_ar: 1, raio_km: 150 }, "Campinas"), /1 avião voando .* Campinas/);
  assert.match(speakFor("queimadas", { perto: 0, perto_km: 50, total: 900, mais_perto: { dist_km: 80, municipio: "Itu" } }, "Campinas"), /Nenhuma .* 80 quilômetros, em Itu/);
  assert.match(speakFor("iss", { passagens: [{ dia: "15/11", hora: "19:42", de: "NO", para: "SE", minutos: 4, max_el: 52, nuvens: 10 }] }, "x", now), /hoje às 19:42, do NO para o SE, por 4 minutos/);
  assert.match(speakFor("iss", { passagens: [] }), /não passa visível/);
  assert.match(speakFor("voos", null), /Não consegui/);
  assert.equal(
    summaryText({ chuva: { resumo: { texto: "Sem chuva nas próximas 3 h" } }, voos: { no_ar: 42 }, terremotos: { fortes: 1 }, queimadas: { perto: 2 }, iss: { passagens: [{ dia: "16/11", hora: "05:10" }] } }, now),
    "Sem chuva nas próximas 3 h · 42 voos por perto · 1 terremoto forte hoje · 2 focos de queimada a menos de 50 km · ISS passa visível em 16/11 às 05:10",
  );
  assert.equal(layerValue("queimadas", { perto: 3, total: 10 }), "3 perto");
  assert.equal(layerValue("voos", null), "—");
});

test("V7.11: dados para o globo", () => {
  const g = flightsGeo({ itens: [{ id: "a", voo: "GLO1", lat: -23, lon: -46, rumo: 90, solo: false }, { id: "b", lat: 0, lon: 0, solo: true }] });
  assert.equal(g.features.length, 1);
  assert.equal(g.features[0].properties.rumo, 90);
  // trilha cruzando a linha de data vira duas linhas
  const t = issTrack({ trilha: [[170, 10], [178, 12], [-176, 14], [-170, 16]] });
  assert.equal(t.features.length, 2);
  assert.equal(layerUrl("queimadas", { lat: -23.5, lon: -46.6 }, { lite: true }), "/api/world/queimadas?lat=-23.5000&lon=-46.6000&limit=1500");
  assert.equal(layerUrl("iss", null, { light: true }), "/api/world/iss?leve=1");
  assert.equal(pickCard({ kind: "voos", voo: "GLO1", modelo: "B738", alt_m: 3048, vel_kmh: 556, rumo: 90, dist_km: 4 }).title, "Voo GLO1");
  assert.equal(pickCard(null), null);
});

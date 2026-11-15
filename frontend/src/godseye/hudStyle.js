// V7.13: base comum dos globos (Olho de Deus e mapa do Holograma): MapLibre (versão "csp", worker em arquivo
// próprio, porque o minificador quebra o worker embutido) e os continentes do Natural Earth, sem chave nenhuma.
import maplibreglCsp from "maplibre-gl/dist/maplibre-gl-csp.js";
import workerUrl from "maplibre-gl/dist/maplibre-gl-csp-worker.js?url";
import "maplibre-gl/dist/maplibre-gl.css";
import { feature, mesh } from "topojson-client";
import countries50 from "world-atlas/countries-50m.json?url";
import countries110 from "world-atlas/countries-110m.json?url";

maplibreglCsp.setWorkerUrl(workerUrl);
export const maplibregl = maplibreglCsp;

export const EMPTY = { type: "FeatureCollection", features: [] };

export async function loadWorld(lite) {
  const topo = await (await fetch(lite ? countries110 : countries50)).json();
  const obj = topo.objects.countries;
  return {
    land: feature(topo, obj),
    borders: mesh(topo, obj, (a, b) => a !== b),
    coast: mesh(topo, obj, (a, b) => a === b),
  };
}

/** Estilo "HUD": oceano azul, continentes e contornos em neon, com atmosfera. */
export function hudStyle(extraSources = {}, extraLayers = []) {
  return {
    version: 8,
    projection: { type: "globe" },
    sky: {
      "sky-color": "#04112e", "horizon-color": "#1d6bff", "fog-color": "#0a2d6e",
      "atmosphere-blend": ["interpolate", ["linear"], ["zoom"], 0, 1, 5, 1, 7, 0],
    },
    sources: {
      world: { type: "geojson", data: EMPTY, attribution: "Natural Earth" },
      borders: { type: "geojson", data: EMPTY },
      coast: { type: "geojson", data: EMPTY },
      ...extraSources,
    },
    layers: [
      { id: "ge-ocean", type: "background", paint: { "background-color": "#0a2d6e" } },
      { id: "ge-land", type: "fill", source: "world", paint: { "fill-color": "#11408f", "fill-opacity": 0.92 } },
      { id: "ge-coast-glow", type: "line", source: "coast", paint: { "line-color": "#22d3ee", "line-width": ["interpolate", ["linear"], ["zoom"], 1, 4, 6, 9], "line-blur": 5, "line-opacity": 0.45 } },
      { id: "ge-borders", type: "line", source: "borders", paint: { "line-color": "#38bdf8", "line-width": 0.7, "line-opacity": 0.55 } },
      { id: "ge-coast", type: "line", source: "coast", paint: { "line-color": "#5eead4", "line-width": ["interpolate", ["linear"], ["zoom"], 1, 1, 6, 1.8], "line-opacity": 0.95 } },
      ...extraLayers,
    ],
  };
}

export function fillWorld(map, w) {
  map.getSource("world")?.setData(w.land);
  map.getSource("borders")?.setData(w.borders);
  map.getSource("coast")?.setData(w.coast);
}

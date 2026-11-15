import { useEffect, useRef, useState } from "react";
import { maplibregl, loadWorld } from "./hudStyle.js";
import { firesGeo, flightsGeo, issTrack, launchesGeo, quakesGeo, radarTiles } from "./world.js";

// V7.11: globo 3D de verdade (MapLibre, projeção "globe"). V7.12: visual "HUD" sem nenhuma chave de mapa: oceano
// azul, continentes e fronteiras em neon desenhados a partir do Natural Earth (pacote world-atlas, vem junto com o
// site). Ao aproximar, entram as ruas (Esri, sem chave); a visão satélite também é da Esri.
const ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services";
const STREETS = [`${ESRI}/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}`];
const SAT = [`${ESRI}/World_Imagery/MapServer/tile/{z}/{y}/{x}`];
const PLACES = [`${ESRI}/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}`];
const HUD_LAYERS = ["ge-land", "ge-streets", "ge-coast-glow", "ge-borders", "ge-coast"];
const SAT_LAYERS = ["ge-sat", "ge-places"];

const EMPTY = { type: "FeatureCollection", features: [] };
const PICKABLE = ["ge-quakes", "ge-fires", "ge-flights", "ge-launches"];
const LAYER_IDS = {
  terremotos: ["ge-quakes", "ge-quakes-glow"],
  queimadas: ["ge-fires"],
  voos: ["ge-flights"],
  iss: ["ge-iss-track"],
  lancamentos: ["ge-launches", "ge-launches-ring"],
};

function planeImage() {
  const size = 48;
  const c = document.createElement("canvas");
  c.width = size;
  c.height = size;
  const g = c.getContext("2d");
  g.fillStyle = "#fff";
  g.beginPath();
  // fuselagem, asas e cauda (apontando para o norte; o mapa gira pelo rumo)
  g.moveTo(24, 3); g.lineTo(28, 18); g.lineTo(45, 27); g.lineTo(45, 31); g.lineTo(28, 27); g.lineTo(27, 38);
  g.lineTo(33, 43); g.lineTo(33, 46); g.lineTo(24, 43); g.lineTo(15, 46); g.lineTo(15, 43); g.lineTo(21, 38);
  g.lineTo(20, 27); g.lineTo(3, 31); g.lineTo(3, 27); g.lineTo(20, 18); g.closePath();
  g.fill();
  return g.getImageData(0, 0, size, size);
}

function marker(className, html) {
  const el = document.createElement("div");
  el.className = className;
  el.innerHTML = html;
  return el;
}

export default function Globe3D({ home, layersOn, data, base = "hud", lite = false, flyTo, onPick, onReady }) {
  const boxRef = useRef(null);
  const mapRef = useRef(null);
  const issMarker = useRef(null);
  const homeMarker = useRef(null);
  const radarTimer = useRef(null);
  const [ready, setReady] = useState(false);
  const pickRef = useRef(onPick);
  const readyRef = useRef(onReady);
  const issRef = useRef(null);
  const startRef = useRef(home);
  const liteRef = useRef(lite);
  useEffect(() => {
    pickRef.current = onPick;
    readyRef.current = onReady;
  }, [onPick, onReady]);

  // cria o globo uma vez
  useEffect(() => {
    const start = startRef.current;
    const lite = liteRef.current;
    let map;
    try {
      map = new maplibregl.Map({
        container: boxRef.current,
        style: {
          version: 8,
          projection: { type: "globe" },
          sky: {
            "sky-color": "#04112e", "horizon-color": "#1d6bff", "fog-color": "#0a2d6e",
            "atmosphere-blend": ["interpolate", ["linear"], ["zoom"], 0, 1, 5, 1, 7, 0],
          },
          sources: {
            streets: { type: "raster", tiles: STREETS, tileSize: 256, minzoom: 5, maxzoom: 16, attribution: "Ruas © Esri" },
            sat: { type: "raster", tiles: SAT, tileSize: 256, maxzoom: 19, attribution: "Satélite © Esri, Maxar" },
            places: { type: "raster", tiles: PLACES, tileSize: 256, maxzoom: 19 },
            world: { type: "geojson", data: EMPTY, attribution: "Natural Earth" },
            borders: { type: "geojson", data: EMPTY },
            coast: { type: "geojson", data: EMPTY },
          },
          layers: [
            { id: "ge-ocean", type: "background", paint: { "background-color": "#0a2d6e" } },
            { id: "ge-sat", type: "raster", source: "sat", layout: { visibility: "none" } },
            { id: "ge-land", type: "fill", source: "world", paint: { "fill-color": "#11408f", "fill-opacity": 0.92 } },
            {
              id: "ge-streets", type: "raster", source: "streets", minzoom: 5,
              paint: { "raster-opacity": ["interpolate", ["linear"], ["zoom"], 5, 0, 7.5, 0.55, 12, 0.8], "raster-saturation": -1, "raster-brightness-max": 0.75 },
            },
            { id: "ge-coast-glow", type: "line", source: "coast", paint: { "line-color": "#22d3ee", "line-width": ["interpolate", ["linear"], ["zoom"], 1, 4, 6, 9], "line-blur": 5, "line-opacity": 0.45 } },
            { id: "ge-borders", type: "line", source: "borders", paint: { "line-color": "#38bdf8", "line-width": 0.7, "line-opacity": 0.55 } },
            { id: "ge-coast", type: "line", source: "coast", paint: { "line-color": "#5eead4", "line-width": ["interpolate", ["linear"], ["zoom"], 1, 1, 6, 1.8], "line-opacity": 0.95 } },
            { id: "ge-places", type: "raster", source: "places", layout: { visibility: "none" } },
          ],
        },
        center: [start ? start.lon - 70 : -50, start ? start.lat * 0.4 : -12],
        zoom: 1.3,
        attributionControl: { compact: true },
        maxPitch: 60,
      });
    } catch {
      readyRef.current?.(false);
      return undefined;
    }
    mapRef.current = map;
    map.on("load", () => {
      loadWorld(lite).then((w) => {
        if (!mapRef.current) return;
        map.getSource("world")?.setData(w.land);
        map.getSource("borders")?.setData(w.borders);
        map.getSource("coast")?.setData(w.coast);
      }).catch(() => {});
      map.addImage("ge-plane", planeImage(), { sdf: true });
      map.addSource("ge-quakes", { type: "geojson", data: EMPTY });
      map.addSource("ge-fires", { type: "geojson", data: EMPTY });
      map.addSource("ge-flights", { type: "geojson", data: EMPTY });
      map.addSource("ge-iss-track", { type: "geojson", data: EMPTY });
      map.addSource("ge-launches", { type: "geojson", data: EMPTY });
      map.addLayer({
        id: "ge-fires", type: "circle", source: "ge-fires",
        paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 1, 1.6, 6, 3.5, 10, 6], "circle-color": "#f97316", "circle-opacity": 0.9, "circle-blur": 0.25, "circle-stroke-width": 0.6, "circle-stroke-color": "#fdba74" },
      });
      map.addLayer({
        id: "ge-quakes-glow", type: "circle", source: "ge-quakes",
        paint: { "circle-radius": ["interpolate", ["linear"], ["get", "mag"], 2, 6, 5, 18, 8, 42], "circle-color": "#fb7185", "circle-opacity": 0.18, "circle-blur": 0.8 },
      });
      map.addLayer({
        id: "ge-quakes", type: "circle", source: "ge-quakes",
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["get", "mag"], 2, 2.5, 5, 7, 8, 16],
          "circle-color": ["interpolate", ["linear"], ["get", "mag"], 2, "#fda4af", 5, "#fb7185", 6.5, "#e11d48"],
          "circle-stroke-width": 1, "circle-stroke-color": "#fff1f2", "circle-opacity": 0.9,
        },
      });
      map.addLayer({
        id: "ge-iss-track", type: "line", source: "ge-iss-track",
        paint: { "line-color": "#e879f9", "line-width": 1.6, "line-opacity": 0.75, "line-dasharray": [2, 2] },
      });
      map.addLayer({
        id: "ge-launches-ring", type: "circle", source: "ge-launches",
        paint: { "circle-radius": 14, "circle-color": "transparent", "circle-stroke-width": 1.5, "circle-stroke-color": ["case", ["==", ["get", "tipo"], "proximo"], "#fbbf24", "#f43f5e"], "circle-stroke-opacity": 0.8 },
      });
      map.addLayer({
        id: "ge-launches", type: "circle", source: "ge-launches",
        paint: { "circle-radius": 6, "circle-color": ["case", ["==", ["get", "tipo"], "proximo"], "#fbbf24", "#f43f5e"], "circle-stroke-width": 2, "circle-stroke-color": "#fff" },
      });
      map.addLayer({
        id: "ge-flights", type: "symbol", source: "ge-flights",
        layout: {
          "icon-image": "ge-plane", "icon-size": ["interpolate", ["linear"], ["zoom"], 1, 0.3, 4, 0.42, 9, 0.7],
          "icon-rotate": ["get", "rumo"], "icon-rotation-alignment": "map", "icon-allow-overlap": true,
        },
        paint: { "icon-color": "#fde047", "icon-halo-color": "#713f12", "icon-halo-width": 0.6 },
      });
      for (const id of PICKABLE) {
        map.on("click", id, (e) => {
          const f = e.features?.[0];
          if (f) pickRef.current?.(f.properties);
        });
        map.on("mouseenter", id, () => { map.getCanvas().style.cursor = "pointer"; });
        map.on("mouseleave", id, () => { map.getCanvas().style.cursor = ""; });
      }
      setReady(true);
      readyRef.current?.(true);
    });
    map.on("error", () => {}); // um bloco do mapa que falha (fonte fora do ar) não derruba o globo
    return () => {
      clearInterval(radarTimer.current);
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // abre girando e voa até a cidade
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !flyTo) return;
    const reduce = lite || window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    const c = map.getCenter();
    const target = { center: [flyTo.lon, flyTo.lat], zoom: flyTo.zoom ?? 5.2, essential: true };
    // só zoom (mesmo lugar): o flyTo no globo dá NaN com distância zero; aí é um easeTo
    if (Math.abs(c.lng - flyTo.lon) < 0.01 && Math.abs(c.lat - flyTo.lat) < 0.01) map.easeTo({ ...target, duration: reduce ? 0 : 1800 });
    else if (reduce) map.jumpTo(target);
    else map.flyTo({ ...target, speed: 0.7, curve: 1.5 });
  }, [ready, flyTo, lite]);

  // visão HUD (neon) ou satélite
  useEffect(() => {
    const map = mapRef.current;
    if (!ready) return;
    const sat = base === "sat";
    for (const id of HUD_LAYERS) map.setLayoutProperty(id, "visibility", sat ? "none" : "visible");
    for (const id of SAT_LAYERS) map.setLayoutProperty(id, "visibility", sat ? "visible" : "none");
  }, [ready, base]);

  // casa
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !home) return;
    homeMarker.current?.remove();
    homeMarker.current = new maplibregl.Marker({ element: marker("ge-home-pin", "<i></i><span>CASA</span>") }).setLngLat([home.lon, home.lat]).addTo(map);
  }, [ready, home]);

  // dados e visibilidade das camadas
  useEffect(() => {
    const map = mapRef.current;
    if (!ready) return;
    map.getSource("ge-quakes")?.setData(quakesGeo(data.terremotos));
    map.getSource("ge-fires")?.setData(firesGeo(data.queimadas));
    map.getSource("ge-flights")?.setData(flightsGeo(data.voos));
    map.getSource("ge-iss-track")?.setData(issTrack(data.iss));
    map.getSource("ge-launches")?.setData(launchesGeo(data.lancamentos));
    for (const [layer, ids] of Object.entries(LAYER_IDS)) {
      for (const id of ids) map.setLayoutProperty(id, "visibility", layersOn[layer] ? "visible" : "none");
    }
    const a = data.iss?.agora;
    issRef.current = a;
    if (layersOn.iss && a) {
      if (!issMarker.current) {
        const el = marker("ge-iss-pin", "<i></i><span>ISS</span>");
        el.addEventListener("click", (e) => {
          e.stopPropagation();
          const now = issRef.current;
          if (now) pickRef.current?.({ kind: "iss", alt_km: now.alt_km, vel_kmh: now.vel_kmh });
        });
        issMarker.current = new maplibregl.Marker({ element: el });
      }
      issMarker.current.setLngLat([a.lon, a.lat]).addTo(map);
    } else {
      issMarker.current?.remove();
    }
  }, [ready, data, layersOn]);

  // radar de chuva: os quadros das últimas 2 h passando em sequência
  useEffect(() => {
    const map = mapRef.current;
    if (!ready) return undefined;
    clearInterval(radarTimer.current);
    const style = map.getStyle();
    for (const l of style.layers.filter((x) => x.id.startsWith("ge-rv-"))) map.removeLayer(l.id);
    for (const id of Object.keys(style.sources).filter((x) => x.startsWith("ge-rv-"))) map.removeSource(id);
    const radar = data.chuva?.radar;
    if (!layersOn.chuva || !radar?.quadros?.length) return undefined;
    const frames = radar.quadros.slice(lite ? -6 : -12);
    frames.forEach((f, i) => {
      map.addSource(`ge-rv-${i}`, { type: "raster", tiles: [radarTiles(radar, f)], tileSize: 256, maxzoom: 7, attribution: "Radar © RainViewer" });
      map.addLayer({ id: `ge-rv-${i}`, type: "raster", source: `ge-rv-${i}`, paint: { "raster-opacity": i === frames.length - 1 ? 0.7 : 0, "raster-opacity-transition": { duration: 0 } } }, "ge-fires");
    });
    let k = frames.length - 1;
    if (!lite) {
      radarTimer.current = setInterval(() => {
        if (!mapRef.current) return;
        map.setPaintProperty(`ge-rv-${k}`, "raster-opacity", 0);
        k = (k + 1) % frames.length;
        map.setPaintProperty(`ge-rv-${k}`, "raster-opacity", 0.7);
      }, k === frames.length - 1 ? 900 : 600);
    }
    return () => clearInterval(radarTimer.current);
  }, [ready, data.chuva, layersOn.chuva, lite]);

  return <div ref={boxRef} className="ge-globe3d" aria-label="Globo 3D do Olho de Deus" role="application" />;
}

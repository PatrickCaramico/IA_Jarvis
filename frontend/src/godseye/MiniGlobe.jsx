import { useEffect, useRef } from "react";
import { EMPTY, fillWorld, hudStyle, loadWorld, maplibregl } from "./hudStyle.js";

// V7.13: o mapa das cenas do Holograma: o globo HUD do Olho de Deus voa de um lugar para o outro, com os
// marcadores e (se a cena pedir) a rota tracejada ligando os lugares na ordem.
export default function MiniGlobe({ lugares = [], rota = false, lite = false }) {
  const boxRef = useRef(null);

  useEffect(() => {
    if (!lugares.length) return undefined;
    let map;
    try {
      map = new maplibregl.Map({
        container: boxRef.current,
        style: hudStyle(
          { route: { type: "geojson", data: EMPTY } },
          [{ id: "route", type: "line", source: "route", paint: { "line-color": "#f472b6", "line-width": 2.5, "line-dasharray": [2, 1.5], "line-opacity": 0.9 } }],
        ),
        center: [lugares[0].lon - 60, lugares[0].lat * 0.3],
        zoom: 1.1,
        interactive: false,
        attributionControl: false,
      });
    } catch {
      return undefined;
    }
    const markers = [];
    const timers = [];
    map.on("load", () => {
      loadWorld(lite).then((w) => fillWorld(map, w)).catch(() => {});
      if (rota) {
        map.getSource("route")?.setData({ type: "Feature", geometry: { type: "LineString", coordinates: lugares.map((l) => [l.lon, l.lat]) }, properties: {} });
      }
      lugares.forEach((l, i) => {
        const el = document.createElement("div");
        el.className = "holo-pin";
        el.style.animationDelay = `${0.6 + i * 1.2}s`; // os filhos herdam (o próprio marcador é posicionado pelo mapa)
        el.innerHTML = `<i></i><span>${l.nome.replace(/[<>&"]/g, "")}</span>`;
        markers.push(new maplibregl.Marker({ element: el }).setLngLat([l.lon, l.lat]).addTo(map));
      });
      const zoom = lugares.length > 1 ? 2.6 : 4.2;
      const flyNext = (i) => {
        if (!lugares[i]) {
          if (lugares.length > 1) {
            const lons = lugares.map((l) => l.lon);
            const lats = lugares.map((l) => l.lat);
            map.fitBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]], { padding: 60, maxZoom: 5, duration: 1600 });
          }
          return;
        }
        map.flyTo({ center: [lugares[i].lon, lugares[i].lat], zoom, speed: 0.8, curve: 1.4, essential: true });
        timers.push(setTimeout(() => flyNext(i + 1), 2600));
      };
      timers.push(setTimeout(() => flyNext(0), 300));
    });
    map.on("error", () => {});
    return () => {
      timers.forEach(clearTimeout);
      markers.forEach((m) => m.remove());
      map.remove();
    };
  }, [lugares, rota, lite]);

  return <div ref={boxRef} className="holo-map" role="img" aria-label={`Mapa: ${lugares.map((l) => l.nome).join(", ")}`} />;
}

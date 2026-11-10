import { useEffect, useState } from "react";
import { startPolling } from "../hooks/usePolling.js";
import useNow from "../hooks/useNow.js";
import NowPlaying from "./NowPlaying.jsx";

// Cartões somente leitura da tela de bloqueio (seção 17.4). Nada pessoal antes do acesso:
// só relógio, clima, próximo jogo (Modo Torcedor) e água de hoje.
// allRight (V4.4): todos os cartões à direita, porque a esquerda fica com o painel do jogo (Modo Torcedor).
export default function LockCards({ api, cards = [], fanModeEnabled = false, hidden = false, allRight = false }) {
  const [weather, setWeather] = useState(null);
  const [match, setMatch] = useState(null);
  const [water, setWater] = useState(null);
  const want = (key) => cards.includes(key);

  const now = useNow(want("clock"));

  useEffect(() => {
    let active = true;
    const load = () => {
      if (want("weather")) api("/api/weather").then((d) => active && setWeather(d)).catch(() => active && setWeather(null));
      if (want("fan_match") && fanModeEnabled) api("/api/fan/match").then((d) => active && setMatch(d?.match || null)).catch(() => {});
      if (want("water")) api("/api/water").then((d) => active && setWater(d)).catch(() => {});
    };
    const stopPolling = startPolling(load, 10 * 60 * 1000);
    const onWs = (e) => { if (e.detail?.type === "water_updated" && e.detail.data) setWater(e.detail.data); };
    window.addEventListener("jarvis_ws_event", onWs);
    return () => { active = false; stopPolling(); window.removeEventListener("jarvis_ws_event", onWs); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cards.join(","), fanModeEnabled]);

  if (hidden || !cards.length) return null;
  const items = [];
  if (want("clock")) {
    items.push(
      <div className="lc-card" key="clock">
        <div className="lc-label">AGORA</div>
        <div className="lc-value lc-clock">{now.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</div>
        <div className="lc-sub">{now.toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" })}</div>
      </div>,
    );
  }
  if (want("weather") && weather) {
    items.push(
      <div className="lc-card" key="weather">
        <div className="lc-label">CLIMA · {String(weather.place || "").split(",")[0].toUpperCase()}</div>
        <div className="lc-value">{weather.temperature}°</div>
        <div className="lc-sub">{weather.description}{weather.rain_probability != null ? ` · chuva ${weather.rain_probability}%` : ""}</div>
      </div>,
    );
  }
  if (want("spotify")) {
    // V4.2.2: sem botões no bloqueio; o componente some se nada estiver tocando
    items.push(<NowPlaying key="spotify" api={api} variant="lock" />);
  }
  if (want("fan_match") && fanModeEnabled && match?.opponent) {
    const d = new Date(match.date);
    items.push(
      <div className="lc-card lc-fan" key="fan">
        <div className="lc-label">PRÓXIMO JOGO</div>
        <div className="lc-value lc-small">x {match.opponent}</div>
        <div className="lc-sub">
          {Number.isNaN(d.getTime()) ? "" : d.toLocaleString("pt-BR", { weekday: "short", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}
        </div>
      </div>,
    );
  }
  if (want("water") && water) {
    items.push(
      <div className="lc-card" key="water">
        <div className="lc-label">ÁGUA DE HOJE</div>
        <div className="lc-value lc-small">{water.total_ml} / {water.goal_ml} ml</div>
        <div className="lc-bar"><span style={{ width: `${Math.min(100, water.percentage || 0)}%` }} /></div>
      </div>,
    );
  }
  if (!items.length) return null;
  // Clima à direita do orbe; relógio, jogo e água à esquerda (em telas estreitas, tudo embaixo)
  const right = allRight ? items : items.filter((el) => el.key === "weather" || el.key === "spotify");
  const left = allRight ? [] : items.filter((el) => el.key !== "weather" && el.key !== "spotify");
  return (
    <div className="lc-wrap" aria-label="Informações da tela de bloqueio">
      {left.length > 0 && <div className="lc-row lc-left">{left}</div>}
      {right.length > 0 && <div className="lc-row lc-right">{right}</div>}
    </div>
  );
}

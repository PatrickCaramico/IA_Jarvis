// Demo da tela de bloqueio (só dev, ver lock-demo.html): confere o visual sem backend.
import React from "react";
import ReactDOM from "react-dom/client";
import LockScreen from "../components/LockScreen.jsx";
import FanGoalOverlay from "../components/FanGoalOverlay.jsx";
import NewProfileScreen from "../components/NewProfileScreen.jsx";
import ProfileWelcome from "../components/ProfileWelcome.jsx";
import AlarmOverlay from "../components/AlarmOverlay.jsx";
import "../profiles.css";
import "../accessibility.css";
import "../index.css";
import "../fan-mode.css";
import "../lock-extras.css";
import "../brand.css";
import "../feedback.css";
import "../blueprint.css";
import "../alarm.css";
import "../mobile.css"; // V5.7.1: a demo também mostra o layout do celular
import { applyFanMode, initialAccessibility } from "../utils/theme.js";

initialAccessibility();

const q = new URLSearchParams(window.location.search);
document.documentElement.dataset.bg = q.get("bg") === "classic" ? "classic" : "blueprint";
if (q.get("bg") === "space") document.documentElement.dataset.sky = "space"; // V5.8: ?bg=space
if (q.get("fan") === "1") applyFanMode(true);
const sentinelOn = q.get("mode") !== "classic";
const phase = q.get("phase") || "ready";
const offline = () => Promise.reject(new Error("demo"));
const fanOn = q.get("fan") === "1";
// ?state=live (padrão) | half | pre | done
const state = q.get("state") || (q.get("live") === "0" ? "pre" : "live");
const demoMatch = {
  id: "espn_demo", opponent: "Remo", competition: "Brasileirão", venue: "Allianz Parque",
  date: new Date(Date.now() + (state === "pre" ? 95 * 60000 : -40 * 60000)).toISOString(), time_known: true, home_away: "home",
  status: state === "pre" ? "scheduled" : state === "done" ? "finished" : "live",
  score: state === "pre" ? { home: 0, away: 0 } : { home: 3, away: 1 },
  minute: state === "half" ? "Intervalo" : state === "done" ? "Fim" : "67'",
  is_match_day: true, countdown: "Em 1h 35min", seconds_until_match: 5700, sources: ["espn", "google_news"],
  logos: { ours: "https://a.espncdn.com/i/teamlogos/soccer/500/2029.png", theirs: "https://a.espncdn.com/i/teamlogos/soccer/500/4936.png" },
  details: state === "pre" ? { events: [], stats: null, standing: { rank: 2, points: 70, played: 33, table: "Brasileirão" } } : {
    events: [
      { kind: "goal", minute: "4'", side: "ours", player: "Jhon Arias", assist: "Vitor Roque" },
      { kind: "goal", minute: "14'", side: "ours", player: "Jhon Arias", assist: "Khellven" },
      { kind: "goal", minute: "21'", side: "ours", player: "Maurício", assist: "Marlon Freitas" },
      { kind: "goal", minute: "52'", side: "theirs", player: "Atacante do Remo" },
    ],
    stats: { ours: { possession: 58, shots: 12, on_target: 6, corners: 5 }, theirs: { possession: 42, shots: 6, on_target: 2, corners: 3 } },
    standing: { rank: 2, points: 70, played: 33, table: "Brasileirão" },
  },
};
const upcoming = [
  { id: "u1", opponent: "Vasco", competition: "Copa do Brasil", date_human: "08/11 (dom) às 17:00", home_away: "away" },
  { id: "u2", opponent: "Cruzeiro", competition: "Brasileirão", date_human: "18/11 (qua) às 20:30", home_away: "away" },
];
const demoInfo = (path) => path === "/api/mobile/info"
  ? Promise.resolve({ available: true, network_mode: true, download_url: "http://192.168.0.10:8000/api/mobile", version: "4.5" })
  : path === "/api/profiles/lock-info"
    ? Promise.resolve({ count: 1, can_create: true, owner_pin_required: q.get("pin") !== "0" })
    : null;
const fanApi = (path) => demoInfo(path) || (path === "/api/fan/match"
  ? Promise.resolve({ match: demoMatch, team: { name: "Palmeiras" }, upcoming })
  : path === "/api/weather"
    ? Promise.resolve({ place: "São Paulo", temperature: 24, description: "Garoa leve", rain_probability: 96 })
    : offline());
// V5.6.1: cartão SISTEMAS e clima também na demo
const lockExtras = (path) => (path === "/api/health"
  ? Promise.resolve({ boot_id: String(Date.now() - 134 * 60000), services: { ai: true, microphone: true, camera: true, internet: true } })
  : path === "/api/lock/status"
    ? Promise.resolve({ devices: 2, phones: 1, next_alarm: "amanhã às 07:00" })
    : path === "/api/weather"
      ? Promise.resolve({ place: "São Paulo", temperature: 19, description: "Tempo parcialmente nublado", rain_probability: 67, humidity: 89, wind: 11, sunrise: "05:15", sunset: "18:26", apparent_temperature: 18, minimum: 16, maximum: 24, tomorrow: { minimum: 17, maximum: 27, description: "Céu limpo", rain_probability: 10 } })
      : path === "/api/lock/public-info"
        ? Promise.resolve({
          rates: [
            { pair: "USDBRL", code: "USD", bid: 5.583, pctChange: 0.18 },
            { pair: "EURBRL", code: "EUR", bid: 6.1806, pctChange: -0.21 },
            { pair: "BTCBRL", code: "BTC", bid: 413502, pctChange: 0.46 },
          ],
          headline: { title: "Governo anuncia novo pacote de investimentos em infraestrutura para 2027", source: "g1", category: "brasil",
            more: [{ title: "Chuvas devem continuar no Sudeste até o fim de semana", source: "CNN Brasil" }, { title: "Inflação desacelera pelo terceiro mês seguido", source: "Valor" }] },
        })
      : path === "/api/integrations/spotify/track"
        ? Promise.resolve(q.get("music") === "1"
          ? { state: "playing", title: "Back in Black", artist: "AC/DC", duration_ms: 255000, progress_ms: 61000 }
          : { state: "off" })
        : null);
const baseApi = (path) => demoInfo(path) || lockExtras(path) || offline();

function Demo() {
  const [fan, setFan] = React.useState(fanOn);
  // ?app=1: como aparece dentro do app do celular (botão ATUALIZAR APP)
  const phoneApp = q.get("app") === "1";
  const [note, setNote] = React.useState("");
  const [bgVal, setBgVal] = React.useState(q.get("bg") === "space" ? "space" : q.get("bg") === "classic" ? "classic" : "blueprint");
  const toggle = () => setFan((v) => { applyFanMode(!v); return !v; });
  if (q.get("screen") === "newprofile") return <NewProfileScreen api={baseApi} onCancel={() => {}} onCreated={() => {}} />;
  if (q.get("screen") === "welcome") return <ProfileWelcome api={baseApi} name="Maria" onDone={() => {}} />;
  return (
  <>
  {q.has("alarme") && (
    <AlarmOverlay alarm={{ hora: "07:00", rotulo: q.get("alarme") || "", snooze_minutes: 9 }} onStop={() => {}} onSnooze={() => {}} />
  )}
  {q.get("goal") && <FanGoalOverlay event={{ kind: q.get("goal"), match: demoMatch }} onDone={() => {}} />}
  <LockScreen
    phase={phase}
    name="Patrick"
    jarvisState="idle"
    onContinue={() => {}}
    onChangePhoto={() => {}}
    silent
    fanToggle={{ enabled: fan, busy: false, onToggle: toggle }}
    bgToggle={{ value: bgVal, onCycle: () => {
      const order = ["blueprint", "space", "classic"];
      const next = order[(order.indexOf(bgVal) + 1) % order.length];
      document.documentElement.dataset.bg = next === "classic" ? "classic" : "blueprint";
      if (next === "space") document.documentElement.dataset.sky = "space"; else delete document.documentElement.dataset.sky;
      setBgVal(next);
    } }}
    onNewProfile={() => {}}
    onUpdate={() => { setNote("Procurando atualização no PC…"); setTimeout(() => setNote("O app já está na versão mais nova (5.7.1)."), 900); }}
    updateNote={note}
    phoneApp={phoneApp}
    cards={{ api: fan ? fanApi : baseApi, list: fan ? ["clock", "weather"] : ["clock", "weather", "spotify"], fanModeEnabled: fan }}
    mic={sentinelOn ? null : { muted: true, onToggle: () => {} }}
    sentinel={sentinelOn ? {
      enabled: true,
      state: q.get("st") || "sleeping",
      showClock: true,
      nightDim: false,
      micStatus: "off",
      muted: true,
      onToggleMute: () => {},
    } : null}
  />
  </>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<Demo />);

// Demo da tela de bloqueio (só dev, ver lock-demo.html): confere o visual sem backend.
import React from "react";
import ReactDOM from "react-dom/client";
import LockScreen from "../components/LockScreen.jsx";
import FanGoalOverlay from "../components/FanGoalOverlay.jsx";
import NewProfileScreen from "../components/NewProfileScreen.jsx";
import ProfileWelcome from "../components/ProfileWelcome.jsx";
import "../profiles.css";
import "../accessibility.css";
import "../index.css";
import "../fan-mode.css";
import "../lock-extras.css";
import "../brand.css";
import "../feedback.css";
import "../blueprint.css";
import { applyFanMode, initialAccessibility } from "../utils/theme.js";

initialAccessibility();

const q = new URLSearchParams(window.location.search);
document.documentElement.dataset.bg = q.get("bg") === "classic" ? "classic" : "blueprint";
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
const baseApi = (path) => demoInfo(path) || offline();

function Demo() {
  const [fan, setFan] = React.useState(fanOn);
  const toggle = () => setFan((v) => { applyFanMode(!v); return !v; });
  if (q.get("screen") === "newprofile") return <NewProfileScreen api={baseApi} onCancel={() => {}} onCreated={() => {}} />;
  if (q.get("screen") === "welcome") return <ProfileWelcome api={baseApi} name="Maria" onDone={() => {}} />;
  return (
  <>
  {q.get("goal") && <FanGoalOverlay event={{ kind: q.get("goal"), match: demoMatch }} onDone={() => {}} />}
  <LockScreen
    phase={phase}
    name="Patrick"
    jarvisState="idle"
    onContinue={() => {}}
    onChangePhoto={() => {}}
    silent
    fanToggle={{ enabled: fan, busy: false, onToggle: toggle }}
    onNewProfile={() => {}}
    onUpdate={() => {}}
    cards={{ api: fan ? fanApi : baseApi, list: fan ? ["clock", "weather"] : [], fanModeEnabled: fan }}
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

import { useEffect, useState } from "react";
import { startPolling } from "../hooks/usePolling.js";
import useNow from "../hooks/useNow.js";
import NowPlaying, { useNowPlaying } from "./NowPlaying.jsx";
import LockDetail from "./LockDetail.jsx";

// Cartões somente leitura da tela de bloqueio (seção 17.4). Nada pessoal antes do acesso:
// só relógio, clima, próximo jogo (Modo Torcedor) e água de hoje.
// allRight (V4.4): todos os cartões à direita, porque a esquerda fica com o painel do jogo (Modo Torcedor).
export default function LockCards({ api, cards = [], fanModeEnabled = false, hidden = false, allRight = false }) {
  const [weather, setWeather] = useState(null);
  const [match, setMatch] = useState(null);
  const [water, setWater] = useState(null);
  // V5.6.1: cartão SISTEMAS do lado esquerdo (serviços, tempo no ar, celular, próximo alarme). Nada pessoal.
  const [health, setHealth] = useState(null);
  const [status, setStatus] = useState(null);
  // V5.8: lado direito: cotações (em cima do clima) e a manchete do momento (embaixo). Informação pública.
  const [info, setInfo] = useState(null);
  // V5.9: cartão tocado -> mini janela com mais detalhes (LockDetail)
  const [detail, setDetail] = useState(null);
  const want = (key) => cards.includes(key);

  const now = useNow(want("clock"));

  useEffect(() => {
    let active = true;
    const load = () => {
      api("/api/weather").then((d) => active && setWeather(d)).catch(() => active && setWeather(null));
      if (want("fan_match") && fanModeEnabled) api("/api/fan/match").then((d) => active && setMatch(d?.match || null)).catch(() => {});
      if (want("water")) api("/api/water").then((d) => active && setWater(d)).catch(() => {});
    };
    const stopPolling = startPolling(load, 10 * 60 * 1000);
    const loadStatus = () => {
      api("/api/health").then((d) => active && setHealth(d)).catch(() => active && setHealth(null));
      api("/api/lock/status").then((d) => active && setStatus(d)).catch(() => {});
    };
    const stopStatus = startPolling(loadStatus, 60 * 1000);
    const stopInfo = startPolling(() => api("/api/lock/public-info").then((d) => active && setInfo(d)).catch(() => {}), 10 * 60 * 1000);
    const onWs = (e) => {
      if (e.detail?.type === "water_updated" && e.detail.data) setWater(e.detail.data);
      if (e.detail?.type === "devices") api("/api/lock/status").then((d) => active && setStatus(d)).catch(() => {});
    };
    window.addEventListener("jarvis_ws_event", onWs);
    return () => { active = false; stopPolling(); stopStatus(); stopInfo(); window.removeEventListener("jarvis_ws_event", onWs); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cards.join(","), fanModeEnabled]);

  if (hidden) return null;
  const items = [];
  if (!allRight && health) {
    const svc = health.services || {};
    const dots = [["ia", "IA", svc.ai], ["mic", "MIC", svc.microphone], ["cam", "CÂMERA", svc.camera], ["net", "INTERNET", svc.internet]];
    const bootMs = Number(health.boot_id);
    const upMin = Number.isFinite(bootMs) && bootMs > 1e12 ? Math.max(0, Math.floor((Date.now() - bootMs) / 60000)) : null;
    const up = upMin == null ? "" : upMin < 60 ? `${upMin} min` : `${Math.floor(upMin / 60)}h ${String(upMin % 60).padStart(2, "0")}min`;
    items.push(
      <div className="lc-card lc-status" key="status">
        <div className="lc-label">SISTEMAS · J.A.R.V.I.S.</div>
        <div className="lc-status-dots">
          {dots.map(([k, label, on]) => (
            <span key={k} className={on ? "on" : "off"} title={`${label}: ${on ? "online" : "offline"}`}><i aria-hidden="true" />{label}</span>
          ))}
        </div>
        <ul className="lc-status-list">
          {up && <li><b>◉</b>No ar há {up}</li>}
          <li><b>📱</b>{status?.phones ? `Celular conectado${status.phones > 1 ? ` (${status.phones})` : ""}` : "Nenhum celular conectado"}</li>
          {status?.next_alarm && <li><b>◷</b>Alarme {status.next_alarm}</li>}
        </ul>
        <div className="lc-status-scan" aria-hidden="true" />
      </div>,
    );
  }
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
    // V5.6.3: à esquerda, embaixo do SISTEMAS. Tocando: a faixa; parado ou desconectado: o estado (não some)
    items.push(<LockSpotify key="spotify" api={api} />);
  }
  if (!allRight && weather?.sunrise) {
    items.push(<TodayCard key="today" weather={weather} />);
  }
  if (info?.rates?.length) items.push(<RatesCard key="rates" rates={info.rates} />);
  if (info?.headline?.title) items.push(<HeadlineCard key="headline" item={info.headline} />);
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
  // Clima à direita do orbe; à esquerda, de cima para baixo: SISTEMAS, Spotify, HOJE, relógio, jogo e água
  // (em telas estreitas, tudo embaixo)
  const LEFT_ORDER = ["status", "spotify", "today", "clock", "fan", "water"];
  // direita, de cima para baixo: cotações, clima, manchete
  const RIGHT = ["rates", "weather", "headline"];
  const right = allRight ? items : items.filter((el) => RIGHT.includes(el.key))
    .sort((a, b) => RIGHT.indexOf(a.key) - RIGHT.indexOf(b.key));
  const left = allRight ? [] : items.filter((el) => !RIGHT.includes(el.key))
    .sort((a, b) => LEFT_ORDER.indexOf(a.key) - LEFT_ORDER.indexOf(b.key));
  // V5.9: cada cartão abre a mini janela de detalhes (toque, clique, Enter ou espaço com o foco nele)
  const NAMES = { status: "sistemas", spotify: "Spotify", today: "hoje", clock: "agora", weather: "clima", fan: "próximo jogo", water: "água", rates: "mercado", headline: "manchetes" };
  const clickable = (el) => (
    <div
      key={el.key}
      className="lc-click"
      role="button"
      tabIndex={0}
      aria-label={`Ver detalhes: ${NAMES[el.key] || el.key}`}
      onClick={(e) => { e.stopPropagation(); setDetail(el.key); }}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); e.stopPropagation(); setDetail(el.key); }
      }}
    >
      {el}
    </div>
  );
  return (
    <div className="lc-wrap" aria-label="Informações da tela de bloqueio">
      {left.length > 0 && <div className="lc-row lc-left">{left.map(clickable)}</div>}
      {right.length > 0 && <div className="lc-row lc-right">{right.map(clickable)}</div>}
      {detail && (
        <LockDetail kind={detail} api={api} data={{ health, status, weather, info, water, match }} onClose={() => setDetail(null)} />
      )}
    </div>
  );
}

// V5.6.3: Spotify no bloqueio. Tocando ou pausado: o cartão "Tocando agora"; senão, o estado da conexão.
function LockSpotify({ api }) {
  const { track } = useNowPlaying(api);
  if (track && (track.state === "playing" || track.state === "paused")) return <NowPlaying api={api} variant="lock" />;
  const off = !track || track.state === "off" || track.state === "error";
  return (
    <div className={`lc-card lc-spotify${off ? " is-off" : ""}`}>
      <div className="lc-label">SPOTIFY</div>
      <div className="lc-spotify-row">
        <span className="lc-spotify-logo" aria-hidden="true">♫</span>
        <div>
          <div className="lc-value lc-small">{off ? "Não conectado" : "Conectado"}</div>
          <div className="lc-sub lc-nocap">{off ? "Conecte em TELAS › Fontes de Dados" : "Nada tocando agora"}</div>
        </div>
      </div>
    </div>
  );
}

// V5.6.3: cartão HOJE: nascer e pôr do sol, umidade, vento, quanto do dia já passou e a semana do ano.
function weekOfYear(d) {
  const t = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const day = t.getUTCDay() || 7;
  t.setUTCDate(t.getUTCDate() + 4 - day);
  const start = new Date(Date.UTC(t.getUTCFullYear(), 0, 1));
  return Math.ceil(((t - start) / 86400000 + 1) / 7);
}

function TodayCard({ weather }) {
  const now = useNow(true);
  const minutes = now.getHours() * 60 + now.getMinutes();
  const dayPct = Math.round((minutes / 1440) * 100);
  const toMin = (hm) => { const [h, m] = String(hm || "").split(":").map(Number); return h * 60 + m; };
  const sunUp = toMin(weather.sunrise);
  const sunDown = toMin(weather.sunset);
  const isDay = minutes >= sunUp && minutes < sunDown;
  const sunLeft = isDay ? sunDown - minutes : null;
  return (
    <div className="lc-card lc-today">
      <div className="lc-label">HOJE · SEMANA {weekOfYear(now)}</div>
      <div className="lc-today-sun">
        <span><b>☀</b>{weather.sunrise}<small>nascer</small></span>
        <span><b>☾</b>{weather.sunset}<small>pôr do sol</small></span>
      </div>
      <dl className="lc-today-grid">
        {weather.humidity != null && <div><dt>Umidade</dt><dd>{Math.round(weather.humidity)}%</dd></div>}
        {weather.wind != null && <div><dt>Vento</dt><dd>{Math.round(weather.wind)} km/h</dd></div>}
        {sunLeft != null && <div><dt>Luz do dia</dt><dd>{Math.floor(sunLeft / 60)}h{String(sunLeft % 60).padStart(2, "0")}</dd></div>}
      </dl>
      <div className="lc-bar" title={`${dayPct}% do dia`}><span style={{ width: `${dayPct}%` }} /></div>
      <div className="lc-sub lc-nocap">{dayPct}% do dia já passou</div>
    </div>
  );
}

// V5.8: cotações do dia (dólar, euro, bitcoin), com a variação em verde/vermelho
const RATE_LABEL = { USD: "Dólar", EUR: "Euro", BTC: "Bitcoin" };
function money(v, code) {
  const digits = code === "BTC" ? 0 : 2;
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: digits, maximumFractionDigits: digits });
}
function RatesCard({ rates }) {
  return (
    <div className="lc-card lc-rates">
      <div className="lc-label">MERCADO · AGORA</div>
      <ul className="lc-rates-list">
        {rates.map((r) => {
          const up = r.pctChange >= 0;
          return (
            <li key={r.pair}>
              <span className="lc-rate-name">{RATE_LABEL[r.code] || r.code}</span>
              <b>{money(r.bid, r.code)}</b>
              <em className={up ? "up" : "down"}>{up ? "▲" : "▼"} {Math.abs(r.pctChange).toFixed(2).replace(".", ",")}%</em>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

// V5.8: a manchete do momento (Google Notícias), com a fonte
function HeadlineCard({ item }) {
  return (
    <div className="lc-card lc-headline">
      <div className="lc-label">MANCHETE · {item.category === "mundo" ? "MUNDO" : "BRASIL"}</div>
      <p className="lc-headline-title">{item.title}</p>
      {item.source && <div className="lc-sub lc-nocap">{item.source}</div>}
    </div>
  );
}

import { useEffect } from "react";
import { createPortal } from "react-dom";
import { useNowPlaying } from "./NowPlaying.jsx";

// V5.9: mini janela de detalhes dos cartões da tela de bloqueio. Abre ao tocar no cartão; fecha no ✕,
// no Esc ou tocando fora. Só mostra o que o cartão já pode mostrar com a central bloqueada (nada pessoal).

const pad = (n) => String(n).padStart(2, "0");
const toMin = (hm) => {
  const [h, m] = String(hm || "").split(":").map(Number);
  return Number.isFinite(h) && Number.isFinite(m) ? h * 60 + m : null;
};
const hmFrom = (min) => `${Math.floor(min / 60)}h${pad(min % 60)}`;

function Row({ label, value, tone }) {
  if (value == null || value === "") return null;
  return (
    <div className="ld-row">
      <dt>{label}</dt>
      <dd className={tone ? `is-${tone}` : ""}>{value}</dd>
    </div>
  );
}

function SystemsDetail({ health, status }) {
  const svc = health?.services || {};
  const list = [["ai", "Inteligência artificial"], ["microphone", "Microfone"], ["camera", "Câmera"], ["internet", "Internet"], ["backend", "Servidor do PC"]];
  const bootMs = Number(health?.boot_id);
  const upMin = Number.isFinite(bootMs) && bootMs > 1e12 ? Math.floor((Date.now() - bootMs) / 60000) : null;
  return (
    <>
      <ul className="ld-services">
        {list.map(([k, label]) => {
          const on = k === "backend" ? Boolean(health) : svc[k] === true;
          return (
            <li key={k} className={on ? "on" : "off"}>
              <i aria-hidden="true" />
              <span>{label}</span>
              <b>{on ? "ONLINE" : "OFFLINE"}</b>
            </li>
          );
        })}
      </ul>
      <dl className="ld-grid">
        <Row label="No ar há" value={upMin == null ? null : upMin < 60 ? `${upMin} min` : hmFrom(upMin)} />
        <Row label="Versão" value={health?.version ? `v${health.version}` : null} />
        <Row label="Aparelhos conectados" value={status ? String(status.devices ?? 0) : null} />
        <Row label="Celulares" value={status ? (status.phones ? String(status.phones) : "nenhum") : null} />
        <Row label="Próximo alarme" value={status?.next_alarm || "nenhum"} />
        <Row label="Modelo de IA" value={health?.provider ? String(health.provider).toUpperCase() : null} />
      </dl>
    </>
  );
}

function SpotifyDetail({ api }) {
  const { track, progress } = useNowPlaying(api);
  const fmt = (ms) => { const s = Math.max(0, Math.floor((ms || 0) / 1000)); return `${Math.floor(s / 60)}:${pad(s % 60)}`; };
  if (track && (track.state === "playing" || track.state === "paused")) {
    const pct = track.duration_ms ? Math.min(100, (progress / track.duration_ms) * 100) : 0;
    return (
      <div className="ld-spotify">
        {track.image ? <img src={track.image} alt="" className="ld-cover" /> : <span className="ld-cover ld-cover-empty">♪</span>}
        <strong>{track.title}</strong>
        <span>{track.artist}</span>
        {track.album && <small>{track.album}</small>}
        <div className="lc-bar"><span style={{ width: `${pct}%` }} /></div>
        <div className="ld-times"><span>{fmt(progress)}</span><span>{track.state === "playing" ? "TOCANDO" : "PAUSADO"}</span><span>{fmt(track.duration_ms)}</span></div>
      </div>
    );
  }
  const off = !track || track.state === "off" || track.state === "error";
  return off ? (
    <ol className="ld-steps">
      <li>Desbloqueie a central e abra <b>TELAS › Fontes de Dados</b>.</li>
      <li>No cartão do <b>Spotify</b>, toque em <b>CONECTAR</b> e entre com a sua conta.</li>
      <li>Toque uma música no celular ou no PC: ela aparece aqui, com capa e tempo.</li>
    </ol>
  ) : (
    <p className="ld-text">O Spotify está conectado, mas nada está tocando agora. Peça "Jarvis, toca minha playlist" depois de desbloquear.</p>
  );
}

function TodayDetail({ weather }) {
  const now = new Date();
  const minutes = now.getHours() * 60 + now.getMinutes();
  const up = toMin(weather?.sunrise);
  const down = toMin(weather?.sunset);
  const dayLen = up != null && down != null ? down - up : null;
  const light = up != null && down != null && minutes >= up && minutes < down ? down - minutes : null;
  const start = new Date(now.getFullYear(), 0, 1);
  const dayOfYear = Math.floor((now - start) / 86400000) + 1;
  const daysInYear = new Date(now.getFullYear(), 1, 29).getDate() === 29 ? 366 : 365;
  return (
    <dl className="ld-grid">
      <Row label="Nascer do sol" value={weather?.sunrise} />
      <Row label="Pôr do sol" value={weather?.sunset} />
      <Row label="Duração do dia" value={dayLen != null ? hmFrom(dayLen) : null} />
      <Row label="Luz do dia restante" value={light != null ? hmFrom(light) : "o sol já se pôs"} />
      <Row label="Umidade" value={weather?.humidity != null ? `${Math.round(weather.humidity)}%` : null} />
      <Row label="Vento" value={weather?.wind != null ? `${Math.round(weather.wind)} km/h` : null} />
      <Row label="Dia do ano" value={`${dayOfYear} de ${daysInYear}`} />
      <Row label="Ano já passou" value={`${Math.round((dayOfYear / daysInYear) * 100)}%`} />
    </dl>
  );
}

function WeatherDetail({ weather }) {
  const t = weather?.tomorrow;
  return (
    <>
      <div className="ld-hero">
        <strong>{weather?.temperature}°</strong>
        <span>{weather?.description}</span>
      </div>
      <dl className="ld-grid">
        <Row label="Sensação" value={weather?.apparent_temperature != null ? `${weather.apparent_temperature}°` : null} />
        <Row label="Mínima / máxima" value={weather?.minimum != null ? `${weather.minimum}° / ${weather.maximum}°` : null} />
        <Row label="Chance de chuva" value={weather?.rain_probability != null ? `${weather.rain_probability}%` : null} tone={weather?.rain_probability >= 60 ? "warn" : null} />
        <Row label="Umidade" value={weather?.humidity != null ? `${Math.round(weather.humidity)}%` : null} />
        <Row label="Vento" value={weather?.wind != null ? `${Math.round(weather.wind)} km/h` : null} />
      </dl>
      {t && (
        <div className="ld-sub">
          <span className="ld-sub-label">AMANHÃ</span>
          <p>{t.description} · {t.minimum}° a {t.maximum}°{t.rain_probability != null ? ` · chuva ${t.rain_probability}%` : ""}</p>
        </div>
      )}
    </>
  );
}

const RATE_LABEL = { USD: "Dólar americano", EUR: "Euro", BTC: "Bitcoin" };
function money(v, code) {
  const digits = code === "BTC" ? 0 : 3;
  return Number(v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: digits, maximumFractionDigits: digits });
}
function RatesDetail({ rates = [] }) {
  return (
    <div className="ld-rates">
      {rates.map((r) => {
        const upDay = r.pctChange >= 0;
        return (
          <section key={r.pair}>
            <header><span>{RATE_LABEL[r.code] || r.code}</span><em className={upDay ? "is-up" : "is-down"}>{upDay ? "▲" : "▼"} {Math.abs(r.pctChange).toFixed(2).replace(".", ",")}%</em></header>
            <strong>{money(r.bid, r.code)}</strong>
            <dl className="ld-grid ld-grid-2">
              <Row label="Máxima do dia" value={r.high ? money(r.high, r.code) : null} />
              <Row label="Mínima do dia" value={r.low ? money(r.low, r.code) : null} />
            </dl>
          </section>
        );
      })}
      <p className="ld-foot">Cotação de compra em reais · AwesomeAPI · atualiza a cada 10 min</p>
    </div>
  );
}

function HeadlineDetail({ item }) {
  return (
    <div className="ld-news">
      <p className="ld-news-main">{item?.title}</p>
      {item?.source && <span className="ld-news-src">{item.source}</span>}
      {item?.more?.length > 0 && (
        <>
          <span className="ld-sub-label">MAIS MANCHETES</span>
          <ul>
            {item.more.map((m) => (
              <li key={m.title}><p>{m.title}</p>{m.source && <span>{m.source}</span>}</li>
            ))}
          </ul>
        </>
      )}
      <p className="ld-foot">Google Notícias · peça "Jarvis, notícias" depois de desbloquear para ouvir o resumo</p>
    </div>
  );
}

function WaterDetail({ water }) {
  return (
    <dl className="ld-grid">
      <Row label="Hoje" value={water ? `${water.total_ml} ml` : null} />
      <Row label="Meta" value={water ? `${water.goal_ml} ml` : null} />
      <Row label="Falta" value={water ? `${Math.max(0, water.goal_ml - water.total_ml)} ml` : null} />
      <Row label="Progresso" value={water ? `${Math.min(100, water.percentage || 0)}%` : null} tone={water?.goal_reached ? "ok" : null} />
    </dl>
  );
}

function MatchDetail({ match }) {
  const d = new Date(match?.date);
  return (
    <dl className="ld-grid">
      <Row label="Adversário" value={match?.opponent} />
      <Row label="Quando" value={Number.isNaN(d.getTime()) ? null : d.toLocaleString("pt-BR", { weekday: "long", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })} />
      <Row label="Competição" value={match?.competition} />
      <Row label="Local" value={match?.venue} />
      <Row label="Falta" value={match?.countdown} />
    </dl>
  );
}

const TITLES = {
  status: "SISTEMAS · J.A.R.V.I.S.",
  spotify: "SPOTIFY",
  today: "HOJE",
  weather: "CLIMA",
  rates: "MERCADO · AGORA",
  headline: "MANCHETES",
  water: "ÁGUA DE HOJE",
  fan: "PRÓXIMO JOGO",
  clock: "AGORA",
};

export default function LockDetail({ kind, api, data = {}, onClose }) {
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape") { e.stopPropagation(); onClose(); }
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [onClose]);
  if (!kind) return null;

  let body = null;
  if (kind === "status") body = <SystemsDetail health={data.health} status={data.status} />;
  else if (kind === "spotify") body = <SpotifyDetail api={api} />;
  else if (kind === "today") body = <TodayDetail weather={data.weather} />;
  else if (kind === "weather") body = <WeatherDetail weather={data.weather} />;
  else if (kind === "rates") body = <RatesDetail rates={data.info?.rates} />;
  else if (kind === "headline") body = <HeadlineDetail item={data.info?.headline} />;
  else if (kind === "water") body = <WaterDetail water={data.water} />;
  else if (kind === "fan") body = <MatchDetail match={data.match} />;
  else if (kind === "clock") {
    const now = new Date();
    body = <p className="ld-text">{now.toLocaleString("pt-BR", { weekday: "long", day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" })}</p>;
  }
  const place = kind === "weather" && data.weather?.place ? ` · ${String(data.weather.place).split(",")[0].toUpperCase()}` : "";

  // Portal no <body>; os cliques não sobem para a tela de bloqueio (não disparam a verificação)
  return createPortal(
    <div
      className="ld-overlay"
      role="dialog"
      aria-modal="true"
      aria-label={TITLES[kind]}
      onClick={(e) => { e.stopPropagation(); if (e.target === e.currentTarget) onClose(); }}
      onKeyDown={(e) => e.stopPropagation()}
    >
      <section className={`ld-card ld-${kind}`}>
        <header className="ld-head">
          <span className="lc-label">{TITLES[kind]}{place}</span>
          <button type="button" className="ld-x" onClick={onClose} aria-label="Fechar" autoFocus>✕</button>
        </header>
        {body}
      </section>
    </div>,
    document.body,
  );
}

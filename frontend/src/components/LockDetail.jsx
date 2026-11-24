import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useNowPlaying } from "./NowPlaying.jsx";
import WeatherScene from "./WeatherScene.jsx";
import { CLOSE_MS, OPEN_MS, arcPoint, flipFrom, rangePos, sunProgress } from "../utils/lockDetail.js";

// V5.9: mini janela de detalhes dos cartões da tela de bloqueio. Abre ao tocar no cartão; fecha no ✕,
// no Esc ou tocando fora. Só mostra o que o cartão já pode mostrar com a central bloqueada (nada pessoal).
// V9.4.5: janela maior que "expande" do cartão tocado (e volta para ele ao fechar), cada uma com a sua
// animação (clima ao vivo, o sol no arco do dia, o copo enchendo, a faixa do dia nas cotações, o equalizador
// do Spotify) e as linhas entrando em cascata. Tudo com transform/opacity; com "reduzir movimento", fica parado.

const pad = (n) => String(n).padStart(2, "0");
const toMin = (hm) => {
  const [h, m] = String(hm || "").split(":").map(Number);
  return Number.isFinite(h) && Number.isFinite(m) ? h * 60 + m : null;
};
const hmFrom = (min) => `${Math.floor(min / 60)}h${pad(min % 60)}`;

function Row({ label, value, tone }) {
  if (value == null || value === "") return null;
  return (
    <div className="ld-row ld-in">
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
  const online = list.filter(([k]) => (k === "backend" ? Boolean(health) : svc[k] === true)).length;
  return (
    <>
      <div className="ld-hero2 ld-sys-hero">
        <span className={`ld-sys-ring${online === list.length ? " is-ok" : ""}`} aria-hidden="true"><i /><i /></span>
        <div>
          <strong>{online}/{list.length}</strong>
          <span>{online === list.length ? "Tudo funcionando" : "Algum serviço precisa de atenção"}</span>
        </div>
      </div>
      <ul className="ld-services">
        {list.map(([k, label]) => {
          const on = k === "backend" ? Boolean(health) : svc[k] === true;
          return (
            <li key={k} className={`ld-in ${on ? "on" : "off"}`}>
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
        <div className={`ld-cover-wrap${track.state === "playing" ? " is-playing" : ""}`}>
          {track.image ? <img src={track.image} alt="" className="ld-cover" /> : <span className="ld-cover ld-cover-empty">♪</span>}
          <span className="ld-eq" aria-hidden="true"><i /><i /><i /><i /><i /></span>
        </div>
        <strong>{track.title}</strong>
        <span>{track.artist}</span>
        {track.album && <small>{track.album}</small>}
        <div className="ld-track"><span style={{ transform: `scaleX(${pct / 100})` }} /></div>
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
  const sun = sunProgress(now, weather?.sunrise, weather?.sunset);
  const pt = sun ? arcPoint(sun.frac) : null;
  return (
    <>
    {sun && (
      <div className={`ld-hero2 ld-sunarc${sun.up ? "" : " is-night"}`}>
        <div className="ld-arc-box">
          <svg viewBox="0 0 240 90" aria-hidden="true">
            <path d="M12 90 A108 78 0 0 1 228 90" className="ld-arc-bg" />
            <path d="M12 90 A108 78 0 0 1 228 90" className="ld-arc-fg" pathLength="1" style={{ strokeDasharray: `${sun.frac} 1` }} />
            <line x1="0" y1="90" x2="240" y2="90" className="ld-arc-ground" />
          </svg>
          <span className="ld-sun-dot" style={{ left: `${(pt.x / 240) * 100}%`, top: `${(pt.y / 90) * 100}%` }} aria-hidden="true" />
        </div>
        <div className="ld-arc-labels"><span>☀ {weather.sunrise}</span><b>{sun.up ? `${Math.round(sun.frac * 100)}% do dia` : "noite"}</b><span>☾ {weather.sunset}</span></div>
      </div>
    )}
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
    </>
  );
}

function WeatherDetail({ weather }) {
  const t = weather?.tomorrow;
  return (
    <>
      <div className="ld-hero2 ld-wx-hero">
        <div className="ld-wx-scene"><WeatherScene weather={weather} /></div>
        <div className="ld-wx-temp">
          <strong>{weather?.temperature}°</strong>
          <span>{weather?.description}</span>
        </div>
      </div>
      {weather?.minimum != null && weather?.maximum != null && (
        <div className="ld-range ld-in" aria-label={`Agora ${weather.temperature} graus, entre ${weather.minimum} e ${weather.maximum}`}>
          <span>{weather.minimum}°</span>
          <div className="ld-range-bar"><i style={{ left: `${rangePos(weather.temperature, weather.minimum, weather.maximum) * 100}%` }} /></div>
          <span>{weather.maximum}°</span>
        </div>
      )}
      {weather?.rain_probability != null && (
        <div className="ld-meter ld-in">
          <span>Chance de chuva</span>
          <div className="ld-meter-bar"><span className={weather.rain_probability >= 60 ? "is-warn" : ""} style={{ transform: `scaleX(${Math.min(100, weather.rain_probability) / 100})` }} /></div>
          <b className={weather.rain_probability >= 60 ? "is-warn" : ""}>{weather.rain_probability}%</b>
        </div>
      )}
      <dl className="ld-grid">
        <Row label="Sensação" value={weather?.apparent_temperature != null ? `${weather.apparent_temperature}°` : null} />
        <Row label="Mínima / máxima" value={weather?.minimum != null ? `${weather.minimum}° / ${weather.maximum}°` : null} />
        <Row label="Umidade" value={weather?.humidity != null ? `${Math.round(weather.humidity)}%` : null} />
        <Row label="Vento" value={weather?.wind != null ? `${Math.round(weather.wind)} km/h` : null} />
      </dl>
      {t && (
        <div className="ld-sub ld-in">
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
          <section key={r.pair} className="ld-in">
            <header><span>{RATE_LABEL[r.code] || r.code}</span><em className={upDay ? "is-up" : "is-down"}>{upDay ? "▲" : "▼"} {Math.abs(r.pctChange).toFixed(2).replace(".", ",")}%</em></header>
            <strong>{money(r.bid, r.code)}</strong>
            {r.high && r.low && Number(r.high) > Number(r.low) && (
              <div className="ld-range ld-range-sm" aria-hidden="true">
                <div className="ld-range-bar"><i style={{ left: `${rangePos(r.bid, r.low, r.high) * 100}%` }} /></div>
              </div>
            )}
            <dl className="ld-grid ld-grid-2">
              <Row label="Mínima do dia" value={r.low ? money(r.low, r.code) : null} />
              <Row label="Máxima do dia" value={r.high ? money(r.high, r.code) : null} />
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
              <li key={m.title} className="ld-in"><p>{m.title}</p>{m.source && <span>{m.source}</span>}</li>
            ))}
          </ul>
        </>
      )}
      <p className="ld-foot">Google Notícias · peça "Jarvis, notícias" depois de desbloquear para ouvir o resumo</p>
    </div>
  );
}

function WaterDetail({ water }) {
  const pct = water ? Math.min(100, water.percentage || 0) : 0;
  return (
    <>
    <div className="ld-hero2 ld-water-hero">
      <div className="ld-glass" aria-hidden="true">
        {/* nível com translateY (a onda vai junto, sem esticar); "ld-water" já é a classe da janela */}
        <span className="ld-h2o-level" style={{ "--lvl": `${(1 - Math.max(0.04, pct / 100)) * 100}%` }}><i className="ld-h2o-wave" /></span>
      </div>
      <div><strong>{pct}%</strong><span>{water?.goal_reached ? "Meta do dia batida" : "da meta de hoje"}</span></div>
    </div>
    <dl className="ld-grid">
      <Row label="Hoje" value={water ? `${water.total_ml} ml` : null} />
      <Row label="Meta" value={water ? `${water.goal_ml} ml` : null} />
      <Row label="Falta" value={water ? `${Math.max(0, water.goal_ml - water.total_ml)} ml` : null} />
      <Row label="Progresso" value={water ? `${Math.min(100, water.percentage || 0)}%` : null} tone={water?.goal_reached ? "ok" : null} />
    </dl>
    </>
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

export default function LockDetail({ kind, api, data = {}, origin = null, onClose }) {
  const cardRef = useRef(null);
  const [closing, setClosing] = useState(false);
  const reduce = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

  // V9.4.5: fecha voltando para o cartão de onde saiu (ou só sumindo, sem a origem)
  const close = useCallback(() => {
    if (closing) return;
    const el = cardRef.current;
    const from = el && origin ? flipFrom(origin, el.getBoundingClientRect()) : null;
    if (!el || reduce || !el.animate) { onClose(); return; }
    setClosing(true);
    const anim = el.animate(
      [{ transform: "none", opacity: 1 }, { transform: from || "translateY(16px) scale(0.94)", opacity: 0 }],
      { duration: CLOSE_MS, easing: "cubic-bezier(0.4, 0, 0.9, 0.6)", fill: "forwards" },
    );
    anim.onfinish = () => onClose();
    anim.oncancel = () => onClose();
  }, [closing, origin, reduce, onClose]);

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape") { e.stopPropagation(); close(); }
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [close]);

  // V9.4.5: "expande" do cartão tocado até o centro
  useLayoutEffect(() => {
    const el = cardRef.current;
    if (!el || reduce || !el.animate) return;
    const from = origin ? flipFrom(origin, el.getBoundingClientRect()) : null;
    el.animate(
      [{ transform: from || "translateY(18px) scale(0.92)", opacity: from ? 0.35 : 0 }, { transform: "none", opacity: 1 }],
      { duration: OPEN_MS, easing: "cubic-bezier(0.2, 0.9, 0.25, 1.08)" },
    );
  }, [kind]); // eslint-disable-line react-hooks/exhaustive-deps

  // V9.4.5: com a janela aberta, as animações do bloqueio atrás param (ninguém vê; economiza a placa de vídeo)
  useEffect(() => {
    if (!kind) return undefined;
    document.documentElement.classList.add("ld-open");
    return () => document.documentElement.classList.remove("ld-open");
  }, [kind]);

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
    body = (
      <div className="ld-hero2 ld-clock-hero">
        <strong>{now.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</strong>
        <span>{now.toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}</span>
      </div>
    );
  }
  const place = kind === "weather" && data.weather?.place ? ` · ${String(data.weather.place).split(",")[0].toUpperCase()}` : "";

  // Portal no <body>; os cliques não sobem para a tela de bloqueio (não disparam a verificação)
  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      aria-label={TITLES[kind]}
      className={`ld-overlay${closing ? " is-closing" : ""}`}
      onClick={(e) => { e.stopPropagation(); if (e.target === e.currentTarget) close(); }}
      onKeyDown={(e) => e.stopPropagation()}
    >
      {/* V9.4.5: "ld-k-" (antes "ld-<tipo>" colidia com .ld-rates/.ld-spotify/.ld-water do conteúdo e bagunçava o cabeçalho) */}
      <section className={`ld-card ld-k-${kind}`} ref={cardRef}>
        <header className="ld-head">
          <span className="lc-label">{TITLES[kind]}{place}</span>
          <button type="button" className="ld-x" onClick={close} aria-label="Fechar" autoFocus>✕</button>
        </header>
        {body}
      </section>
    </div>,
    document.body,
  );
}

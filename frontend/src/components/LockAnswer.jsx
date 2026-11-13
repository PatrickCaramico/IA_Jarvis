import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

// V6.5.8: na tela de bloqueio, cada pergunta respondida abre uma mini janela com o assunto.
// Clima: agora, hoje (máx/mín, chuva, sol) e os próximos dias. Outras: a pergunta e a resposta.
// Fecha sozinha depois de um tempo sem toque (cada toque recomeça a contagem) ou no ✕.
const IDLE_MS = 30000;

function WeatherBody({ card }) {
  const { now = {}, today = {}, days = [] } = card;
  return (
    <>
      <div className="la-now">
        <span className="la-now-icon" aria-hidden="true">{now.icon || "☁"}</span>
        <div>
          <strong className="la-now-temp">{now.temp ?? "–"}°</strong>
          <span className="la-now-desc">{now.desc}</span>
        </div>
        <dl className="la-now-meta">
          {now.feels != null && <><dt>Sensação</dt><dd>{now.feels}°</dd></>}
          {now.humidity != null && <><dt>Umidade</dt><dd>{now.humidity}%</dd></>}
          {now.wind != null && <><dt>Vento</dt><dd>{now.wind} km/h</dd></>}
        </dl>
      </div>
      <div className="la-today">
        <span>HOJE</span>
        <b>{today.max ?? "–"}° / {today.min ?? "–"}°</b>
        {today.rain != null && <span>☂ {today.rain}%</span>}
        {today.sunrise && <span>☀ {today.sunrise}</span>}
        {today.sunset && <span>☾ {today.sunset}</span>}
      </div>
      {days.length > 1 && (
        <ol className="la-days" aria-label="Próximos dias">
          {days.slice(1).map((d) => (
            <li key={d.label} title={d.desc}>
              <span className="la-day-label">{d.label}</span>
              <span className="la-day-icon" aria-hidden="true">{d.icon}</span>
              <span className="la-day-temp"><b>{d.max ?? "–"}°</b> {d.min ?? "–"}°</span>
              {d.rain != null && <span className={`la-day-rain${d.rain >= 60 ? " is-wet" : ""}`}>☂ {d.rain}%</span>}
            </li>
          ))}
        </ol>
      )}
    </>
  );
}

export default function LockAnswer({ answer, onClose }) {
  const [left, setLeft] = useState(IDLE_MS);
  const deadline = useRef(Date.now() + IDLE_MS);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    deadline.current = Date.now() + IDLE_MS;
    setLeft(IDLE_MS);
  }, [answer]);

  useEffect(() => {
    const t = setInterval(() => {
      const ms = deadline.current - Date.now();
      setLeft(Math.max(0, ms));
      if (ms <= 0) {
        clearInterval(t);
        closeRef.current?.();
      }
    }, 250);
    return () => clearInterval(t);
  }, [answer]);

  if (!answer?.card) return null;
  const { card } = answer;
  const touch = () => {
    deadline.current = Date.now() + IDLE_MS;
  };

  return createPortal(
    <section
      className={`la-window la-${card.kind}`}
      role="dialog"
      aria-label={card.title}
      onPointerDown={touch}
      onWheel={touch}
      onTouchStart={touch}
    >
      <div className="la-timer" aria-hidden="true"><i style={{ width: `${(left / IDLE_MS) * 100}%` }} /></div>
      <header className="la-head">
        <span className="la-title">{card.kind === "weather" ? "☁ " : card.kind === "news" ? "📰 " : card.kind === "music" ? "♫ " : "◈ "}{card.title}</span>
        <button type="button" className="la-x" onClick={onClose} aria-label="Fechar">✕</button>
      </header>
      {card.kind === "weather" ? <WeatherBody card={card} /> : card.kind === "news" ? (
        <ol className="la-news">
          {(card.items || []).map((n) => (
            <li key={n.link || n.title}>
              {n.title}{n.source && <span className="la-news-src"> · {n.source}</span>}
            </li>
          ))}
        </ol>
      ) : <p className="la-text">{card.text}</p>}
    </section>,
    document.body,
  );
}

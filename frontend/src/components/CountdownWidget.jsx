import { useEffect, useState } from "react";

// V5.6: contagem regressiva até um compromisso ("Jarvis, contagem regressiva para a viagem").
// Mostra dias, horas, minutos e segundos correndo; no dia, vira "É HOJE". ✕ tira da tela.
function parts(target, allDay, now) {
  if (allDay) {
    const t = new Date(target);
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const day = new Date(t.getFullYear(), t.getMonth(), t.getDate());
    const days = Math.round((day - today) / 86_400_000);
    return { done: days <= 0, days, hours: null, minutes: null, seconds: null };
  }
  const ms = new Date(target) - now;
  if (ms <= 0) return { done: true, days: 0, hours: 0, minutes: 0, seconds: 0 };
  const s = Math.floor(ms / 1000);
  return { done: false, days: Math.floor(s / 86400), hours: Math.floor((s % 86400) / 3600), minutes: Math.floor((s % 3600) / 60), seconds: s % 60 };
}

const pad = (n) => String(n).padStart(2, "0");

function whenLabel(target, allDay) {
  const d = new Date(target);
  const date = d.toLocaleDateString("pt-BR", { weekday: "short", day: "2-digit", month: "2-digit" });
  return allDay ? date : `${date} · ${d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}`;
}

export default function CountdownWidget({ items = [], onRemove }) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    if (!items.length) return undefined;
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, [items.length]);
  if (!items.length) return null;

  return (
    <div className="cd-wrap" aria-label="Contagens regressivas">
      {items.map((c) => {
        const p = parts(c.target, c.all_day, now);
        return (
          <section key={c.id} className={`cd-card${p.done ? " is-done" : ""}`} aria-live="off">
            <header className="cd-head">
              <span className="cd-label">◷ CONTAGEM REGRESSIVA</span>
              {onRemove && (
                <button type="button" className="cd-x" onClick={() => onRemove(c.id)} aria-label={`Tirar a contagem de ${c.title}`} title="Tirar da tela">✕</button>
              )}
            </header>
            <h3 className="cd-title">{c.title}</h3>
            {p.done ? (
              <strong className="cd-today">{c.all_day ? "É HOJE" : "CHEGOU A HORA"}</strong>
            ) : (
              <div className="cd-digits" role="timer" aria-label={`Faltam ${p.days} dias`}>
                <span><b>{p.days}</b><small>{p.days === 1 ? "DIA" : "DIAS"}</small></span>
                {p.hours != null && (
                  <>
                    <span><b>{pad(p.hours)}</b><small>H</small></span>
                    <span><b>{pad(p.minutes)}</b><small>MIN</small></span>
                    <span><b>{pad(p.seconds)}</b><small>S</small></span>
                  </>
                )}
              </div>
            )}
            <footer className="cd-foot">{whenLabel(c.target, c.all_day)}</footer>
          </section>
        );
      })}
    </div>
  );
}

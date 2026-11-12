import { useEffect, useMemo, useState } from "react";
import useNow from "../hooks/useNow.js";

// V6.5.15: tela de espera da Área Limpa no estilo "smart display" (Echo Show / Nest Hub):
//   em cima, relógio grande com a saudação; à esquerda, o clima de agora e a semana;
//   à direita, os próximos compromissos, a água e as compras; embaixo, as manchetes passando.
// Só leitura (nada pessoal é falado); tudo se atualiza sozinho. Tocar em um cartão faz o pedido por voz.
const WEEKDAYS = ["domingo", "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado"];
const MONTHS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
  "novembro", "dezembro"];

function greeting(h) {
  if (h < 5) return "Boa madrugada";
  if (h < 12) return "Bom dia";
  if (h < 18) return "Boa tarde";
  return "Boa noite";
}

function usePoll(api, path, ms, map = (x) => x) {
  const [data, setData] = useState(null);
  useEffect(() => {
    let alive = true;
    const load = () => api(path).then((d) => alive && setData(map(d))).catch(() => {});
    load();
    const t = setInterval(load, ms);
    return () => {
      alive = false;
      clearInterval(t);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, path, ms]);
  return data;
}

function Ring({ pct }) {
  const r = 26;
  const c = 2 * Math.PI * r;
  const p = Math.max(0, Math.min(100, pct || 0));
  return (
    <svg className="zg-ring" viewBox="0 0 64 64" aria-hidden="true">
      <circle cx="32" cy="32" r={r} className="zg-ring-bg" />
      <circle cx="32" cy="32" r={r} className="zg-ring-fg" strokeDasharray={c} strokeDashoffset={c * (1 - p / 100)} />
    </svg>
  );
}

function Headlines({ api }) {
  const [items, setItems] = useState([]);
  const [i, setI] = useState(0);
  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const themes = (await api("/api/briefing/news-themes")).items || [];
        const lists = await Promise.all(themes.slice(0, 4).map(async (t) => {
          try {
            const d = t.topic
              ? await api(`/api/news?category=${encodeURIComponent(t.topic)}&limit=3`)
              : await api(`/api/news/search?q=${encodeURIComponent(t.query)}&limit=3`);
            return (d.items || []).slice(0, 2).map((n) => ({ ...n, theme: t.title }));
          } catch {
            return [];
          }
        }));
        const flat = [];
        for (let k = 0; k < 2; k += 1) lists.forEach((l) => l[k] && flat.push(l[k]));
        if (alive && flat.length) setItems(flat);
      } catch {
        /* sem notícias agora: a faixa some */
      }
    };
    load();
    const t = setInterval(load, 15 * 60 * 1000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [api]);
  useEffect(() => {
    if (items.length < 2) return undefined;
    const t = setInterval(() => setI((n) => (n + 1) % items.length), 9000);
    return () => clearInterval(t);
  }, [items]);
  if (!items.length) return null;
  const it = items[i % items.length];
  return (
    <button
      type="button"
      className="zg-ticker"
      onClick={() => window.dispatchEvent(new CustomEvent("jarvis-open-news"))}
      title="Abrir as notícias"
    >
      <span className="zg-ticker-tag">📰 {it.theme}</span>
      <span key={i} className="zg-ticker-text">{it.title.replace(/\s+-\s+[^-]+$/, "")}</span>
      <span className="zg-ticker-src">{it.source}</span>
    </button>
  );
}

export default function ZenGlance({ api, name = "", onCommand }) {
  const now = useNow(true);
  const weather = usePoll(api, "/api/weather", 10 * 60 * 1000);
  const agenda = usePoll(api, "/api/agenda/next?limit=3", 5 * 60 * 1000, (d) => d.items || []);
  const water = usePoll(api, "/api/water", 2 * 60 * 1000);
  const shopping = usePoll(api, "/api/shopping", 2 * 60 * 1000, (d) => (d.items || []).filter((x) => !x.comprado));
  const status = usePoll(api, "/api/lock/status", 60 * 1000);

  const hh = String(now.getHours()).padStart(2, "0");
  const mm = String(now.getMinutes()).padStart(2, "0");
  const first = useMemo(() => (name || "").split(" ")[0], [name]);
  const say = (text) => onCommand && onCommand(text);

  return (
    <div className="zg-root" aria-label="Painel de espera">
      <header className="zg-clock">
        <span className="zg-hello">{greeting(now.getHours())}{first ? `, ${first}` : ""}</span>
        <strong className="zg-time">{hh}<i>:</i>{mm}</strong>
        <span className="zg-date">{WEEKDAYS[now.getDay()]}, {now.getDate()} de {MONTHS[now.getMonth()]}</span>
      </header>

      <section className="zg-side zg-left">
        {weather && (
          <button type="button" className="zg-card zg-weather" onClick={() => say("como está o clima")}>
            <span className="zg-label">CLIMA · {(weather.place || "").toUpperCase()}</span>
            <div className="zg-weather-now">
              <span className="zg-weather-icon" aria-hidden="true">{weather.icon || "☁"}</span>
              <strong>{weather.temperature}°</strong>
              <span className="zg-weather-desc">
                {weather.description}
                <small>máx {weather.maximum}° · mín {weather.minimum}°{weather.rain_probability != null ? ` · ☂ ${weather.rain_probability}%` : ""}</small>
              </span>
            </div>
            {Array.isArray(weather.week) && weather.week.length > 1 && (
              <ol className="zg-week">
                {weather.week.slice(1, 6).map((d) => (
                  <li key={d.label}>
                    <span>{d.label.replace("Amanhã", "Amanhã").split(" ")[0]}</span>
                    <i aria-hidden="true">{d.icon}</i>
                    <b>{d.max}°</b>
                    <small>{d.min}°</small>
                  </li>
                ))}
              </ol>
            )}
          </button>
        )}
      </section>

      <section className="zg-side zg-right">
        <button type="button" className="zg-card zg-agenda" onClick={() => say("agenda")}>
          <span className="zg-label">PRÓXIMOS</span>
          {agenda && agenda.length ? (
            <ul>
              {agenda.map((a) => (
                <li key={`${a.at}-${a.title}`}>
                  <span className="zg-when">{a.label}</span>
                  <span className="zg-what">{a.title}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="zg-empty">Agenda livre. {status?.next_alarm ? "" : "Nenhum lembrete."}</p>
          )}
          {status?.next_alarm && <p className="zg-alarm">⏰ Alarme {status.next_alarm}</p>}
        </button>
        <div className="zg-row">
          {water && (
            <button type="button" className="zg-card zg-mini" onClick={() => say("bebi um copo de água")} title="Toque: bebi um copo">
              <span className="zg-ring-wrap">
                <Ring pct={water.percentage} />
                <b>{water.percentage}%</b>
              </span>
              <span className="zg-mini-txt">
                <span className="zg-label">ÁGUA</span>
                {(water.total_ml / 1000).toFixed(1).replace(".", ",")} L de {(water.goal_ml / 1000).toFixed(1).replace(".", ",")} L
                <small>toque: +1 copo</small>
              </span>
            </button>
          )}
          {shopping && (
            <button type="button" className="zg-card zg-mini" onClick={() => say("o que tem na lista de compras")}>
              <span className="zg-big-icon" aria-hidden="true">🛒</span>
              <span className="zg-mini-txt">
                <span className="zg-label">COMPRAS</span>
                {shopping.length ? `${shopping.length} ${shopping.length === 1 ? "item" : "itens"}` : "Lista vazia"}
                <small>{shopping.slice(0, 2).map((s) => s.texto || s.text).filter(Boolean).join(", ")}</small>
              </span>
            </button>
          )}
        </div>
      </section>

      <footer className="zg-bottom">
        <Headlines api={api} />
      </footer>
    </div>
  );
}

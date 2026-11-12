import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { timeAgo } from "../utils/timeAgo.js";

// V6.5: janela de notícias. Abas com os temas do briefing (Configurações › Geral › NOTÍCIAS DO
// BRIEFING), busca livre e o liga/desliga dos avisos de notícias no celular. Tocar numa manchete
// abre a matéria (no app, no navegador do celular).
export default function NewsWindow({ api, onClose }) {
  const [themes, setThemes] = useState([]);
  const [active, setActive] = useState(null); // {title, query?, topic?}
  const [items, setItems] = useState(null);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [notify, setNotify] = useState(null);

  useEffect(() => {
    api("/api/briefing/news-themes")
      .then((d) => {
        const list = d.items || [];
        setThemes(list);
        setActive((cur) => cur || list[0] || { title: "Tecnologia", topic: "tecnologia" });
      })
      .catch(() => setActive({ title: "Tecnologia", topic: "tecnologia" }));
    api("/api/prefs").then((p) => setNotify(p.news_notify_enabled !== false)).catch(() => {});
  }, [api]);

  const load = useCallback(async (theme) => {
    if (!theme) return;
    setItems(null);
    setError("");
    try {
      const d = theme.topic
        ? await api(`/api/news?category=${encodeURIComponent(theme.topic)}&limit=12`)
        : await api(`/api/news/search?q=${encodeURIComponent(theme.query)}&limit=12`);
      setItems(d.items || []);
    } catch (err) {
      setItems([]);
      setError(err.message || "Não consegui carregar as notícias agora.");
    }
  }, [api]);

  useEffect(() => { load(active); }, [active, load]);

  const runSearch = (e) => {
    e.preventDefault();
    const q = search.trim();
    if (q) setActive({ title: q, query: q, custom: true });
  };

  const toggleNotify = async () => {
    const next = !notify;
    setNotify(next);
    try {
      await api("/api/prefs", { method: "PATCH", body: JSON.stringify({ news_notify_enabled: next }) });
    } catch {
      setNotify(!next);
    }
  };

  const same = (a, b) => a && b && a.title === b.title && (a.query || a.topic) === (b.query || b.topic);

  return createPortal(
    <div
      className="ld-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Notícias"
      onClick={(e) => { e.stopPropagation(); if (e.target === e.currentTarget) onClose(); }}
      onKeyDown={(e) => { e.stopPropagation(); if (e.key === "Escape") onClose(); }}
    >
      <section className="ld-card nw-card">
        <header className="ld-head">
          <span className="lc-label">📰 NOTÍCIAS</span>
          <button type="button" className="ld-x" onClick={onClose} aria-label="Fechar" autoFocus>✕</button>
        </header>

        <div className="nw-chips" role="tablist" aria-label="Temas">
          {themes.map((t) => (
            <button
              key={`${t.title}-${t.query || t.topic}`}
              type="button"
              role="tab"
              aria-selected={same(t, active)}
              className={`nw-chip ${same(t, active) ? "on" : ""}`}
              onClick={() => setActive(t)}
            >
              {t.title}
            </button>
          ))}
          {active?.custom && <span className="nw-chip on" role="tab" aria-selected="true">🔎 {active.title}</span>}
        </div>

        <form className="nw-search" onSubmit={runSearch}>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            maxLength={80}
            placeholder="Buscar outro assunto (ex.: Homem-Aranha)"
            aria-label="Buscar notícias"
          />
          <button type="submit" disabled={!search.trim()}>BUSCAR</button>
        </form>

        <div className="nw-list" aria-live="polite">
          {items === null && <p className="nw-empty">Carregando manchetes…</p>}
          {items && !items.length && <p className="nw-empty">{error || "Nenhuma manchete agora para esse tema."}</p>}
          {items && items.map((it, i) => (
            <a key={`${it.link}-${i}`} className="nw-item" href={it.link} target="_blank" rel="noreferrer noopener">
              <strong>{it.title.replace(/\s+-\s+[^-]+$/, "")}</strong>
              <span>{it.source || "Google Notícias"}{it.published ? ` · ${timeAgo(it.published)}` : ""}</span>
            </a>
          ))}
        </div>

        <footer className="nw-foot">
          <button type="button" className="nw-refresh" onClick={() => load(active)}>↻ ATUALIZAR</button>
          {notify !== null && (
            <label className="nw-notify">
              <input type="checkbox" checked={notify} onChange={toggleNotify} />
              Avisar no celular quando sair notícia nova
            </label>
          )}
        </footer>
      </section>
    </div>,
    document.body,
  );
}

import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import useEscape from "../hooks/useEscape.js";

// V9.4.2: janela 📜 LOGS (faixa DIGA e CONTROLES). Antes, para ver um erro era preciso abrir logs/jarvis.log no PC.
// Abas: ERROS E AVISOS (do arquivo de log, cada erro com o rastro completo), EVENTOS (o que o JARVIS registrou para
// o senhor: falhas de habilidades, ações) e TUDO (as últimas linhas do log), com busca e cópia.
const TABS = [
  { id: "erros", label: "ERROS E AVISOS" },
  { id: "eventos", label: "EVENTOS" },
  { id: "tudo", label: "TUDO" },
];

function Entry({ e }) {
  const [open, setOpen] = useState(false);
  const level = e.level || (e.kind === "error" ? "ERROR" : "INFO");
  const tone = level === "ERROR" || level === "CRITICAL" ? "is-error" : level === "WARNING" ? "is-warn" : "";
  const detail = e.detail || "";
  return (
    <li className={`lgw-item ${tone}`}>
      <button type="button" className="lgw-row" onClick={() => detail && setOpen((v) => !v)} aria-expanded={detail ? open : undefined}>
        <b>{level === "ERROR" || level === "CRITICAL" ? "ERRO" : level === "WARNING" ? "AVISO" : (e.kind || level).toUpperCase()}</b>
        <time>{String(e.at || "").replace("T", " ").slice(5, 16)}</time>
        <span>{e.message}</span>
        {e.name && <small>{e.name}</small>}
        {detail && <i aria-hidden="true">{open ? "▾" : "▸"}</i>}
      </button>
      {open && <pre className="lgw-detail">{detail}</pre>}
    </li>
  );
}

export default function LogsWindow({ api, onClose }) {
  const [tab, setTab] = useState("erros");
  const [query, setQuery] = useState("");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  useEscape(onClose);

  const load = useCallback(async () => {
    setError("");
    try {
      if (tab === "eventos") {
        const r = await api("/api/logs?limit=200", { timeout: 10000 });
        const q = query.trim().toLowerCase();
        const items = (r.events || []).filter((e) => !q || `${e.message} ${e.detail}`.toLowerCase().includes(q));
        setData({ items, errors: items.filter((e) => e.kind === "error").length });
      } else {
        const level = tab === "erros" ? "WARNING" : "INFO";
        setData(await api(`/api/logs/file?level=${level}&limit=300&q=${encodeURIComponent(query.trim())}`, { timeout: 15000 }));
      }
    } catch (err) {
      setError(err.message || "Não consegui ler os registros.");
    }
  }, [api, tab, query]);

  useEffect(() => {
    const t = setTimeout(load, query ? 300 : 0);
    return () => clearTimeout(t);
  }, [load, query]);

  const copy = async () => {
    const text = (data?.items || []).map((e) => `${e.at} [${e.level || e.kind}] ${e.name ? `${e.name}: ` : ""}${e.message}${e.detail ? `\n${e.detail}` : ""}`).join("\n");
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setError("O navegador não deixou copiar.");
    }
  };

  const items = data?.items || [];
  return createPortal(
    <div className="lgw-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <section className="lgw" role="dialog" aria-modal="true" aria-label="Logs do JARVIS">
        <header className="lgw-head">
          <div>
            <h2>📜 LOGS</h2>
            <span>{data ? `${items.length} registro${items.length === 1 ? "" : "s"}${data.errors ? ` · ${data.errors} erro${data.errors === 1 ? "" : "s"}` : ""}` : "Carregando…"}</span>
          </div>
          <button type="button" className="sp-close" onClick={onClose} aria-label="Fechar">✕</button>
        </header>
        <div className="lgw-tools">
          <div className="lgw-tabs" role="tablist">
            {TABS.map((t) => (
              <button key={t.id} type="button" role="tab" aria-selected={tab === t.id} className={tab === t.id ? "is-on" : ""} onClick={() => setTab(t.id)}>
                {t.label}
              </button>
            ))}
          </div>
          <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Buscar (ex.: auto-análise, spotify)" aria-label="Buscar nos logs" />
          <button type="button" className="lgw-btn" onClick={load}>↻</button>
          <button type="button" className="lgw-btn" onClick={copy} disabled={!items.length}>{copied ? "✓ COPIADO" : "COPIAR"}</button>
        </div>
        {error && <p className="lgw-error" role="alert">{error}</p>}
        <ul className="lgw-list">
          {items.map((e, i) => <Entry key={`${e.at}-${i}`} e={e} />)}
          {data && !items.length && !error && <li className="lgw-empty">{tab === "erros" ? "Nenhum erro ou aviso recente. Tudo certo." : "Nada registrado."}</li>}
        </ul>
        <footer className="lgw-foot">Tudo vem do PC (logs/jarvis.log). Toque num erro para ver o rastro completo.</footer>
      </section>
    </div>,
    document.body,
  );
}

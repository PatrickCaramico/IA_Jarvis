import { useEffect, useState } from "react";

export default function LogReportWidget({ api, onClose }) {
  const [events, setEvents] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/api/logs?limit=100")
      .then((data) => setEvents(data.events ?? []))
      .catch((err) => setError(err.message));
  }, [api]);

  return (
    <section className="jarvis-log-window hud-panel" aria-label="Relatório de logs">
      <header className="widget-workspace-toolbar">
        <span>Relatório do sistema</span>
        <button type="button" onClick={onClose} aria-label="Fechar relatório">×</button>
      </header>
      <div className="jarvis-log-content">
        {error && <p className="text-sm text-red-300">{error}</p>}
        {!error && events.length === 0 && <p className="text-sm text-arc-300/70">Nenhum evento registrado.</p>}
        {events.map((event, index) => (
          <article className={`jarvis-log-entry ${event.kind === "error" ? "is-error" : ""}`} key={`${event.at}-${index}`}>
            <div className="flex items-center justify-between gap-2">
              <strong>{event.kind === "error" ? "ERRO" : event.kind.toUpperCase()}</strong>
              <time>{event.at}</time>
            </div>
            <p>{event.message}</p>
            {event.detail && <small>{event.detail}</small>}
          </article>
        ))}
      </div>
    </section>
  );
}

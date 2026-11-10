import { useCallback, useEffect, useState } from "react";
import { EmptyState, Skeleton } from "./ui/Skeleton.jsx";

export default function CalendarWidget({ api }) {
  const [status, setStatus] = useState({ configured: false, connected: false });
  const [events, setEvents] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const current = await api("/api/integrations/google-calendar/status");
      setStatus(current);
      if (current.connected) setEvents((await api("/api/integrations/google-calendar/events")).events ?? []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => { load(); }, [load]);

  const connect = () => {
    window.open(`${api.baseUrl ?? "http://localhost:8000"}/api/integrations/google-calendar/authorize`, "_blank", "width=600,height=700");
  };

  return (
    <section className="hud-panel p-3.5" aria-label="Google Calendar">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="font-display text-xs tracking-wide text-arc-200">Calendário</h2>
        {status.connected && <button type="button" onClick={load} className="text-[10px] text-arc-300/70 hover:text-arc-100">Atualizar</button>}
      </div>
      {loading ? <Skeleton lines={3} label="Carregando a agenda" />
        : !status.configured ? <p className="text-xs text-arc-300/60">Configure as credenciais OAuth no arquivo .env.</p>
        : !status.connected ? <button type="button" onClick={connect} className="w-full rounded border border-arc-300 bg-arc-500/15 px-3 py-2 font-display text-xs tracking-widest text-arc-100 hover:bg-arc-400/30">Conectar Google Calendar</button>
          : events.length ? <ul className="space-y-1.5">{events.map((event) => <li key={event.id} className="rounded border border-arc-700/70 px-2 py-1.5"><p className="text-xs text-arc-100">{event.title}</p><p className="text-[10px] text-arc-300/60">{event.start ? new Date(event.start).toLocaleString("pt-BR") : "Data não informada"}</p></li>)}</ul>
            : <EmptyState icon="◷" title="Agenda livre" hint="Nenhum compromisso nos próximos 14 dias." action="Atualizar" onAction={load} />}
      {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
    </section>
  );
}

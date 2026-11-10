import { useCallback, useEffect, useState } from "react";
import BriefingScreen from "./BriefingScreen.jsx";
import DataSourcesScreen from "./DataSourcesScreen.jsx";
import FinanceScreen from "./FinanceScreen.jsx";
import { startPolling } from "../hooks/usePolling.js";

/**
 * ScreensOverlay — "Telas" do HUD (somente leitura).
 * Quatro telas com dados que o projeto já tem: Centro de comando, Agenda tática,
 * Radar de notícias (endpoint novo /api/news) e Núcleo do sistema.
 * Não altera nenhuma função existente.
 */

const TIME_ZONE = "America/Sao_Paulo";

const TABS = [
  ["command", "CENTRO DE COMANDO"],
  ["briefing", "BRIEFING"],
  ["agenda", "AGENDA TÁTICA"],
  ["news", "RADAR DE NOTÍCIAS"],
  ["datasources", "FONTES DE DADOS"],
  ["finance", "FINANCEIRO"],
  ["system", "NÚCLEO DO SISTEMA"],
];

const NEWS_CATEGORIES = [
  ["tecnologia", "TECNOLOGIA"],
  ["economia", "ECONOMIA"],
  ["brasil", "BRASIL"],
  ["mundo", "MUNDO"],
  ["ciencia", "CIÊNCIA"],
  ["saude", "SAÚDE"],
  ["esportes", "ESPORTES"],
];

/* ---------- utilidades ---------- */

function useLoader(load, intervalMs = 0) {
  const [state, setState] = useState({ data: null, error: "", loading: true });
  const run = useCallback(async () => {
    try {
      const data = await load();
      setState({ data, error: "", loading: false });
    } catch (err) {
      setState((current) => ({ data: current.data, error: err?.message || "Erro inesperado.", loading: false }));
    }
  }, [load]);
  useEffect(() => {
    if (!intervalMs) {
      run();
      return undefined;
    }
    return startPolling(run, intervalMs);
  }, [run, intervalMs]);
  return { ...state, reload: run };
}

const fmtTime = (date) =>
  new Intl.DateTimeFormat("pt-BR", { timeZone: TIME_ZONE, hour: "2-digit", minute: "2-digit", hour12: false }).format(date);

const fmtDay = (date) =>
  new Intl.DateTimeFormat("pt-BR", { timeZone: TIME_ZONE, weekday: "short", day: "2-digit", month: "short" })
    .format(date)
    .replace(".", "")
    .toUpperCase();

const dayKey = (date) =>
  new Intl.DateTimeFormat("en-CA", { timeZone: TIME_ZONE, year: "numeric", month: "2-digit", day: "2-digit" }).format(date);

function timeAgo(iso) {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  if (Number.isNaN(diff)) return "";
  const min = Math.max(0, Math.round(diff / 60000));
  if (min < 1) return "agora";
  if (min < 60) return `há ${min} min`;
  const h = Math.round(min / 60);
  if (h < 24) return `há ${h} h`;
  return `há ${Math.round(h / 24)} d`;
}

// Junta compromissos do Google Calendar e lembretes numa lista única ordenada.
function buildAgenda(events = [], reminders = []) {
  const items = [];
  events.forEach((event) => {
    if (!event.start) return;
    const allDay = !String(event.start).includes("T");
    const when = allDay ? new Date(`${event.start}T00:00:00`) : new Date(event.start);
    if (Number.isNaN(when.getTime())) return;
    items.push({ id: `e-${event.id}`, kind: "event", title: event.title, when, allDay, place: event.location || "" });
  });
  reminders.forEach((reminder) => {
    const m = /^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})$/.exec(reminder.data_hora || "");
    if (!m) return;
    const when = new Date(`${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}:00-03:00`);
    items.push({ id: `r-${reminder.id}`, kind: "reminder", title: reminder.texto, when, allDay: false, place: "" });
  });
  return items.sort((a, b) => a.when - b.when);
}

async function loadAgendaData(api) {
  const [reminders, status] = await Promise.allSettled([
    api("/api/reminders?only_pending=true"),
    api("/api/integrations/google-calendar/status"),
  ]);
  const cal = status.status === "fulfilled" ? status.value : null;
  let events = [];
  let calendar = "off";
  if (cal?.connected) {
    try {
      events = (await api("/api/integrations/google-calendar/events")).events ?? [];
      calendar = "on";
    } catch {
      calendar = "error";
    }
  } else if (cal && cal.configured === false) {
    calendar = "unconfigured";
  }
  const pending = reminders.status === "fulfilled" ? reminders.value.reminders ?? [] : [];
  return { agenda: buildAgenda(events, pending), calendar };
}

function Panel({ title, tag, className = "", children }) {
  return (
    <section className={`hl-panel ${className}`}>
      <header className="hl-panel-head">
        <span>{title}</span>
        {tag != null && <em>{tag}</em>}
      </header>
      <div className="hl-panel-body">{children}</div>
    </section>
  );
}

function CalendarHint({ calendar, api }) {
  if (calendar === "on") return null;
  const connect = () =>
    window.open(`${api.baseUrl ?? "http://localhost:8000"}/api/integrations/google-calendar/authorize`, "_blank", "width=600,height=700");
  if (calendar === "unconfigured") {
    return <p className="hs-hint">Google Calendar não configurado (credenciais OAuth no .env). Mostrando só os lembretes.</p>;
  }
  if (calendar === "error") {
    return <p className="hs-hint">Não consegui ler o Google Calendar agora. Mostrando só os lembretes.</p>;
  }
  return (
    <p className="hs-hint">
      Google Calendar não conectado.{" "}
      <button type="button" className="hs-link" onClick={connect}>CONECTAR</button>
    </p>
  );
}

/* ---------- Centro de comando ---------- */

function CommandScreen({ api }) {
  const load = useCallback(async () => {
    const [agendaData, tasks, focus, weather] = await Promise.all([
      loadAgendaData(api),
      api("/api/tasks?include_completed=false").catch(() => ({ tasks: [] })),
      api("/api/focus").catch(() => null),
      api("/api/weather").catch(() => null),
    ]);
    return { ...agendaData, tasks: tasks.tasks ?? [], focus, weather };
  }, [api]);
  const { data, error, loading } = useLoader(load, 60000);

  if (loading && !data) return <p className="hs-empty">Carregando painel…</p>;
  if (!data) return <p className="hs-empty">{error || "Sem dados."}</p>;

  const now = Date.now();
  const upcoming = data.agenda.filter((item) => item.when.getTime() >= now - 3600000).slice(0, 5);
  const next = upcoming[0];
  const pendingTasks = data.tasks.filter((task) => !task.concluida);
  const focusOn = data.focus?.active;
  const focusPhase = String(data.focus?.phase ?? "").toUpperCase();
  const focusLabel = !focusPhase || focusPhase === "FOCO" ? "MODO FOCO ATIVO" : `FOCO · ${focusPhase}`;

  return (
    <div className="hs-grid hs-grid-command">
      <div className="hs-stats hs-span-4">
        <div className="hs-stat"><b>{pendingTasks.length}</b><span>TAREFAS PENDENTES</span></div>
        <div className="hs-stat"><b>{data.agenda.filter((i) => i.kind === "reminder").length}</b><span>LEMBRETES</span></div>
        <div className="hs-stat"><b>{data.agenda.filter((i) => i.kind === "event").length}</b><span>COMPROMISSOS (14 DIAS)</span></div>
        <div className="hs-stat">
          <b>{focusOn ? `${Math.ceil((data.focus.remaining_seconds ?? 0) / 60)} min` : "—"}</b>
          <span>{focusOn ? focusLabel : "MODO FOCO INATIVO"}</span>
        </div>
      </div>

      <Panel title="AGENDA · PRÓXIMOS COMPROMISSOS" tag={`${data.agenda.length} ITENS`} className="hs-span-2">
        {next ? (
          <div className="hs-next">
            <strong>{next.allDay ? "DIA TODO" : fmtTime(next.when)}</strong>
            <div>
              <p>{next.title}</p>
              <small>{fmtDay(next.when)}{next.place ? ` · ${next.place}` : ""}</small>
            </div>
          </div>
        ) : (
          <p className="hs-empty">Sem compromissos nos próximos dias.</p>
        )}
        <ul className="hs-list">
          {upcoming.slice(1).map((item) => (
            <li key={item.id}>
              <span className="hs-when">{item.allDay ? "DIA TODO" : fmtTime(item.when)}</span>
              <span>{item.title}</span>
              <small>{fmtDay(item.when)}{item.kind === "reminder" ? " · LEMBRETE" : ""}</small>
            </li>
          ))}
        </ul>
        <CalendarHint calendar={data.calendar} api={api} />
      </Panel>

      <Panel title="PEDEM SUA ATENÇÃO" tag={`${pendingTasks.length} TAREFA${pendingTasks.length === 1 ? "" : "S"}`}>
        {pendingTasks.length === 0 ? (
          <p className="hs-empty">Tudo em dia.</p>
        ) : (
          <ul className="hs-list">
            {pendingTasks.slice(0, 7).map((task) => (
              <li key={task.id}><span className="hs-dot" /> <span>{task.texto}</span></li>
            ))}
          </ul>
        )}
      </Panel>

      <Panel title="SENSORES · CLIMA" tag={data.weather?.place ?? "—"}>
        {data.weather ? (
          <div className="hs-weather">
            <strong>{data.weather.temperature}°</strong>
            <ul className="hs-kv">
              <li><span>CONDIÇÃO</span><b>{String(data.weather.description ?? "").toUpperCase()}</b></li>
              <li><span>SENSAÇÃO</span><b>{data.weather.apparent_temperature}°</b></li>
              <li><span>MÁX / MÍN</span><b>{data.weather.maximum}° / {data.weather.minimum}°</b></li>
              <li><span>CHUVA</span><b>{data.weather.rain_probability ?? "--"}%</b></li>
            </ul>
          </div>
        ) : (
          <p className="hs-empty">Clima indisponível.</p>
        )}
      </Panel>
    </div>
  );
}

/* ---------- Agenda tática ---------- */

function AgendaScreen({ api }) {
  const load = useCallback(() => loadAgendaData(api), [api]);
  const { data, error, loading, reload } = useLoader(load, 120000);
  if (loading && !data) return <p className="hs-empty">Carregando agenda…</p>;
  if (!data) return <p className="hs-empty">{error || "Sem dados."}</p>;

  const groups = [];
  data.agenda.forEach((item) => {
    const key = dayKey(item.when);
    const last = groups[groups.length - 1];
    if (last && last.key === key) last.items.push(item);
    else groups.push({ key, label: fmtDay(item.when), items: [item] });
  });

  return (
    <div className="hs-stack">
      <div className="hs-toolbar">
        <CalendarHint calendar={data.calendar} api={api} />
        <button type="button" className="hl-btn" onClick={reload}>ATUALIZAR</button>
      </div>
      {groups.length === 0 && <p className="hs-empty">Nada agendado nos próximos 14 dias.</p>}
      <div className="hs-days">
        {groups.map((group) => (
          <Panel key={group.key} title={group.label} tag={`${group.items.length} ITEM${group.items.length === 1 ? "" : "S"}`}>
            <ul className="hs-list">
              {group.items.map((item) => (
                <li key={item.id}>
                  <span className="hs-when">{item.allDay ? "DIA TODO" : fmtTime(item.when)}</span>
                  <span>{item.title}{item.place ? ` · ${item.place}` : ""}</span>
                  <small>{item.kind === "reminder" ? "LEMBRETE" : "EVENTO"}</small>
                </li>
              ))}
            </ul>
          </Panel>
        ))}
      </div>
    </div>
  );
}

/* ---------- Radar de notícias ---------- */

function NewsBody({ api, category }) {
  const load = useCallback(() => api(`/api/news?category=${category}&limit=9`), [api, category]);
  const { data, error, loading, reload } = useLoader(load, 300000);

  if (loading && !data) return <p className="hs-empty">Buscando notícias…</p>;
  if (!data) {
    return (
      <div className="hs-empty">
        <p>{error || "Não consegui carregar as notícias."}</p>
        <p className="hs-hint">Se você acabou de atualizar o JARVIS, feche e abra o programa de novo para ativar o novo recurso de notícias.</p>
        <button type="button" className="hl-btn" onClick={reload}>TENTAR DE NOVO</button>
      </div>
    );
  }
  const items = data.items ?? [];
  if (items.length === 0) return <p className="hs-empty">Nenhuma notícia encontrada.</p>;
  const [top, ...rest] = items;

  return (
    <div className="hs-news">
      <a className="hs-news-top" href={top.link} target="_blank" rel="noopener noreferrer">
        <small>{["DESTAQUE", top.source, timeAgo(top.published)].filter(Boolean).join(" · ")}</small>
        <strong>{top.title}</strong>
      </a>
      <ul className="hs-news-list">
        {rest.map((item, index) => (
          <li key={`${item.link}-${index}`}>
            <a href={item.link} target="_blank" rel="noopener noreferrer">
              <small>{[item.source, timeAgo(item.published)].filter(Boolean).join(" · ")}</small>
              <span>{item.title}</span>
            </a>
          </li>
        ))}
      </ul>
      {error && <p className="hs-hint">Exibindo a última atualização ({error}).</p>}
    </div>
  );
}

function NewsScreen({ api }) {
  const [category, setCategory] = useState("tecnologia");
  return (
    <div className="hs-stack">
      <div className="hs-subtabs" role="tablist" aria-label="Categorias de notícias">
        {NEWS_CATEGORIES.map(([id, label]) => (
          <button key={id} type="button" role="tab" aria-selected={category === id} className={category === id ? "on" : ""} onClick={() => setCategory(id)}>
            {label}
          </button>
        ))}
      </div>
      <Panel title={`NOTÍCIAS · ${category.toUpperCase()}`} tag="GOOGLE NEWS · BRASIL" className="hs-news-panel">
        <NewsBody key={category} api={api} category={category} />
      </Panel>
    </div>
  );
}

/* ---------- Núcleo do sistema ---------- */

function Meter({ label, value, suffix = "%" }) {
  const known = typeof value === "number";
  return (
    <div className="hs-meter">
      <div><span>{label}</span><b>{known ? `${Math.round(value)}${suffix}` : "—"}</b></div>
      <i><u style={{ width: `${known ? Math.max(2, Math.min(100, value)) : 0}%` }} /></i>
    </div>
  );
}

const SERVICE_LABELS = [["ai", "IA"], ["microphone", "Microfone"], ["camera", "Câmera"], ["internet", "Internet"], ["backend", "Backend"]];

function SystemScreen({ api, services, connected }) {
  const loadSystem = useCallback(() => api("/api/system"), [api]);
  const loadLogs = useCallback(() => api("/api/logs?limit=8"), [api]);
  const system = useLoader(loadSystem, 4000);
  const logs = useLoader(loadLogs, 15000);
  const s = system.data;

  return (
    <div className="hs-grid hs-grid-system">
      <Panel title="DESEMPENHO" tag={s ? String(s.platform || "").toUpperCase() : "…"}>
        {s ? (
          <>
            <Meter label="CPU" value={s.cpu_percent} />
            <Meter label="MEMÓRIA RAM" value={s.ram_percent} />
            <Meter label="VOLUME" value={typeof s.volume === "number" && s.volume >= 0 ? s.volume : null} />
            <ul className="hs-kv">
              <li><span>ESPAÇO LIVRE</span><b>{s.disk_free_gb != null ? `${s.disk_free_gb} GB` : "—"}</b></li>
              <li><span>PROCESSOS</span><b>{s.processes ?? "—"}</b></li>
              <li><span>TEMPERATURA</span><b>{typeof s.temperature === "number" ? `${s.temperature} °C` : s.temperature}</b></li>
              <li><span>GPU</span><b>{s.gpu}</b></li>
              <li><span>REDE</span><b>{s.network}</b></li>
            </ul>
          </>
        ) : (
          <p className="hs-empty">{system.error || "Lendo sensores…"}</p>
        )}
      </Panel>

      <Panel title="NÚCLEO · SERVIÇOS" tag={connected ? "OPERACIONAL" : "DEGRADADO"}>
        <ul className="hs-kv">
          {SERVICE_LABELS.map(([key, label]) => {
            const online = key === "backend" ? connected && services?.[key] !== false : services?.[key] === true;
            return (
              <li key={key}>
                <span>{label}</span>
                <b className={online ? "ok" : "off"}>● {online ? "ONLINE" : "OFFLINE"}</b>
              </li>
            );
          })}
        </ul>
      </Panel>

      <Panel title="ATIVIDADE RECENTE" tag="ÚLTIMOS EVENTOS" className="hs-span-2">
        {logs.data?.events?.length ? (
          <ul className="hs-list">
            {logs.data.events.map((event, index) => (
              <li key={`${event.at}-${index}`}>
                <span className="hs-when">{event.at ? String(event.at).slice(11, 16) : "--:--"}</span>
                <span>{event.message}</span>
                <small>{String(event.kind || "").toUpperCase()}</small>
              </li>
            ))}
          </ul>
        ) : (
          <p className="hs-empty">{logs.error || "Nenhum evento registrado ainda."}</p>
        )}
      </Panel>
    </div>
  );
}

/* ---------- carcaça ---------- */

export default function ScreensOverlay({ api, services, connected, onClose, onOpenMonitors, onSend, initialTab = "command" }) {
  const [tab, setTab] = useState(initialTab);

  useEffect(() => {
    if (initialTab) setTab(initialTab);
  }, [initialTab]);

  useEffect(() => {
    const onKey = (event) => {
      if (event.key === "Escape") {
        event.stopImmediatePropagation(); // não dispara o "cancelar" do App
        event.preventDefault();
        onClose();
        return;
      }
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;
      if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
        setTab((current) => {
          const index = TABS.findIndex(([id]) => id === current);
          const step = event.key === "ArrowRight" ? 1 : -1;
          return TABS[(index + step + TABS.length) % TABS.length][0];
        });
      }
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [onClose]);

  return (
    <div className="hs-overlay" role="dialog" aria-modal="true" aria-label="Telas do JARVIS">
      <header className="hs-head">
        <strong>TELAS</strong>
        <nav className="hs-tabs" role="tablist">
          {TABS.map(([id, label]) => (
            <button key={id} type="button" role="tab" aria-selected={tab === id} className={tab === id ? "on" : ""} onClick={() => setTab(id)}>
              {label}
            </button>
          ))}
        </nav>
        <div className="hs-head-actions">
          <button type="button" className="hl-btn" onClick={onOpenMonitors} title="Mover janelas para outro monitor">MONITORES</button>
          <button type="button" className="hl-btn hl-btn-danger" onClick={onClose} aria-label="Fechar telas">✕ FECHAR</button>
        </div>
      </header>

      <main className="hs-body" key={tab}>
        {tab === "command" && <CommandScreen api={api} />}
        {tab === "briefing" && <BriefingScreen onSend={onSend} />}
        {tab === "agenda" && <AgendaScreen api={api} />}
        {tab === "news" && <NewsScreen api={api} />}
        {tab === "datasources" && <DataSourcesScreen api={api} />}
        {tab === "finance" && <FinanceScreen api={api} />}
        {tab === "system" && <SystemScreen api={api} services={services} connected={connected} />}
      </main>

      <footer className="hs-foot">← → ALTERNAM AS TELAS · ESC FECHA</footer>
    </div>
  );
}

import { useEffect, useState } from "react";

const CATEGORIES = ["Todas", "Produtividade", "Comunicação", "Finanças", "Sensores e Clima", "Casa e dispositivos"];

// V5.6: agenda pelo "endereço secreto no formato iCal" do Google Agenda (sem criar projeto no Google Cloud)
export function IcsConnect({ api, onDone, hideHelp = false }) {
  const [url, setUrl] = useState("");
  const [state, setState] = useState({ busy: false, msg: "", ok: false });
  const save = async () => {
    setState({ busy: true, msg: "Lendo a agenda…", ok: false });
    try {
      const r = await api("/api/calendar/ics", { method: "POST", body: JSON.stringify({ url: url.trim() }), timeout: 25_000 });
      setState({ busy: false, ok: true, msg: `Agenda conectada: ${r.next_30_days ?? 0} compromissos nos próximos 30 dias.` });
      onDone?.();
    } catch (err) {
      setState({ busy: false, ok: false, msg: err.message });
    }
  };
  return (
    <div className="hs-ics">
      {!hideHelp && <p className="hs-ds-desc">
        Ou cole o <b>endereço secreto no formato iCal</b>: no Google Agenda (computador), Configurações › sua agenda ›
        Integrar agenda › <i>Endereço secreto no formato iCal</i>.
      </p>}
      <div className="hs-ics-row">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://calendar.google.com/calendar/ical/…/basic.ics"
          aria-label="Endereço iCal da agenda"
          autoComplete="off"
          spellCheck={false}
        />
        <button type="button" className="hl-btn" onClick={save} disabled={state.busy || !url.trim()}>
          {state.busy ? "LENDO…" : "USAR ESTA AGENDA"}
        </button>
      </div>
      {state.msg && <p className={`hs-ics-msg${state.ok ? " is-ok" : ""}`} role="status">{state.msg}</p>}
    </div>
  );
}

export default function DataSourcesScreen({ api }) {
  const [sources, setSources] = useState([]);
  const [category, setCategory] = useState("Todas");
  const [loading, setLoading] = useState(true);

  const [reload, setReload] = useState(0);
  useEffect(() => {
    let active = true;
    api("/api/datasources")
      .then((data) => {
        if (active) {
          setSources(data.sources || []);
          setLoading(false);
        }
      })
      .catch(() => active && setLoading(false));
    return () => { active = false; };
  }, [api, reload]);

  const filtered = sources.filter((s) => category === "Todas" || s.category === category);

  return (
    <div className="hs-stack">
      {/* Filtro por categoria */}
      <div className="hs-subtabs" role="tablist">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            type="button"
            className={category === cat ? "on" : ""}
            onClick={() => setCategory(cat)}
          >
            {cat.toUpperCase()}
          </button>
        ))}
      </div>

      <div className="hs-grid hs-grid-command">
        {filtered.map((item) => (
          <div key={item.id} className="hl-panel hs-ds-card">
            <div className="hl-panel-head">
              <span>{item.name}</span>
              <em className={item.status === "connected" ? "rc-source-connected" : ""}>
                {item.status === "connected" ? "● CONECTADO" : "＋ DISPONÍVEL"}
              </em>
            </div>
            <div className="hl-panel-body">
              <p className="hs-ds-desc">{item.description}</p>
              <div className="hs-ds-meta">
                <span className="hs-ds-cat">{item.category}</span>
                {item.id === "calendar" && item.status !== "connected" && (
                  <button
                    type="button"
                    className="hl-btn"
                    onClick={() => window.open(`${api.baseUrl || "http://localhost:8000"}/api/integrations/google-calendar/authorize`, "_blank")}
                  >
                    CONECTAR
                  </button>
                )}
              </div>
              {item.id === "calendar" && item.status !== "connected" && (
                <IcsConnect api={api} onDone={() => setReload((n) => n + 1)} />
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

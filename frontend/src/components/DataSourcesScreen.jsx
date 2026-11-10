import { useEffect, useState } from "react";

const CATEGORIES = ["Todas", "Produtividade", "Comunicação", "Finanças", "Sensores e Clima", "Casa e dispositivos"];

export default function DataSourcesScreen({ api }) {
  const [sources, setSources] = useState([]);
  const [category, setCategory] = useState("Todas");
  const [loading, setLoading] = useState(true);

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
  }, [api]);

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
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

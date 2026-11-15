import { useCallback, useEffect, useMemo, useState } from "react";
import { mapLayout } from "../utils/desk.js";

// V8.0: MEMÓRIA EM MAPA (Modo Desk): você no centro, os assuntos em volta e cada memória ligada ao seu assunto.
// Tocar numa bolinha mostra a memória (e dá para apagar); o campo embaixo guarda uma memória nova.
export default function DeskMemoryMap({ api, accent = "#22d3ee" }) {
  const [map, setMap] = useState(null);
  const [sel, setSel] = useState(null);
  const [text, setText] = useState("");
  const [msg, setMsg] = useState("");
  const load = useCallback(() => api("/api/desk/memory-map").then(setMap).catch((e) => setMsg(e.message)), [api]);
  useEffect(() => { load(); }, [load]);
  const pos = useMemo(() => mapLayout(map), [map]);
  const add = async (e) => {
    e.preventDefault();
    if (!text.trim()) return;
    try {
      await api("/api/memory", { method: "POST", body: JSON.stringify({ text: text.trim() }) });
      setText("");
      load();
    } catch (err) {
      setMsg(err.message);
    }
  };
  const forget = async () => {
    if (!sel || !window.confirm(`Esquecer: "${sel.rotulo}"?`)) return;
    try {
      setMap(await api("/api/desk/memory/forget", { method: "POST", body: JSON.stringify({ texto: sel.rotulo }) }));
      setSel(null);
    } catch (err) {
      setMsg(err.message);
    }
  };
  const nodes = map?.nos || [];
  return (
    <section className="dk-card dk-memory">
      <header><span className="dk-card-ico">✳</span><h3>Memória</h3><span className="dk-pill">{map?.total ?? 0} memórias</span></header>
      {map?.cloud ? <p className="dk-muted">O mapa da memória fica no PC.</p> : (
        <div className="dk-map">
          <svg viewBox="0 0 800 560" role="img" aria-label="Mapa da memória">
            {(map?.ligacoes || []).map((l) => pos[l.de] && pos[l.para] && (
              <line key={`${l.de}-${l.para}`} x1={pos[l.de].x} y1={pos[l.de].y} x2={pos[l.para].x} y2={pos[l.para].y} className={l.de === "eu" ? "is-main" : ""} />
            ))}
            {nodes.map((n) => pos[n.id] && (
              <g key={n.id} className={`dk-node is-${n.tipo}${sel?.id === n.id ? " is-sel" : ""}`} transform={`translate(${pos[n.id].x} ${pos[n.id].y})`}
                onClick={() => setSel(n.tipo === "memoria" ? n : null)} role={n.tipo === "memoria" ? "button" : undefined} tabIndex={n.tipo === "memoria" ? 0 : undefined}
                onKeyDown={(e) => { if (e.key === "Enter" && n.tipo === "memoria") setSel(n); }}>
                <circle r={n.tipo === "centro" ? 26 : n.tipo === "assunto" ? 18 : 7} style={n.tipo !== "memoria" ? { fill: accent } : undefined} />
                {n.tipo === "centro" && <text y="5" textAnchor="middle" className="dk-node-ico">★</text>}
                {n.tipo === "assunto" && <text y="5" textAnchor="middle" className="dk-node-ico">{n.icone}</text>}
                {n.tipo !== "memoria" && <text y={n.tipo === "centro" ? 44 : 34} textAnchor="middle">{n.rotulo}{n.qtd ? ` (${n.qtd})` : ""}</text>}
                {n.tipo === "memoria" && <title>{n.rotulo}</title>}
              </g>
            ))}
          </svg>
          {map && map.total === 0 && <p className="dk-map-empty">Ainda não sei nada sobre você. Guarde algo importante abaixo, ou diga "lembre que…".</p>}
        </div>
      )}
      {sel && (
        <div className="dk-map-sel" role="status">
          <span>{sel.rotulo}</span>
          <button type="button" className="dk-btn is-danger" onClick={forget}>🗑 ESQUECER</button>
          <button type="button" className="dk-del" onClick={() => setSel(null)} aria-label="Fechar">✕</button>
        </div>
      )}
      {!map?.cloud && (
        <form className="dk-add is-two" onSubmit={add}>
          <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Guardar algo importante (ex.: minha namorada se chama Ana)" aria-label="Nova memória" />
          <button type="submit" className="dk-btn is-main">＋ GUARDAR</button>
        </form>
      )}
      {msg && <p className="dk-err" role="alert">{msg}</p>}
    </section>
  );
}

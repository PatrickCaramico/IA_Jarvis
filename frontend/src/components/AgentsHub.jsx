import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

// V6.8.3: Central de Agentes (botão ao lado do Olho de Deus e em CONTROLES).
// - os agentes do JARVIS, o que fazem e exemplos (tocar envia o pedido);
// - lugares do agente de rotas (rota com um toque, adicionar, apagar);
// - chat com os agentes: o que você pede e o que eles fazem/respondem aparece aqui.
export default function AgentsHub({ api, onSend, onClose }) {
  const [agents, setAgents] = useState([]);
  const [places, setPlaces] = useState({});
  const [form, setForm] = useState({ name: "", address: "" });
  const [msg, setMsg] = useState("");
  const [chat, setChat] = useState([]);
  const [text, setText] = useState("");
  const endRef = useRef(null);

  const load = useCallback(() => {
    api("/api/agents").then((d) => {
      setAgents(d.agents || []);
      setPlaces(d.places || {});
    }).catch((err) => setMsg(err.message));
  }, [api]);
  useEffect(() => {
    load();
  }, [load]);

  // o que os agentes fazem (evento "agent") e as respostas do JARVIS entram no chat
  useEffect(() => {
    const onWs = (e) => {
      const m = e.detail || {};
      if (m.type === "agent" && m.status !== "working") {
        setChat((c) => [...c, { who: "agent", icon: m.icon, label: m.label, text: m.text }].slice(-40));
        if (m.agent === "rotas") load();
      } else if (m.type === "response" && m.text) {
        setChat((c) => (c.length && c[c.length - 1].who === "me" ? [...c, { who: "jarvis", text: m.text }].slice(-40) : c));
      }
    };
    window.addEventListener("jarvis_ws_event", onWs);
    return () => window.removeEventListener("jarvis_ws_event", onWs);
  }, [load]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [chat.length]);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const send = (t) => {
    const clean = String(t || "").trim();
    if (!clean) return;
    setChat((c) => [...c, { who: "me", text: clean }].slice(-40));
    onSend(clean);
  };

  const savePlace = async (e) => {
    e.preventDefault();
    if (!form.name.trim() || !form.address.trim()) return;
    try {
      const d = await api("/api/agents/places", { method: "POST", body: JSON.stringify(form) });
      setPlaces(d.places || {});
      setForm({ name: "", address: "" });
      setMsg("Lugar salvo.");
    } catch (err) {
      setMsg(err.message);
    }
  };

  const removePlace = async (name) => {
    if (!window.confirm(`Apagar o lugar "${name}"?`)) return;
    try {
      const d = await api(`/api/agents/places/${encodeURIComponent(name)}`, { method: "DELETE" });
      setPlaces(d.places || {});
    } catch (err) {
      setMsg(err.message);
    }
  };

  return createPortal(
    <div className="agh-overlay" role="dialog" aria-modal="true" aria-label="Central de Agentes" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="agh">
        <header className="agh-head">
          <span>🤖 CENTRAL DE AGENTES</span>
          <small>O JARVIS entrega cada pedido ao agente especialista</small>
          <button type="button" className="agh-x" onClick={onClose} aria-label="Fechar">✕</button>
        </header>

        <div className="agh-grid">
          <section className="agh-col">
            {agents.map((a) => (
              <article key={a.name} className="agh-card">
                <h3>{a.icon} {a.label}</h3>
                <p>{a.desc}</p>
                <div className="agh-examples">
                  {(a.examples || []).map((ex) => (
                    <button key={ex} type="button" onClick={() => send(ex)} title="Pedir isto">“{ex}”</button>
                  ))}
                </div>
                {a.name === "rotas" && (
                  <div className="agh-places">
                    {Object.keys(places).length === 0 ? (
                      <p className="agh-muted">Nenhum lugar salvo ainda.</p>
                    ) : (
                      <ul>
                        {Object.entries(places).map(([name, address]) => (
                          <li key={name}>
                            <span><b>{name}</b> · {address}</span>
                            <button type="button" onClick={() => send(`quero ir para ${name}`)}>▶ ROTA</button>
                            <button type="button" className="agh-del" onClick={() => removePlace(name)} aria-label={`Apagar ${name}`}>✕</button>
                          </li>
                        ))}
                      </ul>
                    )}
                    <form onSubmit={savePlace} className="agh-form">
                      <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Nome (trabalho)" aria-label="Nome do lugar" />
                      <input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} placeholder="Endereço (Av. Paulista, 1000)" aria-label="Endereço" />
                      <button type="submit">＋ SALVAR</button>
                    </form>
                  </div>
                )}
              </article>
            ))}
            {msg && <p className="agh-muted" role="status">{msg}</p>}
          </section>

          <section className="agh-chat" aria-label="Chat com os agentes">
            <div className="agh-log">
              {chat.length === 0 && <p className="agh-muted">Peça algo aos agentes. Ex.: “quero ir para o trabalho”, “procura receita de pão no YouTube”.</p>}
              {chat.map((m, i) => (
                <div key={i} className={`agh-msg is-${m.who}`}>
                  {m.who === "agent" ? <><b>{m.icon} {m.label}</b> {m.text}</> : m.text}
                </div>
              ))}
              <div ref={endRef} />
            </div>
            <form className="agh-input" onSubmit={(e) => { e.preventDefault(); send(text); setText(""); }}>
              <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Fale com os agentes…" aria-label="Mensagem para os agentes" />
              <button type="submit" disabled={!text.trim()}>ENVIAR</button>
            </form>
          </section>
        </div>
      </div>
    </div>,
    document.body,
  );
}

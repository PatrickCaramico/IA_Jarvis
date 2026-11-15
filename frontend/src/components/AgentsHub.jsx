import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import useEscape from "../hooks/useEscape.js";
import { CHAT_AGENTS } from "../utils/agentMention.js";
import FinancePanel from "./FinancePanel.jsx";

// V6.8.3: Central de Agentes. V7.9: UMA ABA POR AGENTE, cada uma com a própria conversa (salva no PC, últimas 30
// mensagens) — fala direto com o agente, sem passar pelo JARVIS principal. Ações simples acontecem na hora; as
// maiores aparecem com ✓ CONFIRMAR. O agente de rotas mantém os lugares salvos (rota com um toque, adicionar, apagar).

function PendingCard({ api, agent, action, onDone }) {
  const [state, setState] = useState("");
  const confirm = async () => {
    setState("…");
    try {
      const r = await api("/api/agents/chat/confirm", { method: "POST", body: JSON.stringify({ agent, acao: action }) });
      setState(r.text || "Feito.");
      onDone?.();
    } catch (err) {
      setState(err.message);
    }
  };
  return (
    <div className={`agh-pending${state && state !== "…" ? " is-done" : ""}`}>
      <span>{action.descricao}</span>
      {state && state !== "…" ? <b>{state}</b> : <button type="button" onClick={confirm} disabled={state === "…"}>✓ CONFIRMAR</button>}
    </div>
  );
}

function Places({ api, onSend }) {
  const [places, setPlaces] = useState({});
  const [form, setForm] = useState({ name: "", address: "" });
  const [msg, setMsg] = useState("");
  const load = useCallback(() => {
    api("/api/agents").then((d) => setPlaces(d.places || {})).catch(() => {});
  }, [api]);
  useEffect(() => {
    load();
  }, [load]);
  const save = async (e) => {
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
  const remove = async (name) => {
    if (!window.confirm(`Apagar o lugar "${name}"?`)) return;
    try {
      const d = await api(`/api/agents/places/${encodeURIComponent(name)}`, { method: "DELETE" });
      setPlaces(d.places || {});
    } catch (err) {
      setMsg(err.message);
    }
  };
  return (
    <div className="agh-places">
      <small className="agh-label">LUGARES SALVOS</small>
      {Object.keys(places).length === 0 ? <p className="agh-muted">Nenhum lugar salvo ainda.</p> : (
        <ul>
          {Object.entries(places).map(([name, address]) => (
            <li key={name}>
              <span><b>{name}</b> · {address}</span>
              <button type="button" onClick={() => onSend(`quero ir para ${name}`)}>▶ ROTA</button>
              <button type="button" className="agh-del" onClick={() => remove(name)} aria-label={`Apagar ${name}`}>✕</button>
            </li>
          ))}
        </ul>
      )}
      <form onSubmit={save} className="agh-form">
        <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Nome (trabalho)" aria-label="Nome do lugar" />
        <input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} placeholder="Endereço" aria-label="Endereço" />
        <button type="submit">＋ SALVAR</button>
      </form>
      {msg && <p className="agh-muted" role="status">{msg}</p>}
    </div>
  );
}

export default function AgentsHub({ api, onClose, onOpenHolo, initialAgent = "mercado" }) {
  const [agents, setAgents] = useState(CHAT_AGENTS);
  const [tab, setTab] = useState(initialAgent);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [finKey, setFinKey] = useState(0); // V7.10: atualiza o painel de finanças depois de cada resposta
  const endRef = useRef(null);
  useEscape(onClose);

  useEffect(() => {
    api("/api/agents").then((d) => d.chat_agents?.length && setAgents(d.chat_agents)).catch(() => {});
  }, [api]);

  const load = useCallback((id) => {
    api(`/api/agents/chat/${id}`).then((d) => setMessages(d.messages || [])).catch(() => setMessages([]));
  }, [api]);
  useEffect(() => {
    setError("");
    load(tab);
  }, [tab, load]);

  // uma resposta de agente pedida pelo campo de conversa (@) ou por voz atualiza a aba aberta
  useEffect(() => {
    const on = (e) => {
      if (e.detail?.agent === tab) load(tab);
    };
    window.addEventListener("jarvis-agent-reply", on);
    return () => window.removeEventListener("jarvis-agent-reply", on);
  }, [tab, load]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length, busy]);

  const agent = agents.find((a) => a.id === tab) || agents[0];

  const send = async (raw) => {
    const message = String(raw || "").trim();
    if (!message || busy) return;
    setBusy(true);
    setError("");
    setMessages((m) => [...m, { role: "user", text: message }]);
    try {
      const r = await api("/api/agents/chat", { method: "POST", body: JSON.stringify({ agent: tab, message }), timeout: 60_000 });
      setMessages((m) => [...m, { role: "agent", text: r.reply, done: r.done, pending: r.pending, sources: r.sources }]);
      if (tab === "financas") setFinKey((k) => k + 1);
      if (r.holo) onOpenHolo?.(r.holo);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const clearChat = async () => {
    if (!window.confirm(`Apagar a conversa com o ${agent.label.toLowerCase()}?`)) return;
    await api(`/api/agents/chat/${tab}`, { method: "DELETE" }).catch(() => {});
    setMessages([]);
  };

  return createPortal(
    <div className="agh-overlay" role="dialog" aria-modal="true" aria-label="Central de Agentes" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="agh">
        <header className="agh-head">
          <span>🤖 CENTRAL DE AGENTES</span>
          <small>Fale direto com cada um. No campo de conversa, use @nome.</small>
          <button type="button" className="agh-x" onClick={onClose} aria-label="Fechar">✕</button>
        </header>

        <nav className="agh-tabs" role="tablist" aria-label="Agentes">
          {agents.map((a) => (
            <button key={a.id} type="button" role="tab" aria-selected={tab === a.id} className={tab === a.id ? "is-on" : ""} onClick={() => setTab(a.id)}>
              <span aria-hidden="true">{a.icon}</span>{a.label.replace(/^Agente (de |do |da )?/i, "")}
            </button>
          ))}
        </nav>

        <div className={`agh-grid${tab === "financas" ? " is-fin" : ""}`} key={tab}>
          <section className="agh-col">
            <article className="agh-card">
              <h3>{agent.icon} {agent.label} <code>@{agent.id}</code></h3>
              <p>{agent.desc}</p>
              {agent.pc && <p className="agh-muted">Fora de casa este agente precisa do PC ligado.</p>}
              <small className="agh-label">EXPERIMENTE</small>
              <div className="agh-examples">
                {(agent.examples || []).map((ex) => (
                  <button key={ex} type="button" onClick={() => send(ex)} disabled={busy}>“{ex}”</button>
                ))}
              </div>
              {tab === "rotas" && <Places api={api} onSend={send} />}
              {tab === "financas" && <FinancePanel api={api} refreshKey={finKey} onAsk={send} />}
              <button type="button" className="agh-clear" onClick={clearChat} disabled={!messages.length}>🗑 LIMPAR CONVERSA</button>
            </article>
          </section>

          <section className="agh-chat" aria-label={`Conversa com o ${agent.label}`}>
            <div className="agh-log">
              {messages.length === 0 && !busy && <p className="agh-muted">Comece a conversa com o {agent.label.toLowerCase()}. Ele lembra das últimas 30 mensagens.</p>}
              {messages.map((m, i) => (
                <div key={i} className={`agh-msg ${m.role === "user" ? "is-me" : "is-agent"}`}>
                  {m.role !== "user" && <b className="agh-who">{agent.icon} {agent.label.replace(/^Agente (de |do |da )?/i, "")}</b>}
                  <span>{m.text}</span>
                  {(m.done || []).map((d) => <em key={d} className="agh-done">{d}</em>)}
                  {(m.pending || []).map((p, j) => <PendingCard key={j} api={api} agent={tab} action={p} onDone={() => setFinKey((k) => k + 1)} />)}
                  {(m.sources || []).length > 0 && (
                    <span className="agh-sources">{m.sources.map((s) => <a key={s.url} href={s.url} target="_blank" rel="noreferrer">{s.name || "fonte"}</a>)}</span>
                  )}
                </div>
              ))}
              {busy && <div className="agh-msg is-agent agh-typing" aria-label="digitando"><i /><i /><i /></div>}
              <div ref={endRef} />
            </div>
            {error && <p className="agh-error" role="alert">{error}</p>}
            <form className="agh-input" onSubmit={(e) => { e.preventDefault(); send(text); setText(""); }}>
              <input value={text} onChange={(e) => setText(e.target.value)} placeholder={`Fale com @${agent.id}…`} aria-label={`Mensagem para o ${agent.label}`} />
              <button type="submit" disabled={!text.trim() || busy}>ENVIAR</button>
            </form>
          </section>
        </div>
      </div>
    </div>,
    document.body,
  );
}

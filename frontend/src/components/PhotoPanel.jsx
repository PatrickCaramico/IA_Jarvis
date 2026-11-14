import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import useEscape from "../hooks/useEscape.js";
import { Diagnosis } from "./CameraWindow.jsx";

// V7.8: FOTO ENVIADA (galeria, clipe 📎 ou arrastar no PC). 4 funções:
// 🔍 ANALISAR (diagnóstico) · 📄 LER E AGIR (propõe; só faz depois do CONFIRMAR) · 🌐 PESQUISAR · ✦ HOLOGRAMA.
// A foto fica só na memória desta tela: fechou, sumiu. Nada é gravado no PC nem na nuvem.
const MODES = [
  ["analisar", "🔍", "ANALISAR", "O que é, detalhes e dicas"],
  ["ler", "📄", "LER E AGIR", "Lista, lembrete, contato"],
  ["pesquisar", "🌐", "PESQUISAR", "Preço e onde comprar"],
  ["holograma", "✦", "HOLOGRAMA", "Explicação animada"],
];
const ACTION_ICON = { compras: "🛒", tarefas: "☑", lembrete: "⏰", contato: "👤" };

function ActionCard({ api, action }) {
  const [state, setState] = useState({ busy: false, done: "", error: "" });
  const confirm = async () => {
    setState({ busy: true, done: "", error: "" });
    try {
      const r = await api("/api/photo/apply", { method: "POST", body: JSON.stringify({ acao: action }) });
      setState({ busy: false, done: r.text || "Feito.", error: "" });
    } catch (err) {
      setState({ busy: false, done: "", error: err.message });
    }
  };
  return (
    <div className={`ph-action${state.done ? " is-done" : ""}`}>
      <b>{ACTION_ICON[action.tipo]} {action.titulo}</b>
      {action.itens && <ul>{action.itens.map((i) => <li key={i}>{i}</li>)}</ul>}
      {action.tipo === "lembrete" && <p>{action.texto} · {action.data_hora.slice(0, 10).split("-").reverse().join("/")} às {action.data_hora.slice(11)}</p>}
      {action.tipo === "contato" && <p>{action.nome} · {action.telefone}</p>}
      {state.done ? <span className="ph-done">✓ {state.done}</span> : (
        <button type="button" onClick={confirm} disabled={state.busy}>{state.busy ? "FAZENDO…" : "✓ CONFIRMAR"}</button>
      )}
      {state.error && <span className="ph-error">{state.error}</span>}
    </div>
  );
}

export default function PhotoPanel({ api, photo, onClose, onSpeak, onOpenHolo }) {
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  useEscape(onClose);

  useEffect(() => () => setResult(null), []);

  const ask = async (mode) => {
    if (busy) return;
    setBusy(mode);
    setError("");
    setResult(null);
    try {
      const r = await api("/api/photo/ask", { method: "POST", body: JSON.stringify({ image: photo, question: question.trim(), mode }), timeout: 90_000 });
      if (r.mode === "holograma" && r.holo_topic) {
        onSpeak?.(r.text);
        onOpenHolo(r.holo_topic, photo);
        return;
      }
      setResult(r);
      if (r.text) onSpeak?.(r.text);
    } catch (err) {
      setError(err.message || "Não consegui analisar a foto agora.");
    } finally {
      setBusy("");
    }
  };

  return createPortal(
    <div className="ph-overlay" role="dialog" aria-modal="true" aria-label="Foto enviada" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="ph">
        <header className="ph-head">
          <span>🖼 FOTO ENVIADA</span>
          <small>Não é guardada: fechou, sumiu.</small>
          <button type="button" className="ph-x" onClick={onClose} aria-label="Fechar">✕</button>
        </header>
        <div className="ph-body">
          <div className={`ph-preview${busy ? " is-scanning" : ""}`}>
            <img src={photo} alt="Foto enviada" />
            {busy && <i className="ph-scan" aria-hidden="true" />}
          </div>
          <form className="ph-ask" onSubmit={(e) => { e.preventDefault(); ask("auto"); }}>
            <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Pergunta (opcional): quanto custa? que planta é essa?" aria-label="Pergunta sobre a foto" />
            <button type="submit" disabled={Boolean(busy)}>PERGUNTAR</button>
          </form>
          <div className="ph-modes">
            {MODES.map(([id, icon, label, sub]) => (
              <button type="button" key={id} className={busy === id ? "is-busy" : ""} disabled={Boolean(busy)} onClick={() => ask(id)}>
                <span aria-hidden="true">{icon}</span><b>{busy === id ? "…" : label}</b><small>{sub}</small>
              </button>
            ))}
          </div>
          {error && <p className="ph-error" role="alert">{error}</p>}
          {result && !result.diagnostico && (
            <div className="ph-result" role="status">
              <p className="ph-text">{result.leitura?.resumo || result.pesquisa?.resposta || result.text}</p>
              {result.leitura?.acoes?.length > 0 && (
                <div className="ph-actions">
                  <small>O JARVIS SUGERE (só faz se você confirmar):</small>
                  {result.leitura.acoes.map((a, i) => <ActionCard key={i} api={api} action={a} />)}
                </div>
              )}
              {result.leitura && !result.leitura.acoes?.length && <p className="ph-muted">Nada para adicionar a partir desta foto.</p>}
              {result.pesquisa?.fontes?.length > 0 && (
                <div className="ph-sources">
                  <small>FONTES</small>
                  {result.pesquisa.fontes.map((f) => <a key={f.url} href={f.url} target="_blank" rel="noreferrer">{f.name || f.url}</a>)}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      {result?.diagnostico && <Diagnosis diag={{ ...result.diagnostico, photo }} onClose={() => setResult(null)} />}
    </div>,
    document.body,
  );
}

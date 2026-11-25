import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import useEscape from "../hooks/useEscape.js";

// V9.5.6: 💡 BLOCO DE IDEIAS (CONTROLES). Rascunhos de ideias e projetos que ficam salvos no PC (data/ideias.json).
// 📌 = projeto em andamento: os projetos entram no briefing do dia. Também por voz: "anota uma ideia: ...",
// "nova ideia de projeto: ...", "quais são meus projetos".
function fmt(ts) {
  const d = new Date(Number(ts) * 1000);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

export default function IdeasPad({ api, onClose }) {
  useEscape(onClose);
  const [items, setItems] = useState(null);
  const [error, setError] = useState("");
  const [draft, setDraft] = useState({ titulo: "", texto: "", projeto: false });
  const [editing, setEditing] = useState(null); // { id, titulo, texto }
  const [confirmDel, setConfirmDel] = useState(null);
  const [busy, setBusy] = useState(false);

  const [google, setGoogle] = useState(null); // V9.5.6: { configured, connected, tasks }
  const load = useCallback((sync = false) => {
    // sync = traz o que foi anotado no app do Google Tarefas (lista "Ideias JARVIS")
    api(`/api/ideas${sync ? "?sync=1" : ""}`, sync ? { timeout: 30_000 } : undefined)
      .then((d) => { setItems(d.ideas || []); setGoogle(d.google || null); setError(""); })
      .catch(() => setError("Não consegui carregar o bloco de ideias agora."));
  }, [api]);
  useEffect(() => { load(true); }, [load]);
  const connectGoogle = () => window.open(`${api.baseUrl || "http://localhost:8000"}/api/integrations/google-calendar/authorize`, "_blank");
  useEffect(() => { // outra tela ou a voz mudou o bloco
    const on = (e) => { if (e.detail?.type === "ideas_updated") load(); };
    window.addEventListener("jarvis_ws_event", on);
    return () => window.removeEventListener("jarvis_ws_event", on);
  }, [load]);

  const call = async (path, opts) => {
    setBusy(true);
    try {
      await api(path, opts);
      load();
      return true;
    } catch (err) {
      setError(err?.message || "Não deu certo. Tente de novo.");
      return false;
    } finally {
      setBusy(false);
    }
  };
  const add = async (e) => {
    e.preventDefault();
    if (!draft.texto.trim() && !draft.titulo.trim()) return;
    if (await call("/api/ideas", { method: "POST", body: JSON.stringify(draft) })) setDraft({ titulo: "", texto: "", projeto: false });
  };
  const save = async () => {
    if (await call(`/api/ideas/${editing.id}`, { method: "PATCH", body: JSON.stringify({ titulo: editing.titulo, texto: editing.texto }) })) setEditing(null);
  };
  const toggleProject = (i) => call(`/api/ideas/${i.id}`, { method: "PATCH", body: JSON.stringify({ projeto: !i.projeto }) });
  const remove = async (id) => { if (await call(`/api/ideas/${id}`, { method: "DELETE" })) setConfirmDel(null); };

  const projects = (items || []).filter((i) => i.projeto).length;
  return createPortal(
    <div className="lgw-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <section className="lgw idp" role="dialog" aria-modal="true" aria-label="Bloco de ideias">
        <header className="lgw-head">
          <div>
            <h2>💡 BLOCO DE IDEIAS</h2>
            <span>{items ? `${items.length} ${items.length === 1 ? "ideia" : "ideias"} · ${projects} ${projects === 1 ? "projeto" : "projetos"} no briefing do dia` : "Carregando…"}</span>
          </div>
          <button type="button" className="lgw-btn" onClick={onClose} aria-label="Fechar">✕</button>
        </header>

        {google && (
          <div className={`idp-sync${google.tasks ? " is-on" : ""}`} role="status">
            {google.tasks ? (
              <>
                <span>☁ Sincronizado com o <b>Google Tarefas</b> (lista "Ideias JARVIS"). O que anotar lá pelo celular aparece aqui; 📌 no título = projeto.</span>
                <button type="button" className="lgw-btn" onClick={() => load(true)}>↻ SINCRONIZAR</button>
              </>
            ) : google.configured ? (
              <>
                <span>{google.connected
                  ? "Falta a permissão do Google Tarefas: conecte o Google de novo uma vez para as ideias irem para lá."
                  : "Conecte o Google para as ideias irem também para o Google Tarefas (no celular, no Gmail e na Agenda)."}</span>
                <button type="button" className="lgw-btn idp-save" onClick={connectGoogle}>☁ CONECTAR GOOGLE TAREFAS</button>
              </>
            ) : (
              <span>Para sincronizar com o Google Tarefas, configure o Google em Configurações › Integrações. Enquanto isso, as ideias ficam salvas aqui.</span>
            )}
          </div>
        )}

        <form className="idp-new" onSubmit={add}>
          <input value={draft.titulo} onChange={(e) => setDraft({ ...draft, titulo: e.target.value })} placeholder="Título (opcional)" maxLength={80} />
          <textarea value={draft.texto} onChange={(e) => setDraft({ ...draft, texto: e.target.value })}
            placeholder="Escreva a ideia… (ou diga: Jarvis, anota uma ideia: …)" rows={3} maxLength={4000} />
          <div className="idp-row">
            <label className="idp-check">
              <input type="checkbox" checked={draft.projeto} onChange={(e) => setDraft({ ...draft, projeto: e.target.checked })} />
              📌 É um projeto (entra no briefing do dia)
            </label>
            <button type="submit" className="lgw-btn idp-save" disabled={busy || (!draft.texto.trim() && !draft.titulo.trim())}>＋ SALVAR IDEIA</button>
          </div>
        </form>

        {error && <p className="lgw-error" role="alert">{error}</p>}
        <ul className="idp-list">
          {items && items.length === 0 && <li className="idp-empty">Nenhuma ideia ainda. A primeira fica aqui e no briefing de amanhã.</li>}
          {(items || []).map((i) => (
            <li key={i.id} className={`idp-item${i.projeto ? " is-project" : ""}`}>
              {editing?.id === i.id ? (
                <div className="idp-edit">
                  <input value={editing.titulo} onChange={(e) => setEditing({ ...editing, titulo: e.target.value })} maxLength={80} />
                  <textarea value={editing.texto} onChange={(e) => setEditing({ ...editing, texto: e.target.value })} rows={4} maxLength={4000} />
                  <div className="idp-row">
                    <button type="button" className="lgw-btn" onClick={() => setEditing(null)}>CANCELAR</button>
                    <button type="button" className="lgw-btn idp-save" disabled={busy} onClick={save}>✓ SALVAR</button>
                  </div>
                </div>
              ) : (
                <>
                  <button type="button" className={`idp-pin${i.projeto ? " is-on" : ""}`} onClick={() => toggleProject(i)} disabled={busy}
                    title={i.projeto ? "Projeto (entra no briefing). Toque para virar só ideia." : "Marcar como projeto (entra no briefing do dia)"}
                    aria-pressed={Boolean(i.projeto)}>📌</button>
                  <div className="idp-body">
                    <b>{i.titulo}</b>
                    {i.texto && i.texto !== i.titulo && <p>{i.texto}</p>}
                    <small>{i.projeto ? "PROJETO · " : ""}{fmt(i.atualizado)}</small>
                  </div>
                  <div className="idp-acts">
                    <button type="button" className="lgw-btn" onClick={() => setEditing({ id: i.id, titulo: i.titulo, texto: i.texto || "" })}>EDITAR</button>
                    {confirmDel === i.id ? (
                      <button type="button" className="lgw-btn idp-del" disabled={busy} onClick={() => remove(i.id)}>APAGAR?</button>
                    ) : (
                      <button type="button" className="lgw-btn" onClick={() => setConfirmDel(i.id)} aria-label="Apagar">🗑</button>
                    )}
                  </div>
                </>
              )}
            </li>
          ))}
        </ul>
      </section>
    </div>,
    document.body,
  );
}

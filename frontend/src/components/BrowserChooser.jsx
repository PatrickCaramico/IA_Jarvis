import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

// V6.5.11: "Em qual navegador, senhor?" — a lista aparece junto com a pergunta.
// Tocar abre lá; "Lembrar" faz o JARVIS usar sempre esse (dá para mudar em Configurações › Mídia & Foco).
// Responder falando ("no Chrome", "sempre no Edge") também fecha esta janela.
const ICONS = { chrome: "🟡", edge: "🌊", firefox: "🦊", brave: "🦁", opera: "⭕", default: "🖥" };

export default function BrowserChooser({ api, browsers, onClose }) {
  const [remember, setRemember] = useState(false);
  const [busy, setBusy] = useState("");

  useEffect(() => {
    const t = setTimeout(onClose, 120000); // o pedido vale 2 minutos
    return () => clearTimeout(t);
  }, [onClose]);

  const pick = async (id) => {
    setBusy(id);
    try {
      await api("/api/browser/choose", { method: "POST", body: JSON.stringify({ browser: id, remember }) });
    } catch {
      /* o PC responde por voz; se falhar, a janela fecha do mesmo jeito */
    }
    onClose();
  };

  const options = [...browsers, { id: "default", name: "Padrão do Windows" }];
  return createPortal(
    <div className="bc-window" role="dialog" aria-label="Escolher o navegador">
      <header className="bc-head">
        <span>🌐 EM QUAL NAVEGADOR?</span>
        <button type="button" className="la-x" onClick={() => pick("cancel")} aria-label="Cancelar">✕</button>
      </header>
      <div className="bc-list">
        {options.map((b) => (
          <button key={b.id} type="button" className="bc-opt" onClick={() => pick(b.id)} disabled={Boolean(busy)}>
            <span aria-hidden="true">{ICONS[b.id] || "🌐"}</span>
            {b.name}
            {busy === b.id && <small> · abrindo…</small>}
          </button>
        ))}
      </div>
      <label className="bc-remember">
        <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
        Lembrar a escolha (não perguntar mais)
      </label>
      <p className="bc-hint">Ou diga: "no Chrome", "sempre no Edge"…</p>
    </div>,
    document.body,
  );
}

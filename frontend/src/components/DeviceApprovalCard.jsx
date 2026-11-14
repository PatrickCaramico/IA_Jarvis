import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { api } from "../utils/api.js";

// V7.6: na tela do PC, cada aparelho novo pedindo acesso aparece aqui: PERMITIR / RECUSAR.
// Só a tela do próprio PC aprova (o servidor confere). Some sozinho quando o pedido expira.
const ICON = { celular: "📱", tablet: "📲", tv: "📺", pc: "💻", outro: "🔌" };

export default function DeviceApprovalCard() {
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState("");

  const load = useCallback(() => {
    api("/api/security/pending").then((d) => setItems(d.items || [])).catch(() => {});
  }, []);

  useEffect(() => {
    load();
    const on = (e) => {
      if (e.detail?.type === "device_request") setItems(e.detail.items || []);
    };
    window.addEventListener("jarvis_ws_event", on);
    return () => window.removeEventListener("jarvis_ws_event", on);
  }, [load]);

  useEffect(() => {
    if (!items.length) return undefined;
    const t = setInterval(() => {
      setItems((list) => list.map((i) => ({ ...i, seconds_left: i.seconds_left - 1 })).filter((i) => i.seconds_left > 0));
    }, 1000);
    return () => clearInterval(t);
  }, [items.length]);

  const decide = async (id, approve) => {
    setBusy(id);
    try {
      await api(`/api/security/pending/${id}`, { method: "POST", body: JSON.stringify({ approve }) });
    } catch {
      /* já expirou: a lista atualiza */
    }
    setBusy("");
    load();
  };

  if (!items.length) return null;
  return createPortal(
    <div className="dac-stack" role="region" aria-label="Aparelhos pedindo acesso">
      {items.map((i) => (
        <div className="dac" key={i.id} role="alertdialog" aria-label={`${i.name} quer se conectar`}>
          <div className="dac-head">
            <span className="dac-icon" aria-hidden="true">{ICON[i.kind] || "🔌"}</span>
            <div>
              <small>APARELHO NOVO QUER SE CONECTAR</small>
              <b>{i.name}</b>
              <span>{i.ip} · expira em {i.seconds_left} s</span>
            </div>
          </div>
          <p>Só permita se for um aparelho seu ou de alguém da casa.</p>
          <div className="dac-actions">
            <button type="button" className="is-no" disabled={busy === i.id} onClick={() => decide(i.id, false)}>✕ RECUSAR</button>
            <button type="button" className="is-yes" disabled={busy === i.id} onClick={() => decide(i.id, true)}>✓ PERMITIR</button>
          </div>
        </div>
      ))}
    </div>,
    document.body,
  );
}

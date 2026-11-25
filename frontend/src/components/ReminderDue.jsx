import { useEffect, useState } from "react";

// V9.5.6: AVISO DE LEMBRETE. Quando um lembrete vence, a central abre este aviso (fica até o senhor tocar em OK ou
// ADIAR) e toca um sinal. Antes o lembrete vencido virava só uma linha no Canal Ativo e, se a voz não saísse,
// passava despercebido. Com a central bloqueada, o texto não aparece (pode ser pessoal).
export default function ReminderDue({ api, items = [], onDone }) {
  const item = items[0];
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  useEffect(() => {
    setNote("");
    setBusy(false);
  }, [item?.key]);
  if (!item) return null;

  const postpone = async (minutos) => {
    if (item.id == null) {
      onDone(item.key);
      return;
    }
    setBusy(true);
    try {
      await api(`/api/reminders/${item.id}/postpone`, { method: "POST", body: JSON.stringify({ minutos }) });
      onDone(item.key);
    } catch {
      setNote("Não consegui adiar agora. Tente de novo.");
      setBusy(false);
    }
  };

  return (
    <div className="rdu-wrap" role="alertdialog" aria-live="assertive" aria-label="Lembrete">
      <section className="rdu">
        <span className="rdu-bell" aria-hidden="true">⏰</span>
        <div className="rdu-main">
          <span className="rdu-tag">LEMBRETE{item.hora ? ` · ${item.hora}` : ""}{item.atrasado ? " · VENCEU COM O PC DESLIGADO" : ""}</span>
          <p className="rdu-text">{item.texto || "Há um lembrete para o senhor. Desbloqueie a central para ver."}</p>
          {note && <p className="rdu-note" role="status">{note}</p>}
          <div className="rdu-actions">
            <button type="button" className="rdu-btn" disabled={busy} onClick={() => postpone(10)}>ADIAR 10 MIN</button>
            <button type="button" className="rdu-btn" disabled={busy} onClick={() => postpone(60)}>ADIAR 1 H</button>
            <button type="button" className="rdu-btn is-main" disabled={busy} onClick={() => onDone(item.key)} autoFocus>OK</button>
          </div>
        </div>
        {items.length > 1 && <span className="rdu-more">+{items.length - 1}</span>}
      </section>
    </div>
  );
}

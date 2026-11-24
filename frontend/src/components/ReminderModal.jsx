import { useState } from "react";
import { createPortal } from "react-dom";
import useEscape from "../hooks/useEscape.js";
import { fromInput, quickTimes, toApi, toInput, whenLabel } from "../utils/reminderTime.js";

// V9.4.2: NOVO LEMBRETE (CONTROLES › AÇÕES RÁPIDAS e o ＋ da faixa de lembretes). O lembrete fica na faixa da
// central até a hora e, na hora, o JARVIS avisa como os lembretes criados por voz.
export default function ReminderModal({ api, onClose, onSaved }) {
  const quick = quickTimes();
  const [text, setText] = useState("");
  const [when, setWhen] = useState(toInput(quick[0].at));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEscape(onClose);

  const save = async (e) => {
    e.preventDefault();
    const at = fromInput(when);
    if (!text.trim()) return setError("Escreva do que o JARVIS deve lembrar.");
    if (!at || at.getTime() < Date.now() - 60_000) return setError("Escolha um horário que ainda não passou.");
    setBusy(true);
    setError("");
    try {
      await api("/api/reminders", { method: "POST", body: JSON.stringify({ texto: text.trim(), data_hora: toApi(at) }) });
      onSaved?.();
      onClose();
    } catch (err) {
      setError(err.message || "Não consegui salvar o lembrete.");
      setBusy(false);
    }
  };

  return createPortal(
    <div className="rmd-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <form className="rmd" role="dialog" aria-modal="true" aria-label="Novo lembrete" onSubmit={save}>
        <header className="rmd-head">
          <h2>⏰ NOVO LEMBRETE</h2>
          <button type="button" className="sp-close" onClick={onClose} aria-label="Fechar">✕</button>
        </header>
        <label className="rmd-field">
          <span>Lembrar de</span>
          <input autoFocus value={text} maxLength={200} onChange={(e) => setText(e.target.value)} placeholder="Ex.: ligar para a mãe" />
        </label>
        <div className="rmd-quick" role="group" aria-label="Horários rápidos">
          {quick.map((q) => (
            <button key={q.label} type="button" className={toInput(q.at) === when ? "is-on" : ""} onClick={() => setWhen(toInput(q.at))}>
              {q.label}
            </button>
          ))}
        </div>
        <label className="rmd-field">
          <span>Quando</span>
          <input type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} />
        </label>
        {fromInput(when) && <p className="rmd-hint">Fica na faixa de lembretes da central e eu aviso na hora: {whenLabel(fromInput(when))}.</p>}
        {error && <p className="rmd-error" role="alert">{error}</p>}
        <div className="rmd-actions">
          <button type="button" onClick={onClose}>CANCELAR</button>
          <button type="submit" className="is-main" disabled={busy}>{busy ? "SALVANDO…" : "✓ CRIAR LEMBRETE"}</button>
        </div>
      </form>
    </div>,
    document.body,
  );
}

import { useEffect, useState } from "react";
import { soonText } from "../utils/updateSoon.js";

// V9.4.1: aviso da ATUALIZAÇÃO AUTOMÁTICA. O PC confere a cada 40 min; com versão nova, avisa aqui (e no celular e
// por voz) e atualiza sozinho em 2 minutos, num momento em que o JARVIS não está falando nem há algo em tela cheia.
// ATUALIZAR AGORA pula a espera; ADIAR 1 H deixa para depois.
export default function UpdateSoon({ api, soon, onClose }) {
  const [now, setNow] = useState(Date.now());
  const [busy, setBusy] = useState("");
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  if (!soon) return null;
  const act = async (path, label) => {
    setBusy(label);
    try {
      await api(path, { method: "POST" });
      if (path.endsWith("postpone")) onClose();
    } catch {
      setBusy("");
    }
  };
  return (
    <div className="upd-soon" role="status" aria-live="polite">
      <i aria-hidden="true">⬆</i>
      <div className="upd-soon-txt">
        <b>VERSÃO {soon.version} DISPONÍVEL</b>
        <span>{busy === "now" ? "Atualizando assim que o JARVIS ficar livre…" : soonText(soon.until, now)}</span>
        {soon.notes?.[0] && <small>{soon.notes[0]}</small>}
      </div>
      <button type="button" className="upd-soon-btn is-main" disabled={Boolean(busy)} onClick={() => act("/api/system/update/now", "now")}>
        ATUALIZAR AGORA
      </button>
      <button type="button" className="upd-soon-btn" disabled={Boolean(busy)} onClick={() => act("/api/system/update/postpone", "later")}>
        ADIAR 1 H
      </button>
    </div>
  );
}

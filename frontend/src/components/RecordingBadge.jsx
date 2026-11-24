import { useEffect, useState } from "react";
import { recordingText } from "../utils/lockExtras.js";

// V9.4: selo ⏺ GRAVANDO do modo gravar. O PC manda {type: "recording", active, label, steps, max} a cada passo
// gravado. Tocar no selo para a gravação (o mesmo que dizer "para de gravar").
export default function RecordingBadge({ onStop }) {
  const [rec, setRec] = useState(null);
  useEffect(() => {
    const on = (e) => {
      if (e.detail?.type === "recording") setRec(e.detail.active ? e.detail : null);
    };
    window.addEventListener("jarvis_ws_event", on);
    return () => window.removeEventListener("jarvis_ws_event", on);
  }, []);
  const text = recordingText(rec);
  if (!text) return null;
  return (
    <button type="button" className="rec-badge" onClick={() => onStop?.("para de gravar")}
      title="Tocar para parar e salvar a gravação (ou diga: para de gravar)" aria-live="polite">
      <i aria-hidden="true" />
      <span>{text}</span>
      <b>PARAR</b>
    </button>
  );
}

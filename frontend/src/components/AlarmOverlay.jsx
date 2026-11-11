// V5.1: alarme tocando (como a Alexa). Aparece na central e na tela de bloqueio.
// PARAR desliga; SONECA adia 9 minutos. Por voz: "Jarvis, parar" ou "soneca".
// Com a central bloqueada, o backend não manda o rótulo (pode ser pessoal).
import { useEffect, useRef } from "react";

export default function AlarmOverlay({ alarm, onStop, onSnooze }) {
  const stopRef = useRef(null);
  useEffect(() => {
    if (!alarm) return undefined;
    stopRef.current?.focus();
    const onKey = (e) => {
      if (e.key === "Escape" || e.key === "Enter") onStop();
      if (e.key.toLowerCase() === "s") onSnooze();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [alarm, onStop, onSnooze]);

  if (!alarm) return null;
  return (
    <div className="alarm-back" role="alertdialog" aria-modal="true" aria-labelledby="alarm-title" aria-describedby="alarm-hint">
      <div className="alarm-card">
        <div className="alarm-rings" aria-hidden="true"><i /><i /><i /></div>
        <div className="alarm-eyebrow" id="alarm-title">⏰ ALARME</div>
        <div className="alarm-time">{alarm.hora}</div>
        {alarm.rotulo && <div className="alarm-label">{alarm.rotulo}</div>}
        <div className="alarm-actions">
          <button ref={stopRef} type="button" className="alarm-stop" onClick={onStop}>PARAR</button>
          <button type="button" className="alarm-snooze" onClick={onSnooze}>
            SONECA · {alarm.snooze_minutes || 9} MIN
          </button>
        </div>
        <p className="alarm-hint" id="alarm-hint">
          Diga “Jarvis, parar” ou “soneca”.<br />
          <span className="alarm-keys">ENTER: parar · S: soneca</span>
        </p>
      </div>
    </div>
  );
}

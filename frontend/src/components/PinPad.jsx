import { useEffect, useState } from "react";
import useNow from "../hooks/useNow.js";

// Teclado numérico do PIN de reserva (seção 17.1). Aceita também o teclado físico.
export default function PinPad({ onSubmit, onCancel, busy = false, message = "", lockedUntil = null }) {
  const [pin, setPin] = useState("");
  const now = useNow(Boolean(lockedUntil)).getTime();
  const locked = lockedUntil && lockedUntil * 1000 > now;


  const submit = () => {
    if (pin.length < 4 || busy || locked) return;
    const value = pin;
    setPin("");
    onSubmit(value);
  };

  useEffect(() => {
    const onKey = (e) => {
      if (e.repeat) return;
      if (/^\d$/.test(e.key)) {
        e.preventDefault();
        e.stopPropagation();
        setPin((p) => (p.length < 8 ? p + e.key : p));
      } else if (e.key === "Backspace") {
        e.preventDefault();
        e.stopPropagation();
        setPin((p) => p.slice(0, -1));
      } else if (e.key === "Enter") {
        e.preventDefault();
        e.stopPropagation();
        submit();
      } else if (e.key === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        onCancel();
      } else if (e.code === "Space") {
        e.preventDefault();
        e.stopPropagation(); // espaço não dispara o escaneamento enquanto digita o PIN
      }
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  });

  const remaining = locked ? Math.max(0, Math.ceil(lockedUntil - now / 1000)) : 0;
  const keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "⌫", "0", "OK"];

  return (
    <div className="pp-root" role="group" aria-label="Digite o PIN">
      <div className="pp-title">PIN DE RESERVA</div>
      <div className="pp-dots" aria-live="polite" aria-label={`${pin.length} dígitos digitados`}>
        {Array.from({ length: Math.max(4, pin.length) }, (_, i) => (
          <span key={i} className={i < pin.length ? "on" : ""} />
        ))}
      </div>
      {locked ? (
        <div className="pp-msg is-error">PIN bloqueado. Tente em {Math.floor(remaining / 60)}:{String(remaining % 60).padStart(2, "0")}</div>
      ) : (
        message && <div className="pp-msg">{message}</div>
      )}
      <div className="pp-grid">
        {keys.map((k) => (
          <button
            key={k}
            type="button"
            disabled={busy || locked}
            className={k === "OK" ? "pp-ok" : ""}
            onClick={() => {
              if (k === "⌫") setPin((p) => p.slice(0, -1));
              else if (k === "OK") submit();
              else setPin((p) => (p.length < 8 ? p + k : p));
            }}
            aria-label={k === "⌫" ? "Apagar" : k === "OK" ? "Confirmar PIN" : k}
          >
            {k}
          </button>
        ))}
      </div>
      <button type="button" className="pp-cancel" onClick={onCancel}>Voltar ao escaneamento facial</button>
    </div>
  );
}

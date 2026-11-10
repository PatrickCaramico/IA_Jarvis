import { useState } from "react";

function MicIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
    </svg>
  );
}

// Campo de texto + botão de microfone (a barra de espaço também liga/desliga o microfone).
export default function CommandBar({ onSend, disabled, listening, onToggleMic }) {
  const [value, setValue] = useState("");

  const submit = (e) => {
    e.preventDefault();
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue("");
  };

  return (
    <form onSubmit={submit} className="jarvis-command-bar mx-auto flex w-full max-w-2xl items-center gap-3 rounded-full p-2.5">
      <button
        type="button"
        onClick={onToggleMic}
        aria-label={listening ? "Parar de ouvir" : "Falar com o JARVIS"}
        className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full border transition focus:outline-none focus-visible:ring-2 focus-visible:ring-arc-200 ${
          listening
            ? "animate-arc-pulse border-arc-100 bg-arc-400/40 text-white shadow-arc"
            : "border-arc-400/60 text-arc-200 hover:bg-arc-500/20"
        }`}
      >
        <MicIcon />
      </button>

      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={listening ? "Ouvindo…" : "Digite um comando para o JARVIS"}
        disabled={disabled || listening}
        className="min-w-0 flex-1 bg-transparent px-2 text-base text-arc-100 placeholder:text-arc-300/50 focus:outline-none disabled:opacity-50"
      />
    </form>
  );
}

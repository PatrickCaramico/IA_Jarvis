import { useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { agentSuggestions } from "../utils/agentMention.js";

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
  const fileRef = useRef(null);
  const inputRef = useRef(null);
  const [pick, setPick] = useState(0);
  const mentions = agentSuggestions(value); // V7.9: "@" mostra os agentes
  const formRef = useRef(null);
  const [box, setBox] = useState(null);
  // a lista flutua por cima da tela (dentro do painel ela era cortada pela borda)
  useLayoutEffect(() => {
    if (!mentions.length || !formRef.current) {
      setBox(null);
      return;
    }
    const r = formRef.current.getBoundingClientRect();
    setBox({ left: r.left, width: r.width, bottom: window.innerHeight - r.top + 6 });
  }, [mentions.length]);
  const choose = (a) => {
    setValue(`@${a.id} `);
    setPick(0);
    inputRef.current?.focus();
  };
  const onKeyDown = (e) => {
    if (!mentions.length) return;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      setPick((n) => (n + (e.key === "ArrowDown" ? 1 : mentions.length - 1)) % mentions.length);
    } else if (e.key === "Enter" || e.key === "Tab") {
      e.preventDefault();
      choose(mentions[Math.min(pick, mentions.length - 1)]);
    }
  };

  const submit = (e) => {
    e.preventDefault();
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue("");
  };

  return (
    <form ref={formRef} onSubmit={submit} className="jarvis-command-bar relative mx-auto flex w-full max-w-2xl items-center gap-3 rounded-full p-2.5">
      {mentions.length > 0 && box && createPortal(
        <div className="cmd-mention" role="listbox" aria-label="Falar direto com um agente"
          style={{ position: "fixed", left: box.left, width: box.width, bottom: box.bottom, right: "auto" }}>
          {mentions.map((a, i) => (
            <button key={a.id} type="button" role="option" aria-selected={i === pick} className={i === pick ? "is-on" : ""}
              onMouseDown={(e) => { e.preventDefault(); choose(a); }}>
              <span aria-hidden="true">{a.icon}</span><code>@{a.id}</code><small>{a.label}</small>
            </button>
          ))}
        </div>,
        document.body,
      )}
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

      {/* V7.8: 📎 foto da galeria (abre a janela FOTO ENVIADA) */}
      <button type="button" className="ph-clip" onClick={() => fileRef.current?.click()} aria-label="Enviar uma foto da galeria" title="Enviar uma foto">📎</button>
      <input ref={fileRef} type="file" accept="image/*" hidden onChange={(e) => {
        const file = e.target.files?.[0];
        e.target.value = "";
        if (file) window.dispatchEvent(new CustomEvent("jarvis-photo-file", { detail: file }));
      }} />
      <input
        ref={inputRef}
        value={value}
        onKeyDown={onKeyDown}
        onChange={(e) => { setValue(e.target.value); setPick(0); }}
        placeholder={listening ? "Ouvindo…" : "Digite um comando (ou @agente) para o JARVIS"}
        disabled={disabled || listening}
        className="min-w-0 flex-1 bg-transparent px-2 text-base text-arc-100 placeholder:text-arc-300/50 focus:outline-none disabled:opacity-50"
      />
    </form>
  );
}

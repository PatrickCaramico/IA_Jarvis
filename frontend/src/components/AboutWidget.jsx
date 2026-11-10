import { useEffect, useState } from "react";
import { APP_VERSION } from "../utils/version.js";

const MAX_CHARS = 4000;

// Widget "Sobre mim": o que você escrever aqui o JARVIS guarda e usa quando perguntarem sobre você.
export default function AboutWidget({ api }) {
  const [text, setText] = useState("");
  const [saved, setSaved] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/api/about")
      .then((data) => {
        setText(data.text ?? "");
        setSaved(data.text ?? "");
      })
      .catch(() => {});
  }, [api]);

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      const data = await api("/api/about", { method: "POST", body: JSON.stringify({ text }) });
      setSaved(data.text ?? text);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const dirty = text !== saved;

  return (
    <section className="hud-panel p-3.5" aria-label="Sobre mim">
      <h2 className="mb-0.5 font-display text-xs tracking-wide text-arc-200">Sobre mim</h2>
      <p className="mb-2 text-xs text-arc-300/70">O que o JARVIS deve saber sobre você.</p>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        maxLength={MAX_CHARS}
        rows={3}
        placeholder="Ex.: Moro em São Paulo, trabalho com… Meu time é… Gosto de…"
        className="w-full resize-y rounded border border-arc-700 bg-void/60 px-2.5 py-1.5 text-xs leading-snug text-arc-100 placeholder:text-arc-300/40 focus:border-arc-300 focus:outline-none"
      />

      <div className="mt-3 flex items-center justify-between gap-3">
        <span className="text-sm text-arc-300/70">
          {error ? <span className="text-red-400">{error}</span> : dirty ? "Alterações não salvas" : saved ? "Salvo" : ""}
        </span>
        <button
          type="button"
          onClick={save}
          disabled={!dirty || saving}
          className="rounded border border-arc-300 bg-arc-500/15 px-5 py-1.5 font-display text-sm tracking-widest text-arc-100 transition hover:bg-arc-400/30 focus:outline-none focus-visible:ring-2 focus-visible:ring-arc-200 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {saving ? "Salvando…" : "Salvar"}
        </button>
      </div>
      <p className="mt-2 border-t border-arc-700/50 pt-1.5 text-[10px] tracking-widest text-arc-300/50">JARVIS v{APP_VERSION}</p>
    </section>
  );
}

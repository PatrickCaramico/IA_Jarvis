import { useEffect, useState } from "react";

export default function MemoryWidget({ api }) {
  const [memory, setMemory] = useState({ facts: [], preferences: {}, routine: [] });
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);

  const load = () => api("/api/memory").then(setMemory).catch(() => {});
  useEffect(() => { load(); }, []);

  const save = async () => {
    if (!text.trim()) return;
    setSaving(true);
    try {
      await api("/api/memory", { method: "POST", body: JSON.stringify({ text, category: "facts" }) });
      setText("");
      await load();
    } finally {
      setSaving(false);
    }
  };

  const items = [...(memory.facts ?? []), ...(memory.routine ?? [])].slice(-4).reverse();
  return (
    <section className="hud-panel p-3.5" aria-label="Memória do JARVIS">
      <h2 className="mb-0.5 font-display text-xs tracking-wide text-arc-200">Memória</h2>
      <p className="mb-2 text-xs text-arc-300/70">Preferências e fatos que o JARVIS pode usar nas respostas.</p>
      <div className="mb-2 flex gap-1.5">
        <input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && save()} placeholder="Ex.: prefiro respostas curtas" className="min-w-0 flex-1 rounded border border-arc-700 bg-void/60 px-2 py-1 text-xs text-arc-100 placeholder:text-arc-300/40 focus:border-arc-300 focus:outline-none" />
        <button type="button" onClick={save} disabled={saving || !text.trim()} className="rounded border border-arc-400/60 px-2 text-xs text-arc-200 disabled:opacity-40">+</button>
      </div>
      {items.length ? <ul className="space-y-1">{items.map((item) => <li key={`${item.created_at}-${item.text}`} className="truncate text-xs text-arc-100">• {item.text}</li>)}</ul> : <p className="text-xs text-arc-300/50">Nenhuma memória manual ainda.</p>}
    </section>
  );
}

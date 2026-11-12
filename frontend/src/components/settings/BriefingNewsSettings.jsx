import { useEffect, useState } from "react";
import { Note, Section } from "./SettingsControls.jsx";

// V6.2: temas de notícias do "bom dia" (Google Notícias). Cada tema tem um nome, o que buscar e quantas
// manchetes o JARVIS lê (1 a 5). Ex.: Marvel com as 3 principais.
const IDEAS = [
  ["Marvel", "Marvel"], ["DC", "DC Comics filme"], ["Palmeiras", "Palmeiras"], ["Inteligência artificial", "inteligência artificial"],
  ["Games", "games lançamento"], ["Fórmula 1", "Fórmula 1"], ["Bitcoin", "bitcoin"], ["Séries e filmes", "Netflix séries estreia"],
  ["Espaço", "NASA espaço"], ["Economia", "economia Brasil"], ["Tecnologia", "tecnologia"], ["Star Wars", "Star Wars"],
];
const MAX = 6;

export default function BriefingNewsSettings({ api }) {
  const [themes, setThemes] = useState(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    api("/api/briefing/news-themes").then((d) => setThemes(d.items || [])).catch(() => setThemes([]));
  }, [api]);

  const save = async (next) => {
    setThemes(next);
    try {
      await api("/api/prefs", { method: "PATCH", body: JSON.stringify({ briefing_news_themes: next }) });
      setStatus("✓ Salvo. Vale no próximo \"bom dia\".");
    } catch (err) {
      setStatus(`Erro: ${err.message}`);
    }
    setTimeout(() => setStatus(""), 3000);
  };

  const update = (i, patch) => setThemes((cur) => cur.map((t, j) => (j === i ? { ...t, ...patch } : t)));
  const commit = () => themes && save(themes.map((t) => ({ title: t.title.trim(), query: (t.query || t.topic || "").trim(), count: t.count || 1 }))
    .filter((t) => t.title && t.query));

  if (themes === null) return <Section title="NOTÍCIAS DO BRIEFING"><p className="text-xs text-cyan-300/70">Carregando…</p></Section>;
  const names = new Set(themes.map((t) => t.title.toLowerCase()));

  return (
    <Section title="NOTÍCIAS DO BRIEFING">
      <div className="space-y-2">
        {themes.map((t, i) => (
          <div key={i} className="flex flex-wrap items-center gap-1.5 rounded border border-cyan-500/15 bg-black/30 p-1.5">
            <input
              value={t.title}
              onChange={(e) => update(i, { title: e.target.value })}
              onBlur={commit}
              maxLength={40}
              aria-label="Nome do tema"
              className="w-28 flex-none rounded border border-cyan-500/30 bg-black/60 p-1 text-[11px] text-cyan-100"
            />
            <input
              value={t.query || t.topic || ""}
              onChange={(e) => update(i, { query: e.target.value, topic: undefined })}
              onBlur={commit}
              maxLength={80}
              placeholder="o que buscar"
              aria-label="Busca no Google Notícias"
              className="min-w-0 flex-1 rounded border border-cyan-500/30 bg-black/60 p-1 text-[11px] text-cyan-100"
            />
            <select
              value={t.count || 1}
              onChange={(e) => { const next = themes.map((x, j) => (j === i ? { ...x, count: Number(e.target.value) } : x)); save(next.map((x) => ({ title: x.title, query: x.query || x.topic, count: x.count || 1 }))); }}
              aria-label="Quantas manchetes"
              className="rounded border border-cyan-500/30 bg-black/60 p-1 text-[11px] text-cyan-100"
            >
              {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n} {n === 1 ? "manchete" : "manchetes"}</option>)}
            </select>
            <button
              type="button"
              onClick={() => save(themes.filter((_, j) => j !== i).map((x) => ({ title: x.title, query: x.query || x.topic, count: x.count || 1 })))}
              className="px-1.5 text-xs text-red-300/80 hover:text-red-200"
              aria-label={`Tirar ${t.title}`}
            >
              ✕
            </button>
          </div>
        ))}
      </div>
      {themes.length < MAX && (
        <div className="mt-2 flex flex-wrap gap-1.5" aria-label="Ideias de temas">
          {IDEAS.filter(([n]) => !names.has(n.toLowerCase())).map(([name, query]) => (
            <button
              key={name}
              type="button"
              onClick={() => save([...themes, { title: name, query, count: 3 }].map((x) => ({ title: x.title, query: x.query || x.topic, count: x.count || 1 })))}
              className="rounded-full border border-cyan-500/30 bg-black/40 px-2.5 py-1 text-[11px] text-cyan-200 hover:border-cyan-300"
            >
              ＋ {name}
            </button>
          ))}
        </div>
      )}
      {status && <p className="mt-2 text-[11px] text-emerald-300">{status}</p>}
      <Note>Cada tema vira um card no "bom dia" e o JARVIS lê as manchetes escolhidas (busca no Google Notícias, últimos 2 dias). Até {MAX} temas.</Note>
    </Section>
  );
}

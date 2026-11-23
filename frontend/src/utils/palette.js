// V9.0: PALETA DE COMANDOS (Ctrl+K) — partes puras, testadas.
// Um só lugar para achar tudo: telas e ações da central, as frases das Skills e (pelo backend) a memória
// pesquisável e os copiados. Enter executa; o que não bater com nada vira pergunta para o JARVIS.

const strip = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

export const MAX_RESULTS = 12;

/** Itens das Skills: cada frase de exemplo vira um comando ("organiza as janelas"). */
export function skillItems(skills) {
  const out = [];
  for (const sk of skills || []) {
    if (sk.enabled === false) continue;
    for (const ex of (sk.examples || []).slice(0, 3)) {
      out.push({
        id: `skill:${sk.name}:${ex}`,
        kind: "skill",
        icon: "⚡",
        label: ex,
        hint: sk.title || sk.name,
        keywords: `${sk.name} ${sk.description || ""}`,
        run: { type: "send", text: ex },
      });
    }
  }
  return out;
}

/** Itens da memória (/api/search/local): Enter copia o trecho. */
export function memoryItems(results) {
  return (results || []).map((r, i) => {
    const text = String(r.snippet || r.title || "").replace(/[[\]]/g, "").replace(/\s+/g, " ").trim();
    return {
      id: `mem:${i}:${text.slice(0, 20)}`,
      kind: r.kind === "copiado" ? "copiado" : "memoria",
      icon: r.kind === "copiado" ? "📋" : "🧠",
      label: text.length > 110 ? `${text.slice(0, 107)}…` : text,
      hint: `${r.label || r.kind}${r.at ? ` · ${String(r.at).slice(0, 10)}` : ""} · Enter copia`,
      run: { type: "copy", text: String(r.title && r.kind === "copiado" ? r.title : text) },
    };
  });
}

/** Pontua um item para a busca: todas as palavras precisam aparecer; começo do rótulo vale mais. */
export function score(item, query) {
  const q = strip(query).trim();
  if (!q) return item.kind === "acao" ? 1 : 0;
  const label = strip(item.label);
  const hay = `${label} ${strip(item.hint)} ${strip(item.keywords)}`;
  const words = q.split(/\s+/);
  if (!words.every((w) => hay.includes(w))) return 0;
  let s = 10;
  if (label.startsWith(q)) s += 30;
  else if (label.includes(q)) s += 15;
  s += words.filter((w) => label.includes(w)).length * 4;
  if (item.kind === "acao") s += 5; // telas e ações primeiro, depois frases
  return s - label.length / 100;
}

/** A lista final: locais pontuados + memória (como vier) + "Perguntar ao JARVIS" quando houver texto. */
export function rank(items, query, memory = []) {
  const q = String(query || "").trim();
  const local = items
    .map((it) => ({ it, s: score(it, q) }))
    .filter((x) => x.s > 0)
    .sort((a, b) => b.s - a.s)
    .slice(0, q ? MAX_RESULTS : 10)
    .map((x) => x.it);
  if (!q) return local;
  const ask = { id: "ask", kind: "perguntar", icon: "💬", label: `Perguntar ao JARVIS: “${q}”`, hint: "Enter envia", run: { type: "send", text: q } };
  const exact = local[0] && strip(local[0].label) === strip(q);
  return exact ? [...local, ...memory, ask] : [...local.slice(0, 1), ask, ...local.slice(1), ...memory].filter(Boolean);
}

export function move(index, delta, length) {
  if (!length) return 0;
  return (index + delta + length) % length;
}

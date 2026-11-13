// V7.3: NOTAS DA VERSÃO. Lê o CHANGELOG.md (o mesmo do projeto) e separa por versão.
// Formato: "## 7.2.0 — 13 de novembro de 2026", itens "- texto" e subitens "  - texto", títulos "### Grupo".

export function parseChangelog(md) {
  const versions = [];
  let cur = null;
  let lastItem = null;
  for (const raw of String(md || "").split(/\r?\n/)) {
    const line = raw.replace(/\s+$/, "");
    const head = line.match(/^##\s+([^\s—–-]+)\s*(?:[—–-]\s*(.+))?$/);
    if (head) {
      cur = { version: head[1].trim(), date: (head[2] || "").trim(), items: [] };
      versions.push(cur);
      lastItem = null;
      continue;
    }
    if (!cur || !line.trim()) continue;
    const group = line.match(/^#{3,4}\s+(.+)$/);
    if (group) {
      cur.items.push({ heading: true, text: group[1].trim(), sub: [] });
      lastItem = null;
      continue;
    }
    const sub = line.match(/^\s{2,}[-*]\s+(.+)$/);
    if (sub && lastItem) {
      lastItem.sub.push(sub[1].trim());
      continue;
    }
    const item = line.match(/^[-*]\s+(.+)$/);
    if (item) {
      lastItem = { text: item[1].trim(), sub: [] };
      cur.items.push(lastItem);
      continue;
    }
    if (lastItem && /^\s+\S/.test(line)) {
      lastItem.text += ` ${line.trim()}`; // continuação do item na linha de baixo
      continue;
    }
    lastItem = { text: line.trim(), sub: [] };
    cur.items.push(lastItem);
  }
  return versions;
}

// "**negrito**" e "`código`" viram pedaços para a tela (sem HTML cru)
export function inlineParts(text) {
  const parts = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0;
  let m;
  while ((m = re.exec(text))) {
    if (m.index > last) parts.push({ t: "text", v: text.slice(last, m.index) });
    parts.push(m[0].startsWith("**") ? { t: "bold", v: m[0].slice(2, -2) } : { t: "code", v: m[0].slice(1, -1) });
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push({ t: "text", v: text.slice(last) });
  return parts;
}

export function matches(version, query) {
  const q = String(query || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").trim();
  if (!q) return true;
  const hay = [version.version, version.date, ...version.items.flatMap((i) => [i.text, ...i.sub])].join(" ")
    .toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  return q.split(/\s+/).every((w) => hay.includes(w));
}

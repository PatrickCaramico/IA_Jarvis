// V8.11: catálogo das Skills (habilidades plug-and-play) na Central de Agentes — partes puras, testadas.
// O backend (GET /api/skills) devolve cada skill com o módulo de onde veio (skills.workspace, skills.deep_brief…);
// aqui elas viram grupos com nome e ícone. Skill nova de um módulo desconhecido entra num grupo com o nome dele.

export const GROUPS = {
  workspace: { label: "Janelas e monitores", icon: "🪟", order: 1 },
  system_guard: { label: "O PC", icon: "🛡️", order: 2 },
  context_autopilot: { label: "Agenda e reuniões", icon: "📅", order: 3 },
  deep_brief: { label: "Dossiês", icon: "🔎", order: 4 },
  clipboard_ai: { label: "Área de transferência", icon: "📋", order: 5 },
  dia_a_dia: { label: "Dia a dia", icon: "☀️", order: 6 },
  datas: { label: "Datas", icon: "🗓️", order: 7 }, // V8.13
  sorteio: { label: "Sorteios", icon: "🎲", order: 8 }, // V8.13
  musica_de_entrada: { label: "Música de entrada", icon: "🎸", order: 9 }, // V8.13
  memoria_busca: { label: "Memória", icon: "🧠", order: 10 }, // V9.0
  copiados: { label: "Copiados", icon: "📋", order: 11 }, // V9.0
  tempo_de_tela: { label: "Tempo de tela", icon: "⏱", order: 12 }, // V9.0
  ocr_tela: { label: "Texto da tela", icon: "🔤", order: 13 }, // V9.0
  navegador: { label: "Navegador", icon: "🌐", order: 14 }, // V9.0
  auto_analise: { label: "Auto-análise", icon: "⚡", order: 3 }, // V9.2
  seguranca: { label: "Segurança", icon: "🛡️", order: 2 }, // V9.3
  tela_de_bloqueio: { label: "Tela de bloqueio", icon: "🔒", order: 15 }, // V9.4
  analisar_imagem: { label: "Imagens", icon: "🖼", order: 16 }, // V9.4
  modo_gravar: { label: "Modo gravar", icon: "⏺", order: 17 }, // V9.4
  inicializacao: { label: "Inicialização", icon: "🚀", order: 70 },
  microfone: { label: "Microfone", icon: "🎙", order: 65 },
  habilidades: { label: "Central", icon: "⚡", order: 80 },
  abrir_programa: { label: "Segurança", icon: "🔐", order: 90 },
};

export const PERMISSIONS = {
  read: { label: "LEITURA", hint: "só consulta", cls: "is-read" },
  action: { label: "AÇÃO", hint: "mexe no PC, reversível", cls: "is-action" },
  critical: { label: "CRÍTICA", hint: "sempre pede o seu “sim”", cls: "is-critical" },
};

const strip = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

export function groupKey(module) {
  const parts = String(module || "").split(".");
  return parts[0] === "skills" && parts[1] ? parts[1] : parts[parts.length - 1] || "outras";
}

export function groupInfo(key) {
  if (GROUPS[key]) return GROUPS[key];
  const label = key.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
  return { label, icon: "⚡", order: 50 };
}

export function matches(item, query) {
  const q = strip(query).trim();
  if (!q) return true;
  const hay = strip([item.title, item.name, item.description, ...(item.examples || [])].join(" "));
  return q.split(/\s+/).every((w) => hay.includes(w));
}

/** Itens do /api/skills -> [{ key, label, icon, items }] na ordem dos grupos, filtrados pela busca. */
export function groupSkills(items, query = "") {
  const groups = new Map();
  for (const item of items || []) {
    if (!matches(item, query)) continue;
    const key = groupKey(item.module);
    if (!groups.has(key)) groups.set(key, { key, ...groupInfo(key), items: [] });
    groups.get(key).items.push(item);
  }
  return [...groups.values()].sort((a, b) => a.order - b.order || a.label.localeCompare(b.label));
}

export function titleOf(item) {
  const t = String(item.title || item.name || "").replace(/_/g, " ").replace(/^(o|a)\s+/i, "");
  return t.replace(/^\w/, (c) => c.toUpperCase());
}

/** "12 usos · 1 falha · ~140 ms" (ou "ainda não usada"), e a pausa do disjuntor quando houver. */
export function statsText(item) {
  const parts = [];
  const calls = Number(item.calls || 0);
  if (!calls) parts.push("ainda não usada nesta sessão");
  else {
    parts.push(`${calls} ${calls === 1 ? "uso" : "usos"}`);
    const fails = Number(item.failures || 0);
    if (fails) parts.push(`${fails} ${fails === 1 ? "falha" : "falhas"}`);
    const ms = Number(item.last_ms || 0);
    if (ms) parts.push(ms >= 1000 ? `~${Math.round(ms / 1000)} s` : `~${ms} ms`);
  }
  const paused = Number(item.paused_s || 0);
  if (paused) parts.push(`em pausa por ${Math.max(1, Math.round(paused / 60))} min`);
  return parts.join(" · ");
}

export function summary(items) {
  const list = items || [];
  const on = list.filter((i) => i.enabled).length;
  return `${on} de ${list.length} ligadas`;
}

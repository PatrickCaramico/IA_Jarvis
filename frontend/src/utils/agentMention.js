// V7.9: falar direto com um agente. "@mercado monta a lista", por voz "agente mercado, monta a lista",
// "pergunta pro agente de finanças quanto gastei", "fala com o professor: me explica frações".
export const CHAT_AGENTS = [
  { id: "rotas", label: "Agente de rotas", icon: "🧭", aliases: ["rotas", "rota", "mapa", "mapas"] },
  { id: "pesquisa", label: "Agente de pesquisa", icon: "🔎", aliases: ["pesquisa", "busca", "youtube", "pesquisas"] },
  { id: "mercado", label: "Agente de mercado", icon: "🛒", aliases: ["mercado", "compras", "lista"] },
  { id: "financas", label: "Agente de finanças", icon: "💰", aliases: ["financas", "financa", "dinheiro", "gastos", "financeiro"] },
  { id: "secretario", label: "Agente secretário", icon: "📅", aliases: ["secretario", "secretaria", "agenda"] },
  { id: "professor", label: "Agente professor", icon: "🧠", aliases: ["professor", "prof", "estudos", "professora"] },
];

const norm = (t) => String(t || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").trim();

export function findAgent(name) {
  const n = norm(name).replace(/^@/, "");
  return CHAT_AGENTS.find((a) => a.id === n || a.aliases.includes(n)) || null;
}

// lista para o "@" do campo de conversa: "@me" -> mercado
export function agentSuggestions(text) {
  const m = String(text || "").match(/^@([\wÀ-ú]*)$/i);
  if (!m) return [];
  const q = norm(m[1]);
  return CHAT_AGENTS.filter((a) => !q || a.id.startsWith(q) || a.aliases.some((x) => x.startsWith(q)));
}

const VOICE = [
  /^(?:jarvis[\s,]+)?@\s*([\wÀ-ú]+)[\s,:]+(.+)$/i,
  /^(?:jarvis[\s,]+)?agente\s+(?:de\s+|do\s+|da\s+)?([\wÀ-ú]+)[\s,:]+(.+)$/i,
  /^(?:jarvis[\s,]+)?(?:pergunta|pergunte|fala|fale|diz|diga|manda|pede|pe[cç]a)\s+(?:pro|para o|pra|ao|com o|com a|pra a|para a)\s+(?:agente\s+(?:de\s+|do\s+|da\s+)?)?([\wÀ-ú]+)[\s,:]+(?:que\s+)?(.+)$/i,
];

// {agent, message} quando o pedido é para um agente; null para o JARVIS de sempre
export function parseAgentMention(text) {
  const t = String(text || "").trim();
  for (const re of VOICE) {
    const m = t.match(re);
    if (!m) continue;
    const agent = findAgent(m[1]);
    const message = m[2].trim();
    if (agent && message) return { agent: agent.id, message, info: agent };
  }
  return null;
}

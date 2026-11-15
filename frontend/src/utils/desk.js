// V8.0: MODO DESK: textos e contas pequenas (sem React: testável com node).

export const DESK_COLORS = ["#22d3ee", "#a3e635", "#4ade80", "#a855f7", "#f472b6", "#fb923c", "#facc15", "#f43f5e", "#60a5fa", "#ffffff"];

export function greeting(d = new Date()) {
  const h = d.getHours();
  return h < 5 ? "Boa noite" : h < 12 ? "Bom dia" : h < 18 ? "Boa tarde" : "Boa noite";
}

export function stateText(state) {
  return { listening: "Ouvindo", processing: "Pensando", speaking: "Falando" }[state] || "Pronto";
}

export function hexToRgb(hex) {
  const m = /^#?([0-9a-f]{6})$/i.exec(String(hex || ""));
  if (!m) return "34, 211, 238";
  const n = parseInt(m[1], 16);
  return `${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}`;
}

/** Cor clara (texto escuro por cima) ou escura (texto branco)? */
export function isLight(hex) {
  const [r, g, b] = hexToRgb(hex).split(",").map(Number);
  return (r * 299 + g * 587 + b * 114) / 1000 > 150;
}

/** Posições do mapa da memória: o centro, os assuntos num círculo e as memórias em volta de cada assunto. */
export function mapLayout(map, w = 800, h = 560) {
  const nodes = map?.nos || [];
  const topics = nodes.filter((n) => n.tipo === "assunto");
  const cx = w / 2;
  const cy = h / 2;
  const R = Math.min(w, h) * 0.3;
  const pos = { eu: { x: cx, y: cy } };
  topics.forEach((t, i) => {
    const a = (i / Math.max(1, topics.length)) * Math.PI * 2 - Math.PI / 2;
    pos[t.id] = { x: cx + R * Math.cos(a), y: cy + R * Math.sin(a), a };
  });
  for (const t of topics) {
    const kids = (map.ligacoes || []).filter((l) => l.de === t.id).map((l) => l.para);
    const base = pos[t.id];
    kids.forEach((k, j) => {
      const spread = Math.min(Math.PI * 0.9, 0.42 * kids.length);
      const a = base.a + (kids.length === 1 ? 0 : (j / (kids.length - 1) - 0.5) * spread);
      const r = Math.min(w, h) * 0.17 + (j % 2) * 18;
      pos[k] = { x: base.x + r * Math.cos(a), y: base.y + r * Math.sin(a) };
    });
  }
  return pos;
}

export const FUNCTIONS = [
  { icone: "▶", titulo: "YouTube e vídeos", exemplos: ["abre um vídeo de receita de pão no YouTube", "toca o clipe de Highway to Hell"] },
  { icone: "🔊", titulo: "Volume", exemplos: ["aumenta o som", "volume em 40", "volume no máximo"] },
  { icone: "♫", titulo: "Música", exemplos: ["toca minha playlist", "próxima música", "pausa a música"] },
  { icone: "🔔", titulo: "Lembretes e tarefas", exemplos: ["me lembra de ligar pro cliente em 30 minutos", "cria a tarefa comprar pão"] },
  { icone: "⏱", titulo: "Timers e foco", exemplos: ["timer de 10 minutos para a pizza", "modo foco 25"] },
  { icone: "☁", titulo: "Clima", exemplos: ["vai chover hoje?", "como está o clima?"] },
  { icone: "💵", titulo: "Cotações", exemplos: ["quanto está o dólar?", "cotação do bitcoin"] },
  { icone: "🖥", titulo: "Verificar o PC", exemplos: ["meu PC está lento", "limpa os arquivos temporários"] },
  { icone: "◆", titulo: "Hábitos", exemplos: ["marquei o treino de hoje", "como estão meus hábitos?"] },
  { icone: "✳", titulo: "Memória", exemplos: ["lembre que minha esposa se chama Ana", "o que você sabe sobre mim?"] },
  { icone: "💰", titulo: "Finanças", exemplos: ["gastei 50 no mercado", "quanto eu devo?"] },
  { icone: "🌐", titulo: "Olho de Deus", exemplos: ["mostra os voos agora", "tem terremoto hoje?"] },
  { icone: "✨", titulo: "Holograma", exemplos: ["me explica o sistema solar", "receita de bolo de cenoura"] },
  { icone: "🛒", titulo: "Lista de compras", exemplos: ["coloca leite na lista", "o que tem na lista?"] },
];

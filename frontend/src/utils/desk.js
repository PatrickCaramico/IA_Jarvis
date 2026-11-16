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

// V8.1 (ideia 7): guarda-roupa do robô e temas das datas (desenhados em components/RoboAvatar.jsx)
export const WARDROBE = [
  ["chapeu", "🎩 Chapéus", [["nenhum", "Nenhum"], ["gorro", "Gorro de Natal"], ["bone", "Boné"], ["fone", "Fone"], ["cartola", "Cartola"],
    ["gatinho", "Tiara de gatinho"], ["bruxa", "Chapéu de bruxa"], ["headset", "Headset"], ["coroa", "Coroa"],
    ["aureola", "Auréola"], ["chifrinhos", "Chifrinhos"], ["festa", "Chapéu de festa"], ["flor", "Flor"], ["bone_time", "Boné do time"]]],
  ["rosto", "🕶 Rosto", [["nenhum", "Nenhum"], ["oculos", "Óculos"], ["laco", "Laço"], ["bigode", "Bigode"], ["oculos_escuros", "Óculos escuros"]]],
  ["roupa", "👕 Roupas", [["nenhuma", "Nenhuma"], ["cachecol", "Cachecol"], ["gravata", "Gravata-borboleta"], ["camisa", "Camisa do time"],
    ["capa", "Capa de herói"], ["armadura", "Colete de armadura"]]],
  ["olhos_forma", "👀 Olhos", [["reator", "Arco-reator"], ["coracao", "Coração"], ["estrela", "Estrela"], ["pixel", "Pixel"]]],
  ["efeito", "✨ Efeitos", [["nenhum", "Nenhum"], ["brilho", "Brilho"], ["neve", "Neve"], ["faiscas", "Faíscas"]]],
];
export const DEFAULT_AVATAR = {
  corpo: "#e8f4ff", visor: "#0b1220", olhos: "#22d3ee", expressao: "feliz", acessorio: "nenhum",
  chapeu: "nenhum", rosto: "nenhum", roupa: "nenhuma", olhos_forma: "reator", efeito: "nenhum", temas: true,
  antena: true, olhos_seguem: true, olhos_vel: 1, // V8.2 (ideia 8)
};

/** V8.2: chapéus que deixam a antena aparecer (os outros cobrem o topo da cabeça). */
export const ANTENNA_HATS = ["nenhum", "fone", "headset", "chifrinhos", "flor"];

/** V8.2: para onde os olhos olham (-1..1 em x e y), a partir do mouse e do centro do avatar. */
export function lookAt(mouseX, mouseY, rect) {
  if (!rect || !rect.width) return { x: 0, y: 0 };
  const cx = rect.left + rect.width / 2;
  const cy = rect.top + rect.height / 2;
  const reach = Math.max(rect.width, 160) * 3;
  const clamp = (v) => Math.max(-1, Math.min(1, v));
  return { x: clamp((mouseX - cx) / reach), y: clamp((mouseY - cy) / reach) };
}
const OLD = { fone: ["chapeu", "fone"], gorro: ["chapeu", "gorro"], coroa: ["chapeu", "coroa"], oculos: ["rosto", "oculos"] };

/** O visual que aparece: o escolhido + o tema da data por cima (Natal, Halloween, Carnaval, dia de jogo). */
export function withTheme(avatar, tema) {
  const a = { ...DEFAULT_AVATAR, ...(avatar || {}) };
  const old = OLD[a.acessorio]; // avatar salvo no 8.0
  if (old && a[old[0]] === DEFAULT_AVATAR[old[0]]) a[old[0]] = old[1];
  if (!tema || a.temas === false) return a;
  for (const k of ["chapeu", "rosto", "roupa", "efeito"]) if (tema[k]) a[k] = tema[k];
  return a;
}

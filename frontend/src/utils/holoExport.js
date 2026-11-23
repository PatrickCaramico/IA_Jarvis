// V8.14: holograma — exportar (copiar / baixar .txt), velocidade da narração e id do pedido. Partes puras, testadas.

export const HOLO_SPEEDS = [1, 1.25, 1.5];
const SPEED_KEY = "jarvis.holo.speed";

export function nextSpeed(cur) {
  const i = HOLO_SPEEDS.indexOf(Number(cur));
  return HOLO_SPEEDS[(i + 1) % HOLO_SPEEDS.length];
}

export function speedLabel(v) {
  return `${String(v).replace(".", ",")}x`;
}

export function readSpeed() {
  try {
    const v = Number(localStorage.getItem(SPEED_KEY));
    return HOLO_SPEEDS.includes(v) ? v : 1;
  } catch {
    return 1;
  }
}

export function saveSpeed(v) {
  try {
    localStorage.setItem(SPEED_KEY, String(v));
  } catch {
    /* sem armazenamento: vale só agora */
  }
}

// A apresentação em texto corrido (para colar numa conversa, num documento ou estudar depois)
export function holoText(data) {
  if (!data) return "";
  const lines = [`${data.titulo || "Apresentação"}`, ""];
  (data.cenas || []).forEach((c, i) => {
    lines.push(`${i + 1}. ${c.icone ? `${c.icone} ` : ""}${c.titulo || ""}`.trimEnd());
    if (c.fala) lines.push(c.fala);
    for (const p of c.pontos || []) lines.push(`   • ${p}`);
    if (c.numero && c.numero.valor != null) {
      lines.push(`   ➜ ${Number(c.numero.valor).toLocaleString("pt-BR")} ${c.numero.unidade || ""}${c.numero.rotulo ? ` (${c.numero.rotulo})` : ""}`.trimEnd());
    }
    lines.push("");
  });
  if ((data.fontes || []).length) {
    lines.push("Fontes:");
    for (const f of data.fontes) lines.push(`- ${f.titulo}: ${f.url}`);
    lines.push("");
  }
  lines.push("Feito pelo holograma do JARVIS.");
  return lines.join("\n");
}

export function holoFileName(title) {
  const base = String(title || "apresentacao")
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60);
  return `holograma-${base || "apresentacao"}.txt`;
}

// Id do pedido: a tela reconhece as cenas que chegam aos poucos (evento holo_partial) que são suas
export function newReqId(random = Math.random) {
  return `h${Date.now().toString(36)}${Math.floor(random() * 1e6).toString(36)}`;
}

// Cenas parciais: só troca se chegou cena nova (e nunca por cima da versão final)
export function mergePartial(cur, event, query = "") {
  if (cur && !cur.partial) return cur;
  const cenas = Array.isArray(event?.cenas) ? event.cenas : [];
  if (!cenas.length || (cur && cur.cenas.length >= cenas.length)) return cur;
  return { tipo: "apresentacao", titulo: event.titulo || cur?.titulo || query, wiki: "", cenas, partial: true };
}

// V8.12.4: respostas instantâneas no MODO NUVEM (site ou celular com o PC fora de alcance), as mesmas do PC
// (backend/modules/quick_replies.py). Antes, no modo nuvem, até um "olá" ia para o Netlify e para a IA (Gemini),
// e a resposta levava alguns segundos. Agora cumprimento, "tudo bem?", obrigado, tchau, hora e data respondem
// na hora, sem rede. Qualquer coisa além disso segue para a IA, como antes.

export function norm(text) {
  return String(text || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

const MONTHS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
const WEEKDAYS = ["domingo", "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado"];

const TIME_Q = ["que horas sao", "que hora e", "que horas e", "me diz as horas", "me diga as horas", "horas"];
const DATE_Q = ["que dia e hoje", "que dia eh hoje", "qual e a data de hoje", "qual a data de hoje", "que data e hoje", "em que dia estamos", "data de hoje"];

// Conversa rápida: só responde aqui se a mensagem for SÓ isso.
const NICE = ["muito prazer", "prazer em conhecer", "prazer"];
const HOW = ["tudo bem", "tudo bom", "tudo certo", "tudo joia", "como voce esta", "como voce ta", "como vai voce",
  "como vai", "como esta", "e com voce", "e voce", "como anda", "beleza"];
const TIME_GREETS = ["boa tarde", "boa noite"]; // "bom dia" fica com a IA (no PC ele abre o briefing)
const HELLO = ["e ai", "oi", "ola", "opa", "ei", "hey", "hello", "fala", "salve"];
const NOISE = ["por favor", "entao", "ai"];
const THANKS = ["muito obrigado", "muito obrigada", "obrigado", "obrigada", "valeu"];
const BYE = ["tchau", "ate logo", "ate mais", "falou"];

const escape = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

function strip(text, phrases) {
  const re = new RegExp(`\\b(?:${[...phrases].sort((a, b) => b.length - a.length).map(escape).join("|")})\\b`, "g");
  const out = text.replace(re, " ");
  return [out.replace(/\s+/g, " ").trim(), out !== text];
}

const pick = (list, random) => list[Math.floor(random() * list.length) % list.length];
const hello = (name) => (name ? `Olá, ${name}!` : "Olá!");

// Hora de Brasília (o celular pode estar em outro fuso)
export function brazilNow(now = new Date()) {
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Sao_Paulo", hour12: false, year: "numeric", month: "numeric", day: "numeric",
    hour: "numeric", minute: "numeric", weekday: "short",
  }).formatToParts(now).map((p) => [p.type, p.value]));
  const wd = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].indexOf(parts.weekday);
  return { year: +parts.year, month: +parts.month, day: +parts.day, hour: +parts.hour % 24, minute: +parts.minute, weekday: wd };
}

export function timeGreeting(hour) {
  if (hour >= 5 && hour < 12) return "Bom dia";
  if (hour >= 12 && hour < 18) return "Boa tarde";
  return "Boa noite";
}

export function spokenTime({ hour: h, minute: m }) {
  let base;
  let exact = " em ponto";
  if (h === 0) [base, exact] = ["É meia-noite", ""];
  else if (h === 12) [base, exact] = ["É meio-dia", ""];
  else if (h === 1) base = "É uma hora";
  else base = `São ${h} horas`;
  return m === 0 ? `${base}${exact}.` : `${base} e ${m} minuto${m === 1 ? "" : "s"}.`;
}

function smalltalk(n, name, hour, random) {
  let rest = n;
  let nice; let how; let timeGreet; let hi;
  [rest, nice] = strip(rest, NICE);
  [rest, how] = strip(rest, HOW);
  [rest, timeGreet] = strip(rest, TIME_GREETS);
  [rest, hi] = strip(rest, HELLO);
  [rest] = strip(rest, NOISE);
  if (rest || !(nice || how || timeGreet || hi)) return null; // sobrou um pedido de verdade: a IA responde
  const parts = [];
  if (timeGreet) parts.push(name ? `${timeGreeting(hour)}, ${name}!` : `${timeGreeting(hour)}!`);
  else if (hi) parts.push(hello(name));
  if (nice) parts.push("O prazer é meu.");
  if (how) parts.push(pick(["Tudo bem por aqui, obrigado por perguntar.", "Tudo ótimo por aqui, obrigado.", "Tudo em ordem por aqui, obrigado por perguntar."], random));
  parts.push(pick(["Em que posso ajudar?", "Como posso ajudar?", "O que posso fazer por você?"], random));
  return parts.join(" ");
}

// Frase curta que é SÓ uma dessas expressões (com "jarvis" e "por favor" em volta, no máximo)
function only(n, phrases) {
  let [rest, hit] = strip(n, phrases);
  [rest] = strip(rest, NOISE);
  return hit && !rest;
}

/** Resposta instantânea, ou null quando a IA precisa responder. */
export function quickReply(message, { name = "", now = new Date(), random = Math.random } = {}) {
  const n = norm(message).replace(/\bjarvis\b/g, " ").replace(/\s+/g, " ").trim();
  if (!n || n.split(" ").length > 12) return null;
  const t = brazilNow(now);
  if (n.split(" ").length <= 6) {
    if (TIME_Q.some((p) => new RegExp(`\\b${p}\\b`).test(n))) return spokenTime(t);
    if (DATE_Q.some((p) => new RegExp(`\\b${p}\\b`).test(n))) {
      return `Hoje é ${WEEKDAYS[t.weekday]}, ${t.day} de ${MONTHS[t.month - 1]} de ${t.year}.`;
    }
  }
  if (only(n, THANKS)) return pick([name ? `Disponha, ${name}.` : "Disponha.", name ? `Sempre às ordens, ${name}.` : "Sempre às ordens."], random);
  if (only(n, BYE)) return `Até logo${name ? `, ${name}` : ""}. Estarei por aqui quando precisar.`;
  return smalltalk(n, name, t.hour, random);
}

// V8.13: STREAMING da resposta no chat. O PC manda {"type": "response_stream", seq, text, reset?} enquanto a IA
// escreve (o texto ACUMULADO); a resposta final continua vindo no "response". Partes puras, testadas.

export const EMPTY_STREAM = { seq: 0, text: "" };

// Junta um aviso novo ao estado atual. Aviso mais velho (fora de ordem) é ignorado.
export function applyStream(prev, event) {
  const cur = prev || EMPTY_STREAM;
  const seq = Number(event?.seq) || 0;
  if (seq && seq <= cur.seq) return cur;
  if (event?.reset) return { seq: seq || cur.seq, text: "" };
  return { seq: seq || cur.seq + 1, text: String(event?.text || "") };
}

// A resposta final que chegou já estava toda na tela pelo streaming? (aí ela não é "digitada" de novo)
let lastStreamed = "";

export function markStreamed(text) {
  lastStreamed = String(text || "").trim();
}

export function wasStreamed(text) {
  const t = String(text || "").trim();
  if (!t || !lastStreamed) return false;
  // a final pode ter um pedacinho a mais (o último pedaço segurado pelo limite de envio)
  return t === lastStreamed || (t.startsWith(lastStreamed) && lastStreamed.length >= t.length * 0.6);
}

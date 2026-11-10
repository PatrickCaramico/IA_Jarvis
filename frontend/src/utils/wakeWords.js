// Palavra de ativação do Modo Sentinela (função pura, testável).

export function normalizeSpeech(text) {
  return String(text || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

/** Lista efetiva: as frases configuradas + o nome da IA ("A.R.E.S" -> "ares"). */
export function effectiveWakeWords(wakeWords, aiName) {
  const list = (Array.isArray(wakeWords) && wakeWords.length ? wakeWords : ["jarvis", "ei jarvis", "ta acordado"])
    .map(normalizeSpeech)
    .filter(Boolean);
  const name = normalizeSpeech(String(aiName || "").replace(/\./g, ""));
  if (name && !list.includes(name)) list.push(name);
  if (name && !list.includes(`ei ${name}`)) list.push(`ei ${name}`);
  return [...new Set(list)].sort((a, b) => b.length - a.length);
}

/**
 * A palavra precisa estar NO COMEÇO da frase (reduz falsos positivos de TV e música).
 * Retorna { matched, wake, rest } — rest é o pedido que veio junto ("que horas são").
 */
export function matchWake(text, wakeWords) {
  const norm = normalizeSpeech(text);
  for (const w of wakeWords) {
    if (norm === w) return { matched: true, wake: w, rest: "" };
    if (norm.startsWith(`${w} `)) return { matched: true, wake: w, rest: norm.slice(w.length).trim() };
  }
  return { matched: false, wake: "", rest: norm };
}

// V4.2.2: frases de liberar a central. Com o microfone ligado (P ou clique), vão direto para o
// escaneamento do rosto, com ou sem a palavra de ativação na frente. Nada roda depois de entrar.
// A mesma regra fica em backend/modules/sentinel.py (_UNLOCK_ONLY); os testes conferem as duas.
const UNLOCK_RE = /^(?:(?:pode|por favor|quero)\s+)?(?:(?:abrir|abre|abra|liberar|libera|libere|desbloquear|desbloqueia|desbloqueie|destravar|destrava|destrave)(?:\s+(?:a|o))?(?:\s+(?:central|jarvis|sistema|tela))?|entrar|me deixa entrar|deixa eu entrar)(?:\s+por favor)?$/;

export function isUnlockPhrase(text) {
  const norm = normalizeSpeech(text);
  if (!norm) return false;
  // "abrir"/"abre" sozinhos são vagos demais (ex.: "abre"): exigem um complemento
  if (/^(?:abrir|abre|abra)$/.test(norm)) return false;
  return UNLOCK_RE.test(norm);
}

/** Frase de liberar, sozinha ou depois da palavra de ativação ("Jarvis, abrir central"). */
export function matchUnlock(text, wakeWords) {
  const { matched, rest } = matchWake(text, wakeWords || []);
  return isUnlockPhrase(matched ? rest : text);
}

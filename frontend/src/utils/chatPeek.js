// V9.4.5: TRANSCRIÇÃO AO VIVO. Quando o JARVIS fala (ou o senhor fala com ele), a conversa abre numa janela de
// vidro maior, por cima da central, e fecha sozinha alguns segundos depois. Antes, a fala só aparecia no Canal Ativo,
// que ficou pequeno na coluna direita (ou nem aparecia, com a coluna recolhida). Puro, testado em tests/chatPeek.test.js.

export const KEY = "jarvis.chatPeek"; // "off" = não abrir sozinho (vale para este aparelho)
export const CLOSE_AFTER_MS = 7000; // depois que ele termina de falar
export const EXIT_MS = 260; // duração da animação de saída (igual ao CSS .cpk-out)

export function peekEnabled(storage = globalThis.localStorage) {
  try {
    return storage?.getItem(KEY) !== "off";
  } catch {
    return true;
  }
}

export function setPeekEnabled(on, storage = globalThis.localStorage) {
  try {
    if (on) storage?.removeItem(KEY);
    else storage?.setItem(KEY, "off");
  } catch {
    /* aba anônima: vale só nesta sessão */
  }
  return Boolean(on);
}

/** A janela deve estar aberta agora? (o fechamento com atraso fica no componente) */
export function wantsPeek({ enabled = true, speaking = false, streaming = false, listening = false, zen = false, briefing = false,
  fresh = false, pinned = false } = {}) {
  if (pinned) return true; // V9.5.5: ⤢ AMPLIAR: fica aberta até o senhor fechar
  if (!enabled || zen || briefing) return false; // a Área Limpa já tem a janelinha dela; o briefing tem o palco
  // V9.5.5: fresh = chegou resposta nova. Antes a janela só abria com a voz tocando: quando ele não falava (voz
  // falhou, modo silencioso, voz no celular), a resposta aparecia só no Canal Ativo pequeno.
  return Boolean(speaking || streaming || listening || fresh);
}

/** V9.5.5: quanto tempo uma resposta nova fica aberta para ler (sem voz): ~60 ms por letra, de 8 a 30 s. */
export function readMs(text) {
  const n = String(text || "").length;
  return Math.max(8000, Math.min(30000, n * 60));
}

/** V9.5.5: a última mensagem é uma resposta nova do JARVIS (que ainda não abriu a janela)? */
export function newReply(log, seenId) {
  const list = Array.isArray(log) ? log : [];
  const last = list[list.length - 1];
  if (!last || last.role !== "jarvis" || last.old || !last.text || last.id === seenId) return null;
  return last;
}

/** As últimas falas da conversa (sem divisórias nem mensagens antigas de outro dia). */
export function recentMessages(log, n = 4) {
  const list = Array.isArray(log) ? log.filter((m) => m && (m.role === "user" || m.role === "jarvis" || m.role === "error") && !m.old && m.text) : [];
  return list.slice(-n);
}

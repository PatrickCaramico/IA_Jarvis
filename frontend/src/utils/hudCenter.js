// V8.11.1: centro da central renovado (linha de estado, telemetria em volta do reator e legenda do microfone).
// Partes puras, testadas (node --test frontend/tests).

/** Segundos decorridos como texto curto: 4 -> "4 s", 75 -> "1 min 15 s". */
export function elapsedText(sec) {
  const s = Math.max(0, Math.floor(Number(sec) || 0));
  if (s < 60) return `${s} s`;
  const m = Math.floor(s / 60);
  const r = s % 60;
  return r ? `${m} min ${r} s` : `${m} min`;
}

// A partir daqui o "pensando" vira um convite para cancelar (a IA tem prazo no backend, mas a tela não pode
// parecer travada: antes ficava "PROCESSANDO" piscando sem dizer nada).
export const SLOW_AFTER_S = 25;

/**
 * O que a linha abaixo do estado diz: { text, tone, cancel }.
 * tone: "idle" | "listen" | "work" | "slow" | "talk"; cancel: mostra o botão de cancelar.
 */
export function stateHint({ state = "idle", listening = false, interim = "", elapsed = 0, micOk = true } = {}) {
  if (listening) {
    const said = String(interim || "").trim();
    return { text: said ? `“${said.length > 70 ? `${said.slice(0, 69)}…` : said}”` : "Pode falar, senhor. Estou ouvindo.", tone: "listen", cancel: false };
  }
  if (state === "processing") {
    if (elapsed >= SLOW_AFTER_S) return { text: `Está demorando (${elapsedText(elapsed)}). Pode cancelar e pedir de novo.`, tone: "slow", cancel: true };
    return { text: elapsed >= 1 ? `Pensando… ${elapsedText(elapsed)}` : "Pensando…", tone: "work", cancel: true };
  }
  if (state === "speaking") return { text: "Respondendo. Toque em parar para interromper.", tone: "talk", cancel: true };
  return {
    text: micOk ? "Toque no microfone ou aperte espaço para falar." : "Digite seu pedido no canal ao lado.",
    tone: "idle",
    cancel: false,
  };
}

/** Legenda embaixo do botão do microfone. */
export function micCaption({ listening = false, state = "idle" } = {}) {
  if (listening) return "OUVINDO · TOQUE P/ ENVIAR";
  if (state === "processing") return "AGUARDE";
  if (state === "speaking") return "FALANDO";
  return "FALAR";
}

/** Próximo compromisso numa linha: { when, title } ou null. */
export function nextAgenda(items) {
  const it = (items || []).find((i) => i && (i.title || i.label));
  if (!it) return null;
  const title = String(it.title || "Compromisso");
  return { when: String(it.label || "").trim() || "Em breve", title: title.length > 28 ? `${title.slice(0, 27)}…` : title };
}

/** Disco livre: 412.3 -> "412 GB"; 1536 -> "1,5 TB". */
export function diskText(gb) {
  if (gb === null || gb === undefined || gb === "") return "—";
  const v = Number(gb);
  if (!Number.isFinite(v)) return "—";
  return v >= 1000 ? `${(v / 1024).toFixed(1).replace(".", ",")} TB` : `${Math.round(v)} GB`;
}

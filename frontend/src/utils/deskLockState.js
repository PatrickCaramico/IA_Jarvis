// V8.16: bloqueio do Modo Desk só com o avatar do JARVIS (sem Tamagotchi, jogo nem atividades), com as funções do
// bloqueio clássico. A expressão e o balão seguem o estado de verdade. Partes puras, testadas.

/** Está de noite? (o robô dorme quando está tudo quieto) */
export function isNight(hour) {
  return hour >= 23 || hour < 6;
}

/**
 * A expressão do avatar agora. Ordem: cutucada > reação > reconhecimento do rosto > ouvindo > falando > noite.
 * Devolve { expr, state }: expr é a expressão fixa (ou null = a dele, com piscadas), state é o estado do RoboAvatar.
 */
export function deskFace({ phase = "ready", listening = false, jarvisState = "idle", hour = 12, mood = null, reaction = null } = {}) {
  if (mood) return { expr: mood, state: "idle" };
  if (reaction) return { expr: reaction, state: "idle" };
  if (phase === "scanning") return { expr: null, state: "processing" };
  if (phase === "verified") return { expr: "conseguiu", state: "idle" };
  if (phase === "failed") return { expr: "surpreso", state: "idle" };
  if (jarvisState === "speaking") return { expr: null, state: "speaking" };
  if (listening) return { expr: null, state: "listening" };
  if (jarvisState === "processing") return { expr: null, state: "processing" };
  if (phase === "ready" && isNight(hour)) return { expr: "dormindo", state: "idle" };
  return { expr: null, state: "idle" };
}

/** O anel de luz em volta dele (só CSS): ok, falha, ouvindo, falando, pensando, dormindo ou calmo. */
export function haloTone({ phase = "ready", listening = false, jarvisState = "idle", hour = 12 } = {}) {
  if (phase === "verified") return "ok";
  if (phase === "failed") return "fail";
  if (phase === "scanning" || jarvisState === "processing") return "think";
  if (jarvisState === "speaking") return "talk";
  if (listening) return "listen";
  if (phase === "ready" && isNight(hour)) return "sleep";
  return "calm";
}

/** O que o balão diz agora (null = as falas de sempre, que vão trocando). */
export function deskBubble({ phase = "ready", name = "", message = "", caption = "", listening = false, hint = "", hintShown = false, wake = "Jarvis", hour = 12, mood = null } = {}) {
  if (hint && (hintShown || phase === "failed")) return hint;
  if (phase === "failed") return message || "Não reconheci. Tente de novo ou use o PIN.";
  if (phase === "verified") return `Bem-vindo de volta${name ? `, ${name}` : ""}! 💙`;
  if (phase === "scanning") return "Olhe para a câmera… estou te reconhecendo.";
  if (mood === "comendo") return "Agora você me irritou! 😤";
  if (mood) return "Ei! Pare de me cutucar! 😠";
  if (caption) return `🎙 “${caption}”`;
  if (listening) return `Estou ouvindo. Diga "abrir central" ou "${wake}, …"`;
  if (phase === "ready" && isNight(hour)) return "Zzz… 😴 (estou de olho, pode entrar quando quiser)";
  return null;
}

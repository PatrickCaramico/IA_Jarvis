// V6.1: estilos da voz do JARVIS (os mesmos de backend/modules/tts.py VOICE_STYLES).
// V8.13: lista única, usada nas Configurações e no botão VOZ do topo da central.
export const VOICE_STYLES = [
  ["natural", "Natural", "Antonio um pouco mais grave e calmo, como um mordomo (padrão)."],
  ["grave", "Grave", "Mais grave e pausado."],
  ["classica", "Clássica", "Como era antes."],
  ["thalita", "Thalita", "Voz feminina, natural."],
  ["andrew", "Andrew", "Multilíngue e muito natural, com um leve sotaque."],
];

export const VOICE_SAMPLE = "Olá, senhor. Assim fica a minha voz. Em que posso ajudar?";
export const DEFAULT_INTRO_SONG = "Back in Black AC/DC";

// V8.13: a música de entrada toca uma vez por página aberta quando o painel VOZ abre (não a cada clique)
export function shouldPlayOnOpen({ alreadyPlayed, silent, song }) {
  return !alreadyPlayed && !silent && Boolean(String(song || "").trim());
}

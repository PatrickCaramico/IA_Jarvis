// V9.5.0: o visual da tela de bloqueio (reator personalizado, estados, anel dos segundos e economia de madrugada).
// Puro, testado em tests/lockLook.test.js.
import { isDefault, normalize } from "./reactor.js";

/**
 * Qual reator desenhar no bloqueio. Sem personalização (🎨 REATOR no padrão), fica o Reator Arc clássico do
 * bloqueio de sempre; personalizado, a forma escolhida ("reator" ganha a cor escolhida).
 */
export function lockReactorShape(cfg) {
  if (!cfg || isDefault(cfg)) return "classic";
  return normalize(cfg).shape;
}

/** O que o anel de estado em volta do reator mostra agora. */
export function reactorStateClass({ phase = "ready", listening = false, speaking = false } = {}) {
  if (phase === "scanning") return "is-scanning";
  if (phase === "verified") return "is-ok";
  if (phase === "failed") return "is-fail";
  if (listening) return "is-listening";
  if (speaking) return "is-speaking";
  return "is-idle";
}

/** Atraso negativo para o ponteiro do anel dos segundos começar no segundo certo (a animação CSS faz o resto). */
export function secondsDelay(now = new Date()) {
  const d = now instanceof Date ? now : new Date(now);
  return `-${(d.getSeconds() + d.getMilliseconds() / 1000).toFixed(2)}s`;
}

export const SLEEP_IDLE_MS = 2 * 60 * 1000;

/**
 * Economia de madrugada: entre 0h e 6h, sem ninguém mexer há 2 min e com o bloqueio parado (pronto ou recusado),
 * a tela escurece e as animações param. Qualquer tecla, toque ou movimento acorda.
 */
export function lockSleeping({ hour, idleMs, phase = "ready", listening = false } = {}) {
  if (listening || (phase !== "ready" && phase !== "failed")) return false;
  const h = Number(hour);
  return Number.isFinite(h) && h >= 0 && h < 6 && Number(idleMs) >= SLEEP_IDLE_MS;
}

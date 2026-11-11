// V5.2: espera entre tentativas de reconexão do WebSocket: 1 s, 2 s, 4 s, 8 s e depois 10 s,
// com ±20% de sorteio para várias abas/celulares não baterem no PC ao mesmo tempo.
export const MAX_WAIT_MS = 10_000;

export function reconnectDelay(attempt, random = Math.random) {
  const base = Math.min(MAX_WAIT_MS, 1000 * 2 ** Math.max(0, attempt));
  return Math.round(base * (0.8 + random() * 0.4));
}

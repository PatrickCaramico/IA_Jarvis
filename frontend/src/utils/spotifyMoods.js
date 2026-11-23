// V9.1: atalhos de clima da janela do Spotify (um toque toca uma playlist pela busca do Spotify).
export const MOODS = [
  { id: "foco", icon: "🎧", label: "Lo-fi para focar", query: "lofi focus", playlist: true },
  { id: "relaxar", icon: "🌙", label: "Relaxar", query: "chill relax", playlist: true },
  { id: "jazz", icon: "🎷", label: "Jazz calmo", query: "jazz relaxante", playlist: true },
  { id: "chuva", icon: "🌧", label: "Chuva", query: "rain sounds", playlist: true },
];

/** Volume da barra: número inteiro entre 0 e 100 (o que vier de fora é corrigido). */
export function clampVolume(value, fallback = 60) {
  const n = Math.round(Number(value));
  return Number.isFinite(n) ? Math.max(0, Math.min(100, n)) : fallback;
}

/** "1:05" a partir de milissegundos. */
export function fmtTime(ms) {
  const s = Math.max(0, Math.floor((Number(ms) || 0) / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

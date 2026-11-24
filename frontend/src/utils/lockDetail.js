// V9.4.5: contas das janelas de detalhe da tela de bloqueio (LockDetail.jsx). Puro, testado em tests/lockDetail.test.js.

const toMin = (hm) => {
  const [h, m] = String(hm || "").split(":").map(Number);
  return Number.isFinite(h) && Number.isFinite(m) ? h * 60 + m : null;
};

/** Onde o valor fica entre a mínima e a máxima (0 a 1). Sem faixa válida, fica no meio. */
export function rangePos(value, lo, hi) {
  const v = Number(value);
  const a = Number(lo);
  const b = Number(hi);
  if (![v, a, b].every(Number.isFinite) || b <= a) return 0.5;
  return Math.min(1, Math.max(0, (v - a) / (b - a)));
}

/** O sol no arco do dia: frac 0 = nascer, 1 = pôr; up = ainda é dia. Sem horários, null. */
export function sunProgress(now, sunrise, sunset) {
  const up = toMin(sunrise);
  const down = toMin(sunset);
  if (up == null || down == null || down <= up) return null;
  const d = now instanceof Date ? now : new Date(now);
  const minutes = d.getHours() * 60 + d.getMinutes();
  const frac = (minutes - up) / (down - up);
  return { frac: Math.min(1, Math.max(0, frac)), up: frac >= 0 && frac < 1 };
}

/** Ponto do arco (meia elipse) para a fração do dia, num quadro de largura w e altura h. */
export function arcPoint(frac, w = 240, h = 90) {
  const t = Math.PI * (1 - Math.min(1, Math.max(0, frac)));
  return { x: Math.round((w / 2 + (w / 2 - 12) * Math.cos(t)) * 10) / 10, y: Math.round((h - (h - 12) * Math.sin(t)) * 10) / 10 };
}

/**
 * "Expandir o cartão": a janela nasce no lugar e no tamanho do cartão tocado e cresce até o centro.
 * Devolve o transform inicial (só transform/opacity: a placa de vídeo anima sem refazer a página).
 */
export function flipFrom(origin, target) {
  if (!origin || !target || !(target.width > 0) || !(target.height > 0) || !(origin.width > 0)) return null;
  const sx = Math.max(0.2, Math.min(1, origin.width / target.width));
  const sy = Math.max(0.12, Math.min(1, origin.height / target.height));
  const dx = Math.round(origin.left + origin.width / 2 - (target.left + target.width / 2));
  const dy = Math.round(origin.top + origin.height / 2 - (target.top + target.height / 2));
  return `translate(${dx}px, ${dy}px) scale(${sx.toFixed(3)}, ${sy.toFixed(3)})`;
}

export const OPEN_MS = 420;
export const CLOSE_MS = 260;

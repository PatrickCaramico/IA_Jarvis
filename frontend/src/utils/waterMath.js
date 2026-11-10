// Cálculos puros do recipiente de água (seção 18), testados com node --test.

export function clampPct(totalMl, goalMl) {
  const goal = Number(goalMl) > 0 ? Number(goalMl) : 2000;
  const total = Math.max(0, Number(totalMl) || 0);
  return Math.min(100, Math.round((total / goal) * 100));
}

/** Nível (0..1) da água dentro do recipiente. Acima da meta, fica cheio. */
export function waterLevel(totalMl, goalMl) {
  const goal = Number(goalMl) > 0 ? Number(goalMl) : 2000;
  return Math.min(1, Math.max(0, (Number(totalMl) || 0) / goal));
}

export function remainingMl(totalMl, goalMl) {
  return Math.max(0, (Number(goalMl) || 0) - (Number(totalMl) || 0));
}

/**
 * Ritmo do dia: compara o total com o esperado para o horário, distribuindo a meta de forma
 * linear entre start_hour e end_hour (janela do lembrete de água).
 * Retorna { expected, diff, status: "ahead" | "behind" | "on_track" | "outside" }.
 */
export function paceInfo({ totalMl, goalMl, startHour = 8, endHour = 22, now = new Date(), toleranceMl = 150 }) {
  const goal = Number(goalMl) > 0 ? Number(goalMl) : 2000;
  const hours = now.getHours() + now.getMinutes() / 60;
  if (endHour <= startHour) return { expected: 0, diff: 0, status: "outside" };
  let fraction;
  if (hours <= startHour) fraction = 0;
  else if (hours >= endHour) fraction = 1;
  else fraction = (hours - startHour) / (endHour - startHour);
  const expected = Math.round((goal * fraction) / 10) * 10;
  const diff = Math.round((Number(totalMl) || 0) - expected);
  if (hours < startHour) return { expected, diff, status: "outside" };
  const status = Math.abs(diff) <= toleranceMl ? "on_track" : diff > 0 ? "ahead" : "behind";
  return { expected, diff, status };
}

export function paceText(info) {
  if (!info || info.status === "outside") return "";
  if (info.status === "on_track") return "Você está no ritmo do dia.";
  const abs = Math.abs(info.diff);
  return info.status === "ahead" ? `Você está ${abs} ml acima do ritmo.` : `Você está ${abs} ml abaixo do ritmo.`;
}

/** Mesma frase do backend (water.status_sentence), usada para manter texto e cartão iguais. */
export function statusSentence(st) {
  return `Hoje você já consumiu ${st.total_ml} ml de água (${st.percentage}% da sua meta de ${st.goal_ml} ml).`;
}

/** Aceita "300", "300 ml", "0,5 L", "1.5l", "meio litro". Devolve ml inteiro ou null. */
export function parseVolume(text) {
  if (text == null) return null;
  const raw = String(text).trim().toLowerCase().replace(/\s+/g, " ");
  if (!raw) return null;
  if (/^meio\s+litro$/.test(raw)) return 500;
  const m = raw.match(/^(\d+(?:[.,]\d+)?)\s*(ml|mililitros?|l|litros?)?$/);
  if (!m) return null;
  const value = Number(m[1].replace(",", "."));
  if (!Number.isFinite(value) || value <= 0) return null;
  const unit = m[2] || (value <= 5 ? "l" : "ml");
  const ml = unit.startsWith("l") ? Math.round(value * 1000) : Math.round(value);
  return ml >= 20 && ml <= 3000 ? ml : null;
}

/** Interpolação usada no contador e no nível (aceleração e frenagem). */
export function easeInOutCubic(t) {
  const x = Math.min(1, Math.max(0, t));
  return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
}

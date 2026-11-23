// V9.0: VISUAL 9.0 — a central muda de clima com a hora do dia (de leve: o azul da planta fica mais claro de
// manhã, mais fundo à noite e quase apagado de madrugada). A troca é suave (as cores fazem transição de 3 s).
// <html data-mood="manha|tarde|noite|madrugada">; o CSS está em v9.css. "Reduzir movimento" não é afetado
// (só cor), e o Modo Torcedor continua com o verde dele por cima.

export const MOODS = ["madrugada", "manha", "tarde", "noite"];

export function moodFor(hour) {
  const h = ((Number(hour) % 24) + 24) % 24;
  if (h < 5) return "madrugada";
  if (h < 12) return "manha";
  if (h < 18) return "tarde";
  return "noite";
}

export function applyMood(date = new Date(), root = document.documentElement) {
  const mood = moodFor(date.getHours());
  if (root.dataset.mood !== mood) root.dataset.mood = mood;
  return mood;
}

/** Liga a troca automática (confere a cada minuto). Devolve a função que desliga. */
export function startMood() {
  applyMood();
  const id = setInterval(() => applyMood(), 60_000);
  return () => clearInterval(id);
}

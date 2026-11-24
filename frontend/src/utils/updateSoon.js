// V9.4.1: texto da contagem do aviso de atualização automática (puro, testado em tests/updateSoon.test.js).

export function soonText(until, now = Date.now()) {
  const left = Math.max(0, Math.round((Number(until) - now) / 1000));
  if (left <= 0) return "Atualizando assim que o JARVIS ficar livre…";
  const m = Math.floor(left / 60);
  const s = left % 60;
  return `Atualizo sozinho em ${m ? `${m} min ` : ""}${String(s).padStart(m ? 2 : 1, "0")} s`;
}

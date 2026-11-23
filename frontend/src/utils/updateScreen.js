// V8.12.2: tela de ATUALIZANDO O JARVIS. Partes puras, testadas (node --test frontend/tests).

/** De qual versão para qual: { from, to, code }. Sem o número novo, cai no código do commit (como era antes). */
export function versionLine(current, info = {}) {
  const to = String(info.versao || "").trim();
  if (info.changed === false) return { from: current, to: current, code: "", same: true };
  if (to && to !== current) return { from: current, to, code: "", same: false };
  return { from: current, to: "", code: String(info.depois || "").slice(0, 7), same: false };
}

/** "O que há de novo": os destaques do CHANGELOG; sem eles, os assuntos dos commits sem o prefixo "JARVIS x.y.z:". */
export function whatsNew(info = {}, limit = 4) {
  const list = (info.destaques || []).length
    ? info.destaques
    : (info.notas || []).map((n) => String(n).replace(/^JARVIS \d+\.\d+\.\d+:?\s*/, ""));
  return list.filter(Boolean).slice(0, limit);
}

/** O que a tela promete no fim: nada de "verificação do rosto" (a central volta liberada se estava liberada). */
export function footText(secs, slow = false) {
  if (slow) return "";
  if (secs >= 150) return "Está demorando mais que o normal. Se passar de 5 minutos, dê dois cliques no Iniciar-JARVIS.bat do PC: ele termina a atualização.";
  return "Leva uns segundos. Quando terminar, a central abre sozinha, do jeito que estava.";
}

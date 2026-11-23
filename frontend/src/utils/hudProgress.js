// V8.12.5: XP e missões do dia também na central (antes só no Modo Desk). Partes puras, testadas.

export const MISSION_ICON = { uso: "⚡", sobre: "💭", bem: "🌿", semana: "🏆" };
export const MISSION_KIND = { uso: "Usar o JARVIS", sobre: "Sobre você", bem: "Bem-estar", semana: "Desafio da semana" };

// O que a linha da missão mostra embaixo do texto: progresso (2/3), "responda", "toque em FEITO"…
export function missionHint(m, { cloud = false } = {}) {
  if (!m) return "";
  if (m.feita) return "concluída";
  if ((m.tipo === "uso" || m.tipo === "semana") && (m.meta || 1) > 1) return `${m.progresso || 0}/${m.meta}`;
  if (m.tipo === "uso") return "completa sozinha quando você fizer";
  if (m.tipo === "sobre") return cloud ? "responda no PC" : "responda aqui";
  if (m.tipo === "bem") return "toque em FEITO quando fizer";
  return "";
}

export function missionPct(m) {
  if (!m) return 0;
  if (m.feita) return 100;
  return Math.min(100, Math.max(0, Math.round(((m.progresso || 0) / (m.meta || 1)) * 100)));
}

// Ganhou XP / subiu de nível desde a última leitura? (o painel mostra "+15 XP" e "NÍVEL 3!" por uns segundos)
export function progressDelta(prev, next) {
  if (!prev || !next) return null;
  const xp = (next.xp || 0) - (prev.xp || 0);
  const levelUp = (next.nivel || 0) > (prev.nivel || 0);
  if (xp <= 0 && !levelUp) return null;
  return { xp: Math.max(0, xp), levelUp, nivel: next.nivel };
}

// Resumo da etiqueta do painel: "1/3 HOJE"
export function missionsTag(data) {
  if (!data) return "…";
  return `${data.feitas ?? 0}/${data.total ?? 0} HOJE`;
}

// V6.6.6: texto do status do acesso pela nuvem (sem dependências: testado em tests/cloudStatus.test.js).

// "2026-11-13 15:09" -> minutos desde 2000 (só para comparar duas horas de São Paulo)
const minutes = (stamp) => {
  const m = /^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})/.exec(stamp || "");
  return m ? Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]) / 60000 : NaN;
};

/** O notebook falou com a nuvem nos últimos minutos? Então está ligado (você é que está fora de casa). */
export function pcLine(st) {
  const seen = st?.sincronizado_em;
  const gap = minutes(st?.agora) - minutes(seen);
  if (seen && gap >= 0 && gap <= 3) return "notebook ligado em casa · listas sincronizadas";
  if (!seen) return "notebook ainda não sincronizou";
  return `notebook desligado · visto ${seen.slice(8, 10)}/${seen.slice(5, 7)} ${seen.slice(11, 16)}`;
}


// V8.11: o Modo Desk usa as Habilidades (Skills) com botões. Partes puras, testadas (node --test frontend/tests).
// Tudo passa pela rota /api/skills/{nome}/run (só no próprio PC), com as mesmas regras da voz: o que é crítico
// (fechar programa, apagar workspace) só roda depois da confirmação na tela.

export const SKILL_TIMEOUTS = { abrir_workspace: 60_000, area_de_transferencia_ia: 50_000, deep_brief: 130_000 };

/** Roda uma habilidade e devolve { ok, pending, speech, cards, data } (erros de rede viram ok: false). */
export async function runSkill(api, name, { args = null, text = null, confirm = false } = {}) {
  try {
    const body = { ...(args ? { args } : {}), ...(text ? { text } : {}), ...(confirm ? { confirm: true } : {}) };
    return await api(`/api/skills/${encodeURIComponent(name)}/run`, {
      method: "POST", body: JSON.stringify(body), timeout: SKILL_TIMEOUTS[name] || 20_000,
    });
  } catch (err) {
    const speech = err?.status === 403
      ? "Isso só funciona no próprio PC do JARVIS."
      : err?.status === 404 ? "Essa função está desligada ou não existe nesta versão." : (err?.message || "Não deu certo agora.");
    return { ok: false, pending: false, speech, cards: [], data: null };
  }
}

/** Janelas abertas agrupadas por monitor: [{ monitor, janelas: [...] }] em ordem. */
export function groupByMonitor(janelas) {
  const map = new Map();
  for (const j of janelas || []) {
    const m = Number(j.monitor) || 1;
    if (!map.has(m)) map.set(m, []);
    map.get(m).push(j);
  }
  return [...map.entries()].sort((a, b) => a[0] - b[0]).map(([monitor, list]) => ({ monitor, janelas: list }));
}

/** Nível de uso para a cor da barra: ok (até 69%), atenção (70–89%), alto (90%+). */
export function usageLevel(pct) {
  if (pct === null || pct === undefined || pct === "") return "is-unknown"; // Number(null) = 0: pareceria "tudo ok"
  const v = Number(pct);
  if (!Number.isFinite(v)) return "is-unknown";
  if (v >= 90) return "is-hot";
  if (v >= 70) return "is-warn";
  return "is-ok";
}

export function pctText(pct) {
  if (pct === null || pct === undefined || pct === "") return "—";
  const v = Number(pct);
  return Number.isFinite(v) ? `${Math.round(v)}%` : "—";
}

/** "2.150 MB" -> "2,1 GB"; programas pesados vêm com mem_mb. */
export function memText(mb) {
  const v = Number(mb) || 0;
  return v >= 1024 ? `${(v / 1024).toFixed(1).replace(".", ",")} GB` : `${Math.round(v)} MB`;
}

/** Nome para pedir à habilidade de fechar: "Discord.exe" -> "Discord". */
export function processName(name) {
  return String(name || "").replace(/\.exe$/i, "");
}

/** O texto do primeiro cartão genérico de skill (tradução, correção, resumo do copiado). */
export function cardText(result) {
  const card = (result?.cards || []).find((c) => c?.type === "skill");
  return (card?.data?.rows || []).map((r) => r.value).filter(Boolean).join("\n");
}

/** O cartão do painel de pesquisa (dossiê), se veio. */
export function deepCard(result) {
  return (result?.cards || []).find((c) => c?.type === "deep_search")?.data || null;
}

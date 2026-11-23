// V9.0: fila de pedidos da central. Antes, o que o senhor digitava ou falava enquanto o JARVIS pensava em outro
// pedido era ignorado em silêncio (send() saía na hora). Agora fica numa fila curta e vai sozinho quando ele
// volta a "em espera" (depois de falar a resposta anterior). Cancelar esvazia a fila.
export const MAX_QUEUED = 3;

export function enqueue(list, item) {
  const text = (item?.text || "").trim();
  if (!text || list.length >= MAX_QUEUED) return list;
  if (list.some((p) => p.text === text)) return list; // o mesmo pedido duas vezes (clique duplo, eco da voz)
  return [...list, { ...item, text }];
}

export function canDrain(state, busy, list) {
  return state === "idle" && !busy && list.length > 0;
}

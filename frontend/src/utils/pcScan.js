// V8.10.0 (ideia 13): ajudantes leves da varredura do PC lento (o painel em si é carregado só quando abre).

export const PC_SCAN_EVENT = "jarvis-pc-scan";

/** Abre a varredura de qualquer tela (com o resultado pronto, ou null para rodar na hora). */
export function openPcScan(data = null) {
  window.dispatchEvent(new CustomEvent(PC_SCAN_EVENT, { detail: data }));
}

/** Os cartões da resposta trouxeram uma varredura? Devolve os dados (ou null). */
export function scanFromCards(cards) {
  const c = (cards || []).find((x) => x && x.type === "pc_scan");
  return c ? c.data || {} : null;
}

/** A cor da barra: verde até 60%, amarela até 85%, vermelha acima. */
export function barTone(percent) {
  if (percent == null) return "off";
  return percent >= 85 ? "fail" : percent >= 60 ? "warn" : "ok";
}

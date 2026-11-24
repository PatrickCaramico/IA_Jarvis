// V9.3: relatório de segurança — partes puras, testadas.
export const KIND_ICON = { intruso: "🚨", estranho: "🔒", tentativa: "🙅", usb: "🔌", otimizacao: "🧹", ausente: "🚶" };

/** "hoje 14:32" / "ontem 09:10" / "21/11 18:05" a partir do ISO local salvo pelo PC. */
export function whenText(iso, now = new Date()) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const hm = `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  const day = (x) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const diff = Math.round((day(now) - day(d)) / 86400000);
  if (diff === 0) return `hoje ${hm}`;
  if (diff === 1) return `ontem ${hm}`;
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")} ${hm}`;
}

/** Ao entrar na central: abre o relatório sozinho só quando há novidade. */
export function shouldAutoOpen(report) {
  return Boolean(report && Number(report.unseen) > 0);
}

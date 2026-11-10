// Título da aba do navegador com o estado do orbe (V4.2.2), ex.: "● Ouvindo · J.A.R.V.I.S.".
// Função pura: testada em tests/tabTitle.test.js.
export function tabTitle({ name = "J.A.R.V.I.S.", screen = "main", state = "idle", listening = false, connected = true } = {}) {
  if (screen === "boot") return `Iniciando · ${name}`;
  if (screen === "lock") return `🔒 Bloqueado · ${name}`;
  if (!connected) return `○ Sem conexão · ${name}`;
  if (listening) return `● Ouvindo · ${name}`;
  if (state === "processing") return `◐ Pensando · ${name}`;
  if (state === "speaking") return `◉ Falando · ${name}`;
  return name;
}

// V9.4.2: horários do botão NOVO LEMBRETE e da faixa de lembretes da central (puro, testado em tests/reminderTime.test.js).

const pad = (n) => String(n).padStart(2, "0");

/** Data no formato que o PC aceita: "AAAA-MM-DD HH:MM". */
export function toApi(d) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** Valor do <input type="datetime-local"> ("AAAA-MM-DDTHH:MM"). */
export function toInput(d) {
  return toApi(d).replace(" ", "T");
}

export function fromInput(value) {
  const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(String(value || ""));
  return m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]), Number(m[4]), Number(m[5])) : null;
}

export function fromApi(value) {
  return fromInput(String(value || "").replace(" ", "T"));
}

/** Atalhos de horário: em 15 min, 30 min, 1 h, hoje às 18h (se ainda não passou) e amanhã às 9h. */
export function quickTimes(now = new Date()) {
  const plus = (min) => new Date(now.getTime() + min * 60_000);
  const out = [
    { label: "em 15 min", at: plus(15) },
    { label: "em 30 min", at: plus(30) },
    { label: "em 1 h", at: plus(60) },
  ];
  const evening = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 18, 0);
  if (evening.getTime() - now.getTime() > 30 * 60_000) out.push({ label: "hoje às 18h", at: evening });
  out.push({ label: "amanhã às 9h", at: new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 9, 0) });
  return out;
}

/** "14:30", "amanhã 09:00", "sex 28/11 09:00" — como o lembrete aparece na faixa da central. */
export function whenLabel(value, now = new Date()) {
  const d = value instanceof Date ? value : fromApi(value);
  if (!d) return "";
  const hm = `${pad(d.getHours())}:${pad(d.getMinutes())}`;
  const day = (x) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const diff = Math.round((day(d) - day(now)) / 86_400_000);
  if (diff === 0) return hm;
  if (diff === 1) return `amanhã ${hm}`;
  const wd = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"][d.getDay()];
  return `${wd} ${pad(d.getDate())}/${pad(d.getMonth() + 1)} ${hm}`;
}

/** Os pendentes, do mais próximo ao mais distante (os já disparados ficam de fora). */
export function upcoming(reminders, limit = 4) {
  return (reminders || [])
    .filter((r) => r && !r.disparado && fromApi(r.data_hora))
    .sort((a, b) => fromApi(a.data_hora) - fromApi(b.data_hora))
    .slice(0, limit);
}

// V9.4.2: botão NOVO LEMBRETE e faixa de lembretes na central
import { test } from "node:test";
import assert from "node:assert/strict";
import { fromApi, fromInput, quickTimes, toApi, toInput, upcoming, whenLabel } from "../src/utils/reminderTime.js";

const now = new Date(2026, 10, 25, 14, 0); // quarta, 25/11 14:00

test("formatos de data do PC e do campo", () => {
  const d = new Date(2026, 10, 25, 9, 5);
  assert.equal(toApi(d), "2026-11-25 09:05");
  assert.equal(toInput(d), "2026-11-25T09:05");
  assert.equal(fromInput("2026-11-25T09:05").getTime(), d.getTime());
  assert.equal(fromApi("2026-11-25 09:05").getTime(), d.getTime());
  assert.equal(fromInput("lixo"), null);
});

test("atalhos de horário", () => {
  const labels = quickTimes(now).map((q) => q.label);
  assert.deepEqual(labels, ["em 15 min", "em 30 min", "em 1 h", "hoje às 18h", "amanhã às 9h"]);
  assert.equal(toApi(quickTimes(now)[0].at), "2026-11-25 14:15");
  // depois das 17h30 o "hoje às 18h" some
  assert.ok(!quickTimes(new Date(2026, 10, 25, 17, 45)).some((q) => q.label === "hoje às 18h"));
});

test("como aparece na central", () => {
  assert.equal(whenLabel("2026-11-25 16:30", now), "16:30");
  assert.equal(whenLabel("2026-11-26 09:00", now), "amanhã 09:00");
  assert.equal(whenLabel("2026-11-28 09:00", now), "sáb 28/11 09:00");
  const list = upcoming([
    { id: 1, texto: "b", data_hora: "2026-11-26 09:00" },
    { id: 2, texto: "a", data_hora: "2026-11-25 15:00" },
    { id: 3, texto: "velho", data_hora: "2026-11-25 10:00", disparado: true },
  ]);
  assert.deepEqual(list.map((r) => r.id), [2, 1]);
});

// V9.4.5: leituras em volta do reator abrem um menu (processador, memória, disco e próximos)
import { test } from "node:test";
import assert from "node:assert/strict";
import { telemetryMenu } from "../src/utils/hudCenter.js";

test("memória alta sugere ver o que está pesando, com as ações do PC", () => {
  const m = telemetryMenu("ram", { cpu_percent: 23, ram_percent: 90.4, processes: 231, temperature: "Indisponível" });
  assert.equal(m.title, "MEMÓRIA");
  assert.equal(m.value, "90%");
  assert.equal(m.bar, 90.4);
  assert.match(m.note, /Muito alto/);
  assert.deepEqual(m.rows, [["Programas e processos", "231"], ["Processador", "23%"]]); // sem temperatura de mentira
  assert.deepEqual(m.actions.map((a) => a.id), ["heavy", "analyze", "scan"]);
  assert.equal(m.actions[0].command, "o que está pesando no pc");
});

test("processador tranquilo e sem leitura", () => {
  assert.equal(telemetryMenu("cpu", { cpu_percent: 12, temperature: 51.5 }).note, "Tranquilo.");
  assert.deepEqual(telemetryMenu("cpu", { cpu_percent: 12, temperature: 51.5 }).rows, [["Temperatura", "51.5 °C"]]);
  assert.equal(telemetryMenu("cpu", null).value, "—");
});

test("disco com pouco espaço sugere limpar", () => {
  const m = telemetryMenu("disk", { disk_free_gb: 9.2 });
  assert.equal(m.value, "9 GB");
  assert.match(m.note, /Pouco espaço/);
  assert.equal(m.actions[0].event, "pc-scan");
});

test("próximos: até 3, com lembrete e agenda", () => {
  const items = [
    { label: "Hoje 21:00", title: "Ligar para a mãe", kind: "lembrete" },
    { label: "Amanhã 09:30", title: "Reunião", kind: "agenda" },
    { label: "Amanhã 12:00", title: "Almoço", kind: "agenda" },
    { label: "Amanhã 18:00", title: "Academia", kind: "agenda" },
  ];
  const m = telemetryMenu("next", null, items);
  assert.equal(m.value, "Hoje 21:00");
  assert.equal(m.rows.length, 3);
  assert.deepEqual(m.rows[0], ["Hoje 21:00", "⏰ Ligar para a mãe"]);
  assert.deepEqual(m.actions.map((a) => a.id), ["reminder", "agenda"]);
  assert.equal(telemetryMenu("next", null, []).value, "Nada marcado");
});

test("V9.4.6: títulos longos quebram linha dentro do menu PRÓXIMOS", async () => {
  assert.equal(telemetryMenu("next", null, [{ label: "Hoje", title: "x" }]).list, true);
  assert.equal(telemetryMenu("cpu", { cpu_percent: 1 }).list, undefined);
  const { readFileSync } = await import("node:fs");
  const css = readFileSync(new URL("../src/v94.css", import.meta.url), "utf8");
  assert.match(css, /\.hc-menu-rows dd \{[^}]*min-width: 0;[^}]*overflow-wrap: anywhere/);
  assert.match(css, /\.hc-menu-rows\.is-list dd \{[^}]*-webkit-line-clamp: 2/);
});

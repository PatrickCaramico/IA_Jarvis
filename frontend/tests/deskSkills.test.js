// V8.11: o Modo Desk usando as Habilidades (node --test frontend/tests)
import { test } from "node:test";
import assert from "node:assert/strict";
import { cardText, deepCard, groupByMonitor, memText, pctText, processName, runSkill, usageLevel } from "../src/utils/deskSkills.js";

test("runSkill monta o pedido e trata os erros", async () => {
  const calls = [];
  const api = async (path, opts) => { calls.push([path, JSON.parse(opts.body), opts.timeout]); return { ok: true, speech: "feito" }; };
  assert.equal((await runSkill(api, "abrir_workspace", { args: { nome: "estudo" } })).speech, "feito");
  await runSkill(api, "converter_unidades", { text: "5 milhas em km" });
  await runSkill(api, "fechar_programa", { args: { programa: "Discord" }, confirm: true });
  assert.deepEqual(calls[0], ["/api/skills/abrir_workspace/run", { args: { nome: "estudo" } }, 60_000]);
  assert.deepEqual(calls[1][1], { text: "5 milhas em km" });
  assert.deepEqual(calls[2][1], { args: { programa: "Discord" }, confirm: true });
  const denied = await runSkill(async () => { const e = new Error("x"); e.status = 403; throw e; }, "janelas_abertas");
  assert.equal(denied.ok, false);
  assert.match(denied.speech, /próprio PC/);
});

test("janelas por monitor, em ordem", () => {
  const g = groupByMonitor([{ programa: "Spotify", monitor: 2 }, { programa: "Chrome", monitor: 1 }, { programa: "Word", monitor: 1 }]);
  assert.deepEqual(g.map((x) => [x.monitor, x.janelas.map((j) => j.programa)]), [[1, ["Chrome", "Word"]], [2, ["Spotify"]]]);
  assert.deepEqual(groupByMonitor(null), []);
});

test("textos e níveis", () => {
  assert.equal(usageLevel(40), "is-ok");
  assert.equal(usageLevel(75), "is-warn");
  assert.equal(usageLevel(95), "is-hot");
  assert.equal(usageLevel(null), "is-unknown");
  assert.equal(pctText(41.6), "42%");
  assert.equal(pctText(undefined), "—");
  assert.equal(pctText(null), "—");
  assert.equal(memText(2150), "2,1 GB");
  assert.equal(memText(420), "420 MB");
  assert.equal(processName("Discord.exe"), "Discord");
});

test("cartões das respostas", () => {
  const r = { cards: [{ type: "skill", data: { rows: [{ label: "", value: "texto traduzido" }] } }, { type: "deep_search", data: { title: "T" } }] };
  assert.equal(cardText(r), "texto traduzido");
  assert.deepEqual(deepCard(r), { title: "T" });
  assert.equal(deepCard({}), null);
});

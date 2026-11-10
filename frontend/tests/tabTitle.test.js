import { test } from "node:test";
import assert from "node:assert/strict";
import { tabTitle } from "../src/utils/tabTitle.js";

test("título da aba mostra o estado do orbe", () => {
  assert.equal(tabTitle({ listening: true }), "● Ouvindo · J.A.R.V.I.S.");
  assert.equal(tabTitle({ state: "processing" }), "◐ Pensando · J.A.R.V.I.S.");
  assert.equal(tabTitle({ state: "speaking", name: "SEXTA" }), "◉ Falando · SEXTA");
  assert.equal(tabTitle({ state: "idle" }), "J.A.R.V.I.S.");
});

test("bloqueio, início e sem conexão têm prioridade", () => {
  assert.equal(tabTitle({ screen: "lock", listening: true }), "🔒 Bloqueado · J.A.R.V.I.S.");
  assert.equal(tabTitle({ screen: "boot" }), "Iniciando · J.A.R.V.I.S.");
  assert.equal(tabTitle({ connected: false, listening: true }), "○ Sem conexão · J.A.R.V.I.S.");
});

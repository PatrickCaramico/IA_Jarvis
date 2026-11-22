// V8.11: atualizar ao abrir a central (node --test frontend/tests)
import { test } from "node:test";
import assert from "node:assert/strict";
import { AUTO_OPEN_RETRY_MS, shouldAutoUpdateOnOpen } from "../src/utils/updateCheck.js";

const info = { available: true, latest: "8.12.0", auto_on_open: true, busy: false };

test("versão nova ao abrir: atualiza", () => {
  assert.equal(shouldAutoUpdateOnOpen(info, null, 1_000), true);
});

test("sem versão nova, desligado nas configurações ou JARVIS ocupado: não atualiza", () => {
  assert.equal(shouldAutoUpdateOnOpen({ ...info, available: false }, null), false);
  assert.equal(shouldAutoUpdateOnOpen({ ...info, auto_on_open: false }, null), false);
  assert.equal(shouldAutoUpdateOnOpen({ ...info, busy: true }, null), false);
  assert.equal(shouldAutoUpdateOnOpen(null, null), false);
});

test("não insiste na mesma versão logo depois de tentar", () => {
  const last = { latest: "8.12.0", at: 10_000 };
  assert.equal(shouldAutoUpdateOnOpen(info, last, 10_000 + 60_000), false);
  assert.equal(shouldAutoUpdateOnOpen(info, last, 10_000 + AUTO_OPEN_RETRY_MS + 1), true);
  assert.equal(shouldAutoUpdateOnOpen({ ...info, latest: "8.13.0" }, last, 10_001), true); // versão mais nova ainda: tenta
});

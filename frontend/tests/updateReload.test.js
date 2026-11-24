// V9.4.5: depois de uma atualização, o bloqueio aparece sem ligar a câmera sozinho
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { UPDATE_RELOAD_WINDOW_MS, consumeUpdateReload, markUpdateReload } from "../src/utils/session.js";

function memory() {
  const data = {};
  return { getItem: (k) => data[k] ?? null, setItem: (k, v) => { data[k] = String(v); }, removeItem: (k) => { delete data[k]; } };
}

test("a marca vale uma abertura só e por pouco tempo", () => {
  const st = memory();
  assert.equal(consumeUpdateReload(1000, st), false); // abrir normal: verificação rápida como sempre
  markUpdateReload(1000, st);
  assert.equal(consumeUpdateReload(2000, st), true);
  assert.equal(consumeUpdateReload(3000, st), false); // já consumida
  markUpdateReload(0 + 5, st);
  assert.equal(consumeUpdateReload(5 + UPDATE_RELOAD_WINDOW_MS + 1, st), false); // velha demais
});

test("todo recarregamento por atualização deixa a marca e o boot respeita", () => {
  const app = readFileSync(new URL("../src/App.jsx", import.meta.url), "utf8");
  assert.doesNotMatch(app, /window\.location\.reload\(\), (900|1500|700)\)/);
  assert.match(app, /const afterUpdate = consumeUpdateReload\(\)/);
  assert.match(app, /if \(afterUpdate && !wake\) wakeHandledRef\.current = true;/);
  const nb = readFileSync(new URL("../src/utils/newBuild.js", import.meta.url), "utf8");
  assert.match(nb, /reloadAfterUpdate\(\)/);
});

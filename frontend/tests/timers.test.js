// Busca periódica que pausa com a aba oculta e relógio central (otimização 4.2).
import { test } from "node:test";
import assert from "node:assert/strict";
import { startPolling } from "../src/utils/polling.js";

function fakeDocument(hidden = false) {
  const listeners = new Set();
  return {
    hidden,
    addEventListener: (_, fn) => listeners.add(fn),
    removeEventListener: (_, fn) => listeners.delete(fn),
    setHidden(value) {
      this.hidden = value;
      listeners.forEach((fn) => fn());
    },
    get listenerCount() {
      return listeners.size;
    },
  };
}

test("roda na hora e repete no intervalo com a aba visível", (t) => {
  t.mock.timers.enable({ apis: ["setInterval", "Date"] });
  const doc = fakeDocument(false);
  let calls = 0;
  const stop = startPolling(() => { calls += 1; }, 1000, { doc });
  assert.equal(calls, 1);
  t.mock.timers.tick(3000);
  assert.equal(calls, 4);
  stop();
  t.mock.timers.tick(3000);
  assert.equal(calls, 4);
  assert.equal(doc.listenerCount, 0);
});

test("para com a aba oculta e atualiza ao voltar se o dado ficou velho", (t) => {
  t.mock.timers.enable({ apis: ["setInterval", "Date"] });
  const doc = fakeDocument(false);
  let calls = 0;
  const stop = startPolling(() => { calls += 1; }, 1000, { doc });
  doc.setHidden(true);
  t.mock.timers.tick(10_000);
  assert.equal(calls, 1, "nenhuma busca com a aba oculta");
  doc.setHidden(false);
  assert.equal(calls, 2, "uma busca imediata ao voltar");
  t.mock.timers.tick(1000);
  assert.equal(calls, 3);
  stop();
});

test("não repete a busca ao voltar rápido para a aba", (t) => {
  t.mock.timers.enable({ apis: ["setInterval", "Date"] });
  const doc = fakeDocument(false);
  let calls = 0;
  const stop = startPolling(() => { calls += 1; }, 60_000, { doc });
  doc.setHidden(true);
  t.mock.timers.tick(5000);
  doc.setHidden(false);
  assert.equal(calls, 1);
  stop();
});

test("aba já oculta ao montar: busca uma vez e espera a aba aparecer", (t) => {
  t.mock.timers.enable({ apis: ["setInterval", "Date"] });
  const doc = fakeDocument(true);
  let calls = 0;
  const stop = startPolling(() => { calls += 1; }, 1000, { doc });
  t.mock.timers.tick(5000);
  assert.equal(calls, 1);
  stop();
});

test("erro na busca não derruba o timer", (t) => {
  t.mock.timers.enable({ apis: ["setInterval", "Date"] });
  const doc = fakeDocument(false);
  let calls = 0;
  const stop = startPolling(() => { calls += 1; return Promise.reject(new Error("offline")); }, 1000, { doc });
  t.mock.timers.tick(2000);
  assert.equal(calls, 3);
  stop();
});

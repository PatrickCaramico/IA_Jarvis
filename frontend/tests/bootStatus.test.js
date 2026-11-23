import assert from "node:assert/strict";
import test from "node:test";

const store = new Map();
globalThis.localStorage = {
  getItem: (k) => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => store.set(k, String(v)),
  removeItem: (k) => store.delete(k),
};

const { formatElapsed, knownAlwaysOn, nextCheckProgress, reconnectHint, rememberAlwaysOn } =
  await import("../src/utils/bootStatus.js");

test("V8.12.3: lembra se o PC está no sempre ligado", () => {
  store.clear();
  assert.equal(knownAlwaysOn(), null);
  rememberAlwaysOn(true);
  assert.equal(knownAlwaysOn(), true);
  rememberAlwaysOn(false);
  assert.equal(knownAlwaysOn(), false);
});

test("V8.12.3: tempo procurando em texto curto", () => {
  assert.equal(formatElapsed(0), "0 s");
  assert.equal(formatElapsed(8_400), "8 s");
  assert.equal(formatElapsed(60_000), "1 min");
  assert.equal(formatElapsed(80_000), "1 min 20 s");
  assert.equal(formatElapsed((2 * 60 + 5) * 60_000), "2 h 05 min");
  assert.equal(formatElapsed(-5), "0 s");
});

test("V8.12.3: frase conforme o que está acontecendo", () => {
  assert.match(reconnectHint({ launchState: "opening" }), /Ligando o JARVIS do PC/);
  assert.match(reconnectHint({ launchState: "asked" }), /Clique em Abrir/);
  assert.match(reconnectHint({ alwaysOn: true }), /liga o JARVIS sozinho/);
  assert.match(reconnectHint({ alwaysOn: true, elapsedMs: 6 * 60_000 }), /desligado ou sem internet/);
  assert.match(reconnectHint({}), /eu entro sozinho/);
});

test("V8.12.3: barrinha até a próxima conferência", () => {
  assert.equal(nextCheckProgress(1000, 0, 0), 0);
  assert.equal(nextCheckProgress(11_000, 10_000, 12_000), 0.5);
  assert.equal(nextCheckProgress(15_000, 10_000, 12_000), 1);
  assert.equal(nextCheckProgress(9_000, 10_000, 12_000), 0);
});

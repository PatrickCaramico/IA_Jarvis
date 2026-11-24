// V9.5.0: tela de bloqueio renovada (reator personalizado, estados, anel dos segundos e economia de madrugada)
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SLEEP_IDLE_MS, lockReactorShape, lockSleeping, reactorStateClass, secondsDelay } from "../src/utils/lockLook.js";

test("sem personalização fica o Reator Arc de sempre; personalizado, a forma escolhida", () => {
  assert.equal(lockReactorShape(null), "classic");
  assert.equal(lockReactorShape({}), "classic");
  assert.equal(lockReactorShape({ shape: "fios" }), "classic"); // padrão da central = clássico no bloqueio
  assert.equal(lockReactorShape({ shape: "fios", color: "#a855f7" }), "fios");
  assert.equal(lockReactorShape({ shape: "reator", color: "#22c55e" }), "reator");
  assert.equal(lockReactorShape({ shape: "minimal" }), "minimal");
});

test("o anel mostra o estado", () => {
  assert.equal(reactorStateClass({ phase: "scanning" }), "is-scanning");
  assert.equal(reactorStateClass({ phase: "verified", listening: true }), "is-ok");
  assert.equal(reactorStateClass({ phase: "failed" }), "is-fail");
  assert.equal(reactorStateClass({ phase: "ready", listening: true }), "is-listening");
  assert.equal(reactorStateClass({ phase: "ready", speaking: true }), "is-speaking");
  assert.equal(reactorStateClass({}), "is-idle");
});

test("o ponteiro dos segundos começa no segundo certo", () => {
  assert.equal(secondsDelay(new Date(2026, 10, 24, 17, 30, 42, 500)), "-42.50s");
  assert.equal(secondsDelay(new Date(2026, 10, 24, 17, 30, 0, 0)), "-0.00s");
});

test("economia só de madrugada, parado e sem ninguém mexer", () => {
  assert.equal(lockSleeping({ hour: 3, idleMs: SLEEP_IDLE_MS }), true);
  assert.equal(lockSleeping({ hour: 3, idleMs: SLEEP_IDLE_MS - 1 }), false);
  assert.equal(lockSleeping({ hour: 14, idleMs: SLEEP_IDLE_MS * 10 }), false);
  assert.equal(lockSleeping({ hour: 6, idleMs: SLEEP_IDLE_MS * 10 }), false);
  assert.equal(lockSleeping({ hour: 0, idleMs: SLEEP_IDLE_MS, phase: "scanning" }), false);
  assert.equal(lockSleeping({ hour: 0, idleMs: SLEEP_IDLE_MS, listening: true }), false);
  assert.equal(lockSleeping({ hour: 2, idleMs: SLEEP_IDLE_MS, phase: "failed" }), true);
});

test("o layout: GERENCIAR no lugar dos 10 botões, colunas alinhadas, sono e entrada da central", () => {
  const jsx = readFileSync(new URL("../src/components/LockScreen.jsx", import.meta.url), "utf8");
  assert.match(jsx, /<LockManage updateCount=/);
  assert.match(jsx, /\{phase !== "pin" && essentialActions\}/); // Sentinela: só o essencial à vista
  assert.doesNotMatch(jsx, /<ArcReactorHUD/); // o reator do bloqueio passa pelo LockReactor
  const css = readFileSync(new URL("../src/v94.css", import.meta.url), "utf8");
  assert.match(css, /\.ls-container \.lc-row \{ top: clamp\(150px, 20vh, 220px\); transform: none; \}/);
  assert.match(css, /html\.lock-sleep #root \* \{ animation-play-state: paused !important; \}/);
  assert.match(css, /\.hl-root \{ animation: hl-reveal/);
});

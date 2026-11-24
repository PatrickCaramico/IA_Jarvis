import test from "node:test";
import assert from "node:assert/strict";
import { FPS, breath, nextAngle, paused } from "../src/utils/slowSpin.js";

test("ângulo anda uma volta por período, nos dois sentidos", () => {
  assert.equal(nextAngle(0, 15, 60), 90);
  assert.equal(nextAngle(10, 30, -60), 190);
  assert.equal(nextAngle(350, 6, 60), 26);
  assert.equal(nextAngle(42, 1, 0), 42);
});

test("respiração vai de 0 a 1 e volta", () => {
  assert.equal(breath(0, 5), 0);
  assert.ok(Math.abs(breath(2.5, 5) - 1) < 1e-9);
  assert.ok(Math.abs(breath(5, 5)) < 1e-9);
});

test("10 quadros por segundo e parado no modo leve, com movimento reduzido ou aba escondida", () => {
  assert.equal(FPS, 10);
  const mk = (cls = [], motion, hidden = false, reduce = false) => [
    { hidden, documentElement: { classList: { contains: (c) => cls.includes(c) }, dataset: { motion } } },
    { matchMedia: () => ({ matches: reduce }) },
  ];
  assert.equal(paused(...mk()), false);
  assert.equal(paused(...mk(["is-lite"])), true);
  assert.equal(paused(...mk([], "reduce")), true);
  assert.equal(paused(...mk([], undefined, true)), true);
  assert.equal(paused(...mk([], undefined, false, true)), true);
});

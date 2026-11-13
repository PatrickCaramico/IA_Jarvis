// V7.2: nota do ⚡ OTIMIZAR (node --test frontend/tests)
import { test } from "node:test";
import assert from "node:assert/strict";
import { score } from "../src/utils/perfMode.js";

test("nota: tela lisa e PC rápido = 100; aparelho travando cai", () => {
  assert.equal(score({ fps: 60, pingMs: 80 }), 100);
  assert.ok(score({ fps: 25, pingMs: 900 }) < 15);
  assert.equal(score({ fps: 60, pingMs: null }), 85);
});

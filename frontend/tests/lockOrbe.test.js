import { test } from "node:test";
import assert from "node:assert/strict";
import { buildCurves, orbeLabel, radius } from "../src/utils/lockOrbe.js";

test("V7.12: estado em cima do orbe do bloqueio", () => {
  assert.equal(orbeLabel({ phase: "ready", jarvisState: "idle" }), "EM ESPERA");
  assert.equal(orbeLabel({ phase: "ready", jarvisState: "speaking" }), "FALANDO");
  assert.equal(orbeLabel({ phase: "ready", jarvisState: "idle", listening: true }), "OUVINDO");
  assert.equal(orbeLabel({ phase: "scanning" }), "ESCANEANDO");
  assert.equal(orbeLabel({ phase: "verified" }), "IDENTIDADE CONFIRMADA");
  assert.equal(orbeLabel({ phase: "failed" }), "ACESSO NEGADO");
});

test("V7.12: linhas do orbe ficam perto do anel e abrem com a energia", () => {
  const curves = buildCurves(15);
  assert.equal(curves.length, 15);
  assert.deepEqual(buildCurves(3), buildCurves(3)); // sempre o mesmo desenho
  for (const c of curves) {
    for (let t = 0; t < 6.3; t += 0.3) {
      const r = radius(c, t, 12.5, 1);
      assert.ok(r > 0.7 && r < 1.15, `raio ${r}`);
    }
  }
  const c = curves[0];
  const spread = (e) => Math.max(...[0, 1, 2, 3, 4, 5].map((t) => Math.abs(radius(c, t, 0, e) - c.base)));
  assert.ok(spread(1.7) > spread(1));
});

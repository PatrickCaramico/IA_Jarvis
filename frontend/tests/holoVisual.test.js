import { test } from "node:test";
import assert from "node:assert/strict";
import { chartGeometry, fmtNum } from "../src/utils/holoVisual.js";

test("V7.13: gráfico do holograma", () => {
  const g = chartGeometry([{ rotulo: "a", valor: 10 }, { rotulo: "b", valor: 5 }, { rotulo: "c", valor: 0 }]);
  assert.equal(g.points.length, 3);
  assert.ok(g.points[0].y < g.points[1].y); // maior valor = barra mais alta
  assert.equal(g.points[2].y, g.base);
  const neg = chartGeometry([{ rotulo: "a", valor: -4 }, { rotulo: "b", valor: 4 }]);
  assert.equal(neg.points[0].y, neg.base); // negativo desce a partir do eixo
  const line = chartGeometry([{ rotulo: "a", valor: 1 }, { rotulo: "b", valor: 3 }], "linha");
  assert.match(line.line, /^M[\d.]+ [\d.]+ L/);
  assert.match(line.area, /Z$/);
  assert.equal(fmtNum(6.12), "6,1");
  assert.equal(fmtNum(1500), "1.500");
});

// Testes do detector de palmas (rodar com: node --test frontend/tests)
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import {
  countDoubles,
  createClapDetector,
  postSilenceFor,
  sensitivityParams,
} from "../src/utils/clapDetector.js";

const here = dirname(fileURLToPath(import.meta.url));
const fixtures = JSON.parse(readFileSync(join(here, "..", "..", "tests", "fixtures", "clap_sequences.json"), "utf8"));

for (const seq of fixtures.sequences) {
  test(`sequência compartilhada: ${seq.name}`, () => {
    assert.equal(countDoubles(seq, fixtures.frame_ms), seq.expect);
  });
}

test("sensibilidade mapeia fator e mínimo absoluto", () => {
  assert.deepEqual(sensitivityParams(1), { factor: 12, minAbs: 0.12 });
  const s10 = sensitivityParams(10);
  assert.equal(s10.factor, 3);
  assert.ok(Math.abs(s10.minAbs - 0.02) < 1e-9);
  assert.deepEqual(sensitivityParams(99), sensitivityParams(10));
});

test("silêncio depois da segunda palma acompanha o intervalo", () => {
  assert.equal(postSilenceFor(150), 400);
  assert.equal(postSilenceFor(600), 750);
  assert.equal(postSilenceFor(800), 900);
});

test("dispara em menos de 1 s após a segunda palma", () => {
  const det = createClapDetector({ sensitivity: 5 });
  let firedAt = null;
  for (let t = 0; t < 3000; t += 10) {
    let e = 0.004;
    if (t >= 600 && t < 630) e = 0.5;
    if (t >= 900 && t < 930) e = 0.5;
    if (det.process(e, t) === "double" && firedAt == null) firedAt = t;
  }
  assert.ok(firedAt != null);
  assert.ok(firedAt - 900 < 1000, `disparou ${firedAt - 900} ms após a 2ª palma`);
});

test("entradas inválidas não quebram", () => {
  const det = createClapDetector();
  assert.equal(det.process(NaN, 0), null);
  assert.equal(det.process(-1, 10), null);
  assert.equal(det.process(undefined, 20), null);
});

import test from "node:test";
import assert from "node:assert/strict";
import { enqueue, canDrain, MAX_QUEUED } from "../src/utils/turnQueue.js";

test("enfileira até o limite, sem repetidos nem vazios", () => {
  let q = [];
  q = enqueue(q, { text: " que horas são " });
  q = enqueue(q, { text: "que horas são" });
  q = enqueue(q, { text: "  " });
  assert.deepEqual(q.map((p) => p.text), ["que horas são"]);
  for (let i = 0; i < 5; i += 1) q = enqueue(q, { text: `pedido ${i}` });
  assert.equal(q.length, MAX_QUEUED);
});

test("só libera em espera e sem pedido em andamento", () => {
  const q = [{ text: "a" }];
  assert.equal(canDrain("idle", false, q), true);
  assert.equal(canDrain("speaking", false, q), false);
  assert.equal(canDrain("processing", true, q), false);
  assert.equal(canDrain("idle", false, []), false);
});

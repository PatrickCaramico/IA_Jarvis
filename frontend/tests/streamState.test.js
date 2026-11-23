import assert from "node:assert/strict";
import test from "node:test";

const { EMPTY_STREAM, applyStream, markStreamed, wasStreamed } = await import("../src/utils/streamState.js");
const { copyText } = await import("../src/utils/copyText.js");

test("V8.13: o texto ao vivo cresce e ignora aviso fora de ordem", () => {
  let st = applyStream(EMPTY_STREAM, { seq: 1, text: "Olá" });
  st = applyStream(st, { seq: 3, text: "Olá, senhor. Hoje" });
  st = applyStream(st, { seq: 2, text: "Olá, senhor" }); // chegou atrasado
  assert.deepEqual(st, { seq: 3, text: "Olá, senhor. Hoje" });
});

test("V8.13: trocou de IA no meio: recomeça do zero", () => {
  const st = applyStream({ seq: 4, text: "abc" }, { seq: 5, reset: true, text: "" });
  assert.deepEqual(st, { seq: 5, text: "" });
});

test("V8.13: resposta já mostrada pelo streaming não é redigitada", () => {
  markStreamed("Vai chover à tarde, senhor");
  assert.equal(wasStreamed("Vai chover à tarde, senhor."), true); // o último pedacinho chegou só na final
  assert.equal(wasStreamed("Outra resposta"), false);
  markStreamed("");
  assert.equal(wasStreamed("Vai chover à tarde, senhor."), false);
});

test("V8.13: copiar a resposta", async () => {
  const got = [];
  assert.equal(await copyText("oi", { clipboard: { writeText: async (t) => got.push(t) } }, null), true);
  assert.deepEqual(got, ["oi"]);
  assert.equal(await copyText("", { clipboard: { writeText: async () => {} } }, null), false);
  assert.equal(await copyText("x", { clipboard: { writeText: async () => { throw new Error("negado"); } } }, null), false);
});

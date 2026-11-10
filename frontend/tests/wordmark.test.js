import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { LETTERS, wordmarkStrokes, isJarvisName } from "../src/utils/wordmark.js";

const py = readFileSync(fileURLToPath(new URL("../../scripts/dev/gerar_kit_logo.py", import.meta.url)), "utf8");

test("as letras da tela são as mesmas do kit de logo", () => {
  for (const [ch, [width, paths]] of Object.entries(LETTERS)) {
    const m = py.match(new RegExp(`"${ch}": \\((\\d+), \\[([^\\]]+)\\]\\)`));
    assert.ok(m, `letra ${ch} no gerador`);
    assert.equal(Number(m[1]), width, `largura de ${ch}`);
    assert.deepEqual([...m[2].matchAll(/"([^"]+)"/g)].map((x) => x[1]), paths, `traços de ${ch}`);
  }
});

test("largura do nome e reconhecimento do nome", () => {
  const { strokes, width } = wordmarkStrokes();
  assert.equal(width, 5 * 56 + 9 + 5 * 18);
  assert.equal(strokes.length, 8);
  assert.ok(isJarvisName("J.A.R.V.I.S.") && isJarvisName("jarvis"));
  assert.ok(!isJarvisName("SEXTA"));
});

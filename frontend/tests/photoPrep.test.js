// V7.8: foto da galeria (node --test frontend/tests)
import { test } from "node:test";
import assert from "node:assert/strict";
import { fitSize, isImageFile } from "../src/utils/photoPrep.js";

test("reduz para no máximo 1600 px mantendo a proporção", () => {
  assert.deepEqual(fitSize(4000, 3000), { width: 1600, height: 1200 });
  assert.deepEqual(fitSize(1080, 2400), { width: 720, height: 1600 });
  assert.deepEqual(fitSize(800, 600), { width: 800, height: 600 }); // pequena: não aumenta
});

test("aceita só imagens", () => {
  assert.ok(isImageFile({ type: "image/jpeg", name: "a.jpg" }));
  assert.ok(isImageFile({ type: "", name: "IMG_0001.HEIC" }));
  assert.ok(!isImageFile({ type: "application/pdf", name: "conta.pdf" }));
  assert.ok(!isImageFile(null));
});

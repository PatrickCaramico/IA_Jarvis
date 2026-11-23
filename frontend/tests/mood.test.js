import test from "node:test";
import assert from "node:assert/strict";
import { applyMood, moodFor } from "../src/utils/mood.js";

test("clima por hora", () => {
  assert.deepEqual([0, 4, 5, 11, 12, 17, 18, 23, 24, -1].map(moodFor),
    ["madrugada", "madrugada", "manha", "manha", "tarde", "tarde", "noite", "noite", "madrugada", "noite"]);
});

test("aplica no documento só quando muda", () => {
  const root = { dataset: {} };
  assert.equal(applyMood(new Date(2026, 10, 23, 8), root), "manha");
  assert.equal(root.dataset.mood, "manha");
  assert.equal(applyMood(new Date(2026, 10, 23, 21), root), "noite");
  assert.equal(root.dataset.mood, "noite");
});

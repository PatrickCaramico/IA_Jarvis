import test from "node:test";
import assert from "node:assert/strict";
import { MOODS, clampVolume, fmtTime } from "../src/utils/spotifyMoods.js";

test("volume sempre entre 0 e 100", () => {
  assert.equal(clampVolume("42.6"), 43);
  assert.equal(clampVolume(140), 100);
  assert.equal(clampVolume(-3), 0);
  assert.equal(clampVolume("abc", 55), 55);
});

test("tempo da faixa", () => {
  assert.equal(fmtTime(65_000), "1:05");
  assert.equal(fmtTime(undefined), "0:00");
});

test("atalhos de clima têm busca e rótulo", () => {
  assert.ok(MOODS.length >= 4);
  for (const m of MOODS) assert.ok(m.query && m.label && m.icon);
});

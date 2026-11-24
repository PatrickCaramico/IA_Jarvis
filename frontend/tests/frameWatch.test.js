import test from "node:test";
import assert from "node:assert/strict";
import { LOW_FPS, STRIKES, nextStrikes, shouldEco } from "../src/utils/frameWatch.js";

test("duas medições ruins seguidas ligam o modo econômico; uma boa zera", () => {
  assert.equal(LOW_FPS, 40);
  let s = 0;
  s = nextStrikes(s, 25);
  assert.equal(shouldEco(s), false);
  s = nextStrikes(s, 58);
  assert.equal(s, 0);
  s = nextStrikes(nextStrikes(s, 30), 22);
  assert.equal(s, STRIKES);
  assert.equal(shouldEco(s), true);
});

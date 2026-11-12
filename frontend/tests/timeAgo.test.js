import { test } from "node:test";
import assert from "node:assert/strict";
import { timeAgo } from "../src/utils/timeAgo.js";

test("tempo relativo das manchetes", () => {
  const now = Date.parse("2026-11-12T15:00:00Z");
  assert.equal(timeAgo("2026-11-12T14:59:50Z", now), "agora");
  assert.equal(timeAgo("2026-11-12T14:40:00Z", now), "há 20 min");
  assert.equal(timeAgo("2026-11-12T12:00:00Z", now), "há 3 h");
  assert.equal(timeAgo("2026-11-11T13:00:00Z", now), "ontem");
  assert.equal(timeAgo("2026-11-09T15:00:00Z", now), "há 3 dias");
  assert.equal(timeAgo("", now), "");
});

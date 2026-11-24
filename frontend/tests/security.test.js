import test from "node:test";
import assert from "node:assert/strict";
import { KIND_ICON, shouldAutoOpen, whenText } from "../src/utils/security.js";

test("quando: hoje, ontem ou a data", () => {
  const now = new Date(2026, 10, 24, 15, 0);
  assert.equal(whenText("2026-11-24T14:32:00", now), "hoje 14:32");
  assert.equal(whenText("2026-11-23T09:05:00", now), "ontem 09:05");
  assert.equal(whenText("2026-11-21T18:05:00", now), "21/11 18:05");
  assert.equal(whenText("lixo", now), "");
});

test("abre sozinho só com novidade; todo tipo tem ícone", () => {
  assert.equal(shouldAutoOpen({ unseen: 2 }), true);
  assert.equal(shouldAutoOpen({ unseen: 0 }), false);
  assert.equal(shouldAutoOpen(null), false);
  for (const k of ["intruso", "estranho", "tentativa", "usb", "otimizacao", "ausente"]) assert.ok(KIND_ICON[k], k);
});

// V7.6: nome e tipo do aparelho que pede a chave (node --test frontend/tests)
import { test } from "node:test";
import assert from "node:assert/strict";

import { deviceInfo } from "../src/utils/deviceInfo.js";

test("reconhece celular, tablet, TV, PC e o app", () => {
  assert.deepEqual(deviceInfo("Mozilla/5.0 (Linux; Android 14; SM-S911B Build/UP1A) AppleWebKit Mobile Safari"), { name: "SM-S911B", kind: "celular" });
  assert.deepEqual(deviceInfo("Mozilla/5.0 (Linux; Android 13; SM-X200) AppleWebKit Safari"), { name: "SM-X200", kind: "tablet" });
  assert.equal(deviceInfo("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Mobile").name, "iPhone");
  assert.equal(deviceInfo("Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome").kind, "pc");
  assert.equal(deviceInfo("Mozilla/5.0 (Linux; Android 11; BRAVIA 4K) SmartTV").kind, "tv");
  assert.match(deviceInfo("Mozilla/5.0 (Linux; Android 14; K) Mobile JarvisApp/7.6").name, /Celular Android \(app JARVIS\)/);
});

// V8.12: a janela do Spotify da central fica sempre visível (node --test frontend/tests)
import { test } from "node:test";
import assert from "node:assert/strict";
import { hasTrack, standbyView } from "../src/utils/nowPlaying.js";

test("com faixa, o cartão completo", () => {
  assert.equal(hasTrack({ state: "playing" }), true);
  assert.equal(hasTrack({ state: "paused" }), true);
  assert.equal(hasTrack({ state: "idle" }), false);
  assert.equal(hasTrack(null), false);
});

test("sem faixa, o próximo passo certo", () => {
  assert.equal(standbyView({ state: "off" }).action, "connect");
  assert.equal(standbyView({ state: "idle" }).action, "play");
  assert.equal(standbyView({ state: "error" }).action, "retry");
  assert.equal(standbyView(null).action, "retry"); // o PC não respondeu
  assert.match(standbyView({ state: "idle" }).head, /SPOTIFY/);
});

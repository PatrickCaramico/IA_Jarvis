// V8.12: a janela do Spotify da central fica sempre visível (node --test frontend/tests)
import { test } from "node:test";
import assert from "node:assert/strict";
import { CLOUD_STALE_S, cloudTrack, hasTrack, standbyView } from "../src/utils/nowPlaying.js";

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

test("V8.12.2: no site, a música vem do PC", () => {
  const t = { state: "playing", title: "Yellow", progress_ms: 1000, duration_ms: 266000, at: 1000 };
  assert.equal(cloudTrack(t, 1030).progress_ms, 31000); // andou 30 s desde a última notícia
  assert.equal(cloudTrack({ ...t, progress_ms: 265000 }, 1100).progress_ms, 266000); // não passa do fim
  assert.equal(cloudTrack({ ...t, state: "paused" }, 1100).progress_ms, 1000); // pausada não anda
  assert.equal(cloudTrack(t, 1000 + CLOUD_STALE_S + 1).state, "away"); // PC sem dar notícia
  assert.equal(cloudTrack(null).state, "away");
  assert.equal(standbyView({ state: "away" }).action, "none");
});

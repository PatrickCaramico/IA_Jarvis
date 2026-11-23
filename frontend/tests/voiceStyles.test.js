import assert from "node:assert/strict";
import test from "node:test";

const { DEFAULT_INTRO_SONG, VOICE_STYLES, shouldPlayOnOpen } = await import("../src/utils/voiceStyles.js");

test("V8.13: Back in Black toca ao abrir o painel VOZ só uma vez e nunca no modo silencioso", () => {
  assert.equal(DEFAULT_INTRO_SONG, "Back in Black AC/DC");
  assert.equal(shouldPlayOnOpen({ alreadyPlayed: false, silent: false, song: DEFAULT_INTRO_SONG }), true);
  assert.equal(shouldPlayOnOpen({ alreadyPlayed: true, silent: false, song: DEFAULT_INTRO_SONG }), false);
  assert.equal(shouldPlayOnOpen({ alreadyPlayed: false, silent: true, song: DEFAULT_INTRO_SONG }), false);
  assert.equal(shouldPlayOnOpen({ alreadyPlayed: false, silent: false, song: "  " }), false);
});

test("V8.13: os estilos de voz batem com os do PC (tts.VOICE_STYLES)", () => {
  assert.deepEqual(VOICE_STYLES.map(([k]) => k), ["natural", "grave", "classica", "thalita", "andrew"]);
});

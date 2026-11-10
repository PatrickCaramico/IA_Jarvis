import { test } from "node:test";
import assert from "node:assert/strict";
import { soundPolicy, soundManager } from "../src/utils/soundEffects.js";

const at = (hour) => new Date(2026, 9, 30, hour, 0, 0);
const cfg = (over = {}) => ({ enabled: true, silent: false, mode: "all", volume: 60, ...over });

test("de dia, modo todos: toca no volume configurado", () => {
  assert.equal(soundPolicy("listening", cfg(), at(12)), 0.6);
  assert.equal(soundPolicy("error", cfg({ volume: 100 }), at(12)), 1);
});

test("desligado, silencioso ou modo off: nada toca", () => {
  assert.equal(soundPolicy("error", cfg({ enabled: false }), at(12)), 0);
  assert.equal(soundPolicy("error", cfg({ silent: true }), at(12)), 0);
  assert.equal(soundPolicy("error", cfg({ mode: "off" }), at(12)), 0);
});

test("só o que importa: erro e alerta tocam, o resto não", () => {
  const c = cfg({ mode: "important" });
  assert.equal(soundPolicy("error", c, at(12)), 0.6);
  assert.equal(soundPolicy("alert", c, at(12)), 0.6);
  assert.equal(soundPolicy("success", c, at(12)), 0);
  assert.equal(soundPolicy("listening", c, at(12)), 0);
});

test("das 22h às 7h: só sons importantes, com metade do volume", () => {
  for (const h of [22, 23, 0, 3, 6]) {
    assert.equal(soundPolicy("listening", cfg(), at(h)), 0, `hora ${h}`);
    assert.equal(soundPolicy("error", cfg(), at(h)), 0.3, `hora ${h}`);
  }
  assert.equal(soundPolicy("listening", cfg(), at(7)), 0.6);
  assert.equal(soundPolicy("listening", cfg(), at(21)), 0.6);
});

test("volume fora da faixa é limitado de 0 a 100", () => {
  assert.equal(soundPolicy("error", cfg({ volume: 250 }), at(12)), 1);
  assert.equal(soundPolicy("error", cfg({ volume: -5 }), at(12)), 0);
});

test("configure muda o volume e o modo do soundManager", () => {
  const before = { ...soundManager.settings };
  soundManager.configure({ volume: 30, mode: "important", silent: 1 });
  assert.deepEqual(soundManager.settings, { volume: 30, mode: "important", silent: true });
  soundManager.configure(before);
});

test("prévia sem navegador não quebra e limpa o volume temporário", () => {
  soundManager.preview("error", 80);
  soundManager.preview("inexistente");
  assert.equal(soundManager.previewLevel, null);
});

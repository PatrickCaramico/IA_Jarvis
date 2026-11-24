// V9.4.2: personalizar o Reator Arc (forma, cor, contraste, brilho, velocidade e fios)
import { test } from "node:test";
import assert from "node:assert/strict";
import { DEFAULTS, cssVars, hexToRgb, isDefault, load, normalize, resetFromUrl, save } from "../src/utils/reactor.js";

function memory() {
  const data = {};
  return { getItem: (k) => data[k] ?? null, setItem: (k, v) => { data[k] = String(v); }, removeItem: (k) => { delete data[k]; } };
}

test("valores estranhos voltam para o que a central sabe desenhar", () => {
  assert.deepEqual(normalize(null), DEFAULTS);
  const n = normalize({ shape: "triângulo", color: "red", contrast: 999, glow: -5, speed: "abc", wires: 3 });
  assert.deepEqual(n, { shape: "fios", color: "#4fdcff", contrast: 160, glow: 0, speed: 100, wires: 6 });
  assert.equal(normalize({ color: "#A855F7" }).color, "#a855f7");
  assert.ok(isDefault({}) && !isDefault({ shape: "minimal" }));
});

test("salva neste aparelho e lê de volta", () => {
  const st = memory();
  assert.deepEqual(load(st), DEFAULTS);
  save({ shape: "minimal", color: "#22c55e", glow: 0 }, st);
  assert.deepEqual(load(st), { ...DEFAULTS, shape: "minimal", color: "#22c55e", glow: 0 });
});

test("variáveis do orbe", () => {
  assert.deepEqual(cssVars({ color: "#ef4444", contrast: 120, glow: 0, speed: 200 }),
    { "--rx-color": "#ef4444", "--rx-hue": "169deg", "--rx-contrast": "1.20", "--rx-glow": "0.0px", "--rx-slow": "0.500" });
  assert.equal(cssVars({})["--rx-hue"], "1deg"); // o ciano do JARVIS quase não gira
  assert.deepEqual(hexToRgb("#22c55e"), [34, 197, 94]);
  assert.deepEqual(hexToRgb("x"), [79, 220, 255]);
});

test("V9.4.4: ?reator=padrao volta ao padrão", () => {
  const st = memory();
  save({ shape: "emaranhado" }, st);
  assert.equal(resetFromUrl("?upd=0", st), false);
  assert.equal(load(st).shape, "emaranhado");
  assert.equal(resetFromUrl("?reator=padrao", st), true);
  assert.deepEqual(load(st), DEFAULTS);
});

test("V9.4.4: o canvas do Emaranhado fica preso ao quadro do orbe e não engole cliques", async () => {
  const { readFileSync } = await import("node:fs");
  const css = readFileSync(new URL("../src/v94.css", import.meta.url), "utf8");
  assert.match(css, /\.rx-wrap \{ position: relative;/);
  assert.match(css, /\.rx-wrap \.to-canvas \{[^}]*pointer-events: none/);
});

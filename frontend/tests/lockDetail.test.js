// V9.4.5: janelas de detalhe do bloqueio maiores e animadas
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { arcPoint, flipFrom, rangePos, sunProgress } from "../src/utils/lockDetail.js";

test("posição entre a mínima e a máxima", () => {
  assert.equal(rangePos(20, 16, 24), 0.5);
  assert.equal(rangePos(30, 16, 24), 1);
  assert.equal(rangePos(10, 16, 24), 0);
  assert.equal(rangePos(5, 5, 5), 0.5); // faixa vazia: meio
  assert.equal(rangePos("x", 1, 2), 0.5);
});

test("o sol no arco do dia", () => {
  const at = (h, m) => new Date(2026, 10, 24, h, m);
  assert.deepEqual(sunProgress(at(5, 15), "05:15", "18:15"), { frac: 0, up: true });
  assert.deepEqual(sunProgress(at(11, 45), "05:15", "18:15"), { frac: 0.5, up: true });
  assert.equal(sunProgress(at(22, 0), "05:15", "18:15").up, false);
  assert.equal(sunProgress(at(22, 0), "05:15", "18:15").frac, 1);
  assert.equal(sunProgress(at(12, 0), null, "18:00"), null);
  const mid = arcPoint(0.5);
  assert.equal(mid.x, 120);
  assert.ok(mid.y < arcPoint(0).y); // no meio do dia, o sol está no alto
});

test("a janela nasce do cartão tocado", () => {
  const origin = { left: 1400, top: 300, width: 300, height: 100 };
  const target = { left: 520, top: 200, width: 560, height: 500 };
  assert.equal(flipFrom(origin, target), "translate(750px, -100px) scale(0.536, 0.200)");
  assert.equal(flipFrom(null, target), null);
  assert.equal(flipFrom(origin, { ...target, width: 0 }), null);
});

test("sem desfoque de tela cheia e com as animações de trás paradas", () => {
  const css = readFileSync(new URL("../src/v94.css", import.meta.url), "utf8");
  assert.match(css, /\.ld-overlay \{[^}]*backdrop-filter: none/);
  assert.match(css, /html\.ld-open #root \* \{ animation-play-state: paused/);
  const jsx = readFileSync(new URL("../src/components/LockDetail.jsx", import.meta.url), "utf8");
  assert.match(jsx, /ld-card ld-k-\$\{kind\}/); // a classe da janela não colide com as do conteúdo
  const cards = readFileSync(new URL("../src/components/LockCards.jsx", import.meta.url), "utf8");
  assert.doesNotMatch(cards, /\.map\(clickable\)/); // o índice virava "cópia" e tirava o cartão do teclado
});

test("V9.5.1: 'abre o clima' no bloqueio abre a janela do cartão (evento do App para o LockCards)", () => {
  const app = readFileSync(new URL("../src/App.jsx", import.meta.url), "utf8");
  assert.match(app, /if \(msg\.open\) window\.dispatchEvent\(new CustomEvent\("jarvis-lock-open-card", \{ detail: msg\.open \}\)\)/);
  const cards = readFileSync(new URL("../src/components/LockCards.jsx", import.meta.url), "utf8");
  assert.match(cards, /addEventListener\("jarvis-lock-open-card"/);
  assert.match(cards, /data-card=\{el\.key\}/);
});

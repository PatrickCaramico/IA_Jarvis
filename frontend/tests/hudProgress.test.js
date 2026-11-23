import assert from "node:assert/strict";
import test from "node:test";

const { missionHint, missionPct, missionsTag, progressDelta } = await import("../src/utils/hudProgress.js");

test("V8.12.5: o que cada missão mostra embaixo do texto", () => {
  assert.equal(missionHint({ tipo: "uso", meta: 3, progresso: 1 }), "1/3");
  assert.equal(missionHint({ tipo: "uso", meta: 1 }), "completa sozinha quando você fizer");
  assert.equal(missionHint({ tipo: "sobre" }), "responda aqui");
  assert.equal(missionHint({ tipo: "sobre" }, { cloud: true }), "responda no PC");
  assert.equal(missionHint({ tipo: "bem" }), "toque em FEITO quando fizer");
  assert.equal(missionHint({ tipo: "bem", feita: true }), "concluída");
});

test("V8.12.5: porcentagem da missão", () => {
  assert.equal(missionPct({ meta: 4, progresso: 1 }), 25);
  assert.equal(missionPct({ meta: 2, progresso: 9 }), 100);
  assert.equal(missionPct({ feita: true, meta: 3, progresso: 0 }), 100);
  assert.equal(missionPct(null), 0);
});

test("V8.12.5: ganhou XP ou subiu de nível", () => {
  assert.equal(progressDelta(null, { xp: 10, nivel: 1 }), null); // primeira leitura não comemora
  assert.equal(progressDelta({ xp: 10, nivel: 1 }, { xp: 10, nivel: 1 }), null);
  assert.deepEqual(progressDelta({ xp: 10, nivel: 1 }, { xp: 25, nivel: 1 }), { xp: 15, levelUp: false, nivel: 1 });
  assert.deepEqual(progressDelta({ xp: 95, nivel: 1 }, { xp: 110, nivel: 2 }), { xp: 15, levelUp: true, nivel: 2 });
});

test("V8.12.5: etiqueta do painel", () => {
  assert.equal(missionsTag(null), "…");
  assert.equal(missionsTag({ feitas: 1, total: 3 }), "1/3 HOJE");
});

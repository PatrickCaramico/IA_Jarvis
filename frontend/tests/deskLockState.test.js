import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";

const { deskBubble, deskFace, haloTone, isNight } = await import("../src/utils/deskLockState.js");

test("V8.16: a expressão do avatar segue o estado de verdade", () => {
  assert.deepEqual(deskFace({ phase: "scanning" }), { expr: null, state: "processing" });
  assert.deepEqual(deskFace({ phase: "verified" }), { expr: "conseguiu", state: "idle" });
  assert.deepEqual(deskFace({ phase: "failed" }), { expr: "surpreso", state: "idle" });
  assert.deepEqual(deskFace({ listening: true }), { expr: null, state: "listening" });
  assert.deepEqual(deskFace({ jarvisState: "speaking", listening: true }), { expr: null, state: "speaking" });
  assert.deepEqual(deskFace({ hour: 2 }), { expr: "dormindo", state: "idle" });
  assert.deepEqual(deskFace({ hour: 2, listening: true }), { expr: null, state: "listening" }); // ouvindo acorda
  assert.deepEqual(deskFace({ mood: "bravo", phase: "verified" }), { expr: "bravo", state: "idle" }); // cutucada vence
  assert.deepEqual(deskFace({}), { expr: null, state: "idle" });
});

test("V8.16: anel de luz e noite", () => {
  assert.equal(haloTone({ phase: "verified" }), "ok");
  assert.equal(haloTone({ phase: "failed" }), "fail");
  assert.equal(haloTone({ phase: "scanning" }), "think");
  assert.equal(haloTone({ jarvisState: "speaking" }), "talk");
  assert.equal(haloTone({ listening: true }), "listen");
  assert.equal(haloTone({ hour: 3 }), "sleep");
  assert.equal(haloTone({ hour: 15 }), "calm");
  assert.equal(isNight(23), true);
  assert.equal(isNight(6), false);
});

test("V8.16: o balão: falha, entrada, legenda da Sentinela e ouvindo", () => {
  assert.equal(deskBubble({ phase: "failed", message: "Rosto não reconhecido." }), "Rosto não reconhecido.");
  assert.equal(deskBubble({ phase: "verified", name: "Patrick" }), "Bem-vindo de volta, Patrick! 💙");
  assert.match(deskBubble({ caption: "abrir central" }), /“abrir central”/);
  assert.match(deskBubble({ listening: true, wake: "Jarvis" }), /Diga "abrir central" ou "Jarvis, …"/);
  assert.match(deskBubble({ hour: 1 }), /Zzz/);
  assert.equal(deskBubble({ hour: 15 }), null); // as falas de sempre
  assert.equal(deskBubble({ hint: "Use o PIN", hintShown: true }), "Use o PIN");
});

test("V8.16: o bloqueio do robô recebe as mesmas funções do clássico e não tem mais Tamagotchi nem jogo", () => {
  const lock = fs.readFileSync(new URL("../src/components/LockScreen.jsx", import.meta.url), "utf8");
  const desk = lock.slice(lock.indexOf("  if (deskLock) {"), lock.indexOf("// ---------------------------------------------------------------- V7.12: estilo ORBE"));
  for (const k of ["mic={", "clapNode={", "stampNode={", "hubActions={secondaryActions}", "fanPanelNode={", "caption={", "listening={listening}", "styleToggle={styleToggle}"]) {
    assert.ok(desk.includes(k), k);
  }
  assert.ok(lock.includes("{onDeskLock && !deskLock && ("), "dentro do robô não aparece o botão de ir para o robô");
  const src = fs.readFileSync(new URL("../src/components/DeskLock.jsx", import.meta.url), "utf8");
  for (const k of ["pet.js", "useStarsGame", "useActivity", "ALIMENTAR", "JOGAR"]) assert.ok(!src.includes(k), `${k} saiu`);
  assert.ok(src.includes("⚙ GERENCIAR") && src.includes("lo-mic"));
  // V9.1.1: sem a faixa de cartões no bloqueio do robô
  assert.ok(!src.includes("<LockCards") && !desk.includes("cardsList={"), "faixa de cartões saiu do robô");
  assert.ok(!fs.existsSync(new URL("../src/utils/pet.js", import.meta.url)));
});

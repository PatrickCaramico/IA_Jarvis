// V8.11.1: centro da central renovado (node --test frontend/tests)
import { test } from "node:test";
import assert from "node:assert/strict";
import { SLOW_AFTER_S, diskText, elapsedText, micCaption, nextAgenda, stateHint } from "../src/utils/hudCenter.js";

test("tempo decorrido curto", () => {
  assert.equal(elapsedText(0), "0 s");
  assert.equal(elapsedText(4.7), "4 s");
  assert.equal(elapsedText(60), "1 min");
  assert.equal(elapsedText(75), "1 min 15 s");
  assert.equal(elapsedText(undefined), "0 s");
});

test("a linha de estado diz o que está acontecendo", () => {
  assert.deepEqual(stateHint({}), { text: "Toque no microfone ou aperte espaço para falar.", tone: "idle", cancel: false });
  assert.equal(stateHint({ micOk: false }).text, "Digite seu pedido no canal ao lado.");
  assert.equal(stateHint({ listening: true }).tone, "listen");
  assert.equal(stateHint({ listening: true, interim: "abre o spotify" }).text, "“abre o spotify”");
  assert.ok(stateHint({ listening: true, interim: "x".repeat(200) }).text.length < 80);
  const work = stateHint({ state: "processing", elapsed: 4 });
  assert.equal(work.text, "Pensando… 4 s");
  assert.equal(work.cancel, true);
  assert.equal(stateHint({ state: "processing", elapsed: 0 }).text, "Pensando…");
  const slow = stateHint({ state: "processing", elapsed: SLOW_AFTER_S });
  assert.equal(slow.tone, "slow");
  assert.match(slow.text, /cancelar/);
  assert.equal(stateHint({ state: "speaking" }).cancel, true);
  // ouvindo vence o estado (o microfone aberto é o que importa)
  assert.equal(stateHint({ state: "processing", listening: true }).tone, "listen");
});

test("legenda do microfone", () => {
  assert.equal(micCaption({}), "FALAR");
  assert.equal(micCaption({ listening: true }), "OUVINDO · TOQUE P/ ENVIAR");
  assert.equal(micCaption({ state: "processing" }), "AGUARDE");
  assert.equal(micCaption({ state: "speaking" }), "FALANDO");
});

test("próximo compromisso e disco", () => {
  assert.deepEqual(nextAgenda([{ label: "Hoje 21:00", title: "Ligar para a mãe" }]), { when: "Hoje 21:00", title: "Ligar para a mãe" });
  assert.equal(nextAgenda([]), null);
  assert.equal(nextAgenda(null), null);
  assert.equal(nextAgenda([{ title: "Uma reunião com um título bem comprido demais" }]).title.length, 28);
  assert.equal(nextAgenda([{ title: "Dentista" }]).when, "Em breve");
  assert.equal(diskText(412.6), "413 GB");
  assert.equal(diskText(1536), "1,5 TB");
  assert.equal(diskText(null), "—");
});

test("V9.1.2: diz com o que está ocupado", () => {
  assert.equal(stateHint({ state: "processing", elapsed: 3, doing: "pensando com a inteligência artificial" }).text,
    "Pensando com a inteligência artificial… 3 s");
  assert.equal(stateHint({ state: "processing", elapsed: 51, doing: "esperando o pedido anterior terminar" }).text,
    "Está demorando (51 s): esperando o pedido anterior terminar. Pode cancelar e pedir de novo.");
  assert.equal(stateHint({ state: "processing", elapsed: 51 }).text, "Está demorando (51 s). Pode cancelar e pedir de novo.");
  assert.equal(stateHint({ state: "processing", elapsed: 0 }).text, "Pensando…");
});

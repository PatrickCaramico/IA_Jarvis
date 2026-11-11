import { test } from "node:test";
import assert from "node:assert/strict";
import { effectiveWakeWords, stripWake } from "../src/utils/wakeWords.js";

const words = effectiveWakeWords(null, "J.A.R.V.I.S.");

test("tira a palavra de ativação e mantém acentos do pedido", () => {
  assert.equal(stripWake("Jarvis, que horas são?", words), "que horas são?");
  assert.equal(stripWake("Ei Jarvis quem ganhou o jogo do Palmeiras?", words), "quem ganhou o jogo do Palmeiras?");
  assert.equal(stripWake("jarvis... previsão do tempo", words), "previsão do tempo");
});

test("só a palavra de ativação vira pedido vazio; sem ela, o texto volta igual", () => {
  assert.equal(stripWake("Jarvis", words), "");
  assert.equal(stripWake("que horas são", words), "que horas são");
});

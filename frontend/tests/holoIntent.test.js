// V7.1: HOLOGRAMA (node --test frontend/tests)
import { test } from "node:test";
import assert from "node:assert/strict";
import { holoCommand, holoIntent, speechSeconds, stepTimerText } from "../src/utils/holoIntent.js";

test("receitas e explicações viram holograma; o resto segue o caminho normal", () => {
  assert.equal(holoIntent("Jarvis, receita de bolo de cenoura").kind, "receita");
  assert.equal(holoIntent("como fazer um brigadeiro de panela").kind, "receita");
  assert.equal(holoIntent("me explica como funciona um buraco negro").kind, "apresentacao");
  assert.equal(holoIntent("pesquisa sobre a história do Egito").kind, "apresentacao");
  assert.equal(holoIntent("como funcionam as vacinas de RNA").kind, "apresentacao");
  assert.equal(holoIntent("procura receita de pão no youtube"), null);
  assert.equal(holoIntent("como fazer backup do celular"), null);
  assert.equal(holoIntent("que horas são"), null);
  assert.equal(holoIntent("me explica"), null);
  assert.equal(holoIntent("me fala sobre minha agenda de amanhã"), null);
  assert.equal(holoIntent("como funciona o timer do jarvis"), null);
});

test("modo cozinha por voz", () => {
  assert.equal(holoCommand("próximo passo"), "next");
  assert.equal(holoCommand("volta um passo"), "prev");
  assert.equal(holoCommand("repete por favor"), "repeat");
  assert.equal(holoCommand("pausa"), "pause");
  assert.equal(holoCommand("continua"), "play");
  assert.equal(holoCommand("fecha o holograma"), "close");
  assert.equal(holoCommand("qual a temperatura"), null);
});

test("tempo de fala e timer do passo", () => {
  assert.equal(speechSeconds(""), 3);
  assert.ok(speechSeconds("um dois três quatro cinco seis sete oito nove dez onze doze") > 4);
  assert.equal(stepTimerText(40, "o bolo"), "timer de 40 minutos para o bolo");
  assert.equal(stepTimerText(90, ""), "timer de 1 hora e 30 minutos");
  assert.equal(stepTimerText(0, "x"), "");
});

test("V7.14: perguntas no meio, quiz por voz, salvos e cartão rápido", async () => {
  const { holoQuestion, quizLetter, savedHoloIntent, quickQuestion } = await import("../src/utils/holoIntent.js");
  assert.equal(holoQuestion("espera, o que é horizonte de eventos?"), true);
  assert.equal(holoQuestion("qual a temperatura do sol"), true);
  assert.equal(holoQuestion("legal"), false);
  assert.equal(quizLetter("letra b"), 1);
  assert.equal(quizLetter("é a c"), 2);
  assert.equal(quizLetter("alternativa d"), 3);
  assert.equal(quizLetter("a"), 0);
  assert.equal(quizLetter("acho que a lua"), -1);
  assert.equal(savedHoloIntent("abre os hologramas salvos"), true);
  assert.equal(savedHoloIntent("minhas apresentações salvas"), true);
  assert.equal(quickQuestion("quanto está o dólar hoje?"), true);
  assert.equal(quickQuestion("quem ganhou o jogo do palmeiras"), true);
  assert.equal(quickQuestion("toca uma música"), false);
});

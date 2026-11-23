import assert from "node:assert/strict";
import test from "node:test";

const { quickReply, spokenTime, timeGreeting } = await import("../src/utils/quickReply.js");

const first = () => 0; // sorteio fixo: sempre a primeira opção
// 23/11/2026 15:07 em Brasília (18:07 UTC), segunda-feira
const NOW = new Date("2026-11-23T18:07:00Z");
const opts = { name: "Patrick", now: NOW, random: first };

test("V8.12.4: cumprimentos respondem na hora, sem IA", () => {
  assert.equal(quickReply("olá", opts), "Olá, Patrick! Em que posso ajudar?");
  assert.equal(quickReply("Oi Jarvis!", opts), "Olá, Patrick! Em que posso ajudar?");
  assert.equal(quickReply("e aí, tudo bem?", opts), "Olá, Patrick! Tudo bem por aqui, obrigado por perguntar. Em que posso ajudar?");
  assert.equal(quickReply("boa tarde jarvis", opts), "Boa tarde, Patrick! Em que posso ajudar?");
  assert.equal(quickReply("olá", { ...opts, name: "" }), "Olá! Em que posso ajudar?");
});

test("V8.12.4: obrigado, tchau, hora e data", () => {
  assert.equal(quickReply("valeu jarvis", opts), "Disponha, Patrick.");
  assert.equal(quickReply("muito obrigado", opts), "Disponha, Patrick.");
  assert.match(quickReply("tchau", opts), /^Até logo, Patrick\./);
  assert.equal(quickReply("que horas são?", opts), "São 15 horas e 7 minutos.");
  assert.equal(quickReply("que dia é hoje", opts), "Hoje é segunda-feira, 23 de novembro de 2026.");
});

test("V8.12.4: pedidos de verdade continuam indo para a IA", () => {
  for (const phrase of ["oi, coloca leite na lista", "bom dia", "obrigado, agora me lembra de ligar pro João",
    "olá, qual a previsão do tempo amanhã?", "quantas horas tem um dia em marte e por que é diferente", "", "ei você viu as notícias"]) {
    assert.equal(quickReply(phrase, opts), null, phrase);
  }
});

test("V8.12.4: hora falada e saudação pelo horário", () => {
  assert.equal(spokenTime({ hour: 0, minute: 0 }), "É meia-noite.");
  assert.equal(spokenTime({ hour: 12, minute: 1 }), "É meio-dia e 1 minuto.");
  assert.equal(spokenTime({ hour: 1, minute: 0 }), "É uma hora em ponto.");
  assert.equal(timeGreeting(8), "Bom dia");
  assert.equal(timeGreeting(13), "Boa tarde");
  assert.equal(timeGreeting(2), "Boa noite");
});

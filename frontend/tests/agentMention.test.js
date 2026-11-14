// V7.9: @agente no campo de conversa e por voz (node --test frontend/tests)
import { test } from "node:test";
import assert from "node:assert/strict";
import { agentSuggestions, parseAgentMention } from "../src/utils/agentMention.js";

test("@nome no campo de conversa", () => {
  assert.deepEqual(parseAgentMention("@mercado monta a lista do churrasco"), { agent: "mercado", message: "monta a lista do churrasco", info: parseAgentMention("@mercado x").info });
  assert.equal(parseAgentMention("@finanças, quanto gastei?").agent, "financas");
  assert.equal(parseAgentMention("@xyz oi"), null);
  assert.equal(parseAgentMention("qual a previsão do tempo?"), null);
});

test("por voz", () => {
  assert.equal(parseAgentMention("Jarvis, agente mercado, monta a lista da semana").agent, "mercado");
  assert.equal(parseAgentMention("pergunta pro agente de finanças quanto gastei no mês").message, "quanto gastei no mês");
  assert.equal(parseAgentMention("fala com o professor: me explica frações").agent, "professor");
  assert.equal(parseAgentMention("pede pro secretário marcar dentista sexta às 10").agent, "secretario");
  assert.equal(parseAgentMention("fala com o João que vou atrasar"), null); // João não é agente
});

test("lista do @", () => {
  assert.equal(agentSuggestions("@").length, 6);
  assert.deepEqual(agentSuggestions("@me").map((a) => a.id), ["mercado"]);
  assert.deepEqual(agentSuggestions("@mercado oi"), []);
});

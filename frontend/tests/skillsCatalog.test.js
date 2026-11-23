// V8.11: catálogo das Skills na Central de Agentes (node --test frontend/tests)
import { test } from "node:test";
import assert from "node:assert/strict";
import { groupKey, groupSkills, statsText, summary, titleOf } from "../src/utils/skillsCatalog.js";

const items = [
  { name: "organizar_janelas", title: "organizar as janelas", module: "skills.workspace", description: "Organiza as janelas.", examples: ["organiza as janelas"], enabled: true, permission: "action" },
  { name: "fechar_programa", title: "fechar o programa", module: "skills.system_guard", description: "Fecha um programa.", examples: ["fecha o Discord"], enabled: false, permission: "critical" },
  { name: "nova", title: "algo novo", module: "skills.minha_skill_nova", description: "Teste.", enabled: true },
];

test("grupos na ordem e grupo desconhecido com nome legível", () => {
  const groups = groupSkills(items);
  assert.deepEqual(groups.map((g) => g.label), ["Janelas e monitores", "O PC", "Minha skill nova"]);
  assert.equal(groupKey("skills.workspace"), "workspace");
  assert.equal(groupKey("tests.algo"), "algo");
});

test("busca sem acento e por exemplo", () => {
  assert.deepEqual(groupSkills(items, "discord").map((g) => g.key), ["system_guard"]);
  assert.deepEqual(groupSkills(items, "JANELAS organiza").map((g) => g.key), ["workspace"]);
  assert.equal(groupSkills(items, "nada disso").length, 0);
});

test("textos", () => {
  assert.equal(titleOf(items[1]), "Fechar o programa");
  assert.equal(titleOf({ name: "o_modo_reuniao", title: "o modo reunião" }), "Modo reunião");
  assert.equal(statsText({}), "ainda não usada nesta sessão");
  assert.equal(statsText({ calls: 3, failures: 1, last_ms: 140, paused_s: 290 }), "3 usos · 1 falha · ~140 ms · em pausa por 5 min");
  assert.equal(statsText({ calls: 1, last_ms: 34000 }), "1 uso · ~34 s");
  assert.equal(summary(items), "2 de 3 ligadas");
});

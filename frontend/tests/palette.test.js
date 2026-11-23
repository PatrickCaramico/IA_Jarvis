import test from "node:test";
import assert from "node:assert/strict";
import { memoryItems, move, rank, score, skillItems } from "../src/utils/palette.js";

const actions = [
  { id: "settings", kind: "acao", icon: "⚙️", label: "Abrir configurações", keywords: "preferencias ajustes", run: { type: "action", id: "settings" } },
  { id: "desk", kind: "acao", icon: "🖥️", label: "Modo Desk", keywords: "mesa trabalho", run: { type: "action", id: "desk" } },
];
const skills = skillItems([
  { name: "workspace_layout", title: "organizar janelas", examples: ["organiza as janelas lado a lado"], enabled: true },
  { name: "off", title: "desligada", examples: ["não aparece"], enabled: false },
]);

test("skills viram frases; desligadas ficam de fora", () => {
  assert.deepEqual(skills.map((s) => s.label), ["organiza as janelas lado a lado"]);
  assert.deepEqual(skills[0].run, { type: "send", text: "organiza as janelas lado a lado" });
});

test("busca sem acento, palavras em qualquer ordem, ações primeiro", () => {
  const all = [...actions, ...skills];
  assert.equal(rank(all, "configuracoes")[0].id, "settings");
  assert.equal(rank(all, "janelas lado")[0].label, "organiza as janelas lado a lado");
  assert.equal(score(actions[1], "ajustes"), 0);
  assert.ok(score(actions[0], "ajustes") > 0);
  assert.deepEqual(rank(all, "").map((i) => i.id), ["settings", "desk"]);
});

test("texto livre vira pergunta para o JARVIS, logo depois do melhor resultado", () => {
  const out = rank([...actions, ...skills], "qual a cotação do dólar");
  assert.equal(out[0].kind, "perguntar");
  assert.deepEqual(out[0].run, { type: "send", text: "qual a cotação do dólar" });
  const withHit = rank([...actions, ...skills], "desk");
  assert.equal(withHit[0].id, "desk");
  assert.equal(withHit[1].kind, "perguntar");
});

test("memória e copiados: Enter copia o trecho limpo", () => {
  const mem = memoryItems([
    { kind: "conversa", label: "Conversa", snippet: "a senha do [wifi] é  na geladeira", at: "2026-11-20T10:00:00" },
    { kind: "copiado", label: "Copiado", title: "Rua das Acácias, 123", snippet: "[Rua] das Acácias, 123" },
  ]);
  assert.equal(mem[0].label, "a senha do wifi é na geladeira");
  assert.match(mem[0].hint, /Conversa · 2026-11-20/);
  assert.deepEqual(mem[1].run, { type: "copy", text: "Rua das Acácias, 123" });
  const out = rank(actions, "rua", mem);
  assert.ok(out.some((i) => i.kind === "copiado"));
});

test("setas dão a volta", () => {
  assert.equal(move(0, -1, 3), 2);
  assert.equal(move(2, 1, 3), 0);
  assert.equal(move(0, 1, 0), 0);
});

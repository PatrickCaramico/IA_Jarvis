// V8.12.2: tela de atualização (node --test frontend/tests)
import { test } from "node:test";
import assert from "node:assert/strict";
import { footText, versionLine, whatsNew } from "../src/utils/updateScreen.js";

test("de qual versão para qual", () => {
  assert.deepEqual(versionLine("8.12.1", { versao: "8.12.2", depois: "3c39a40aa" }), { from: "8.12.1", to: "8.12.2", code: "", same: false });
  // sem o número novo (PC antigo): o código do commit, curto
  assert.equal(versionLine("8.12.1", { depois: "3c39a40aa" }).code, "3c39a40");
  assert.equal(versionLine("8.12.1", { changed: false }).same, true);
});

test("o que há de novo", () => {
  assert.deepEqual(whatsNew({ destaques: ["⟳ Botão ATUALIZAR"], notas: ["JARVIS 8.12.1: x"] }), ["⟳ Botão ATUALIZAR"]);
  assert.deepEqual(whatsNew({ notas: ["JARVIS 8.12.1: botão novo", ""] }), ["botão novo"]);
  assert.deepEqual(whatsNew({}), []);
});

test("o fim não fala em verificação do rosto", () => {
  assert.doesNotMatch(footText(10), /rosto/);
  assert.match(footText(10), /abre sozinha/);
  assert.match(footText(200), /Iniciar-JARVIS\.bat/);
  assert.equal(footText(10, true), "");
});

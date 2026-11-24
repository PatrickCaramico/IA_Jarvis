// V9.4.5: transcrição ao vivo (a conversa abre numa janela de vidro quando o JARVIS fala)
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { CLOSE_AFTER_MS, EXIT_MS, peekEnabled, recentMessages, setPeekEnabled, wantsPeek } from "../src/utils/chatPeek.js";

function memory() {
  const data = {};
  return { getItem: (k) => data[k] ?? null, setItem: (k, v) => { data[k] = String(v); }, removeItem: (k) => { delete data[k]; } };
}

test("abre quando ele fala, escreve ou ouve; nunca na Área Limpa nem no briefing", () => {
  assert.equal(wantsPeek({ speaking: true }), true);
  assert.equal(wantsPeek({ streaming: true }), true);
  assert.equal(wantsPeek({ listening: true }), true);
  assert.equal(wantsPeek({}), false);
  assert.equal(wantsPeek({ speaking: true, zen: true }), false);
  assert.equal(wantsPeek({ speaking: true, briefing: true }), false);
  assert.equal(wantsPeek({ speaking: true, enabled: false }), false);
});

test("liga e desliga neste aparelho (padrão: ligada)", () => {
  const st = memory();
  assert.equal(peekEnabled(st), true);
  assert.equal(setPeekEnabled(false, st), false);
  assert.equal(peekEnabled(st), false);
  setPeekEnabled(true, st);
  assert.equal(peekEnabled(st), true);
});

test("mostra só as últimas falas, sem divisórias nem conversa antiga", () => {
  const log = [
    { id: "0", role: "jarvis", text: "de ontem", old: true },
    { id: "d", role: "divider", text: "CONVERSAS ANTERIORES ▲" },
    { id: "1", role: "user", text: "a" }, { id: "2", role: "jarvis", text: "b" },
    { id: "3", role: "user", text: "c" }, { id: "4", role: "jarvis", text: "d" },
    { id: "5", role: "user", text: "e" }, { id: "6", role: "jarvis", text: "" },
  ];
  assert.deepEqual(recentMessages(log).map((m) => m.id), ["2", "3", "4", "5"]);
  assert.deepEqual(recentMessages(null), []);
});

test("a saída do CSS dura o mesmo que o componente espera, e a janela é de vidro", () => {
  const css = readFileSync(new URL("../src/v94.css", import.meta.url), "utf8");
  assert.match(css, new RegExp(`\\.cpk\\.cpk-out \\{ animation: cpk-out ${EXIT_MS}ms`));
  assert.match(css, /\.cpk \{[^}]*background: var\(--g-shine\)/); // vidro pintado (sem desfoque ao vivo na central)
  assert.ok(CLOSE_AFTER_MS >= 4000 && CLOSE_AFTER_MS <= 15000);
});

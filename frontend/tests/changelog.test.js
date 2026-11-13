// V7.3: notas da versão (node --test frontend/tests)
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { inlineParts, matches, parseChangelog } from "../src/utils/changelog.js";

const MD = `# Changelog

Intro.

## 7.2.0 — 13 de novembro de 2026

- **JARVIS mais rápido**:
  - a voz começa na hora;
  - o microfone envia em ~1 s.
- Botão \`OTIMIZAR\`
  continua aqui.

## 4.0

### Tela de bloqueio
- Novo visual.
`;

test("separa versões, itens, subitens, grupos e continuação", () => {
  const v = parseChangelog(MD);
  assert.deepEqual(v.map((x) => [x.version, x.date]), [["7.2.0", "13 de novembro de 2026"], ["4.0", ""]]);
  assert.equal(v[0].items.length, 2);
  assert.deepEqual(v[0].items[0].sub, ["a voz começa na hora;", "o microfone envia em ~1 s."]);
  assert.equal(v[0].items[1].text, "Botão `OTIMIZAR` continua aqui.");
  assert.equal(v[1].items[0].heading, true);
});

test("negrito, código e busca", () => {
  assert.deepEqual(inlineParts("a **b** `c`"), [{ t: "text", v: "a " }, { t: "bold", v: "b" }, { t: "text", v: " " }, { t: "code", v: "c" }]);
  const [v72, v40] = parseChangelog(MD);
  assert.ok(matches(v72, "microfone rapido"));
  assert.ok(!matches(v40, "microfone"));
  assert.ok(matches(v40, ""));
});

test("o CHANGELOG real tem a versão atual do JARVIS no topo", () => {
  const md = readFileSync(fileURLToPath(new URL("../../CHANGELOG.md", import.meta.url)), "utf8");
  const ver = readFileSync(fileURLToPath(new URL("../src/utils/version.js", import.meta.url)), "utf8").match(/APP_VERSION = "([^"]+)"/)[1];
  const list = parseChangelog(md);
  assert.equal(list[0].version, ver);
  assert.ok(list.length > 50 && list.every((x) => x.items.length > 0));
});

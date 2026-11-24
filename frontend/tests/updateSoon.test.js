// V9.4.1: aviso da atualização automática (contagem)
import { test } from "node:test";
import assert from "node:assert/strict";
import { soonText } from "../src/utils/updateSoon.js";

test("contagem do aviso", () => {
  assert.equal(soonText(120_000, 0), "Atualizo sozinho em 2 min 00 s");
  assert.equal(soonText(95_000, 0), "Atualizo sozinho em 1 min 35 s");
  assert.equal(soonText(9_000, 0), "Atualizo sozinho em 9 s");
  assert.equal(soonText(0, 5_000), "Atualizando assim que o JARVIS ficar livre…");
});

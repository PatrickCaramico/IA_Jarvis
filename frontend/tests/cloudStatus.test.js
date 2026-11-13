import assert from "node:assert/strict";
import test from "node:test";
import { pcLine } from "../src/utils/cloudStatus.js";

test("status do acesso pela nuvem: notebook ligado (fora de casa) x desligado", () => {
  assert.equal(pcLine({ agora: "2026-11-13 15:11", sincronizado_em: "2026-11-13 15:09" }), "notebook ligado em casa · listas sincronizadas");
  assert.equal(pcLine({ agora: "2026-11-13 18:00", sincronizado_em: "2026-11-13 15:09" }), "notebook desligado · visto 13/11 15:09");
  assert.equal(pcLine({ agora: "2026-11-14 00:01", sincronizado_em: "2026-11-13 23:59" }), "notebook ligado em casa · listas sincronizadas");
  assert.equal(pcLine({ agora: "2026-11-13 15:11" }), "notebook ainda não sincronizou");
});

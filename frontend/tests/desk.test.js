import { test } from "node:test";
import assert from "node:assert/strict";
import { FUNCTIONS, greeting, hexToRgb, isLight, mapLayout, stateText } from "../src/utils/desk.js";

test("V8.0: Modo Desk: saudação, estado e cores", () => {
  assert.equal(greeting(new Date(2026, 10, 15, 8)), "Bom dia");
  assert.equal(greeting(new Date(2026, 10, 15, 14)), "Boa tarde");
  assert.equal(greeting(new Date(2026, 10, 15, 21)), "Boa noite");
  assert.equal(stateText("listening"), "Ouvindo");
  assert.equal(stateText("idle"), "Pronto");
  assert.equal(hexToRgb("#a3e635"), "163, 230, 53");
  assert.equal(hexToRgb("lixo"), "34, 211, 238");
  assert.equal(isLight("#a3e635"), true);
  assert.equal(isLight("#1f2937"), false);
  assert.ok(FUNCTIONS.length >= 10 && FUNCTIONS.every((f) => f.exemplos.length));
});

test("V8.0: mapa da memória: centro, assuntos em volta e memórias perto do assunto", () => {
  const map = {
    nos: [{ id: "eu", tipo: "centro" }, { id: "g:A", tipo: "assunto" }, { id: "g:B", tipo: "assunto" }, { id: "m:A:0", tipo: "memoria" }, { id: "m:A:1", tipo: "memoria" }],
    ligacoes: [{ de: "eu", para: "g:A" }, { de: "eu", para: "g:B" }, { de: "g:A", para: "m:A:0" }, { de: "g:A", para: "m:A:1" }],
  };
  const pos = mapLayout(map, 800, 560);
  assert.deepEqual(pos.eu, { x: 400, y: 280 });
  const d = (a, b) => Math.hypot(pos[a].x - pos[b].x, pos[a].y - pos[b].y);
  assert.ok(Math.abs(d("eu", "g:A") - d("eu", "g:B")) < 1);
  assert.ok(d("g:A", "m:A:0") < d("g:B", "m:A:0"));
  for (const p of Object.values(pos)) assert.ok(p.x >= 0 && p.x <= 800 && p.y >= 0 && p.y <= 560);
});

test("V8.1: guarda-roupa: tema da data por cima e avatar do 8.0 migrado", async () => {
  const { DEFAULT_AVATAR, WARDROBE, withTheme } = await import("../src/utils/desk.js");
  assert.deepEqual(WARDROBE.map(([slot]) => slot), ["chapeu", "rosto", "roupa", "olhos_forma", "efeito"]);
  assert.ok(WARDROBE.every(([slot, , items]) => items.some(([id]) => id === DEFAULT_AVATAR[slot])));
  assert.equal(withTheme({ acessorio: "coroa" }).chapeu, "coroa");
  const natal = { nome: "Natal", chapeu: "gorro", efeito: "neve" };
  const a = withTheme({ chapeu: "cartola", roupa: "capa" }, natal);
  assert.equal(a.chapeu, "gorro");
  assert.equal(a.efeito, "neve");
  assert.equal(a.roupa, "capa");
  assert.equal(withTheme({ chapeu: "cartola", temas: false }, natal).chapeu, "cartola");
});

test("V8.1.2: ilha: clicar abre o cartão (vence a resposta); sem nada fica a pílula", async () => {
  const src = await import("node:fs").then((fs) => fs.readFileSync(new URL("../src/components/IslandApp.jsx", import.meta.url), "utf8"));
  const fn = src.match(/export function islandMode\(card, reply\) \{([\s\S]*?)\n\}/);
  const islandMode = new Function("card", "reply", fn[1]);
  assert.equal(islandMode(true, true), "cartao");
  assert.equal(islandMode(false, true), "resposta");
  assert.equal(islandMode(false, false), "mini");
});

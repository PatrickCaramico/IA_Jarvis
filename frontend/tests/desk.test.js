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

test("V8.1.3: ilha: o toque avisado pelo app clica no botão e o clique real logo depois é ignorado", async () => {
  const src = await import("node:fs").then((fs) => fs.readFileSync(new URL("../src/components/IslandApp.jsx", import.meta.url), "utf8"));
  const body = src.match(/export function installIslandPress\(win = window, doc = document\) \{([\s\S]*?)\n\}/)[1];
  const install = new Function("win", "doc", "DEDUPE_MS", body);
  let clicks = 0;
  let captured = null;
  const btn = { click: () => clicks++, closest: () => btn };
  const doc = { elementFromPoint: () => btn, addEventListener: (_t, fn) => { captured = fn; }, removeEventListener() {} };
  const win = {};
  const off = install(win, doc, 800);
  win.__jarvisIslandPress(10, 10);
  assert.equal(clicks, 1);
  let stopped = false;
  captured({ isTrusted: true, stopPropagation: () => { stopped = true; }, preventDefault() {} });
  assert.equal(stopped, true);
  off();
  assert.equal(win.__jarvisIslandPress, undefined);
});

test("V8.1.7: tela de atualização: etapas na ordem certa", async () => {
  const src = (await import("node:fs")).readFileSync(new URL("../src/components/UpdateSteps.jsx", import.meta.url), "utf8");
  const order = new Function(`${src.match(/const ORDER = [^;]+;/)[0]} return ORDER;`)();
  const body = src.match(/export function stepState\(index, etapa\) \{([\s\S]*?)\n\}/)[1];
  const stepState = new Function("index", "etapa", "ORDER", body.replace(/ORDER/g, "ORDER"));
  const st = (i, e) => stepState(i, e, order);
  assert.deepEqual([0, 1, 2, 3].map((i) => st(i, "baixado")), ["done", "now", "next", "next"]);
  assert.deepEqual([0, 1, 2, 3].map((i) => st(i, "reiniciando")), ["done", "done", "now", "next"]);
  assert.deepEqual([0, 1, 2, 3].map((i) => st(i, "pronto")), ["done", "done", "done", "done"]);
});

test("V8.2: olhos seguem o mouse e acessórios novos", async () => {
  const { lookAt, WARDROBE, ANTENNA_HATS, DEFAULT_AVATAR } = await import("../src/utils/desk.js");
  const rect = { left: 0, top: 0, width: 100, height: 100 };
  assert.deepEqual(lookAt(50, 50, rect), { x: 0, y: 0 });
  const right = lookAt(5000, 50, rect);
  assert.equal(right.x, 1);
  assert.ok(lookAt(200, 50, rect).x > 0 && lookAt(200, 50, rect).x < 1);
  assert.deepEqual(lookAt(10, 10, null), { x: 0, y: 0 });
  const hats = WARDROBE.find(([s]) => s === "chapeu")[2].map(([id]) => id);
  for (const h of ["aureola", "chifrinhos", "festa", "flor", "bone_time"]) assert.ok(hats.includes(h), h);
  assert.ok(!ANTENNA_HATS.includes("aureola") && ANTENNA_HATS.includes("nenhum"));
  assert.equal(DEFAULT_AVATAR.olhos_seguem, true);
});

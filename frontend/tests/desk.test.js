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

test("V8.3.0: ilha: clicar abre o painel de menus (vence a resposta); sem nada fica a pílula", async () => {
  const src = await import("node:fs").then((fs) => fs.readFileSync(new URL("../src/components/IslandApp.jsx", import.meta.url), "utf8"));
  const fn = src.match(/export function islandMode\(open, reply\) \{([\s\S]*?)\n\}/);
  const islandMode = new Function("open", "reply", fn[1]);
  assert.equal(islandMode(true, true), "painel");
  assert.equal(islandMode(false, true), "resposta");
  assert.equal(islandMode(false, false), "mini");
});

test("V8.3.0: ilha: o toque do app num campo de texto só dá o foco (não clica)", async () => {
  const src = await import("node:fs").then((fs) => fs.readFileSync(new URL("../src/components/IslandApp.jsx", import.meta.url), "utf8"));
  const body = src.match(/export function installIslandPress\(win = window, doc = document\) \{([\s\S]*?)\n\}/)[1];
  const install = new Function("win", "doc", "DEDUPE_MS", body);
  let focused = 0;
  let clicked = 0;
  const input = { tagName: "INPUT", focus: () => focused++, click: () => clicked++, closest: () => null };
  const win = {};
  install(win, { elementFromPoint: () => input, addEventListener() {}, removeEventListener() {} }, 800);
  win.__jarvisIslandPress(10, 10);
  assert.equal(focused, 1);
  assert.equal(clicked, 0);
});

test("V8.4.1: ilha: o botão desceu -> o clique real espera; arrastou -> nada é clicado", async () => {
  const src = await import("node:fs").then((fs) => fs.readFileSync(new URL("../src/components/IslandApp.jsx", import.meta.url), "utf8"));
  const body = src.match(/export function installIslandPress\(win = window, doc = document\) \{([\s\S]*?)\n\}/)[1];
  const install = new Function("win", "doc", "DEDUPE_MS", body);
  let clicks = 0;
  let swallow = null;
  const btn = { tagName: "BUTTON", click: () => clicks++, closest: () => btn };
  const win = {};
  install(win, { elementFromPoint: () => btn, addEventListener: (_t, fn) => { swallow = fn; }, removeEventListener() {} }, 800);
  const real = () => { let stopped = false; swallow({ isTrusted: true, stopPropagation() { stopped = true; }, preventDefault() {} }); return stopped; };
  win.__jarvisIslandDown();
  assert.equal(real(), true); // segurando: o clique real não passa
  win.__jarvisIslandDragged(); // arrastou: não clica em nada
  assert.equal(clicks, 0);
  assert.equal(real(), true);
  win.__jarvisIslandPress(5, 5); // soltou sem arrastar: clica
  assert.equal(clicks, 1);
  const app = src.includes("<DeskApp") && src.includes("embedded") && src.includes("island_center");
  assert.ok(app, "o painel é o Modo Desk inteiro, com a barra de arrastar");
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

test("V8.3.1: interface nova: acha o bundle no index.html", async () => {
  const { bundleName } = await import("../src/utils/newBuild.js");
  assert.equal(bundleName('<script type="module" crossorigin src="/assets/index-AbC_12-x.js"></script>'), "/assets/index-AbC_12-x.js");
  assert.equal(bundleName("<html></html>"), "");
});

test("V8.4.0: modo leve: automático só liga no notebook na bateria", async () => {
  const src = await import("node:fs").then((fs) => fs.readFileSync(new URL("../src/utils/lite.js", import.meta.url), "utf8"));
  const liteFrom = new Function("setting", "battery", src.match(/export function liteFrom\(setting, battery\) \{([\s\S]*?)\n\}/)[1]);
  assert.equal(liteFrom("sim", null), true);
  assert.equal(liteFrom("nao", { charging: false }), false);
  assert.equal(liteFrom("auto", null), false); // PC de mesa
  assert.equal(liteFrom("auto", { charging: true }), false);
  assert.equal(liteFrom("auto", { charging: false }), true);
});

test("V8.4.0: voz pela Groq: volume e quando parar de gravar", async () => {
  const src = await import("node:fs").then((fs) => fs.readFileSync(new URL("../src/utils/voiceRecord.js", import.meta.url), "utf8"));
  const rmsLevel = new Function("bytes", src.match(/export function rmsLevel\(bytes\) \{([\s\S]*?)\n\}/)[1]);
  assert.equal(rmsLevel(new Uint8Array([128, 128, 128])), 0);
  assert.ok(rmsLevel(new Uint8Array([0, 255, 0, 255])) > 0.9);
  const body = src.match(/export function recordStep\(\{ now, start, lastLoud, spoke, maxMs = 15000, silenceMs = 1300, waitMs = 6000 \}\) \{([\s\S]*?)\n\}/)[1];
  const step = (o) => new Function("o", `const { now, start, lastLoud, spoke, maxMs = 15000, silenceMs = 1300, waitMs = 6000 } = o;${body}`)(o);
  assert.equal(step({ now: 1000, start: 0, lastLoud: 0, spoke: false }), "seguir");
  assert.equal(step({ now: 7000, start: 0, lastLoud: 0, spoke: false }), "nada"); // não falou nada
  assert.equal(step({ now: 3000, start: 0, lastLoud: 2500, spoke: true }), "seguir"); // pausa curta
  assert.equal(step({ now: 4000, start: 0, lastLoud: 2500, spoke: true }), "fim"); // falou e calou
  assert.equal(step({ now: 15000, start: 0, lastLoud: 14900, spoke: true }), "fim"); // tempo máximo
});

test("V8.4.0: brincadeiras: nada antes de 1min30, sorteio depois e cochilo com muito tempo parado", async () => {
  const src = await import("node:fs").then((fs) => fs.readFileSync(new URL("../src/components/RoboAvatar.jsx", import.meta.url), "utf8"));
  const consts = src.match(/export const FUN_AFTER_MS[\s\S]*?export const ANTICS = \[[^\]]*\];/)[0].replace(/export /g, "");
  const body = src.match(/export function pickAntic\(idleMs, rnd = Math.random\(\)\) \{([\s\S]*?)\n\}/)[1];
  const pick = new Function("idleMs", "rnd", `${consts}${body}`);
  assert.equal(pick(10_000, 0.9), null); // V8.6.0: começa aos 25 s parado
  assert.equal(pick(120_000, 0.1), null); // às vezes não faz nada
  for (const r of [0.4, 0.55, 0.7, 0.85, 0.999]) assert.ok(["olhar", "piscando", "bocejo", "pulinho", "feliz"].includes(pick(120_000, r)));
  assert.equal(pick(7 * 60_000, 0.5) === "dormindo", false);
  assert.equal(pick(9 * 60_000, 0.1), "dormindo");
  assert.ok(src.includes('case "bocejo"') && src.includes("ra-noblink") && src.includes('case "comendo"') && src.includes("ra-alive"));
});

test("V8.4.0: voz: o limite de fala se ajusta ao ruído do ambiente", async () => {
  const src = await import("node:fs").then((fs) => fs.readFileSync(new URL("../src/utils/voiceRecord.js", import.meta.url), "utf8"));
  const min = Number(src.match(/const MIN_SPEECH_LEVEL = ([\d.]+);/)[1]);
  const th = new Function("floor", "MIN_SPEECH_LEVEL", src.match(/export function speechThreshold\(floor\) \{([\s\S]*?)\n\}/)[1]);
  assert.equal(th(0, min), min); // sala silenciosa: um microfone baixinho (0,02) já conta
  assert.ok(0.02 > th(0, min));
  assert.ok(Math.abs(th(0.03, min) - 0.09) < 1e-9); // sala barulhenta: precisa falar mais alto que o ruído
});

test("V8.6.0: cutucadas: surpreso, bravo e, na 5ª, o modo Pac-Man", async () => {
  const src = await import("node:fs").then((fs) => fs.readFileSync(new URL("../src/utils/poke.js", import.meta.url), "utf8"));
  const max = Number(src.match(/export const POKES_TO_ANGRY = (\d+);/)[1]);
  const mood = new Function("count", "POKES_TO_ANGRY", src.match(/export function pokeMood\(count\) \{([\s\S]*?)\n\}/)[1]);
  assert.equal(mood(0, max), null);
  assert.equal(mood(1, max), "surpreso");
  assert.equal(mood(3, max), "bravo");
  assert.equal(mood(5, max), "comendo");
  const main = await import("node:fs").then((fs) => fs.readFileSync(new URL("../src/main.jsx", import.meta.url), "utf8"));
  assert.ok(main.includes('get("pacman") === "1"') && main.includes("PacmanApp"));
});

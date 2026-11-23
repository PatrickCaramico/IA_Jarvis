import assert from "node:assert/strict";
import test from "node:test";

const { HOLO_SPEEDS, holoFileName, holoText, mergePartial, newReqId, nextSpeed, speedLabel } = await import("../src/utils/holoExport.js");

const DATA = {
  titulo: "Buracos negros",
  cenas: [
    { icone: "🌌", titulo: "Horizonte", fala: "Nada escapa.", pontos: ["luz presa"], numero: { valor: 1500, unidade: "km", rotulo: "raio" } },
    { icone: "⭐", titulo: "Origem", fala: "Estrelas gigantes.", pontos: [], numero: null },
  ],
  fontes: [{ titulo: "NASA", url: "https://nasa.gov/bn" }],
};

test("V8.14: a apresentação vira texto com as fontes", () => {
  const t = holoText(DATA);
  assert.match(t, /^Buracos negros\n/);
  assert.match(t, /1\. 🌌 Horizonte\nNada escapa\.\n {3}• luz presa\n {3}➜ 1\.500 km \(raio\)/);
  assert.match(t, /Fontes:\n- NASA: https:\/\/nasa\.gov\/bn/);
  assert.equal(holoText(null), "");
});

test("V8.14: nome do arquivo e velocidade", () => {
  assert.equal(holoFileName("Buracos Negros: o fim?"), "holograma-buracos-negros-o-fim.txt");
  assert.equal(holoFileName(""), "holograma-apresentacao.txt");
  assert.deepEqual(HOLO_SPEEDS.map(nextSpeed), [1.25, 1.5, 1]);
  assert.equal(nextSpeed(9), 1);
  assert.equal(speedLabel(1.25), "1,25x");
});

test("V8.14: cenas que chegam aos poucos só crescem e não passam por cima da final", () => {
  let d = mergePartial(null, { titulo: "BN", cenas: [{ titulo: "a" }] }, "bn");
  assert.equal(d.partial, true);
  assert.equal(d.cenas.length, 1);
  assert.equal(mergePartial(d, { cenas: [{ titulo: "a" }] }), d); // nada novo
  d = mergePartial(d, { cenas: [{ titulo: "a" }, { titulo: "b" }] });
  assert.equal(d.cenas.length, 2);
  const final = { ...DATA };
  assert.equal(mergePartial(final, { cenas: [1, 2, 3] }), final);
  assert.match(newReqId(() => 0.5), /^h[a-z0-9]+$/);
});

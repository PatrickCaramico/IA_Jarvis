import assert from "node:assert/strict";
import test from "node:test";

const store = new Map();
globalThis.localStorage = { getItem: (k) => (store.has(k) ? store.get(k) : null), setItem: (k, v) => store.set(k, String(v)) };

const { DECAY, act, ageOf, bugCount, lifeLines, loadPet, lowestNeed, moodOf, newPet, savePet, tick } = await import("../src/utils/pet.js");
const H = 3_600_000;
const T0 = Date.UTC(2026, 10, 23, 12);

test("V8.15: as necessidades caem com o tempo e o sono recarrega a energia", () => {
  const pet = newPet(T0);
  const later = tick(pet, T0 + 2 * H);
  assert.equal(later.stats.bateria, 80 - 2 * DECAY.bateria);
  assert.equal(later.stats.diversao, 70 - 2 * DECAY.diversao);
  const asleep = tick({ ...pet, sleeping: true, stats: { ...pet.stats, energia: 20 } }, T0 + 2 * H);
  assert.equal(asleep.stats.energia, 70);
  assert.equal(asleep.stats.bateria, 80 - DECAY.bateria); // dormindo, cai pela metade
  const away = tick(pet, T0 + 30 * 24 * H); // um mês fora: conta no máximo 3 dias e para no zero
  assert.ok(Object.values(away.stats).every((v) => v >= 0));
});

test("V8.15: cuidar dele", () => {
  let pet = { ...newPet(T0), stats: { bateria: 40, energia: 60, diversao: 30, carinho: 50, limpeza: 50 } };
  let r = act(pet, "alimentar", T0);
  assert.equal(r.pet.stats.bateria, 70);
  assert.equal(r.face, "comendo");
  r = act(r.pet, "carinho", T0);
  assert.equal(r.pet.stats.carinho, 70);
  r = act(r.pet, "brincar", T0, { stars: 12 });
  assert.equal(r.pet.stats.diversao, 30 + 4 + Math.min(45, 10 + 36));
  assert.equal(r.face, "conseguiu");
  assert.equal(bugCount(r.pet), 2);
  r = act(r.pet, "bug", T0);
  assert.equal(bugCount(r.pet), 1);
  r = act(r.pet, "limpar", T0);
  assert.equal(r.pet.stats.limpeza, 100);
  assert.equal(bugCount(r.pet), 0);
  assert.deepEqual(r.pet.count, { alimentar: 1, carinho: 1, brincar: 1, limpar: 1 });
  const full = act({ ...pet, stats: { ...pet.stats, bateria: 97 } }, "alimentar", T0);
  assert.equal(full.pet.stats.bateria, 97); // cheio: não come mais
});

test("V8.15: dormindo ele não faz nada até acordar", () => {
  let r = act(newPet(T0), "dormir", T0);
  assert.equal(r.pet.sleeping, true);
  const no = act(r.pet, "alimentar", T0 + H);
  assert.equal(no.face, "dormindo");
  r = act(r.pet, "acordar", T0 + 3 * H);
  assert.equal(r.pet.sleeping, false);
  assert.equal(r.face, "feliz"); // energia 80 + 3h de sono
});

test("V8.15: humor pela necessidade mais baixa", () => {
  const base = newPet(T0);
  assert.equal(moodOf({ ...base, stats: { ...base.stats, bateria: 10 } }, { hour: 12 }).face, "chorando");
  const hungry = moodOf({ ...base, stats: { ...base.stats, diversao: 30 } }, { hour: 12 });
  assert.equal(hungry.level, "pede");
  assert.match(hungry.say, /entediado/);
  assert.equal(moodOf({ ...base, stats: { bateria: 90, energia: 90, diversao: 90, carinho: 90, limpeza: 90 } }, { hour: 12 }).level, "feliz");
  assert.match(moodOf({ ...base, stats: { ...base.stats, energia: 60 } }, { hour: 23 }).say, /dormir/);
  assert.equal(moodOf({ ...base, sleeping: true }).level, "dormindo");
  assert.deepEqual(lowestNeed({ stats: { bateria: 50, energia: 9, diversao: 70, carinho: 60, limpeza: 80 } }), { id: "energia", value: 9 });
});

test("V8.15: idade e o seu dia", () => {
  assert.equal(ageOf(newPet(T0), T0 + H).stage, "Bebê");
  assert.equal(ageOf(newPet(T0), T0 + 4 * 24 * H).label, "🤖 Jovem · 5º dia");
  assert.match(lifeLines({ agua_pct: 30, missoes_feitas: 1, missoes_total: 3 }, 15).join(" "), /30% da água/);
  assert.match(lifeLines({ agua_pct: 100, missoes_feitas: 3, missoes_total: 3 }, 9).join(" "), /Meta de água batida.*missões/s);
  assert.deepEqual(lifeLines(null), []);
});

test("V8.15: guarda e volta com o tempo passado", () => {
  store.clear();
  savePet(newPet(T0));
  const back = loadPet(T0 + 2 * H);
  assert.equal(back.stats.bateria, 80 - 2 * DECAY.bateria);
  store.set("jarvis.deskPet", "{lixo");
  assert.equal(loadPet(T0).stats.bateria, 80);
});

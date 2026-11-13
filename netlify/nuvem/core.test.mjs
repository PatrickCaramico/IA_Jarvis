// Testes do modo nuvem: node --test netlify/nuvem/core.test.mjs   (ou: npm run test:nuvem, na raiz)
import assert from "node:assert/strict";
import test from "node:test";
import { apply, checkToken, handle, loadState, makeToken, nextAlarm, parseReply, parseRss, receiveSnapshot, spNow, tick } from "./core.mjs";

function memStore() {
  const data = new Map();
  return {
    data,
    get: async (k) => (data.has(k) ? structuredClone(data.get(k)) : null),
    set: async (k, v) => { data.set(k, structuredClone(v)); },
  };
}

const ENV = { JARVIS_NUVEM_PIN: "1234", JARVIS_NUVEM_CHAVE: "segredo-de-teste" };
const NOW = new Date("2026-11-13T12:38:00Z"); // 09:38 em São Paulo, sexta-feira

function req(path, { method = "GET", body, token, headers = {} } = {}) {
  return new Request(`https://site.test/api/cloud${path}`, {
    method,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...headers },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

async function call(store, path, opts = {}, extra = {}) {
  const res = await handle(req(path, opts), { store, env: ENV, nowDate: NOW, ...extra });
  return { status: res.status, data: await res.json() };
}

async function login(store) {
  return (await call(store, "/login", { method: "POST", body: { pin: "1234" } })).data.token;
}

test("hora de São Paulo e próximo alarme", () => {
  const now = spNow(NOW);
  assert.equal(now.stamp, "2026-11-13 09:38");
  assert.equal(now.weekday, 4); // sexta
  assert.equal(nextAlarm("10:00", [], now), "2026-11-13 10:00");
  assert.equal(nextAlarm("07:00", [], now), "2026-11-14 07:00");
  assert.equal(nextAlarm("07:00", [0], now), "2026-11-16 07:00"); // próxima segunda
});

test("token assinado vale e expira", async () => {
  const t = await makeToken("k", NOW.getTime());
  assert.ok(await checkToken("k", t, NOW.getTime()));
  assert.ok(!(await checkToken("outra", t, NOW.getTime())));
  assert.ok(!(await checkToken("k", t, NOW.getTime() + 61 * 86400 * 1000)));
  assert.ok(!(await checkToken("k", "123.abc", NOW.getTime())));
});

test("PIN errado é recusado e bloqueia depois de muitas tentativas", async () => {
  const store = memStore();
  assert.equal((await call(store, "/login", { method: "POST", body: { pin: "0000" } })).status, 401);
  for (let i = 0; i < 8; i += 1) await call(store, "/login", { method: "POST", body: { pin: "9" } });
  assert.equal((await call(store, "/login", { method: "POST", body: { pin: "1234" } })).status, 429);
});

test("sem configuração o modo nuvem avisa (e o status é livre)", async () => {
  const store = memStore();
  const res = await handle(req("/state"), { store, env: {}, nowDate: NOW });
  assert.equal(res.status, 503);
  const st = await handle(req("/status"), { store, env: {}, nowDate: NOW });
  assert.equal((await st.json()).configured, false);
});

test("rotas exigem o token do PIN", async () => {
  const store = memStore();
  assert.equal((await call(store, "/state")).status, 401);
  const token = await login(store);
  assert.equal((await call(store, "/state", { token })).status, 200);
});

test("listas: compras, tarefas, água e lembretes", async () => {
  const store = memStore();
  const token = await login(store);
  await call(store, "/change", { method: "POST", token, body: { op: "shopping_add", itens: ["leite", "pão", "Leite"] } });
  await call(store, "/change", { method: "POST", token, body: { op: "shopping_set", texto: "leite", comprado: true } });
  await call(store, "/change", { method: "POST", token, body: { op: "task_add", texto: "pagar a conta de luz" } });
  await call(store, "/change", { method: "POST", token, body: { op: "water_add", ml: 250 } });
  await call(store, "/change", { method: "POST", token, body: { op: "reminder_add", texto: "Remédio", data_hora: "2026-11-13 20:00" } });
  const { data } = await call(store, "/state", { token });
  assert.deepEqual(data.compras.map((i) => [i.texto, i.comprado]), [["Pão", false], ["Leite", true]]);
  assert.equal(data.tarefas[0].texto, "Pagar a conta de luz");
  assert.equal(data.agua.total_ml, 250);
  assert.equal(data.lembretes.length, 1);
  const bad = await call(store, "/change", { method: "POST", token, body: { op: "reminder_add", texto: "x", data_hora: "amanhã" } });
  assert.equal(bad.status, 400);
});

test("sincronização: o PC busca as operações e manda a foto; operações novas são reaplicadas", async () => {
  const store = memStore();
  const token = await login(store);
  const sync = { "X-Jarvis-Nuvem": ENV.JARVIS_NUVEM_CHAVE };
  await call(store, "/change", { method: "POST", token, body: { op: "shopping_add", itens: ["café"] } });
  assert.equal((await call(store, "/sync", { headers: { "X-Jarvis-Nuvem": "errada" } })).status, 401);
  const pulled = await call(store, "/sync", { headers: sync });
  assert.equal(pulled.data.ops.length, 1);
  // chegou uma operação nova enquanto o PC aplicava
  await call(store, "/change", { method: "POST", token, body: { op: "shopping_add", itens: ["açúcar"] } });
  const snap = { compras: [{ id: 7, texto: "Arroz", comprado: false }, { id: 8, texto: "Café", comprado: false }], perfil: { nome: "Patrick", cidade: "Campinas" } };
  const pushed = await call(store, "/sync", { method: "POST", headers: sync, body: { ack: pulled.data.last_id, snapshot: snap } });
  assert.equal(pushed.data.pending, 1);
  const { data } = await call(store, "/state", { token });
  assert.deepEqual(data.compras.map((i) => i.texto), ["Arroz", "Café", "Açúcar"]);
  assert.equal((await call(store, "/status")).data.nome, "Patrick");
});

test("avisos: lembrete vencido e alarme repetido viram notificação uma vez só", async () => {
  const store = memStore();
  const now = spNow(NOW);
  const state = await loadState(store);
  apply(state, { op: "reminder_add", texto: "Ligar para a mãe", data_hora: "2026-11-13 09:30" }, now);
  apply(state, { op: "alarm_add", hora: "09:35", dias: [4], rotulo: "" }, spNow(new Date("2026-11-13T12:00:00Z")));
  apply(state, { op: "water_add", ml: 250, time: "09:00" }, now);
  for (const k of ["lembretes", "alarmes", "agua"]) await store.set(k, state[k]);
  const fired = await tick(store, now);
  assert.deepEqual(fired.map((f) => f.kind).sort(), ["alarm", "reminder"]);
  assert.equal((await tick(store, now)).length, 0);
  assert.equal((await store.get("alarmes"))[0].proximo, "2026-11-20 09:35");
  const token = await login(store);
  const feed = await call(store, "/notifications?since=0", { token });
  assert.equal(feed.data.items.length, 2);
  assert.equal(feed.data.latest, 2);
});

test("conversa: a IA responde em JSON e as ações mudam as listas", async () => {
  const store = memStore();
  const token = await login(store);
  let sent;
  const fetchFn = async (url, init) => {
    sent = { url, body: JSON.parse(init.body), headers: init.headers };
    const text = JSON.stringify({ resposta: "Coloquei leite na lista, senhor.", acoes: [{ tipo: "compras_add", itens: ["leite"] }, { tipo: "agua_add", ml: 500 }] });
    return new Response(JSON.stringify({ candidates: [{ content: { parts: [{ text }] } }] }), { status: 200 });
  };
  const env = { ...ENV, GEMINI_API_KEY: "g" };
  const res = await handle(req("/chat", { method: "POST", token, body: { message: "coloca leite na lista e marca meio litro de água" } }), { store, env, fetchFn, nowDate: NOW });
  const data = await res.json();
  assert.equal(data.reply, "Coloquei leite na lista, senhor.");
  assert.ok(data.actions.every((a) => a.ok));
  assert.match(sent.url, /generativelanguage/);
  assert.equal(sent.headers["x-goog-api-key"], "g");
  const st = await handle(req("/state", { token }), { store, env, nowDate: NOW });
  const s = await st.json();
  assert.equal(s.compras[0].texto, "Leite");
  assert.equal(s.agua.total_ml, 500);
  assert.equal(s.conversa.length, 2);
});

test("conversa sem chave da IA explica o que configurar", async () => {
  const store = memStore();
  const token = await login(store);
  const { data } = await call(store, "/chat", { method: "POST", token, body: { message: "oi" } });
  assert.match(data.reply, /GEMINI_API_KEY/);
});

test("resposta da IA fora do formato vira texto", () => {
  assert.deepEqual(parseReply('```json\n{"resposta":"Olá","acoes":[]}\n```'), { resposta: "Olá", acoes: [] });
  assert.equal(parseReply("Bom dia, senhor.").resposta, "Bom dia, senhor.");
});

test("RSS do Google Notícias", () => {
  const xml = `<rss><channel><item><title>Chuva forte em SP - g1</title><link>https://news.google.com/a</link><pubDate>Fri, 13 Nov 2026 10:00:00 GMT</pubDate><source url="https://g1.globo.com">g1</source></item>
  <item><title><![CDATA[Dólar &amp; bolsa hoje]]></title><link>https://news.google.com/b</link></item></channel></rss>`;
  const items = parseRss(xml);
  assert.equal(items.length, 2);
  assert.equal(items[0].title, "Chuva forte em SP");
  assert.equal(items[0].source, "g1");
  assert.equal(items[1].title, "Dólar & bolsa hoje");
});

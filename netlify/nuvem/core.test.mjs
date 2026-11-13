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

test("configurações da central chegam ao modo nuvem (validadas) e a personalidade vale na conversa", async () => {
  const store = memStore();
  const sync = { "X-Jarvis-Nuvem": ENV.JARVIS_NUVEM_CHAVE };
  const prefs = {
    ai_name: "Sexta-Feira", color_theme: "purple", theme_colors: { primary: "#a855f7", secondary: "#7c3aed", bg: "url(javascript:x)" },
    background_style: "space", personality_mode: "alexa", silent_mode: true, a11y_text_scale: 130, a11y_high_contrast: true,
    briefing_news_themes: [{ title: "Marvel", q: "Marvel" }, { title: "" }], water_quick_ml: [300, 9999], camera_index: 2,
  };
  await call(store, "/sync", { method: "POST", headers: sync, body: { ack: 0, snapshot: { perfil: { nome: "Patrick", assistente: "Sexta-Feira", prefs } } } });
  const { data } = await call(store, "/status");
  assert.equal(data.prefs.background_style, "space");
  assert.equal(data.prefs.personality_mode, "alexa");
  assert.deepEqual(data.prefs.theme_colors, { primary: "#a855f7", secondary: "#7c3aed" }); // cor inválida descartada
  assert.deepEqual(data.prefs.briefing_news_themes, [{ title: "Marvel", q: "Marvel" }]);
  assert.deepEqual(data.prefs.water_quick_ml, [300]);
  assert.equal(data.prefs.camera_index, undefined); // só as chaves da lista
  const token = await login(store);
  let system = "";
  const fetchFn = async (_url, init) => {
    system = JSON.parse(init.body).systemInstruction.parts[0].text;
    return new Response(JSON.stringify({ candidates: [{ content: { parts: [{ text: '{"resposta":"Ok.","acoes":[]}' }] } }] }));
  };
  await handle(req("/chat", { method: "POST", token, body: { message: "oi" } }), { store, env: { ...ENV, GEMINI_API_KEY: "g" }, fetchFn, nowDate: NOW });
  assert.match(system, /estilo Alexa/);
  assert.match(system, /Seu nome aqui é Sexta-Feira/);
});

test("voz da nuvem = voz do PC (validada); sem sincronizar, a padrão do JARVIS", async () => {
  const store = memStore();
  const token = await login(store);
  const calls = [];
  const synth = async (text, voice) => { calls.push({ text, voice }); return Buffer.from("MP3"); };
  const tts = async () => handle(req("/tts", { method: "POST", token, body: { text: "Bom dia, senhor." } }), { store, env: ENV, nowDate: NOW, synth });
  let res = await tts();
  assert.equal(res.status, 200);
  assert.equal(res.headers.get("content-type"), "audio/mpeg");
  assert.equal(Buffer.from(await res.arrayBuffer()).toString(), "MP3");
  assert.deepEqual(calls[0].voice, { name: "pt-BR-AntonioNeural", rate: "-4%", pitch: "-3Hz" });
  const sync = { "X-Jarvis-Nuvem": ENV.JARVIS_NUVEM_CHAVE };
  await call(store, "/sync", { method: "POST", headers: sync, body: { ack: 0, snapshot: { perfil: { prefs: { voice: { name: "pt-BR-ThalitaMultilingualNeural", rate: "-2%", pitch: "+0Hz" } } } } } });
  res = await tts();
  assert.equal(calls[1].voice.name, "pt-BR-ThalitaMultilingualNeural");
  await call(store, "/sync", { method: "POST", headers: sync, body: { ack: 0, snapshot: { perfil: { prefs: { voice: { name: "<script>", rate: "999" } } } } } });
  res = await tts();
  assert.equal(calls[2].voice.name, "pt-BR-AntonioNeural"); // voz inválida descartada
  assert.equal((await handle(req("/tts", { method: "POST", body: { text: "oi" } }), { store, env: ENV, nowDate: NOW, synth })).status, 401);
});

test("bem-estar na nuvem: segurança fixa sem IA, respiração e humor que vai para o PC", async () => {
  const store = memStore();
  const token = await login(store);
  let llmCalls = 0;
  const fetchFn = async () => {
    llmCalls += 1;
    const text = JSON.stringify({ resposta: "Registrei, senhor.", acoes: [{ tipo: "humor", nota: 4 }] });
    return new Response(JSON.stringify({ candidates: [{ content: { parts: [{ text }] } }] }));
  };
  const env = { ...ENV, GEMINI_API_KEY: "g" };
  const ask = async (message) => (await handle(req("/chat", { method: "POST", token, body: { message } }), { store, env, fetchFn, nowDate: NOW })).json();
  const crisis = await ask("Jarvis, quero morrer.");
  assert.match(crisis.reply, /188/);
  assert.match(crisis.reply, /192/);
  assert.equal((await ask("exercício de respiração")).reply.startsWith("Vamos respirar juntos"), true);
  assert.equal(llmCalls, 0); // nada disso passou pela IA
  assert.equal((await ask("vou me matar de rir com esse filme")).reply, "Registrei, senhor."); // expressão comum vai para a IA
  const ops = (await call(store, "/sync", { headers: { "X-Jarvis-Nuvem": ENV.JARVIS_NUVEM_CHAVE } })).data.ops;
  assert.deepEqual(ops.map((o) => [o.op, o.score, o.date]), [["mood_set", 4, "2026-11-13"]]);
});

test("memórias aprendidas no PC chegam ao JARVIS da nuvem", async () => {
  const store = memStore();
  const token = await login(store);
  await call(store, "/sync", { method: "POST", headers: { "X-Jarvis-Nuvem": ENV.JARVIS_NUVEM_CHAVE }, body: { ack: 0, snapshot: { perfil: { memorias: ["Torce para o Palmeiras", 42, "Treina às 18h"] } } } });
  let system = "";
  const fetchFn = async (_url, init) => {
    system = JSON.parse(init.body).systemInstruction.parts[0].text;
    return new Response(JSON.stringify({ candidates: [{ content: { parts: [{ text: '{"resposta":"Ok.","acoes":[]}' }] } }] }));
  };
  await handle(req("/chat", { method: "POST", token, body: { message: "oi" } }), { store, env: { ...ENV, GEMINI_API_KEY: "g" }, fetchFn, nowDate: NOW });
  assert.match(system, /Torce para o Palmeiras; Treina às 18h/);
});

test("agenda do PC e música do celular na nuvem", async () => {
  const store = memStore();
  const token = await login(store);
  await call(store, "/sync", { method: "POST", headers: { "X-Jarvis-Nuvem": ENV.JARVIS_NUVEM_CHAVE }, body: { ack: 0, snapshot: { perfil: { agenda: [
    { titulo: "Dentista", inicio: "2026-11-14T15:00:00", local: "Centro" },
    { titulo: "Feriado", inicio: "2026-11-20" },
    { titulo: "Velho", inicio: "2026-11-01T10:00:00" },
    { titulo: "sem data" },
  ] } } } });
  let system = "";
  const fetchFn = async (_url, init) => {
    system = JSON.parse(init.body).systemInstruction.parts[0].text;
    const text = JSON.stringify({ resposta: "Abrindo Coldplay no Spotify, senhor.", acoes: [{ tipo: "musica", comando: "tocar", busca: "Coldplay" }] });
    return new Response(JSON.stringify({ candidates: [{ content: { parts: [{ text }] } }] }));
  };
  const env = { ...ENV, GEMINI_API_KEY: "g" };
  const chatAs = async (pode_musica) => (await handle(req("/chat", { method: "POST", token, body: { message: "toca Coldplay", pode_musica } }), { store, env, fetchFn, nowDate: NOW })).json();
  const r = await chatAs(true);
  assert.match(system, /14\/11 às 15:00: Dentista \(Centro\); 20\/11 \(dia todo\): Feriado/);
  assert.doesNotMatch(system, /Velho/);
  assert.match(system, /você controla o player do celular/);
  assert.deepEqual(r.actions, [{ tipo: "musica", ok: true, comando: "tocar", busca: "Coldplay" }]);
  await chatAs(false);
  assert.match(system, /aqui \(navegador\) você não controla o player/);
  const st = await call(store, "/state", { token });
  assert.equal(st.data.agenda.length, 3);
});

test("ofensiva da água na nuvem: continua a do PC", async () => {
  const { waterStreak } = await import("./core.mjs");
  const now = spNow(NOW); // 2026-11-13
  // PC sincronizou hoje: base 5 até ontem
  let agua = { goal_ml: 2000, days: {}, streak: { date: "2026-11-13", base: 5, best: 7 } };
  assert.deepEqual(waterStreak(agua, now), { streak: 5, streak_base: 5, streak_today_done: false, streak_best: 7 });
  agua.days["2026-11-13"] = { total_ml: 2000, logs: [] };
  assert.equal(waterStreak(agua, now).streak, 6);
  // PC sumiu desde 11/11 (base 5 até 10/11); na nuvem bateu a meta em 11 e 12: 5 + 2
  agua = { goal_ml: 2000, days: { "2026-11-11": { total_ml: 2100 }, "2026-11-12": { total_ml: 2000 } }, streak: { date: "2026-11-11", base: 5, best: 5 } };
  assert.equal(waterStreak(agua, now).streak_base, 7);
  // falhou ontem: zera
  agua = { goal_ml: 2000, days: { "2026-11-12": { total_ml: 100 } }, streak: { date: "2026-11-11", base: 5 } };
  assert.equal(waterStreak(agua, now).streak_base, 0);
});

test("agentes na nuvem: rota com lugar salvo, salvar lugar e YouTube", async () => {
  const store = memStore();
  const token = await login(store);
  await call(store, "/sync", { method: "POST", headers: { "X-Jarvis-Nuvem": ENV.JARVIS_NUVEM_CHAVE }, body: { ack: 0, snapshot: { perfil: { lugares: { trabalho: "Av. Paulista, 1000" } } } } });
  let answer;
  let system = "";
  const fetchFn = async (_url, init) => {
    system = JSON.parse(init.body).systemInstruction.parts[0].text;
    return new Response(JSON.stringify({ candidates: [{ content: { parts: [{ text: JSON.stringify(answer) }] } }] }));
  };
  const env = { ...ENV, GEMINI_API_KEY: "g" };
  const chatMsg = async (message) => (await handle(req("/chat", { method: "POST", token, body: { message } }), { store, env, fetchFn, nowDate: NOW })).json();

  answer = { resposta: "Abrindo a rota, senhor.", acoes: [{ tipo: "rota", destino: "o trabalho", modo: "a pé" }] };
  let r = await chatMsg("quero ir pro trabalho a pé");
  assert.match(system, /Lugares salvos \(para rotas\): trabalho = Av\. Paulista, 1000/);
  assert.deepEqual(r.actions[0], { tipo: "abrir_url", ok: true, url: "https://www.google.com/maps/dir/?api=1&destination=Av.%20Paulista%2C%201000&travelmode=walking", agente: "rotas", rotulo: "trabalho" });

  answer = { resposta: "Guardado.", acoes: [{ tipo: "lugar_salvar", nome: "a academia", endereco: "Rua Augusta 500" }] };
  await chatMsg("minha academia fica na Rua Augusta 500");
  answer = { resposta: "Indo.", acoes: [{ tipo: "rota", destino: "academia" }] };
  r = await chatMsg("me leva pra academia");
  assert.match(r.actions[0].url, /destination=Rua%20Augusta%20500&travelmode=driving/);
  const ops = (await call(store, "/sync", { headers: { "X-Jarvis-Nuvem": ENV.JARVIS_NUVEM_CHAVE } })).data.ops;
  assert.deepEqual(ops.filter((o) => o.op === "place_set").map((o) => [o.nome, o.endereco]), [["academia", "Rua Augusta 500"]]);

  answer = { resposta: "Pesquisando.", acoes: [{ tipo: "youtube", busca: "receita de pão" }] };
  r = await chatMsg("pesquisa receita de pão no youtube");
  assert.equal(r.actions[0].url, "https://www.youtube.com/results?search_query=receita%20de%20p%C3%A3o");
});

test("o que é isso? pela câmera, na nuvem (foto validada; nada guardado)", async () => {
  const store = memStore();
  const token = await login(store);
  const jpeg = Buffer.from([0xff, 0xd8, 0xff, 0xe0, 1, 2, 3, 4]).toString("base64");
  let sent;
  const fetchFn = async (_url, init) => {
    sent = JSON.parse(init.body);
    return new Response(JSON.stringify({ candidates: [{ content: { parts: [{ text: "É uma jabuticabeira, senhor." }] } }] }));
  };
  const env = { ...ENV, GEMINI_API_KEY: "g" };
  const ask = (image) => handle(req("/vision", { method: "POST", token, body: { image, question: "que planta é essa?" } }), { store, env, fetchFn, nowDate: NOW });
  const r = await ask(`data:image/jpeg;base64,${jpeg}`);
  assert.equal(r.status, 200);
  assert.equal((await r.json()).text, "É uma jabuticabeira, senhor.");
  assert.equal(sent.contents[0].parts[0].inlineData.mimeType, "image/jpeg");
  assert.match(sent.contents[0].parts[1].text, /que planta é essa/);
  assert.equal((await ask(Buffer.from("<html>").toString("base64"))).status, 400);
  assert.deepEqual([...store.data.keys()].filter((k) => /foto|vision|image/.test(k)), []);
});

test("central de agentes: lugar salvo pela nuvem aparece no estado junto com os do PC", async () => {
  const store = memStore();
  const token = await login(store);
  await store.set("perfil", { lugares: { casa: "Rua A, 1" } });
  const r = await call(store, "/change", { method: "POST", token, body: { op: "place_set", nome: "Trabalho", endereco: "Av. Paulista, 1000" } });
  assert.equal(r.status, 200);
  const { data } = await call(store, "/state", { token });
  assert.equal(data.lugares.casa, "Rua A, 1");
  assert.equal(Object.values(data.lugares).includes("Av. Paulista, 1000"), true);
});

// JARVIS · modo nuvem (V6.6): um backend pequeno que roda no Netlify e funciona com o notebook DESLIGADO.
//
// O backend completo continua no PC (câmera, Sentinela, controle do Windows, Spotify...). Aqui fica só o
// que faz sentido no celular longe de casa: conversar com a IA, lista de compras, tarefas, lembretes,
// alarmes, água, notícias e clima. Os dados ficam no Netlify Blobs.
//
// Sincronização com o PC: cada mudança feita na nuvem vira uma "operação" (ops). Quando o PC liga, ele
// busca as operações, aplica nas listas dele e devolve a foto (snapshot) das listas; a nuvem passa a
// mostrar essa foto, reaplicando as operações que chegaram no meio do caminho.
//
// Este arquivo não depende do Netlify: recebe o armazenamento, as variáveis e o fetch por parâmetro
// (assim os testes rodam com Node puro, em netlify/nuvem/core.test.mjs).

export const TZ = "America/Sao_Paulo";
const TOKEN_DAYS = 60;
const MAX_HISTORY = 24;
const MAX_ITEMS = 120;
const MAX_FEED = 60;
const LOGIN_WINDOW_MS = 15 * 60 * 1000;
const LOGIN_MAX_FAILS = 8;

// --------------------------------------------------------------------------- utilidades
export function norm(text) {
  return String(text || "")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

function clean(text, max = 80) {
  return String(text || "").replace(/\s+/g, " ").trim().replace(/^[\s.,!?;:]+|[\s.,!?;:]+$/g, "").slice(0, max);
}

function capitalize(text) {
  return text ? text[0].toUpperCase() + text.slice(1) : text;
}

/** Data e hora de São Paulo: { date: "2026-11-13", time: "09:38", weekday: 0 (segunda) .. 6, stamp: "2026-11-13 09:38" } */
export function spNow(now = new Date()) {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat("en-CA", {
      timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", weekday: "short", hourCycle: "h23",
    }).formatToParts(now).map((p) => [p.type, p.value]),
  );
  const weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].indexOf(parts.weekday);
  const date = `${parts.year}-${parts.month}-${parts.day}`;
  const time = `${parts.hour}:${parts.minute}`;
  return { date, time, weekday, stamp: `${date} ${time}` };
}

function addDays(date, days) {
  const d = new Date(`${date}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

function weekdayOf(date) {
  return (new Date(`${date}T12:00:00Z`).getUTCDay() + 6) % 7; // 0 = segunda
}

/** Próxima vez que um alarme "HH:MM" toca (dias: 0 = segunda; vazio = uma vez só). */
export function nextAlarm(hora, dias, now = spNow()) {
  for (let i = 0; i < 8; i += 1) {
    const date = addDays(now.date, i);
    if (i === 0 && hora <= now.time) continue;
    if (!dias?.length || dias.includes(weekdayOf(date))) return `${date} ${hora}`;
  }
  return `${addDays(now.date, 1)} ${hora}`;
}

function validStamp(text) {
  return typeof text === "string" && /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/.test(text);
}

function validHour(text) {
  return typeof text === "string" && /^([01]\d|2[0-3]):[0-5]\d$/.test(text);
}

function nextId(list) {
  return list.reduce((m, i) => Math.max(m, Number(i.id) || 0), 0) + 1;
}

export class HttpError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

// --------------------------------------------------------------------------- chave de acesso (PIN -> token)
const enc = new TextEncoder();

async function hmac(secret, text) {
  const key = await crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(text));
  return Buffer.from(sig).toString("base64url");
}

function sameText(a, b) {
  const x = enc.encode(String(a));
  const y = enc.encode(String(b));
  if (x.length !== y.length) return false;
  let diff = 0;
  for (let i = 0; i < x.length; i += 1) diff |= x[i] ^ y[i];
  return diff === 0;
}

export async function makeToken(secret, nowMs = Date.now()) {
  const exp = Math.floor(nowMs / 1000) + TOKEN_DAYS * 86400;
  return `${exp}.${await hmac(secret, `nuvem:${exp}`)}`;
}

export async function checkToken(secret, token, nowMs = Date.now()) {
  const [exp, sig] = String(token || "").split(".");
  if (!exp || !sig || !/^\d+$/.test(exp) || Number(exp) * 1000 < nowMs) return false;
  return sameText(sig, await hmac(secret, `nuvem:${exp}`));
}

// --------------------------------------------------------------------------- estado (listas)
// Cada coleção é um documento JSON no armazenamento. As mudanças passam por apply(), que serve tanto para
// o uso normal quanto para reaplicar as operações por cima da foto que o PC mandou.

const EMPTY = {
  compras: () => [],
  tarefas: () => [],
  lembretes: () => [],
  alarmes: () => [],
  agua: () => ({ goal_ml: 2000, days: {} }),
};

export async function loadState(store) {
  const state = {};
  await Promise.all(Object.keys(EMPTY).map(async (k) => {
    const v = await store.get(k);
    state[k] = v ?? EMPTY[k]();
  }));
  return state;
}

async function saveState(store, state, keys) {
  await Promise.all(keys.map((k) => store.set(k, state[k])));
}

function findByText(list, field, text) {
  const want = norm(text);
  if (!want) return null;
  return list.find((i) => norm(i[field]) === want) || list.find((i) => norm(i[field]).includes(want) || want.includes(norm(i[field]))) || null;
}

/** Aplica uma operação no estado. Devolve o que mudou ({ keys, result }) ou lança HttpError. */
export function apply(state, op, now = spNow()) {
  const s = state;
  switch (op.op) {
    case "shopping_add": {
      const added = [];
      for (const raw of op.itens || []) {
        const texto = clean(raw, 60);
        if (!texto) continue;
        const again = s.compras.find((i) => norm(i.texto) === norm(texto));
        if (again) {
          if (again.comprado) { again.comprado = false; added.push(again); }
          continue;
        }
        if (s.compras.length >= MAX_ITEMS) break;
        const item = { id: nextId(s.compras), texto: capitalize(texto), comprado: false, criado_em: now.stamp };
        s.compras.push(item);
        added.push(item);
      }
      return { keys: ["compras"], result: added };
    }
    case "shopping_set": {
      const item = findByText(s.compras, "texto", op.texto);
      if (!item) throw new HttpError(404, "Item não encontrado.");
      item.comprado = Boolean(op.comprado);
      return { keys: ["compras"], result: item };
    }
    case "shopping_remove": {
      const item = findByText(s.compras, "texto", op.texto);
      if (!item) throw new HttpError(404, "Item não encontrado.");
      s.compras = s.compras.filter((i) => i !== item);
      return { keys: ["compras"], result: item };
    }
    case "shopping_clear": {
      const before = s.compras.length;
      s.compras = op.tudo ? [] : s.compras.filter((i) => !i.comprado);
      return { keys: ["compras"], result: before - s.compras.length };
    }
    case "task_add": {
      const texto = clean(op.texto, 140);
      if (!texto) throw new HttpError(400, "Diga qual é a tarefa.");
      if (s.tarefas.length >= MAX_ITEMS) throw new HttpError(400, "A lista de tarefas está cheia.");
      const task = { id: nextId(s.tarefas), texto: capitalize(texto), concluida: false, criada_em: now.stamp };
      s.tarefas.push(task);
      return { keys: ["tarefas"], result: task };
    }
    case "task_done": {
      const task = findByText(s.tarefas.filter((t) => !t.concluida || op.concluida === false), "texto", op.texto);
      if (!task) throw new HttpError(404, "Tarefa não encontrada.");
      task.concluida = op.concluida !== false;
      if (task.concluida) task.concluida_em = now.stamp;
      else delete task.concluida_em;
      return { keys: ["tarefas"], result: task };
    }
    case "task_remove": {
      const task = findByText(s.tarefas, "texto", op.texto);
      if (!task) throw new HttpError(404, "Tarefa não encontrada.");
      s.tarefas = s.tarefas.filter((t) => t !== task);
      return { keys: ["tarefas"], result: task };
    }
    case "reminder_add": {
      const texto = clean(op.texto, 140);
      if (!texto) throw new HttpError(400, "Diga do que devo lembrar.");
      if (!validStamp(op.data_hora)) throw new HttpError(400, "Data inválida. Use AAAA-MM-DD HH:MM.");
      const rem = { id: nextId(s.lembretes), texto, data_hora: op.data_hora, disparado: false, criado_em: now.stamp };
      s.lembretes.push(rem);
      return { keys: ["lembretes"], result: rem };
    }
    case "reminder_remove": {
      const rem = s.lembretes.find((r) => norm(r.texto) === norm(op.texto) && (!op.data_hora || r.data_hora === op.data_hora));
      if (!rem) throw new HttpError(404, "Lembrete não encontrado.");
      s.lembretes = s.lembretes.filter((r) => r !== rem);
      return { keys: ["lembretes"], result: rem };
    }
    case "alarm_add": {
      if (!validHour(op.hora)) throw new HttpError(400, "Hora inválida. Use HH:MM.");
      const dias = [...new Set((op.dias || []).map(Number).filter((d) => d >= 0 && d <= 6))].sort();
      if (s.alarmes.length >= 20) throw new HttpError(400, "Já tenho alarmes demais. Apague alguns antes.");
      const alarm = { id: nextId(s.alarmes), hora: op.hora, dias, rotulo: clean(op.rotulo, 60), proximo: nextAlarm(op.hora, dias, now), criado_em: now.stamp };
      s.alarmes.push(alarm);
      return { keys: ["alarmes"], result: alarm };
    }
    case "alarm_remove": {
      const alarm = s.alarmes.find((a) => a.hora === op.hora && norm(a.rotulo) === norm(op.rotulo));
      if (!alarm) throw new HttpError(404, "Alarme não encontrado.");
      s.alarmes = s.alarmes.filter((a) => a !== alarm);
      return { keys: ["alarmes"], result: alarm };
    }
    case "water_add": {
      const ml = Math.round(Number(op.ml));
      if (!(ml > 0 && ml <= 3000)) throw new HttpError(400, "Quantidade de água inválida.");
      const date = op.date || now.date;
      const day = (s.agua.days[date] ||= { total_ml: 0, logs: [] });
      day.total_ml += ml;
      day.logs.push({ time: op.time || now.time, ml, note: "copo de água" });
      return { keys: ["agua"], result: ml };
    }
    case "water_undo": {
      const day = s.agua.days[op.date || now.date];
      const last = day?.logs?.pop();
      if (last) day.total_ml = Math.max(0, day.total_ml - last.ml);
      return { keys: ["agua"], result: last || null };
    }
    case "water_goal": {
      const goal = Math.round(Number(op.goal_ml));
      if (!(goal >= 500 && goal <= 10000)) throw new HttpError(400, "A meta diária deve ficar entre 500 ml e 10.000 ml.");
      s.agua.goal_ml = goal;
      return { keys: ["agua"], result: goal };
    }
    case "place_set": {
      // V6.8: lugar salvo fora de casa ("meu trabalho fica na..."): a nuvem guarda e repassa ao PC
      const nome = clean(norm(op.nome || "").replace(/^(?:o|a|meu|minha)\s+/, ""), 40);
      const endereco = clean(op.endereco, 160);
      if (!nome || !endereco) throw new HttpError(400, "Diga o nome do lugar e o endereço.");
      op.nome = nome;
      op.endereco = endereco;
      return { keys: [], result: { nome, endereco } };
    }
    case "mood_set": {
      // V6.7: humor do dia (1 a 5); a nuvem só repassa ao PC (data/humor.json)
      const score = Math.round(Number(op.score));
      if (!(score >= 1 && score <= 5)) throw new HttpError(400, "Humor de 1 a 5.");
      op.score = score;
      op.date ||= now.date;
      return { keys: [], result: score };
    }
    default:
      throw new HttpError(400, "Operação desconhecida.");
  }
}

// V6.8: ofensiva (dias seguidos batendo a meta). O PC manda a ofensiva até ontem ("base", com a data);
// se o PC não sincronizou hoje, a nuvem conta pelos dias que ela mesma tem (com a base antiga como piso).
export function waterStreak(agua, now = spNow()) {
  const goal = agua.goal_ml || 2000;
  const done = (date) => (agua.days[date]?.total_ml || 0) >= goal;
  let base;
  const sk = agua.streak;
  if (sk && sk.date === now.date) base = sk.base;
  else {
    base = 0;
    let d = addDays(now.date, -1);
    while (done(d) && base < 3650) {
      base += 1;
      d = addDays(d, -1);
      if (sk && d === addDays(sk.date, -1)) { base += sk.base; break; } // emenda com a base que o PC mandou
    }
  }
  const todayDone = done(now.date);
  const days = base + (todayDone ? 1 : 0);
  return { streak: days, streak_base: base, streak_today_done: todayDone, streak_best: Math.max(sk?.best || 0, days) };
}

export function waterStatus(agua, now = spNow()) {
  const day = agua.days[now.date] || { total_ml: 0, logs: [] };
  const goal = agua.goal_ml || 2000;
  return {
    ...waterStreak(agua, now),
    date: now.date,
    total_ml: day.total_ml,
    goal_ml: goal,
    percentage: goal > 0 ? Math.min(100, Math.floor((day.total_ml / goal) * 100)) : 0,
    goal_reached: day.total_ml >= goal,
    logs: day.logs,
  };
}

function pruneWater(agua, now) {
  const keep = addDays(now.date, -14);
  for (const date of Object.keys(agua.days)) if (date < keep) delete agua.days[date];
}

// --------------------------------------------------------------------------- operações pendentes para o PC
async function recordOp(store, op, now) {
  const log = (await store.get("ops")) || { seq: 0, items: [] };
  log.seq += 1;
  log.items.push({ ...op, id: log.seq, at: now.stamp });
  if (log.items.length > 500) log.items = log.items.slice(-500);
  await store.set("ops", log);
}

/** Muda o estado (e guarda a operação para o PC). */
export async function change(store, op, now = spNow()) {
  const state = await loadState(store);
  const { keys, result } = apply(state, op, now);
  if (keys.includes("agua")) pruneWater(state.agua, now);
  await saveState(store, state, keys);
  await recordOp(store, op, now);
  return { state, result };
}

/** O PC mandou a foto das listas dele: ela vira o estado e as operações ainda não confirmadas são reaplicadas. */
export async function receiveSnapshot(store, { ack = 0, snapshot = {} }, now = spNow()) {
  const log = (await store.get("ops")) || { seq: 0, items: [] };
  log.items = log.items.filter((o) => o.id > Number(ack || 0));
  const state = await loadState(store);
  const pick = (list, fields) => (Array.isArray(list) ? list.slice(0, MAX_ITEMS).map((i) => Object.fromEntries(fields.filter((f) => i[f] !== undefined).map((f) => [f, i[f]]))) : null);
  const compras = pick(snapshot.compras, ["id", "texto", "comprado", "criado_em"]);
  const tarefas = pick(snapshot.tarefas, ["id", "texto", "concluida", "criada_em", "concluida_em"]);
  const lembretes = pick(snapshot.lembretes, ["id", "texto", "data_hora", "disparado", "criado_em", "recorrencia", "dias"]);
  const alarmes = pick(snapshot.alarmes, ["id", "hora", "dias", "rotulo", "proximo", "criado_em"]);
  if (compras) state.compras = compras;
  if (tarefas) state.tarefas = tarefas;
  if (lembretes) state.lembretes = lembretes;
  if (alarmes) state.alarmes = alarmes;
  if (snapshot.agua && typeof snapshot.agua === "object") {
    const goal = Number(snapshot.agua.goal_ml);
    if (goal >= 500 && goal <= 10000) state.agua.goal_ml = goal;
    const sk = snapshot.agua.streak;
    if (sk && /^\d{4}-\d{2}-\d{2}$/.test(sk.date || "")) {
      state.agua.streak = { date: sk.date, base: Math.max(0, Math.round(Number(sk.base) || 0)), best: Math.max(0, Math.round(Number(sk.best) || 0)) };
    }
    const today = snapshot.agua.today;
    if (today && /^\d{4}-\d{2}-\d{2}$/.test(today.date || "")) {
      state.agua.days[today.date] = { total_ml: Math.max(0, Number(today.total_ml) || 0), logs: Array.isArray(today.logs) ? today.logs.slice(-50) : [] };
    }
  }
  for (const op of log.items) {
    try {
      apply(state, op, now);
    } catch {
      // a operação não cabe mais (o item já sumiu no PC, por exemplo)
    }
  }
  pruneWater(state.agua, now);
  await saveState(store, state, Object.keys(EMPTY));
  await store.set("ops", log);
  if (snapshot.perfil && typeof snapshot.perfil === "object") {
    const p = snapshot.perfil;
    await store.set("perfil", {
      nome: clean(p.nome, 40),
      assistente: clean(p.assistente, 30) || "JARVIS",
      cidade: clean(p.cidade, 60),
      sobre: clean(p.sobre, 600),
      prefs: cleanPrefs(p.prefs),
      // V6.7.3: memórias que o PC aprendeu (a nuvem só lê; quem aprende é o PC)
      // V6.7.4: compromissos dos próximos 7 dias que o PC leu na agenda (sem nenhuma chave do Google)
      agenda: Array.isArray(p.agenda)
        ? p.agenda.filter((e) => e && typeof e === "object" && /^\d{4}-\d{2}-\d{2}/.test(e.inicio || ""))
          .map((e) => ({ titulo: clean(e.titulo, 120) || "Compromisso", inicio: String(e.inicio).slice(0, 19), local: clean(e.local, 80) }))
          .slice(0, 25)
        : [],
      // V6.8: lugares do agente de rotas ("trabalho" -> endereço)
      lugares: cleanPlaces(p.lugares),
      memorias: Array.isArray(p.memorias) ? p.memorias.filter((m) => typeof m === "string").map((m) => clean(m, 140)).filter(Boolean).slice(-30) : [],
      atualizado_em: now.stamp,
    });
  }
  return { pending: log.items.length };
}

// V6.6.2: configurações da central que valem no modo nuvem (validadas: vêm do PC, mas nunca confie cego)
const HEX = /^#[0-9a-f]{3,8}$/i;
const VOICE_NAME = /^[a-z]{2}-[A-Z]{2}-[A-Za-z]+Neural$/;
// V6.6.9: a voz padrão do JARVIS no PC (estilo "Natural"), usada até o PC sincronizar a dele
export const DEFAULT_VOICE = { name: "pt-BR-AntonioNeural", rate: "-4%", pitch: "-3Hz" };
export function cleanPrefs(p) {
  if (!p || typeof p !== "object") return {};
  const out = {};
  if (typeof p.ai_name === "string") out.ai_name = clean(p.ai_name, 30);
  if (["blue", "green", "purple", "orange", "red"].includes(p.color_theme)) out.color_theme = p.color_theme;
  if (p.theme_colors && typeof p.theme_colors === "object") {
    const c = {};
    for (const k of ["primary", "secondary", "bg"]) if (HEX.test(p.theme_colors[k] || "")) c[k] = p.theme_colors[k];
    if (Object.keys(c).length) out.theme_colors = c;
  }
  if (["blueprint", "classic", "space"].includes(p.background_style)) out.background_style = p.background_style;
  if (["direto", "descontraido", "formal", "alexa"].includes(p.personality_mode)) out.personality_mode = p.personality_mode;
  if (typeof p.silent_mode === "boolean") out.silent_mode = p.silent_mode;
  if ([100, 115, 130].includes(Number(p.a11y_text_scale))) out.a11y_text_scale = Number(p.a11y_text_scale);
  for (const k of ["a11y_high_contrast", "a11y_reduce_motion"]) if (typeof p[k] === "boolean") out[k] = p[k];
  if (Array.isArray(p.briefing_news_themes)) {
    out.briefing_news_themes = p.briefing_news_themes
      .map((t) => ({ title: clean(t?.title, 40), q: clean(t?.q || t?.query || t?.topic || t?.title, 80) }))
      .filter((t) => t.title && t.q)
      .slice(0, 8);
  }
  if (Array.isArray(p.water_quick_ml)) {
    const ml = p.water_quick_ml.map(Number).filter((n) => n > 0 && n <= 3000).slice(0, 4);
    if (ml.length) out.water_quick_ml = ml;
  }
  if (["all", "important", "off"].includes(p.sfx_mode)) out.sfx_mode = p.sfx_mode;
  const v = p.voice;
  if (v && typeof v === "object" && VOICE_NAME.test(v.name || "")) {
    out.voice = {
      name: v.name,
      rate: /^[+-]\d{1,2}%$/.test(v.rate || "") ? v.rate : "+0%",
      pitch: /^[+-]\d{1,2}Hz$/.test(v.pitch || "") ? v.pitch : "+0Hz",
    };
  }
  return out;
}

const PERSONALITY = {
  direto: "Seja objetivo e natural.",
  descontraido: "Use um tom leve, próximo e bem-humorado, sem exagerar.",
  formal: "Use um tom profissional, claro e respeitoso.",
  alexa: "Responda como uma assistente de voz de casa (estilo Alexa): no máximo 1 ou 2 frases bem curtas, a informação primeiro, sem 'senhor' em toda resposta.",
};

// --------------------------------------------------------------------------- avisos (notificações do celular)
async function pushNotice(store, notice, now) {
  const feed = (await store.get("avisos")) || { seq: 0, items: [] };
  feed.seq += 1;
  feed.items.push({ id: feed.seq, at: now.stamp, ...notice });
  if (feed.items.length > MAX_FEED) feed.items = feed.items.slice(-MAX_FEED);
  await store.set("avisos", feed);
}

/** Confere lembretes, alarmes e água vencidos (roda a cada consulta de avisos: não há relógio na nuvem). */
export async function tick(store, now = spNow()) {
  const state = await loadState(store);
  const fired = [];
  for (const r of state.lembretes) {
    if (!r.disparado && validStamp(r.data_hora) && r.data_hora <= now.stamp) {
      r.disparado = true;
      fired.push({ title: "Lembrete do JARVIS", body: r.texto, kind: "reminder" });
    }
  }
  const keepAlarms = [];
  for (const a of state.alarmes) {
    if (validStamp(a.proximo) && a.proximo <= now.stamp) {
      fired.push({ title: `Alarme · ${a.hora}`, body: a.rotulo || "Hora de levantar, senhor.", kind: "alarm" });
      if (a.dias?.length) {
        a.proximo = nextAlarm(a.hora, a.dias, now);
        keepAlarms.push(a);
      }
    } else keepAlarms.push(a);
  }
  state.alarmes = keepAlarms;
  // água: a cada 2 h sem registro, das 8h às 22h (no máximo um aviso a cada 2 h)
  const meta = (await store.get("agua_aviso")) || {};
  const st = waterStatus(state.agua, now);
  const hour = Number(now.time.slice(0, 2));
  const lastLog = st.logs.at(-1)?.time || "08:00";
  const minutes = (t) => Number(t.slice(0, 2)) * 60 + Number(t.slice(3, 5));
  const nowMin = minutes(now.time);
  if (hour >= 8 && hour < 22 && !st.goal_reached && nowMin - minutes(lastLog) >= 120
      && !(meta.date === now.date && nowMin - minutes(meta.time) < 120)) {
    fired.push({ title: "Água", body: `Hora de um copo d'água, senhor. Hoje: ${st.total_ml} de ${st.goal_ml} ml.`, kind: "water" });
    await store.set("agua_aviso", { date: now.date, time: now.time });
  }
  if (fired.length) {
    await saveState(store, state, ["lembretes", "alarmes"]);
    for (const n of fired) await pushNotice(store, n, now);
  }
  return fired;
}

// --------------------------------------------------------------------------- notícias e clima
const WMO = {
  0: "céu limpo", 1: "céu predominantemente limpo", 2: "parcialmente nublado", 3: "céu nublado", 45: "neblina",
  48: "neblina", 51: "garoa leve", 53: "garoa", 55: "garoa forte", 56: "garoa congelante", 57: "garoa congelante",
  61: "chuva fraca", 63: "chuva", 65: "chuva forte", 66: "chuva congelante", 67: "chuva congelante forte",
  71: "neve fraca", 73: "neve", 75: "neve forte", 77: "grãos de neve", 80: "pancadas de chuva fracas",
  81: "pancadas de chuva", 82: "pancadas de chuva fortes", 85: "pancadas de neve", 86: "pancadas de neve fortes",
  95: "trovoadas", 96: "trovoadas com granizo", 99: "trovoadas com granizo forte",
};
const ICON = (code) => (code <= 1 ? "☀️" : code === 2 ? "⛅" : code === 3 ? "☁️" : code <= 48 ? "🌫️" : code >= 95 ? "⛈️" : code >= 71 && code <= 77 ? "❄️" : "🌧️");

function decodeEntities(text) {
  return String(text || "")
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1")
    .replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#39;|&apos;/g, "'")
    .replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(Number(n)))
    .replace(/&amp;/g, "&")
    .trim();
}

export function parseRss(xml, limit = 12) {
  const items = [];
  for (const m of String(xml).matchAll(/<item>([\s\S]*?)<\/item>/g)) {
    const tag = (name) => decodeEntities((m[1].match(new RegExp(`<${name}[^>]*>([\\s\\S]*?)</${name}>`)) || [])[1]);
    let title = tag("title");
    const source = tag("source");
    if (source && title.endsWith(` - ${source}`)) title = title.slice(0, -(source.length + 3));
    const link = tag("link");
    if (!title || !/^https?:\/\//.test(link)) continue;
    items.push({ title, link, source, published: tag("pubDate") });
    if (items.length >= limit) break;
  }
  return items;
}

export async function getNews(fetchFn, topic = "") {
  const q = clean(topic, 60);
  const url = q
    ? `https://news.google.com/rss/search?q=${encodeURIComponent(q)}&hl=pt-BR&gl=BR&ceid=BR:pt-419`
    : "https://news.google.com/rss?hl=pt-BR&gl=BR&ceid=BR:pt-419";
  const res = await fetchFn(url, { headers: { "User-Agent": "Mozilla/5.0 (JARVIS nuvem)" } });
  if (!res.ok) throw new HttpError(502, "Não consegui buscar as notícias agora.");
  return { topic: q, items: parseRss(await res.text()) };
}

export async function getWeather(fetchFn, city) {
  const name = clean(city, 60) || "São Paulo";
  const geo = await fetchFn(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(name)}&count=1&language=pt&format=json`);
  const place = geo.ok ? (await geo.json()).results?.[0] : null;
  if (!place) throw new HttpError(404, `Não encontrei a cidade ${name}.`);
  const url = "https://api.open-meteo.com/v1/forecast"
    + `?latitude=${place.latitude}&longitude=${place.longitude}`
    + "&current=temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m"
    + "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
    + `&timezone=${encodeURIComponent(TZ)}&forecast_days=6`;
  const res = await fetchFn(url);
  if (!res.ok) throw new HttpError(502, "Não consegui consultar o clima agora.");
  const data = await res.json();
  const c = data.current || {};
  const d = data.daily || {};
  const days = (d.time || []).map((date, i) => ({
    date,
    weekday: ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"][weekdayOf(date)],
    icon: ICON(d.weather_code?.[i] ?? 0),
    description: WMO[d.weather_code?.[i]] || "tempo variável",
    max: Math.round(d.temperature_2m_max?.[i]),
    min: Math.round(d.temperature_2m_min?.[i]),
    rain: d.precipitation_probability_max?.[i] ?? null,
  }));
  return {
    place: [place.name, place.admin1].filter(Boolean).join(", "),
    coords: { lat: place.latitude, lon: place.longitude }, // V6.9: centro do mapa de trânsito (Olho de Deus)
    temperature: Math.round(c.temperature_2m),
    apparent_temperature: Math.round(c.apparent_temperature),
    humidity: c.relative_humidity_2m ?? null,
    wind: c.wind_speed_10m ?? null,
    description: WMO[c.weather_code] || "tempo variável",
    icon: ICON(c.weather_code ?? 0),
    maximum: days[0]?.max,
    minimum: days[0]?.min,
    rain_probability: days[0]?.rain ?? null,
    week: days,
  };
}

// --------------------------------------------------------------------------- bem-estar (V6.7)
// Mesmas frases e textos de backend/modules/wellbeing.py (o PC é a referência; os testes dos dois lados conferem).
const HARM_INTENT = "(?:quero|vou|penso em|pensando em|vontade de|com vontade de|preciso|tentei|tentar)";
const CRISIS = new RegExp(
  "\\b(?:me matar(?! de )|suicid\\w*|tirar (?:a )?(?:minha )?(?:propria )?vida|acabar com (?:a )?minha (?:propria )?vida|"
  + "quero morrer(?! de )|vontade de morrer(?! de )|nao quero (?:mais )?viver|nao quero mais estar aqui|"
  + "sem (?:razao|motivo|vontade) (?:pra|para|de) viver|nao aguento mais viver|"
  + "melhor (?:se )?eu (?:nao existisse|morresse|sumisse)|automutil\\w*|"
  + HARM_INTENT + " me (?:machucar|ferir|cortar(?! (?:o|a|os|as) )))\\b",
);
export const CRISIS_REPLY = "Senhor, sinto muito que esteja passando por isso, e fico feliz que tenha me contado. "
  + "Você não precisa enfrentar isso sozinho. Por favor, ligue agora para o CVV, no 188: é gratuito, "
  + "funciona 24 horas, e também dá para conversar pelo chat em cvv.org.br. "
  + "Se estiver em perigo agora, ligue 192, o SAMU. Se puder, chame alguém de confiança para ficar com você. "
  + "Eu continuo aqui com você.";
const BREATH_478 = "Vamos respirar juntos, senhor. Solte o ar pela boca. Agora inspire pelo nariz contando até quatro... "
  + "segure o ar contando até sete... e solte devagar pela boca contando até oito. "
  + "Mais uma vez: inspire em quatro... segure em sete... solte em oito. "
  + "E a última: inspire... segure... e solte bem devagar. Muito bem. Como está se sentindo agora?";
const BREATH_BOX = "Respiração quadrada, senhor. Inspire contando até quatro... segure quatro... solte em quatro... "
  + "e fique sem ar por quatro. Repita comigo mais três vezes, no seu ritmo. "
  + "Quatro para entrar, quatro segurando, quatro para sair, quatro em pausa. Muito bem.";
const GROUNDING = "Vamos trazer a atenção para o agora, senhor. Olhe em volta e diga para si cinco coisas que você vê. "
  + "Agora, quatro coisas que você consegue tocar. Três sons que você ouve. Duas coisas que você sente o cheiro. "
  + "E uma coisa que você sente o gosto, ou algo bom sobre você. Respire fundo. Você está aqui, e está seguro.";

export function wellbeingReply(text) {
  const n = norm(text).replace(/[^\w\s]/g, " ").replace(/\s+/g, " ").trim();
  if (CRISIS.test(n)) return CRISIS_REPLY;
  if (/\b(?:respiracao|respirar|respira)\b/.test(n)
      && (/\b(?:exercicio|exercicios|guiada|guia|ajuda|ajude|vamos|bora|me ensina|faz|faca|fazer|quero|preciso)\b/.test(n) || n.split(" ").length <= 4)) {
    return n.includes("quadrad") ? BREATH_BOX : BREATH_478;
  }
  if (/\b(?:aterramento|5 4 3 2 1|cinco quatro tres dois um)\b|\bme (?:ajuda|ajude) a (?:me )?acalmar\b|\bme acalma\b/.test(n)) return GROUNDING;
  return null;
}

// --------------------------------------------------------------------------- conversa (IA)
export function llmConfig(env) {
  const keys = { gemini: env.GEMINI_API_KEY, openai: env.OPENAI_API_KEY, anthropic: env.ANTHROPIC_API_KEY };
  const wanted = String(env.LLM_PROVIDER || "").trim().toLowerCase();
  const provider = keys[wanted] ? wanted : ["gemini", "openai", "anthropic"].find((p) => keys[p]);
  if (!provider) return null;
  const model = {
    gemini: env.GEMINI_MODEL || "gemini-2.5-flash-lite",
    openai: env.OPENAI_MODEL || "gpt-4o",
    anthropic: env.ANTHROPIC_MODEL || "claude-sonnet-5-5",
  }[provider];
  return { provider, model, key: keys[provider] };
}

const PERSONA = (
  "Você é J.A.R.V.I.S., o assistente pessoal do usuário: um mordomo digital competente, discreto e leal. "
  + "Fale sempre em português do Brasil, com tom formal e cordial. Trate o usuário por 'senhor', sem repetir em todas as frases. "
  + "Suas respostas são LIDAS EM VOZ ALTA: a resposta primeiro, em 1 a 3 frases curtas (só se alongue se pedirem detalhes), "
  + "sem listas, sem markdown e sem emojis. Humor seco e sutil é bem-vindo, no máximo uma tirada, nunca em assuntos sérios. "
  + "Neste momento o senhor está usando o JARVIS pelo MODO NUVEM: o notebook dele está desligado ou longe. "
  + "Aqui você consegue: lista de compras, tarefas, lembretes, alarmes, registro de água, notícias e clima. "
  + "Não consegue: câmera, Sentinela, abrir programas ou sites no PC, controlar o computador ou o Spotify do PC. "
  + "Se pedirem algo assim, diga em uma frase que isso precisa do notebook ligado. "
  + "Nunca diga que fez algo que não está nas suas ações. Use notícias e clima apenas quando vierem no contexto; nunca invente. "
  // V6.7: bem-estar (igual ao PC: services/llm_orchestrator.SYSTEM_PROMPT)
  + "Quando o usuário demonstrar cansaço, estresse, tristeza, ansiedade ou desabafar: acolha primeiro (nomeie o sentimento "
  + "e valide, sem minimizar), faça no máximo uma pergunta aberta e só depois, se fizer sentido, ofereça algo prático e "
  + "curto (respiração guiada, uma pausa, um primeiro passo, olhar o pensamento por outro ângulo). Deixe o humor de lado "
  + "nesses momentos. Nunca diagnostique nem rotule. Se o mal-estar parecer persistente, sugira com gentileza um psicólogo. "
  + "Se houver sinal de risco à vida, oriente a ligar para o CVV (188, 24 horas) ou o SAMU (192)."
);

const FORMAT = (
  "Responda SEMPRE com um único objeto JSON, sem texto fora dele, no formato: "
  + '{"resposta": "o que você fala", "acoes": [ ... ]}. '
  + "Ações possíveis (use só quando o senhor pedir; pode haver várias ou nenhuma): "
  + '{"tipo":"compras_add","itens":["leite","pão"]}, {"tipo":"compras_comprado","item":"leite"}, {"tipo":"compras_remover","item":"pão"}, '
  + '{"tipo":"compras_limpar"} (apaga os já comprados), '
  + '{"tipo":"tarefa_add","texto":"..."}, {"tipo":"tarefa_concluir","texto":"..."}, {"tipo":"tarefa_remover","texto":"..."}, '
  + '{"tipo":"lembrete_add","texto":"...","data_hora":"AAAA-MM-DD HH:MM"} (calcule a data a partir de agora), '
  + '{"tipo":"lembrete_remover","texto":"..."}, '
  + '{"tipo":"alarme_add","hora":"HH:MM","dias":[0,1,2,3,4],"rotulo":""} (dias: 0=segunda..6=domingo; vazio = uma vez), '
  + '{"tipo":"alarme_remover","hora":"HH:MM"}, '
  + '{"tipo":"agua_add","ml":250} (um copo = 250 ml, uma garrafa = 500 ml), {"tipo":"agua_desfazer"}, {"tipo":"agua_meta","ml":2500}, '
  + '{"tipo":"humor","nota":4} (quando o usuário disser como está de 1 a 5, ex.: "meu humor hoje é 4"), '
  + '{"tipo":"rota","destino":"trabalho ou um endereço","modo":"carro"|"a pe"|"onibus"|"bicicleta"} (abre o Google Maps com a rota saindo de onde ele está; use o nome do lugar salvo quando houver), '
  + '{"tipo":"lugar_salvar","nome":"trabalho","endereco":"Av. Paulista, 1000"} (quando ele disser onde fica um lugar), '
  + '{"tipo":"youtube","busca":"..."} (abre a pesquisa no YouTube), '
  + '{"tipo":"abrir","tela":"noticias"|"clima"|"compras"|"tarefas"|"agua"|"lembretes"}. '
  + "Na resposta, confirme a ação de forma natural ('Coloquei leite na lista, senhor.')."
);

// --------------------------------------------------------------------------- V6.8: sub-agentes (rotas e YouTube)
export function cleanPlaces(p) {
  if (!p || typeof p !== "object" || Array.isArray(p)) return {};
  const out = {};
  for (const [k, v] of Object.entries(p).slice(0, 30)) {
    const key = clean(norm(k), 40);
    const addr = clean(v, 160);
    if (key && addr) out[key] = addr;
  }
  return out;
}

async function allPlaces(store) {
  const perfil = (await store.get("perfil")) || {};
  return { ...(perfil.lugares || {}), ...((await store.get("lugares_nuvem")) || {}) };
}

const MODES = { carro: "driving", "a pe": "walking", ape: "walking", onibus: "transit", transporte: "transit", metro: "transit", bicicleta: "bicycling", bike: "bicycling" };

export async function routeUrl(store, destino, modo = "") {
  const places = await allPlaces(store);
  const key = norm(destino).replace(/^(?:o|a|meu|minha)\s+/, "");
  const address = places[key] || clean(destino, 160);
  const mode = MODES[norm(modo)] || "driving";
  return {
    url: `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(address)}&travelmode=${mode}`,
    rotulo: places[key] ? key : address,
  };
}

export function agendaText(agenda, now) {
  const items = (agenda || []).filter((e) => e.inicio.slice(0, 10) >= now.date);
  if (!items.length) return "Agenda dos próximos 7 dias: nada marcado (ou a agenda não está conectada no PC).";
  const fmt = (e) => {
    const day = e.inicio.slice(0, 10) === now.date ? "hoje" : `${e.inicio.slice(8, 10)}/${e.inicio.slice(5, 7)}`;
    const time = e.inicio.length > 10 ? ` às ${e.inicio.slice(11, 16)}` : " (dia todo)";
    return `${day}${time}: ${e.titulo}${e.local ? ` (${e.local})` : ""}`;
  };
  return `Agenda dos próximos 7 dias (a mais recente que o PC leu): ${items.map(fmt).join("; ")}.`;
}

function describeState(state, now, perfil) {
  const pending = state.compras.filter((i) => !i.comprado).map((i) => i.texto);
  const tasks = state.tarefas.filter((t) => !t.concluida).map((t) => t.texto);
  const rems = state.lembretes.filter((r) => !r.disparado).map((r) => `${r.texto} (${r.data_hora})`);
  const alarms = state.alarmes.map((a) => `${a.hora}${a.dias?.length ? ` dias ${a.dias.join(",")}` : ""}${a.rotulo ? ` ${a.rotulo}` : ""}`);
  const water = waterStatus(state.agua, now);
  const weekday = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"][now.weekday];
  return [
    `Agora: ${weekday}, ${now.date} ${now.time} (horário de Brasília).`,
    perfil?.nome ? `Nome do usuário: ${perfil.nome}.` : "",
    perfil?.sobre ? `O que ele contou sobre si: ${perfil.sobre}` : "",
    agendaText(perfil?.agenda, now),
    perfil?.lugares && Object.keys(perfil.lugares).length
      ? `Lugares salvos (para rotas): ${Object.entries(perfil.lugares).map(([k, v]) => `${k} = ${v}`).join("; ")}.` : "",
    perfil?.memorias?.length ? `Memórias do usuário (use com naturalidade quando ajudar, sem listar): ${perfil.memorias.join("; ")}.` : "",
    `Lista de compras (faltando): ${pending.join(", ") || "vazia"}.`,
    `Tarefas abertas: ${tasks.join("; ") || "nenhuma"}.`,
    `Lembretes: ${rems.join("; ") || "nenhum"}.`,
    `Alarmes: ${alarms.join("; ") || "nenhum"}.`,
    `Água hoje: ${water.total_ml} de ${water.goal_ml} ml.`,
  ].filter(Boolean).join("\n");
}

async function callLlm(fetchFn, cfg, system, history) {
  if (cfg.provider === "gemini") {
    const res = await fetchFn(`https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(cfg.model)}:generateContent`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-goog-api-key": cfg.key },
      body: JSON.stringify({
        systemInstruction: { parts: [{ text: system }] },
        contents: history.map((m) => ({ role: m.role === "user" ? "user" : "model", parts: [{ text: m.text }] })),
        generationConfig: { responseMimeType: "application/json", temperature: 0.6 },
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new HttpError(502, `A IA (Gemini) recusou: ${data.error?.message || res.status}`);
    return (data.candidates?.[0]?.content?.parts || []).map((p) => p.text || "").join("");
  }
  if (cfg.provider === "openai") {
    const res = await fetchFn("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${cfg.key}` },
      body: JSON.stringify({
        model: cfg.model,
        response_format: { type: "json_object" },
        messages: [{ role: "system", content: system }, ...history.map((m) => ({ role: m.role === "user" ? "user" : "assistant", content: m.text }))],
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new HttpError(502, `A IA (OpenAI) recusou: ${data.error?.message || res.status}`);
    return data.choices?.[0]?.message?.content || "";
  }
  const res = await fetchFn("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-api-key": cfg.key, "anthropic-version": "2023-06-01" },
    body: JSON.stringify({
      model: cfg.model,
      max_tokens: 1400, // V7.1: o holograma é um JSON maior que a conversa
      system,
      messages: history.map((m) => ({ role: m.role === "user" ? "user" : "assistant", content: m.text })),
    }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new HttpError(502, `A IA (Claude) recusou: ${data.error?.message || res.status}`);
  return (data.content || []).filter((b) => b.type === "text").map((b) => b.text).join("");
}

// --------------------------------------------------------------------------- V7.1: HOLOGRAMA
// A pesquisa vira uma tela viva: apresentação narrada (cenas) ou receita viva. Igual ao PC (backend/modules/holo.py).
const HOLO_KINDS = ["receita", "apresentacao"];
export const guessHoloKind = (q) => (/\breceitas?\b/i.test(q || "") ? "receita" : "apresentacao");

export function holoPrompt(query, kind) {
  const q = clean(query, 240);
  if (kind === "receita") {
    return `Monte uma RECEITA para a tela do JARVIS (assistente em português do Brasil). Pedido do usuário: "${q}".\n`
      + "Responda SOMENTE com um JSON compacto: "
      + '{"tipo": "receita", "titulo": "nome da receita", "wiki": "nome do prato como título de artigo da Wikipédia", '
      + '"fala": "1 frase curta apresentando a receita", "rende": "ex.: 8 fatias", "tempo": "ex.: 1h10", "dificuldade": "fácil|média|difícil", '
      + '"ingredientes": ["quantidade + ingrediente, curto"], "passos": [{"texto": "passo curto", "minutos": 0}], "dica": "1 dica de ouro"}. '
      + 'Até 12 ingredientes e 8 passos. Em "minutos", o tempo de espera do passo (forno, descanso) ou 0. Receita real e testada.';
  }
  return `Monte uma APRESENTAÇÃO curta e impressionante para a tela holográfica do JARVIS (português do Brasil), explicando: "${q}".\n`
    + "Responda SOMENTE com um JSON compacto: "
    + '{"tipo": "apresentacao", "titulo": "título curto", "wiki": "assunto como título de artigo da Wikipédia", '
    + '"cenas": [{"icone": "1 emoji", "titulo": "até 6 palavras", "fala": "1 ou 2 frases narradas, tom de documentário, tratando o usuário por senhor", '
    + '"pontos": ["até 3 tópicos curtos"], "numero": {"valor": 0, "unidade": "ex.: anos-luz", "rotulo": "o que significa"}}]}. '
    + 'De 4 a 6 cenas: gancho curioso, do simples ao surpreendente, fecha com uma curiosidade. "numero" só com dado real e marcante (senão null). Nada inventado.';
}

const holoNumber = (v) => {
  if (typeof v === "number") return Number.isFinite(v) ? v : null;
  if (typeof v !== "string" || !v.trim()) return null;
  const t = v.includes(",") || /^\s*-?\d{1,3}(\.\d{3})+\s*$/.test(v) ? v.replace(/\./g, "").replace(",", ".") : v; // "1.234,5" e "384.400"
  const n = Number(t.trim());
  return Number.isFinite(n) ? n : null;
};

export function parseHolo(raw, kind) {
  const m = String(raw || "").match(/\{[\s\S]*\}/);
  let data;
  try { data = m ? JSON.parse(m[0]) : null; } catch { data = null; }
  if (!data || typeof data !== "object") throw new HttpError(502, "A IA não devolveu a tela. Tente de novo, senhor.");
  const tipo = HOLO_KINDS.includes(data.tipo) ? data.tipo : kind;
  const base = { tipo, titulo: short(data.titulo, 80), wiki: short(data.wiki, 80) };
  if (!base.titulo) throw new HttpError(502, "A IA não devolveu a tela. Tente de novo, senhor.");
  const arr = (v) => (Array.isArray(v) ? v : []);
  if (tipo === "receita") {
    const passos = arr(data.passos).map((p) => (typeof p === "string" ? { texto: p } : p))
      .filter((p) => p && short(p.texto, 300))
      .map((p) => ({ texto: short(p.texto, 300), minutos: Math.round(Math.max(0, Math.min(holoNumber(p.minutos) || 0, 1440))) })).slice(0, 10);
    const ingredientes = arr(data.ingredientes).filter((i) => typeof i === "string" && i.trim()).map((i) => short(i, 90)).slice(0, 14);
    if (!passos.length || !ingredientes.length) throw new HttpError(502, "A receita veio sem passos. Tente de novo, senhor.");
    return { ...base, fala: short(data.fala, 300), rende: short(data.rende, 30), tempo: short(data.tempo, 30), dificuldade: short(data.dificuldade, 15), ingredientes, passos, dica: short(data.dica, 240) };
  }
  const cenas = arr(data.cenas).filter((c) => c && short(c.fala, 400)).map((c) => {
    const valor = c.numero && typeof c.numero === "object" ? holoNumber(c.numero.valor) : null;
    return {
      icone: short(c.icone, 8) || "✦",
      titulo: short(c.titulo, 70),
      fala: short(c.fala, 400),
      pontos: arr(c.pontos).filter((p) => typeof p === "string" && p.trim()).map((p) => short(p, 120)).slice(0, 3),
      numero: valor === null ? null : { valor, unidade: short(c.numero.unidade, 30), rotulo: short(c.numero.rotulo, 60) },
    };
  }).slice(0, 7);
  if (cenas.length < 2) throw new HttpError(502, "A apresentação veio vazia. Tente de novo, senhor.");
  return { ...base, cenas };
}

// --------------------------------------------------------------------------- V6.8.2: "o que é isso?" pela câmera
// V6.9: além da fala curta, um DIAGNÓSTICO do item (a tela da câmera mostra numa janela)
const VISION_PROMPT = (q) => "A imagem anexada é uma foto feita AGORA pela câmera do celular do usuário, a pedido dele. "
  + "Analise o item principal e responda à pergunta, como o J.A.R.V.I.S. Se for produto, planta, animal, prato, objeto, peça, "
  + "lugar ou texto, diga o que é e informações úteis. Se não der para ver direito, diga isso e peça para aproximar ou iluminar. "
  + "Não invente: sem certeza, diga e use confiança baixa. Não identifique pessoas pelo rosto. Não repita dados sensíveis visíveis.\n"
  + "Responda SOMENTE com um JSON, em português do Brasil: "
  + '{"fala": "1 a 3 frases curtas (vai ser falada)", "item": "nome do item", "categoria": "ex.: Planta, Eletrônico, Alimento", '
  + '"confianca": "alta|media|baixa", "resumo": "2 a 4 frases", "detalhes": [{"rotulo": "ex.: Marca, Modelo, Nome científico, Preço médio", "valor": "..."}], '
  + '"dicas": ["..."], "alertas": ["... (vazio se nada)"]}. No máximo 6 detalhes, 4 dicas e 3 alertas.\n'
  + `Pergunta do usuário: "${q}"`;

const short = (v, n) => String(v ?? "").replace(/\s+/g, " ").trim().slice(0, n);
const CONF = { alta: "alta", media: "media", "média": "media", baixa: "baixa" };

// Separa a fala e o diagnóstico; se a IA não mandou JSON, a resposta toda vira a fala (sem janela).
export function parseVision(raw) {
  const text = String(raw || "").trim();
  const m = text.match(/\{[\s\S]*\}/);
  let data = null;
  try { data = m ? JSON.parse(m[0]) : null; } catch { data = null; }
  if (!data || typeof data !== "object" || Array.isArray(data)) return { text, diagnostico: null };
  const fala = short(data.fala || data.resumo, 600);
  const item = short(data.item, 80);
  if (!item) return { text: fala || text, diagnostico: null };
  const list = (k, n) => (Array.isArray(data[k]) ? data[k] : []).filter((x) => typeof x === "string" && x.trim()).map((x) => short(x, 220)).slice(0, n);
  const diagnostico = {
    item,
    categoria: short(data.categoria, 40),
    confianca: CONF[short(data.confianca, 10).toLowerCase()] || "media",
    resumo: short(data.resumo, 700),
    detalhes: (Array.isArray(data.detalhes) ? data.detalhes : [])
      .filter((d) => d && short(d.rotulo, 40) && short(d.valor, 160))
      .map((d) => ({ rotulo: short(d.rotulo, 40), valor: short(d.valor, 160) })).slice(0, 6),
    dicas: list("dicas", 4),
    alertas: list("alertas", 3),
  };
  return { text: fala || diagnostico.resumo || item, diagnostico };
}

export function cleanImage(data) {
  const raw = String(data || "").trim().replace(/^data:image\/(?:jpeg|jpg|png|webp);base64,/, "");
  if (!raw || !/^[A-Za-z0-9+/=]+$/.test(raw)) throw new HttpError(400, "A foto chegou corrompida.");
  const blob = Buffer.from(raw, "base64");
  if (blob.length > 2_500_000) throw new HttpError(400, "A foto é grande demais.");
  const jpeg = blob[0] === 0xff && blob[1] === 0xd8 && blob[2] === 0xff;
  const png = blob.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]));
  if (!jpeg && !png) throw new HttpError(400, "Isso não parece uma foto.");
  return { data: raw, mime: jpeg ? "image/jpeg" : "image/png" };
}

export async function askVision(fetchFn, cfg, image, question) {
  const text = VISION_PROMPT(clean(question, 300) || "O que é isso?");
  if (cfg.provider === "gemini") {
    const res = await fetchFn(`https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(cfg.model)}:generateContent`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-goog-api-key": cfg.key },
      body: JSON.stringify({ contents: [{ role: "user", parts: [{ inlineData: { mimeType: image.mime, data: image.data } }, { text }] }] }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new HttpError(502, `A IA (Gemini) recusou: ${data.error?.message || res.status}`);
    return (data.candidates?.[0]?.content?.parts || []).map((p) => p.text || "").join("").trim();
  }
  if (cfg.provider === "openai") {
    const res = await fetchFn("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${cfg.key}` },
      body: JSON.stringify({ model: cfg.model, messages: [{ role: "user", content: [{ type: "text", text }, { type: "image_url", image_url: { url: `data:${image.mime};base64,${image.data}` } }] }] }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new HttpError(502, `A IA (OpenAI) recusou: ${data.error?.message || res.status}`);
    return (data.choices?.[0]?.message?.content || "").trim();
  }
  const res = await fetchFn("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-api-key": cfg.key, "anthropic-version": "2023-06-01" },
    body: JSON.stringify({ model: cfg.model, max_tokens: 900, messages: [{ role: "user", content: [{ type: "image", source: { type: "base64", media_type: image.mime, data: image.data } }, { type: "text", text }] }] }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new HttpError(502, `A IA (Claude) recusou: ${data.error?.message || res.status}`);
  return (data.content || []).filter((b) => b.type === "text").map((b) => b.text).join("").trim();
}

export function parseReply(raw) {
  const text = String(raw || "").trim();
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  if (start >= 0 && end > start) {
    try {
      const obj = JSON.parse(text.slice(start, end + 1));
      if (obj && typeof obj.resposta === "string") return { resposta: obj.resposta.trim(), acoes: Array.isArray(obj.acoes) ? obj.acoes : [] };
    } catch {
      // cai no texto puro
    }
  }
  return { resposta: text.replace(/[{}]/g, "").trim() || "Perdão, senhor, não consegui formular a resposta.", acoes: [] };
}

const ACTION_TO_OP = {
  compras_add: (a) => ({ op: "shopping_add", itens: Array.isArray(a.itens) ? a.itens : [a.item || a.texto].filter(Boolean) }),
  compras_comprado: (a) => ({ op: "shopping_set", texto: a.item || a.texto, comprado: true }),
  compras_remover: (a) => ({ op: "shopping_remove", texto: a.item || a.texto }),
  compras_limpar: () => ({ op: "shopping_clear" }),
  tarefa_add: (a) => ({ op: "task_add", texto: a.texto }),
  tarefa_concluir: (a) => ({ op: "task_done", texto: a.texto }),
  tarefa_remover: (a) => ({ op: "task_remove", texto: a.texto }),
  lembrete_add: (a) => ({ op: "reminder_add", texto: a.texto, data_hora: a.data_hora }),
  alarme_add: (a) => ({ op: "alarm_add", hora: a.hora, dias: a.dias || [], rotulo: a.rotulo || "" }),
  agua_add: (a) => ({ op: "water_add", ml: a.ml }),
  agua_desfazer: () => ({ op: "water_undo" }),
  agua_meta: (a) => ({ op: "water_goal", goal_ml: a.ml }),
  humor: (a) => ({ op: "mood_set", score: a.nota ?? a.score }),
  lugar_salvar: (a) => ({ op: "place_set", nome: a.nome, endereco: a.endereco }),
};

async function runAction(store, action, now) {
  const kind = action?.tipo;
  if (kind === "abrir") return { tipo: "abrir", tela: action.tela, ok: true };
  // V6.8: agentes de rotas e pesquisa: devolvem o link para o aparelho abrir
  if (kind === "rota") {
    const r = await routeUrl(store, action.destino || "", action.modo || "");
    return { tipo: "abrir_url", ok: true, url: r.url, agente: "rotas", rotulo: r.rotulo };
  }
  if (kind === "youtube") {
    const q = clean(action.busca, 100);
    if (!q) return { tipo: kind, ok: false, erro: "O que pesquisar?" };
    return { tipo: "abrir_url", ok: true, url: `https://www.youtube.com/results?search_query=${encodeURIComponent(q)}`, agente: "pesquisa", rotulo: q };
  }
  if (kind === "lugar_salvar") {
    try {
      const { result } = await change(store, { op: "place_set", nome: action.nome, endereco: action.endereco }, now);
      const extra = (await store.get("lugares_nuvem")) || {};
      extra[result.nome] = result.endereco;
      await store.set("lugares_nuvem", extra);
      return { tipo: kind, ok: true };
    } catch (err) {
      return { tipo: kind, ok: false, erro: err.message };
    }
  }
  // V6.7.4: música no próprio celular (o app executa; a nuvem só repassa)
  if (kind === "musica") {
    const comando = ["tocar", "pausar", "proxima", "anterior"].includes(action.comando) ? action.comando : "tocar";
    return { tipo: "musica", ok: true, comando, busca: clean(action.busca, 80) };
  }
  if (kind === "lembrete_remover") {
    const state = await loadState(store);
    const rem = findByText(state.lembretes.filter((r) => !r.disparado), "texto", action.texto);
    if (!rem) return { tipo: kind, ok: false, erro: "Lembrete não encontrado." };
    await change(store, { op: "reminder_remove", texto: rem.texto, data_hora: rem.data_hora }, now);
    return { tipo: kind, ok: true };
  }
  if (kind === "alarme_remover") {
    const state = await loadState(store);
    const alarm = state.alarmes.find((a) => a.hora === action.hora);
    if (!alarm) return { tipo: kind, ok: false, erro: "Alarme não encontrado." };
    await change(store, { op: "alarm_remove", hora: alarm.hora, rotulo: alarm.rotulo }, now);
    return { tipo: kind, ok: true };
  }
  const toOp = ACTION_TO_OP[kind];
  if (!toOp) return { tipo: kind, ok: false, erro: "Ação desconhecida." };
  try {
    await change(store, toOp(action), now);
    return { tipo: kind, ok: true };
  } catch (err) {
    return { tipo: kind, ok: false, erro: err.message };
  }
}

export async function chat({ store, env, fetchFn, message, now = spNow(), canMusic = false }) {
  const text = clean(message, 1200);
  if (!text) throw new HttpError(400, "Mensagem vazia.");
  // V6.7: bem-estar com respostas fixas (as mesmas do PC, modules/wellbeing.py). A de segurança vem antes de tudo.
  const fixed = wellbeingReply(text);
  if (fixed) {
    const history = ((await store.get("conversa")) || []).slice(-MAX_HISTORY);
    history.push({ role: "user", text, at: now.stamp }, { role: "assistant", text: fixed, at: now.stamp });
    await store.set("conversa", history.slice(-MAX_HISTORY));
    return { reply: fixed, actions: [] };
  }
  const cfg = llmConfig(env);
  if (!cfg) {
    return {
      reply: "Senhor, o modo nuvem ainda não tem a chave da IA. Coloque a GEMINI_API_KEY (ou OPENAI_API_KEY / ANTHROPIC_API_KEY) nas variáveis do site no Netlify.",
      actions: [],
    };
  }
  const state = await loadState(store);
  const perfil = (await store.get("perfil")) || {};
  const extra = [];
  const n = norm(text);
  if (/\b(noticia|noticias|manchete|manchetes|aconteceu|novidades)\b/.test(n)) {
    try {
      const news = await getNews(fetchFn, "");
      extra.push(`Manchetes de agora (Google Notícias): ${news.items.slice(0, 8).map((i) => `${i.title}${i.source ? ` (${i.source})` : ""}`).join(" | ")}`);
    } catch {
      extra.push("As notícias não carregaram agora.");
    }
  }
  if (/\b(clima|tempo|chuva|chover|temperatura|previsao|frio|calor|sol)\b/.test(n)) {
    try {
      const w = await getWeather(fetchFn, perfil.cidade || env.WEATHER_CITY || "São Paulo");
      extra.push(`Clima em ${w.place}: ${w.temperature}°C, ${w.description}, máx ${w.maximum}° mín ${w.minimum}°, chuva ${w.rain_probability ?? "?"}%. `
        + `Próximos dias: ${w.week.slice(1).map((d) => `${d.weekday} ${d.min}-${d.max}° ${d.description} chuva ${d.rain ?? "?"}%`).join("; ")}.`);
    } catch {
      extra.push("O clima não carregou agora.");
    }
  }
  const history = ((await store.get("conversa")) || []).slice(-MAX_HISTORY);
  history.push({ role: "user", text, at: now.stamp });
  const personality = PERSONALITY[perfil.prefs?.personality_mode] || "";
  const music = canMusic
    ? "Música: você controla o player do celular do usuário com a ação musica: "
      + '{"tipo":"musica","comando":"tocar"|"pausar"|"proxima"|"anterior","busca":"artista, música ou playlist (só ao pedir algo para tocar)"}. '
      + "Confirme em poucas palavras (\"Abrindo Coldplay no Spotify, senhor.\")."
    : "Música: aqui (navegador) você não controla o player; diga que pelo app do JARVIS no celular dá para pedir música.";
  const system = [PERSONA, personality, music, perfil.assistente && perfil.assistente !== "JARVIS" ? `Seu nome aqui é ${perfil.assistente}.` : "", FORMAT, "Contexto:", describeState(state, now, perfil), ...extra].filter(Boolean).join("\n\n");
  const parsed = parseReply(await callLlm(fetchFn, cfg, system, history.map(({ role, text: t }) => ({ role, text: t }))));
  const actions = [];
  for (const a of parsed.acoes.slice(0, 8)) actions.push(await runAction(store, a, now));
  history.push({ role: "assistant", text: parsed.resposta, at: now.stamp });
  await store.set("conversa", history.slice(-MAX_HISTORY));
  return { reply: parsed.resposta, actions };
}

// --------------------------------------------------------------------------- rotas HTTP
function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
  });
}

async function body(req) {
  try {
    return await req.json();
  } catch {
    return {};
  }
}

function clientIp(req) {
  return req.headers.get("x-nf-client-connection-ip") || req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "?";
}

export async function handle(req, { store, env, fetchFn = fetch, nowDate = new Date(), synth = null }) {
  const url = new URL(req.url);
  const path = url.pathname.replace(/^\/api\/cloud/, "").replace(/\/+$/, "") || "/";
  const method = req.method.toUpperCase();
  const now = spNow(nowDate);
  const secret = env.JARVIS_NUVEM_CHAVE || "";
  const pin = String(env.JARVIS_NUVEM_PIN || "");

  try {
    // ---- livre: estado do modo nuvem (para a tela saber se está configurado)
    if (path === "/status" && method === "GET") {
      const cfg = llmConfig(env);
      const perfil = (await store.get("perfil")) || {};
      return json({
        ok: true,
        configured: Boolean(secret && pin),
        llm: cfg ? cfg.provider : null,
        nome: perfil.nome || "",
        assistente: perfil.assistente || "JARVIS",
        sincronizado_em: perfil.atualizado_em || null,
        prefs: perfil.prefs || {},
        agora: now.stamp, // V6.6.6: para a tela saber se o PC sincronizou há pouco (ligado) ou não
      });
    }

    if (!secret || !pin) throw new HttpError(503, "O modo nuvem ainda não foi configurado no Netlify (JARVIS_NUVEM_PIN e JARVIS_NUVEM_CHAVE).");

    // ---- entrada pelo PIN
    if (path === "/login" && method === "POST") {
      const ip = clientIp(req);
      const fails = (await store.get("falhas")) || {};
      const nowMs = nowDate.getTime();
      for (const k of Object.keys(fails)) if (nowMs - fails[k].first > LOGIN_WINDOW_MS) delete fails[k];
      if ((fails[ip]?.count || 0) >= LOGIN_MAX_FAILS) throw new HttpError(429, "Muitas tentativas. Espere 15 minutos.");
      const { pin: typed } = await body(req);
      if (!sameText(String(typed || ""), pin)) {
        fails[ip] = { first: fails[ip]?.first || nowMs, count: (fails[ip]?.count || 0) + 1 };
        await store.set("falhas", fails);
        throw new HttpError(401, "PIN incorreto.");
      }
      if (fails[ip]) {
        delete fails[ip];
        await store.set("falhas", fails);
      }
      return json({ token: await makeToken(secret, nowMs), dias: TOKEN_DAYS });
    }

    // ---- sincronização com o PC (chave do PC, não o PIN)
    if (path.startsWith("/sync")) {
      if (!sameText(req.headers.get("x-jarvis-nuvem") || "", secret)) throw new HttpError(401, "Chave de sincronização inválida.");
      if (path === "/sync" && method === "GET") {
        const log = (await store.get("ops")) || { seq: 0, items: [] };
        return json({ ops: log.items, last_id: log.items.at(-1)?.id || 0 });
      }
      if (path === "/sync" && method === "POST") return json(await receiveSnapshot(store, await body(req), now));
      throw new HttpError(404, "Rota não encontrada.");
    }

    // ---- daqui para baixo: só com a chave do PIN
    const auth = req.headers.get("authorization")?.replace(/^Bearer\s+/i, "") || url.searchParams.get("token") || "";
    if (!(await checkToken(secret, auth, nowDate.getTime()))) throw new HttpError(401, "Entre com o PIN do modo nuvem.");

    if (path === "/state" && method === "GET") {
      await tick(store, now);
      const state = await loadState(store);
      return json({
        compras: [...state.compras].sort((a, b) => Number(a.comprado) - Number(b.comprado) || a.id - b.id),
        tarefas: state.tarefas,
        lembretes: state.lembretes.filter((r) => !r.disparado).sort((a, b) => a.data_hora.localeCompare(b.data_hora)),
        alarmes: [...state.alarmes].sort((a, b) => a.proximo.localeCompare(b.proximo)),
        agua: waterStatus(state.agua, now),
        conversa: ((await store.get("conversa")) || []).slice(-12),
        agenda: ((await store.get("perfil")) || {}).agenda || [],
        lugares: await allPlaces(store), // V6.8.3: Central de Agentes
        agora: now.stamp,
      });
    }
    if (path === "/notifications" && method === "GET") {
      await tick(store, now);
      const since = Number(url.searchParams.get("since") ?? -1);
      const feed = (await store.get("avisos")) || { seq: 0, items: [] };
      return json({ latest: feed.seq, items: since < 0 ? [] : feed.items.filter((i) => i.id > since) });
    }
    if (path === "/chat" && method === "POST") {
      const { message, pode_musica: canMusic } = await body(req);
      return json(await chat({ store, env, fetchFn, message, now, canMusic: Boolean(canMusic) }));
    }
    if (path === "/vision" && method === "POST") {
      const { image, question } = await body(req);
      const cfg = llmConfig(env);
      if (!cfg) throw new HttpError(503, "A nuvem ainda não tem a chave da IA.");
      const r = parseVision(await askVision(fetchFn, cfg, cleanImage(image), question));
      return json({ text: r.text || "Não consegui ver direito, senhor. Tente aproximar ou iluminar melhor.", diagnostico: r.diagnostico });
    }
    if (path === "/holo" && method === "POST") { // V7.1: HOLOGRAMA
      const { query, kind } = await body(req);
      const q = clean(query, 240);
      if (!q) throw new HttpError(400, "Diga o assunto.");
      const cfg = llmConfig(env);
      if (!cfg) throw new HttpError(503, "A nuvem ainda não tem a chave da IA.");
      const k = HOLO_KINDS.includes(kind) ? kind : guessHoloKind(q);
      return json(parseHolo(await callLlm(fetchFn, cfg, holoPrompt(q, k), [{ role: "user", text: q }]), k));
    }
    if (path === "/chat/clear" && method === "POST") {
      await store.set("conversa", []);
      return json({ ok: true });
    }
    if (path === "/change" && method === "POST") {
      const op = await body(req);
      const allowed = ["shopping_add", "shopping_set", "shopping_remove", "shopping_clear", "task_add", "task_done", "task_remove",
        "reminder_add", "reminder_remove", "alarm_add", "alarm_remove", "water_add", "water_undo", "water_goal", "mood_set", "place_set"];
      if (!allowed.includes(op.op)) throw new HttpError(400, "Operação desconhecida.");
      const { result } = await change(store, op, now);
      if (op.op === "place_set") { // V6.8.3: lugar salvo pela Central de Agentes fora de casa
        const extra = (await store.get("lugares_nuvem")) || {};
        extra[result.nome] = result.endereco;
        await store.set("lugares_nuvem", extra);
      }
      return json({ ok: true, result });
    }
    // V6.6.9: a mesma voz do PC (vozes neurais da Microsoft), em MP3
    if (path === "/tts" && method === "POST") {
      const { text } = await body(req);
      const clean = String(text || "").replace(/\s+/g, " ").trim().slice(0, 700);
      if (!clean) throw new HttpError(400, "Texto vazio.");
      if (!synth) throw new HttpError(503, "Voz indisponível.");
      const perfil = (await store.get("perfil")) || {};
      const voice = perfil.prefs?.voice || DEFAULT_VOICE;
      const audio = await synth(clean, voice);
      return new Response(audio, { status: 200, headers: { "Content-Type": "audio/mpeg", "Cache-Control": "no-store" } });
    }
    if (path === "/news" && method === "GET") return json(await getNews(fetchFn, url.searchParams.get("q") || ""));
    if (path === "/weather" && method === "GET") {
      const perfil = (await store.get("perfil")) || {};
      return json(await getWeather(fetchFn, url.searchParams.get("city") || perfil.cidade || env.WEATHER_CITY || "São Paulo"));
    }
    throw new HttpError(404, "Rota não encontrada.");
  } catch (err) {
    if (err instanceof HttpError) return json({ detail: err.message }, err.status);
    console.error("[nuvem]", err);
    return json({ detail: "Erro no modo nuvem. Tente de novo em instantes." }, 500);
  }
}

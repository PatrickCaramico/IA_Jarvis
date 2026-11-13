// V6.6.5: MODO NUVEM com a central de sempre.
// Com o notebook desligado, a central (mesmo layout do app e do site) continua rodando: este adaptador
// fica no lugar do backend do PC. As chamadas `${API_URL}/api/...` e o WebSocket `/ws` passam a ser
// respondidos pela nuvem (funções do Netlify, utils/cloudApi.js): conversa com a IA, compras, tarefas,
// lembretes, alarmes, água, notícias e clima. O que só existe no PC (câmera, Spotify, controle do
// Windows...) responde "precisa do notebook ligado".
import { API_URL, WS_URL, clientId } from "./api.js";
import { CLOUD_URL, change, cloud, cloudToken } from "./cloudApi.js";
import { APP_VERSION } from "./version.js";
import { pcLine } from "./cloudStatus.js";

const NEEDS_PC = "Isso precisa do notebook ligado, senhor. No modo nuvem eu cuido de conversa, listas, lembretes, alarmes, água, notícias e clima.";
const DAYS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];

let installed = false;
let status = {};
let state = null; // última foto das listas da nuvem
const sockets = new Set();

function emit(event) {
  for (const s of sockets) s._deliver(event);
}

// V6.6.9: a voz da nuvem é a MESMA do PC (vozes neurais da Microsoft, estilo escolhido em Ajustes):
// a nuvem gera o MP3 (/api/cloud/tts) e ele toca aqui. Sem internet ou com erro, cai na voz do aparelho.
let playing = null;

function stopVoice() {
  if (playing) {
    try {
      playing.pause();
    } catch {
      /* já parado */
    }
    playing = null;
  }
  try {
    window.speechSynthesis?.cancel();
  } catch {
    /* sem voz do navegador */
  }
}

async function cloudVoice(text) {
  const token = cloudToken();
  const res = await fetch(`${CLOUD_URL}/tts`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error(`voz ${res.status}`);
  const url = URL.createObjectURL(await res.blob());
  const audio = new Audio(url);
  playing = audio;
  await new Promise((resolve, reject) => {
    const done = () => {
      URL.revokeObjectURL(url);
      if (playing === audio) playing = null;
      resolve();
    };
    audio.addEventListener("ended", done, { once: true });
    audio.addEventListener("pause", done, { once: true });
    audio.addEventListener("error", () => reject(new Error("áudio")), { once: true });
    audio.play().catch(reject);
  });
}

function deviceVoice(clean, onEnd) {
  try {
    if (window.JarvisApp?.say) {
      window.JarvisApp.say(clean); // app Android: voz do Android
      setTimeout(() => onEnd?.(), Math.min(15000, 900 + clean.length * 65));
      return;
    }
  } catch {
    /* segue para a voz do navegador */
  }
  try {
    const synth = window.speechSynthesis;
    if (!synth) throw new Error("sem voz");
    synth.cancel();
    const u = new SpeechSynthesisUtterance(clean);
    u.lang = "pt-BR";
    const voice = synth.getVoices().find((v) => /pt[-_]BR/i.test(v.lang));
    if (voice) u.voice = voice;
    u.onend = () => onEnd?.();
    u.onerror = () => onEnd?.();
    synth.speak(u);
  } catch {
    onEnd?.();
  }
}

function speak(text, onEnd) {
  const clean = String(text || "").trim();
  if (!clean || status.prefs?.silent_mode) {
    onEnd?.();
    return;
  }
  stopVoice();
  cloudVoice(clean)
    .then(() => onEnd?.())
    .catch(() => deviceVoice(clean, onEnd));
}

async function refresh() {
  state = await cloud("/state");
  return state;
}

async function current() {
  return state || refresh();
}

function water(st) {
  const w = st.agua || {};
  return {
    reminder_interval_min: 120, start_hour: 8, end_hour: 22,
    ...w,
    last: (w.logs || []).at(-1) || null,
  };
}

async function broadcastLists() {
  const st = await refresh();
  emit({ type: "shopping", items: st.compras });
  emit({ type: "water_updated", data: water(st) });
}

function weather(w) {
  const week = (w.week || []).map((d, i) => {
    const [, m, day] = d.date.split("-");
    const wd = (new Date(`${d.date}T12:00:00Z`).getUTCDay() + 6) % 7;
    return {
      label: i === 0 ? "Hoje" : i === 1 ? "Amanhã" : `${DAYS[wd]} ${Number(day)}`,
      max: d.max, min: d.min, rain: d.rain, icon: d.icon, desc: d.description, date: `${day}/${m}`,
    };
  });
  const t = w.week?.[1];
  return {
    ...w,
    tomorrow: t ? { minimum: t.min, maximum: t.max, description: t.description, rain_probability: t.rain } : null,
    week,
  };
}

function agenda(st) {
  const today = (st.agora || "").slice(0, 10);
  const items = [
    // V6.7.4: compromissos da agenda que o PC mandou
    ...(st.agenda || []).map((e) => ({ at: e.inicio.replace("T", " ").slice(0, 16), title: e.titulo, kind: "agenda" })),
    ...st.lembretes.map((r) => ({ at: r.data_hora, title: r.texto, kind: "lembrete" })),
    ...st.alarmes.map((a) => ({ at: a.proximo, title: a.rotulo || `Alarme ${a.hora}`, kind: "alarme" })),
  ].filter((i) => i.at && i.at >= (st.agora || "")).sort((a, b) => a.at.localeCompare(b.at)).slice(0, 4);
  return items.map((i) => ({ ...i, label: `${i.at.startsWith(today) ? "Hoje" : i.at.slice(0, 10) > today ? "Amanhã" : i.at.slice(0, 10)} ${i.at.slice(11, 16)}` }));
}

const byId = (list, id) => list.find((i) => String(i.id) === String(id));

// V6.7.4: música no próprio celular (só o app Android sabe apertar os botões de mídia e abrir o Spotify)
function canMusic() {
  try {
    return typeof window.JarvisApp?.media === "function";
  } catch {
    return false;
  }
}

function playMusic(command, search = "") {
  if (!canMusic()) return false;
  try {
    if (command === "tocar" && search) return window.JarvisApp.openSpotify(search);
    const key = { tocar: "play", pausar: "pause", proxima: "next", anterior: "previous" }[command] || "toggle";
    return window.JarvisApp.media(key);
  } catch {
    return false;
  }
}

async function chat(message) {
  emit({ type: "state", state: "processing" });
  try {
    const res = await cloud("/chat", { method: "POST", body: { message, pode_musica: canMusic() }, timeout: 45000 });
    for (const a of res.actions || []) {
      if (a.tipo === "musica" && a.ok) playMusic(a.comando, a.busca);
      // V6.8: agentes de rotas e pesquisa: abre o Google Maps / YouTube neste aparelho
      if (a.tipo === "abrir_url" && a.ok && /^https:\/\//.test(a.url || "")) {
        const rotas = a.agente === "rotas";
        emit({ type: "agent", agent: a.agente, label: rotas ? "Agente de rotas" : "Agente de pesquisa", icon: rotas ? "🧭" : "🔎", text: rotas ? `rota para ${a.rotulo}` : `buscando “${a.rotulo}” no YouTube` });
        emit({ type: "open_url", url: a.url, client_id: clientId() });
      }
    }
    const reply = res.reply || "";
    emit({ type: "response", text: reply, cards: [] });
    emit({ type: "state", state: "speaking" });
    speak(reply, () => emit({ type: "state", state: "idle" }));
    if ((res.actions || []).some((a) => a.ok && a.tipo !== "abrir")) broadcastLists().catch(() => {});
    return { status: "ok", response: reply, cards: [], source: "cloud" };
  } catch (err) {
    emit({ type: "state", state: "idle" });
    throw err;
  }
}

/** Responde um pedido da central como o backend do PC responderia. */
async function route(method, path, query, body) {
  const ok = (data) => ({ status: 200, data });
  switch (`${method} ${path}`) {
    case "GET /api/health":
      return ok({ status: "ok", version: APP_VERSION, cloud: true });
    case "GET /api/profile":
      return ok({ name: status.nome || "", has_photo: true, cloud: true, access: { state: "unlocked", effective: "unlocked", enforced: false } });
    case "GET /api/profile/photo":
      return { status: 404, data: {} };
    case "GET /api/access":
    case "POST /api/access/lock":
      return ok({ state: "unlocked", effective: "unlocked", enforced: false });
    case "GET /api/auth/pin/status":
      return ok({ has_pin: false });
    case "GET /api/auth/token":
      return ok({ token: "" });
    case "GET /api/prefs":
    case "PATCH /api/prefs":
      return ok({ ai_name: status.assistente || "JARVIS", hands_free_enabled: true, lock_mic_on: true, ...(status.prefs || {}), cloud: true });
    case "GET /api/tasks": {
      const st = await current();
      return ok({ tasks: query.get("include_completed") === "true" ? st.tarefas : st.tarefas.filter((t) => !t.concluida) });
    }
    case "POST /api/tasks": {
      const res = await change({ op: "task_add", texto: body.texto });
      refresh().catch(() => {});
      return ok({ status: "ok", task: res.result });
    }
    case "GET /api/shopping":
      return ok({ items: (await refresh()).compras });
    case "POST /api/shopping": {
      await change({ op: "shopping_add", itens: String(body.texto || "").split(/,|\se\s/).map((s) => s.trim()).filter(Boolean) });
      const st = await refresh();
      emit({ type: "shopping", items: st.compras });
      return ok({ items: st.compras });
    }
    case "POST /api/shopping/clear": {
      await change({ op: "shopping_clear", tudo: query.get("all") === "true" });
      const st = await refresh();
      emit({ type: "shopping", items: st.compras });
      return ok({ items: st.compras });
    }
    case "GET /api/water":
      return ok(water(await refresh()));
    case "POST /api/water/add":
      await change({ op: "water_add", ml: body.ml });
      break;
    case "POST /api/water/undo":
      await change({ op: "water_undo" });
      break;
    case "POST /api/water/goal":
      await change({ op: "water_goal", goal_ml: body.goal_ml });
      break;
    case "GET /api/reminders":
      return ok({ reminders: (await refresh()).lembretes });
    case "POST /api/reminders": {
      const res = await change({ op: "reminder_add", texto: body.texto, data_hora: body.data_hora });
      return ok({ status: "ok", reminder: res.result });
    }
    case "GET /api/alarms":
      return ok({ alarms: (await refresh()).alarmes.map((a) => ({ ...a, descricao: `${a.hora}${a.rotulo ? ` · ${a.rotulo}` : ""}` })), ringing: null });
    case "GET /api/alarms/ringing":
      return ok({ ringing: false });
    case "GET /api/agenda/next":
      return ok({ items: agenda(await refresh()) });
    case "POST /api/camera/ask":
      // V6.8.2: "o que é isso?" pela câmera do celular, fora de casa
      return ok(await cloud("/vision", { method: "POST", body: { image: body.image, question: body.question }, timeout: 45000 }));
    case "POST /api/integrations/spotify/control": {
      // botões de música da central: no app, viram os botões de mídia do celular
      const map = { play: "tocar", resume: "tocar", pause: "pausar", next: "proxima", previous: "anterior", prev: "anterior" };
      if (playMusic(map[body.action] || "tocar")) return ok({ status: "ok" });
      return { status: 503, data: { detail: "No navegador eu não controlo a música. Pelo app do JARVIS no celular, dá." } };
    }
    case "GET /api/integrations/google-calendar/status": {
      const st = await refresh();
      return ok({ connected: (st.agenda || []).length > 0, cloud: true });
    }
    case "GET /api/integrations/google-calendar/events":
      return ok({ events: ((await refresh()).agenda || []).map((e, i) => ({ id: `nuvem-${i}`, title: e.titulo, start: e.inicio, location: e.local, link: "" })) });
    case "GET /api/weather":
      return ok(weather(await cloud(`/weather${query.get("city") ? `?city=${encodeURIComponent(query.get("city"))}` : ""}`)));
    case "GET /api/news":
      return ok({ category: query.get("category") || "", items: (await cloud(`/news?q=${encodeURIComponent(query.get("category") || "")}`)).items });
    case "GET /api/news/search":
      return ok({ query: query.get("q") || "", items: (await cloud(`/news?q=${encodeURIComponent(query.get("q") || "")}`)).items });
    case "GET /api/briefing/news-themes":
      return ok({ items: (status.prefs?.briefing_news_themes || []).map((t) => ({ title: t.title, query: t.q, count: 1 })) });
    case "POST /api/chat":
    case "POST /api/trigger-jarvis":
      return ok(await chat(body.message || ""));
    case "POST /api/chat/clear":
      await cloud("/chat/clear", { method: "POST" });
      emit({ type: "chat_cleared" });
      return ok({ ok: true });
    case "POST /api/speak":
    case "POST /api/speak/pc":
      speak(body.text);
      return ok({ ok: true });
    case "POST /api/cancel":
      stopVoice();
      emit({ type: "state", state: "idle" });
      return ok({ status: "canceled" });
    case "GET /api/devices":
      return ok({ items: [] });
    case "GET /api/notifications":
    case "GET /api/countdowns":
    case "GET /api/sites":
    case "GET /api/protocols":
    case "GET /api/profiles":
      return ok({ items: [], profiles: [] });
    default:
      break;
  }
  // rotas com id: /api/tasks/3/complete, /api/tasks/3, /api/shopping/2, /api/reminders/4, /api/alarms/1
  let m = path.match(/^\/api\/tasks\/(\d+)(\/complete)?$/);
  if (m) {
    const t = byId((await current()).tarefas, m[1]);
    if (!t) return { status: 404, data: { detail: "Tarefa não encontrada." } };
    await change(m[2] ? { op: "task_done", texto: t.texto } : { op: "task_remove", texto: t.texto });
    return ok({ status: "ok", task: t });
  }
  m = path.match(/^\/api\/shopping\/(\d+)$/);
  if (m) {
    const item = byId((await current()).compras, m[1]);
    if (!item) return { status: 404, data: { detail: "Item não encontrado." } };
    await change(method === "DELETE" ? { op: "shopping_remove", texto: item.texto } : { op: "shopping_set", texto: item.texto, comprado: body.comprado !== false });
    const st = await refresh();
    emit({ type: "shopping", items: st.compras });
    return ok({ items: st.compras });
  }
  m = path.match(/^\/api\/reminders\/(\d+)$/);
  if (m && method === "DELETE") {
    const r = byId((await current()).lembretes, m[1]);
    if (r) await change({ op: "reminder_remove", texto: r.texto, data_hora: r.data_hora });
    return ok({ status: "ok" });
  }
  m = path.match(/^\/api\/alarms\/(\d+)$/);
  if (m && method === "DELETE") {
    const a = byId((await current()).alarmes, m[1]);
    if (a) await change({ op: "alarm_remove", hora: a.hora, rotulo: a.rotulo });
    return ok({ status: "ok" });
  }
  if (path.startsWith("/api/water")) {
    const st = await refresh();
    emit({ type: "water_updated", data: water(st) });
    return ok(water(st));
  }
  // o resto: leitura vazia (o painel some ou fica em espera) e ação = "precisa do notebook"
  if (method === "GET") return ok({});
  return { status: 503, data: { detail: NEEDS_PC, cloud: true } };
}

class CloudSocket {
  constructor(url) {
    this.url = url;
    this.readyState = 0;
    sockets.add(this);
    setTimeout(() => {
      if (this.readyState !== 0) return;
      this.readyState = 1;
      this.onopen?.({});
      this._deliver({ type: "state", state: "idle" });
    }, 30);
  }

  _deliver(event) {
    if (this.readyState !== 1) return;
    setTimeout(() => this.onmessage?.({ data: JSON.stringify(event) }), 0);
  }

  send(data) {
    if (data === "ping") setTimeout(() => this.onmessage?.({ data: "pong" }), 20);
  }

  close() {
    if (this.readyState === 3) return;
    this.readyState = 3;
    sockets.delete(this);
    this.onclose?.({});
  }

  addEventListener() {}

  removeEventListener() {}
}

/** Liga o adaptador (uma vez). `info` = /api/cloud/status (nome, assistente, prefs). */
export function installCloudShim(info) {
  status = info || {};
  if (installed) return;
  installed = true;
  window.__JARVIS_CLOUD__ = true;
  window.__JARVIS_CLOUD_SPEAK__ = (text) => speak(text);
  try {
    localStorage.setItem("jarvis.onboarding.done", "1"); // quem usa a nuvem já conhece o JARVIS
  } catch {
    /* sem armazenamento */
  }
  document.documentElement.dataset.cloud = "1";
  // aviso discreto no topo: a central é a de sempre, mas o acesso é pela nuvem (fora de casa ou PC desligado)
  try {
    const pill = document.createElement("div");
    pill.className = "cloud-pill";
    pill.setAttribute("role", "status");
    document.body.appendChild(pill);
    const paint = (st) => {
      pill.textContent = `☁ ACESSO PELA NUVEM · ${pcLine(st)}`;
    };
    paint(status);
    setInterval(() => cloud("/status").then(paint).catch(() => {}), 60000);
  } catch {
    /* sem DOM: segue sem o aviso */
  }
  const realFetch = window.fetch.bind(window);
  window.fetch = async (input, init = {}) => {
    const url = typeof input === "string" ? input : input.url;
    if (!url.startsWith(API_URL)) return realFetch(input, init);
    const u = new URL(url);
    const method = (init.method || "GET").toUpperCase();
    let body = {};
    try {
      body = init.body ? JSON.parse(init.body) : {};
    } catch {
      body = {};
    }
    let res;
    try {
      res = await route(method, u.pathname.replace(/\/+$/, ""), u.searchParams, body);
    } catch (err) {
      res = { status: err.status || 502, data: { detail: err.message || "Falha no modo nuvem." } };
    }
    return new window.Response(JSON.stringify(res.data ?? {}), { status: res.status, headers: { "Content-Type": "application/json" } });
  };
  const RealSocket = window.WebSocket;
  const wsBase = WS_URL.split("?")[0];
  function ShimSocket(url, protocols) {
    if (String(url).startsWith(wsBase)) return new CloudSocket(url);
    return new RealSocket(url, protocols);
  }
  ShimSocket.CONNECTING = 0;
  ShimSocket.OPEN = 1;
  ShimSocket.CLOSING = 2;
  ShimSocket.CLOSED = 3;
  window.WebSocket = ShimSocket;
  // avisos da nuvem (lembrete, alarme, água) com a central aberta
  let since = null;
  const poll = async () => {
    try {
      const feed = await cloud(`/notifications?since=${since ?? -1}`);
      if (since !== null) {
        for (const n of feed.items) {
          emit({ type: "alert", text: `${n.title}: ${n.body}` });
          speak(`${n.title}. ${n.body}`);
        }
      }
      since = feed.latest;
    } catch {
      /* tenta de novo no próximo ciclo */
    }
  };
  poll();
  setInterval(poll, 20000);
}

export function cloudShimActive() {
  return installed;
}

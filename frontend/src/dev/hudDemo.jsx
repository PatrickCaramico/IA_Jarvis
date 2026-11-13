// Demo da central (só dev, ver hud-demo.html): abre a tela principal sem backend, com respostas de mentira.
// ?offline=1 mostra a tela de "PC desligado"; ?new=1 finge que é a 1ª vez neste navegador.
const q = new URLSearchParams(window.location.search);
const offline = q.get("offline") === "1";
if (q.get("phone") === "1") window.__JARVIS_DEMO_PHONE__ = true; // mostra a barra do celular
// ?app=1: finge ser o app Android (user agent e uma ponte JarvisApp de mentira, com digital)
if (q.get("app") === "1") {
  window.__JARVIS_DEMO_PHONE__ = true;
  const ua = navigator.userAgent + " JarvisApp/6.0.0";
  Object.defineProperty(navigator, "userAgent", { get: () => ua });
  let bio = false;
  window.JarvisApp = {
    version: () => "6.0.0",
    notificationsEnabled: () => true,
    setNotifications: () => {},
    canUseBiometric: () => true,
    hasBiometric: () => bio,
    saveDeviceSecret: () => { bio = true; window.dispatchEvent(new CustomEvent("jarvis-app-biometric", { detail: { action: "saved", message: "Digital ativada. Na próxima vez, é só encostar o dedo." } })); },
    biometricUnlock: () => window.dispatchEvent(new CustomEvent("jarvis-app-biometric", { detail: { action: "unlock", secret: "demo" } })),
    forgetBiometric: () => { bio = false; },
  };
}

try {
  if (q.get("new") === "1") localStorage.removeItem("jarvis.lastLogin");
  else localStorage.setItem("jarvis.lastLogin", String(Date.now() - 60_000));
  localStorage.setItem("jarvis.onboarding.done", "1");
} catch {
  /* sem armazenamento */
}

const DATA = {
  "/api/profile": { name: "Patrick", has_photo: true, access: { state: "unlocked", effective: "unlocked", enforced: true } },
  "/api/auth/token": { token: "demo" },
  "/api/auth/pin/status": { has_pin: true },
  "/api/prefs": { ai_name: "J.A.R.V.I.S.", active_widgets: ["status", "about"], silent_mode: true, hands_free_enabled: false },
  "/api/access": { state: "unlocked", effective: "unlocked", enforced: true },
  "/api/tasks": { tasks: [] },
  "/api/notifications": { items: [] },
  "/api/health": { status: "ok" },
  // V6.7.2: bolinha de atualização no ⟳ ATUALIZAR
  "/api/system/update/status": { available: true, count: 1, current: "6.7.1", latest: "6.7.2", notes: ["JARVIS 6.7.2: bolinha de atualização"] },
  // V6.5.15: tela de espera (Área Limpa)
  "/api/weather": { place: "São Paulo", temperature: 21, description: "parcialmente nublado", maximum: 26, minimum: 17, rain_probability: 100, icon: "⛅",
    week: [["Hoje", 26, 17, "⛅"], ["Amanhã", 25, 18, "🌧"], ["Sáb 14", 27, 18, "⛅"], ["Dom 15", 28, 16, "🌦"], ["Seg 16", 26, 19, "☀"], ["Ter 17", 28, 18, "☀"]]
      .map(([label, max, min, icon]) => ({ label, max, min, icon, rain: 40 })) },
  "/api/agenda/next": { items: [
    { label: "Hoje 21:00", title: "Ligar para a mãe", kind: "lembrete" },
    { label: "Amanhã 09:30", title: "Reunião de planejamento", kind: "agenda" },
  ] },
  "/api/water": { total_ml: 1250, goal_ml: 2500, percentage: 50 },
  "/api/lock/status": { devices: 2, phones: 1, next_alarm: "amanhã às 07:00" },
  "/api/briefing/news-themes": { items: [
    { title: "Tecnologia", query: "tecnologia", count: 1 },
    { title: "Marvel", query: "Marvel", count: 3 },
    { title: "Política", query: "política Brasil", count: 1 },
  ] },
  "/api/news/search": { items: [
    { title: "Marvel confirma data do próximo filme dos Vingadores - Omelete", source: "Omelete", link: "#", published: new Date(Date.now() - 25 * 60000).toISOString() },
    { title: "Nova série da Marvel ganha trailer com cenas inéditas - G1", source: "G1", link: "#", published: new Date(Date.now() - 3 * 3600000).toISOString() },
    { title: "Bilheteria: filme do Quarteto Fantástico passa de US$ 500 milhões", source: "Terra", link: "#", published: new Date(Date.now() - 26 * 3600000).toISOString() },
  ] },
  "/api/shopping": { items: [
    { id: 1, texto: "Leite", comprado: false }, { id: 2, texto: "Pão", comprado: false }, { id: 3, texto: "Café", comprado: true },
  ] },
  "/api/countdowns": { items: [
    { id: 1, title: "Viagem a Maceió", target: new Date(Date.now() + (3 * 86400 + 4 * 3600 + 125) * 1000).toISOString().slice(0, 19), all_day: false },
  ] },
};

const realFetch = window.fetch.bind(window);
window.fetch = async (input, init) => {
  const url = typeof input === "string" ? input : input.url;
  const u = new URL(url, window.location.href);
  if (!u.pathname.startsWith("/api/") || u.origin === window.location.origin) return realFetch(input, init);
  if (offline) throw new TypeError("Failed to fetch");
  const body = DATA[u.pathname] ?? {};
  return new window.Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
};

class DemoSocket {
  constructor() {
    this.readyState = 0;
    setTimeout(() => {
      if (offline) {
        this.readyState = 3;
        this.onclose?.();
        return;
      }
      this.readyState = 1;
      this.onopen?.();
      // Aparelhos conectados e uma resposta de exemplo (para ver o 🔊 e a lista no painel)
      const send = (ev) => this.onmessage?.({ data: JSON.stringify(ev) });
      setTimeout(() => send({ type: "devices", items: [
        { kind: "pc", name: "Este PC", ip: "127.0.0.1", since: 1 },
        { kind: "app", name: "Celular · SM-A546E", ip: "192.168.1.58", since: 2 },
      ] }), 300);
      setTimeout(() => send({ type: "response", text: "Em Maragogi, 27 graus e sol. Vale levar protetor solar hoje.", cards: [] }), 900);
    }, 200);
  }
  send(data) {
    if (data === "ping") setTimeout(() => this.onmessage?.({ data: "pong" }), 50);
  }
  close() {
    this.readyState = 3;
    this.onclose?.();
  }
}
window.WebSocket = DemoSocket;

await import("../main.jsx");

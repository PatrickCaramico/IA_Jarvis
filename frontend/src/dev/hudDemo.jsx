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
  "/api/camera/ask": { text: "É uma caneca azul, senhor." }, // V6.8.2
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
  // V8.12.2: tela de atualização (a demo sem ?upd=0 atualiza ao abrir e fica nela)
  "/api/system/update": { status: "restarting", changed: true, before: "b9bc3ee", after: "3c39a40", boot_id: "demo",
    versao_nova: "8.12.2", destaques: ["🔓 Atualizar sem pedir o rosto de novo", "🎵 Spotify na central também pelo site", "✨ Tela de atualização melhor"] },
  "/api/system/update/progress": { etapa: "interface", detalhe: "Baixando a interface pronta…", versao_nova: "8.12.2" },
  "/api/integrations/spotify/track": { state: "idle" }, // V8.12: o cartão do Spotify fica mesmo sem música
  "/api/system": { cpu_percent: 23, ram_percent: 74, disk_free_gb: 412.6, processes: 231 }, // V8.11.1: telemetria do centro
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
  // V8.14: holograma pesquisado (com fontes) para ver a tela sem IA
  "/api/holo": { tipo: "apresentacao", titulo: "Buracos negros", wiki: "", pesquisado: true,
    fontes: [{ titulo: "NASA — Black Holes", url: "https://science.nasa.gov/universe/black-holes/" },
      { titulo: "ESO — Event Horizon Telescope", url: "https://www.eso.org/public/brazil/news/eso1907/" }],
    cenas: [
      { icone: "🌌", titulo: "Onde a luz não escapa", fala: "Senhor, um buraco negro é uma região onde a gravidade é tão forte que nem a luz consegue sair.", pontos: ["Gravidade extrema", "Horizonte de eventos", "Nada volta"], numero: null, visual: null, foto: "" },
      { icone: "📸", titulo: "A primeira foto", fala: "Em 2019, o telescópio Event Horizon mostrou a primeira imagem de um buraco negro, na galáxia M87.", pontos: ["M87*", "55 milhões de anos-luz"], numero: { valor: 6.5, unidade: "bilhões de sóis", rotulo: "massa do M87*" }, visual: null, foto: "" },
      { icone: "⏳", titulo: "Eles evaporam", fala: "Stephen Hawking previu que eles perdem massa devagar, pela radiação que leva o seu nome.", pontos: ["Radiação Hawking"], numero: null, visual: null, foto: "" },
    ] },
  // V8.12.5: XP e missões do dia na central
  "/api/desk/xp": { nivel: 2, xp: 234, no_nivel: 134, para_subir: 200, pct: 67 },
  "/api/desk/missions": { dia: "2026-11-23", feitas: 1, total: 3, novos: [], cloud: false,
    itens: [
      { id: "m1", tipo: "uso", texto: "Pergunte o clima ao JARVIS", xp: 15, meta: 1, progresso: 1, feita: true },
      { id: "m2", tipo: "bem", texto: "Beba 2 copos d'água antes do almoço", xp: 20, meta: 1, progresso: 0, feita: false },
      { id: "m3", tipo: "sobre", texto: "Qual é a sua comida favorita?", xp: 25, meta: 1, progresso: 0, feita: false },
    ],
    semana: { id: "w1", tipo: "semana", texto: "Converse com o JARVIS em 5 dias da semana", xp: 100, meta: 5, progresso: 2, feita: false },
    ofensiva: { atual: 3, recorde: 7, protetores: 1, max_protetores: 2, feita_hoje: true } },
  // V9.0: paleta Ctrl+K (habilidades e memória)
  "/api/skills": { items: [
    { name: "workspace_layout", title: "organizar janelas", module: "skills.workspace", enabled: true, examples: ["organiza as janelas lado a lado"] },
    { name: "copiados", title: "usar os copiados", module: "skills.copiados", enabled: true, examples: ["o que eu copiei?", "copia de novo o último link"] },
    { name: "tempo_de_tela", title: "tempo de tela", module: "skills.tempo_de_tela", enabled: true, examples: ["quanto tempo eu fiquei no PC hoje?"] },
    { name: "ler_texto_da_tela", title: "ler o texto da tela", module: "skills.ocr_tela", enabled: true, examples: ["copia o texto da tela"] },
    { name: "sessao_navegador", title: "usar as sessões do navegador", module: "skills.navegador", enabled: true, examples: ["abre a sessão trabalho"] },
  ] },
  "/api/search/local": { items: [
    { kind: "conversa", label: "Conversa", title: "viagem", snippet: "Você: a [viagem] para Maceió é dia 12 …", at: "2026-11-18T09:12:00" },
    { kind: "copiado", label: "Copiado", title: "Hotel Ponta Verde, Rua das Acácias, 123", snippet: "Hotel Ponta Verde, Rua das Acácias…", at: "20/11/2026 14:02" },
  ] },
  "/api/countdowns": { items: [
    { id: 1, title: "Viagem a Maceió", target: new Date(Date.now() + (3 * 86400 + 4 * 3600 + 125) * 1000).toISOString().slice(0, 19), all_day: false },
  ] },
};

// V9.1: ?music=1 = Spotify conectado e tocando (janela de vidro do Spotify)
if (q.get("music") === "1") {
  DATA["/api/integrations/spotify/status"] = { configured: true, connected: true };
  DATA["/api/integrations/spotify/track"] = { state: "playing", title: "Weightless", artist: "Marconi Union",
    image: "/brand/avatar-512.png", progress_ms: 95000, duration_ms: 480000 };
  DATA["/api/integrations/spotify/volume"] = { percent: 45, saved: 45, live: true };
}

// ?upd=0: sem atualização pendente (com ela, a atualização ao abrir roda e a demo para no bloqueio)
if (q.get("upd") === "0") DATA["/api/system/update/status"] = { available: false, count: 0 };

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
      // V8.13: ?stream=1 mostra uma resposta chegando em pedaços (streaming), parada no meio
      if (q.get("stream") === "1") {
        const full = "Back in Black saiu em 1980 e virou a trilha do Homem de Ferro em 2008, senhor. O riff de abertura";
        setTimeout(() => send({ type: "state", state: "processing" }), 1200);
        full.split(" ").forEach((_, i, words) => setTimeout(() => send({ type: "response_stream", seq: i + 1, text: words.slice(0, i + 1).join(" ") }), 1400 + i * 60));
      }
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

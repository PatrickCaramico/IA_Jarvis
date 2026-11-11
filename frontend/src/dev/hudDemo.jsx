// Demo da central (só dev, ver hud-demo.html): abre a tela principal sem backend, com respostas de mentira.
// ?offline=1 mostra a tela de "PC desligado"; ?new=1 finge que é a 1ª vez neste navegador.
const q = new URLSearchParams(window.location.search);
const offline = q.get("offline") === "1";

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

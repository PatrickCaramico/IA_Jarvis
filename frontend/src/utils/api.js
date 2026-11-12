// Cliente do backend (refatoração 4.2): endereço, token de acesso e chamadas JSON em um só lugar.

export const API_URL = import.meta.env.VITE_API_URL
  ?? `${window.location.protocol}//${window.location.hostname}:8000`;
export const WS_URL = API_URL.replace(/^http/, "ws") + "/ws";

// O backend roda nesta mesma máquina? (central aberta em localhost ou pelo site, falando com 127.0.0.1)
export const BACKEND_ON_THIS_PC = ["localhost", "127.0.0.1", "[::1]", "::1"].includes(new URL(API_URL).hostname)
  && !(typeof window !== "undefined" && window.__JARVIS_DEMO_PHONE__); // só a demo (hud-demo.html?phone=1) finge ser celular

// Arquivos de public/ (escudos, sons): respeitam a pasta onde a central foi publicada (/ no PC, /app/ no site).
export const publicUrl = (path) =>
  typeof path === "string" && path.startsWith("/") && !path.startsWith("//")
    ? import.meta.env.BASE_URL.replace(/\/$/, "") + path
    : path;

function getStoredToken() {
  if (typeof window === "undefined") return "";
  const params = new URLSearchParams(window.location.search);
  const urlToken = params.get("token");
  if (urlToken) {
    sessionStorage.setItem("jarvis_token", urlToken);
    params.delete("token");
    const cleanSearch = params.toString() ? `?${params.toString()}` : "";
    window.history.replaceState({}, "", `${window.location.pathname}${cleanSearch}${window.location.hash}`);
    return urlToken;
  }
  return sessionStorage.getItem("jarvis_token") || "";
}

let currentJarvisToken = getStoredToken();

// V5.7: identidade desta aba/aparelho. O PC manda a voz da resposta para quem pediu (celular) em vez
// de tocar na caixa de som dele. Fora do PC, a preferência "voz neste aparelho" decide (padrão: sim).
const CLIENT_KEY = "jarvis.client_id";
export function clientId() {
  try {
    let id = sessionStorage.getItem(CLIENT_KEY);
    if (!id) {
      id = `c${Math.random().toString(36).slice(2, 10)}${Date.now().toString(36)}`;
      sessionStorage.setItem(CLIENT_KEY, id);
    }
    return id;
  } catch {
    return "csemarmazenamento";
  }
}
const VOICE_KEY = "jarvis.voice.here";
export function voiceHere() {
  if (BACKEND_ON_THIS_PC) return false; // no próprio PC a voz já sai na caixa dele
  try {
    return localStorage.getItem(VOICE_KEY) !== "0";
  } catch {
    return true;
  }
}
export function setVoiceHere(on) {
  try {
    localStorage.setItem(VOICE_KEY, on ? "1" : "0");
  } catch {
    /* sem armazenamento: vale só agora */
  }
}
function voiceHeaders() {
  return { "X-Jarvis-Client": clientId(), "X-Jarvis-Device": BACKEND_ON_THIS_PC ? "web" : voiceHere() ? "app" : "pc" };
}

export function getJarvisToken() {
  return currentJarvisToken || sessionStorage.getItem("jarvis_token") || "";
}

export function hasMemoryToken() {
  return Boolean(currentJarvisToken);
}

export function setJarvisToken(token) {
  currentJarvisToken = token;
  sessionStorage.setItem("jarvis_token", token);
}

// Chamada JSON ao backend, com mensagens de erro em português.
// options.timeout (ms, V5.2): desiste se o backend não responder a tempo (conta como desligado, sem status).
export async function api(path, { timeout, ...options } = {}) {
  let res;
  const token = getJarvisToken();
  const headers = {
    ...voiceHeaders(),
    ...(options.headers || {}),
  };
  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  if (token) {
    headers["X-Jarvis-Token"] = token;
  }

  const ctrl = timeout ? new AbortController() : null;
  const timer = ctrl ? setTimeout(() => ctrl.abort(), timeout) : null;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...options,
      headers,
      ...(ctrl ? { signal: ctrl.signal } : {}),
    });
  } catch {
    throw new Error(`Não consegui falar com o backend em ${API_URL}. Ele está rodando?`);
  } finally {
    if (timer) clearTimeout(timer);
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    // Bloqueio real (seção 17 / Sentinela): o backend recusou por estar bloqueado ou em modo visitante
    if (res.status === 403 && (data.code === "locked" || data.code === "guest")) {
      window.dispatchEvent(new CustomEvent("jarvis_access_denied", { detail: data }));
    }
    const error = new Error(typeof data.detail === "string" ? data.detail : `Erro ${res.status}`);
    error.status = res.status;
    error.code = data.code;
    throw error;
  }
  return data;
}

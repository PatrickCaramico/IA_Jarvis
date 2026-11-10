// Cliente do backend (refatoração 4.2): endereço, token de acesso e chamadas JSON em um só lugar.

export const API_URL = import.meta.env.VITE_API_URL
  ?? `${window.location.protocol}//${window.location.hostname}:8000`;
export const WS_URL = API_URL.replace(/^http/, "ws") + "/ws";

// O backend roda nesta mesma máquina? (central aberta em localhost ou pelo site, falando com 127.0.0.1)
export const BACKEND_ON_THIS_PC = ["localhost", "127.0.0.1", "[::1]", "::1"].includes(new URL(API_URL).hostname);

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
export async function api(path, options = {}) {
  let res;
  const token = getJarvisToken();
  const headers = {
    ...(options.headers || {}),
  };
  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  if (token) {
    headers["X-Jarvis-Token"] = token;
  }

  try {
    res = await fetch(`${API_URL}${path}`, {
      ...options,
      headers,
    });
  } catch {
    throw new Error(`Não consegui falar com o backend em ${API_URL}. Ele está rodando?`);
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

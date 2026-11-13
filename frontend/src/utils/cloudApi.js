// V6.6: cliente do MODO NUVEM (funções do Netlify em /api/cloud). Funciona com o notebook desligado.
// A chave vem do PIN do modo nuvem e fica guardada neste aparelho (60 dias).
// V6.6.3: só no CELULAR (Chrome do celular e app Android). No computador, sempre o site normal (PC).
import { IS_JARVIS_APP } from "./device.js";

const TOKEN_KEY = "jarvis.cloud.token";
const SITE = "https://projeto-jarvis-ia.netlify.app";

export const CLOUD_URL = typeof window !== "undefined" && /\.netlify\.app$/i.test(window.location.hostname)
  ? "/api/cloud"
  : `${import.meta.env.VITE_CLOUD_URL || SITE}/api/cloud`;

export function cloudToken() {
  try {
    return localStorage.getItem(TOKEN_KEY) || "";
  } catch {
    return "";
  }
}

export function setCloudToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* sem armazenamento: vale só nesta aba */
  }
  // o app Android usa a chave para buscar os avisos (lembretes e alarmes) com o app fechado
  try {
    window.JarvisApp?.setCloudToken?.(token || "");
  } catch {
    /* fora do app */
  }
}

/** O endereço pede o modo nuvem (?nuvem=1, usado pelo app quando o PC não responde)? Só no celular. */
export function cloudRequested() {
  if (typeof window === "undefined" || !isPhone()) return false;
  return new URLSearchParams(window.location.search).get("nuvem") === "1";
}

/** Celular (Chrome do celular ou app Android): com o PC desligado, entra direto no modo nuvem. */
export function isPhone() {
  if (typeof navigator === "undefined") return false;
  return IS_JARVIS_APP || /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent);
}

/** O modo nuvem existe aqui? Só no celular; no computador, a central é sempre a do PC. */
export const CLOUD_AVAILABLE = isPhone();

export async function cloud(path, { method = "GET", body, timeout = 25000 } = {}) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeout);
  const token = cloudToken();
  let res;
  try {
    res = await fetch(`${CLOUD_URL}${path}`, {
      method,
      headers: {
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: ctrl.signal,
      cache: "no-store",
    });
  } catch {
    throw Object.assign(new Error("Sem internet agora. Tento de novo em instantes."), { status: 0 });
  } finally {
    clearTimeout(timer);
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401 && path !== "/login") setCloudToken("");
    throw Object.assign(new Error(data.detail || `Erro ${res.status}`), { status: res.status });
  }
  return data;
}

export const change = (op) => cloud("/change", { method: "POST", body: op });

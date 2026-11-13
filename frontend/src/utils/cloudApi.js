// V6.6: cliente do MODO NUVEM (funções do Netlify em /api/cloud). Funciona com o notebook desligado.
// A chave vem do PIN do modo nuvem e fica guardada neste aparelho (60 dias).
// V6.6.2: só no NAVEGADOR (celular ou computador). O app Android fala só com o PC, como antes.
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
}

/** O endereço pede o modo nuvem (?nuvem=1, usado pelo app quando o PC não responde)? */
export function cloudRequested() {
  if (typeof window === "undefined" || IS_JARVIS_APP) return false;
  return new URLSearchParams(window.location.search).get("nuvem") === "1";
}

/** Navegador do celular: com o PC desligado, entra direto no modo nuvem (o app nunca usa a nuvem). */
export function isPhone() {
  if (typeof navigator === "undefined" || IS_JARVIS_APP) return false;
  return /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent);
}

/** O modo nuvem está disponível aqui? (navegador sim; app Android não) */
export const CLOUD_AVAILABLE = !IS_JARVIS_APP;

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

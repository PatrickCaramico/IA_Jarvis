// V7.6: o aparelho pede a PRÓPRIA chave ao PC (com a chave de pareamento do QR code).
// Na migração (primeiros dias da atualização) sai aprovada na hora; depois, espera alguém tocar PERMITIR no PC.
import { API_URL, BACKEND_ON_THIS_PC, getDeviceToken, getPairingKey, setDeviceToken } from "./api.js";
import { deviceInfo } from "./deviceInfo.js";

export { deviceInfo };

async function call(path, { method = "GET", body } = {}) {
  const key = getPairingKey();
  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers: { "Content-Type": "application/json", ...(key ? { "X-Jarvis-Token": key } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(typeof data.detail === "string" ? data.detail : `Erro ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return data;
}

// precisa pedir? (PC local não precisa; sem a chave do QR não dá para pedir)
export function needsDeviceKey() {
  return !BACKEND_ON_THIS_PC && !getDeviceToken() && Boolean(getPairingKey());
}

// pede a chave: {status: "approved"} | {status: "pending", request_id, secret, expires_in} | {status: "local"}
export async function requestDeviceKey(info = deviceInfo()) {
  const r = await call("/api/security/claim", { method: "POST", body: info });
  if (r.status === "approved" && r.token) setDeviceToken(r.token);
  return r;
}

// espera a decisão do PC (approved | refused | expired | unknown)
export async function pollDeviceKey(requestId, secret, { signal, every = 2000 } = {}) {
  for (;;) {
    if (signal?.aborted) return "aborted";
    try {
      const r = await call(`/api/security/claim?id=${encodeURIComponent(requestId)}&secret=${encodeURIComponent(secret)}`);
      if (r.status === "approved" && r.token) {
        setDeviceToken(r.token);
        return "approved";
      }
      if (r.status !== "pending") return r.status;
    } catch {
      /* PC ocupado ou sem rede: tenta de novo */
    }
    await new Promise((ok) => setTimeout(ok, every));
  }
}

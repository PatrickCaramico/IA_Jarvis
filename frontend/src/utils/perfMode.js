// V7.2: MODO LEVE e medições do ⚡ OTIMIZAR.
// Modo leve: tira o desfoque de vidro (backdrop-filter) e os brilhos mais pesados, que são o que mais
// pesa em celular e notebook fraco. Fica guardado por aparelho (cada um decide o seu).
const KEY = "jarvis.perf";

export function isLite() {
  try {
    return localStorage.getItem(KEY) === "lite";
  } catch {
    return false;
  }
}

export function applyPerf(lite = isLite()) {
  if (typeof document === "undefined") return;
  if (lite) document.documentElement.dataset.perf = "lite";
  else delete document.documentElement.dataset.perf;
}

export function setLite(lite) {
  try {
    if (lite) localStorage.setItem(KEY, "lite");
    else localStorage.removeItem(KEY);
  } catch {
    /* sem armazenamento: vale só nesta sessão */
  }
  applyPerf(lite);
}

// quadros por segundo durante `ms` (60 = liso; abaixo de 40 o aparelho está sofrendo)
export function measureFps(ms = 1500) {
  return new Promise((resolve) => {
    if (typeof requestAnimationFrame === "undefined") {
      resolve(60);
      return;
    }
    let frames = 0;
    const start = performance.now();
    const step = (t) => {
      frames += 1;
      if (t - start < ms) requestAnimationFrame(step);
      else resolve(Math.round((frames * 1000) / (t - start)));
    };
    requestAnimationFrame(step);
  });
}

// nota de 0 a 100 a partir da fluidez e da resposta do JARVIS
export function score({ fps = 60, pingMs = null }) {
  const fpsPart = Math.max(0, Math.min(1, (fps - 20) / 40)) * 60;
  const pingPart = pingMs == null ? 25 : Math.max(0, Math.min(1, (800 - pingMs) / 700)) * 40;
  return Math.round(fpsPart + pingPart);
}

// apaga caches do navegador (Cache Storage e service workers antigos); não mexe em login nem preferências
export async function clearBrowserCaches() {
  let cleared = 0;
  try {
    const store = window.caches;
    if (store) {
      const keys = await store.keys();
      await Promise.all(keys.map((k) => store.delete(k)));
      cleared += keys.length;
    }
  } catch {
    /* sem acesso */
  }
  try {
    const regs = (await navigator.serviceWorker?.getRegistrations?.()) || [];
    await Promise.all(regs.map((r) => r.unregister()));
    cleared += regs.length;
  } catch {
    /* sem service worker */
  }
  try {
    sessionStorage.removeItem("jarvis.chunkReloadAt");
  } catch {
    /* sem armazenamento */
  }
  return cleared;
}

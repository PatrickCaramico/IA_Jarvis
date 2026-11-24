// V9.1.2: VIGIA DE QUADROS. As animações do JARVIS rodam lisas (60 quadros/s) quando o PC acompanha. Este vigia
// mede, de vez em quando, quantos quadros o navegador consegue mostrar; se ficar abaixo de LOW_FPS em STRIKES
// medições seguidas, liga o modo econômico (html.is-eco: utils/slowSpin.js gira tudo a 10 quadros/s) para não
// travar a máquina. Mede por pouco tempo (o laço de medição também custa) e só com a aba visível.

export const LOW_FPS = 40;
export const STRIKES = 2;
export const SAMPLE_MS = 3000;
export const RECHECK_MS = 2 * 60 * 1000;
const KEY = "jarvis_eco";

/** Nova contagem de medições ruins seguidas, dado o fps medido. */
export function nextStrikes(strikes, fps) {
  return fps < LOW_FPS ? strikes + 1 : 0;
}

export function shouldEco(strikes) {
  return strikes >= STRIKES;
}

function setEco(on) {
  document.documentElement.classList.toggle("is-eco", on);
  try {
    if (on) sessionStorage.setItem(KEY, "1"); else sessionStorage.removeItem(KEY);
  } catch {
    /* sem armazenamento: só não lembra na próxima página */
  }
}

/** Mede quantos quadros por segundo o navegador mostra durante `ms`. */
function sample(ms) {
  return new Promise((resolve) => {
    let frames = 0;
    const start = performance.now();
    const step = (now) => {
      frames += 1;
      if (now - start < ms) requestAnimationFrame(step);
      else resolve((frames * 1000) / (now - start));
    };
    requestAnimationFrame(step);
  });
}

/** Liga o vigia (uma vez). `?eco=1` / `?eco=0` na URL forçam (diagnóstico). Devolve a função que desliga. */
export function startFrameWatch() {
  if (typeof window === "undefined") return () => {};
  const forced = new URLSearchParams(window.location.search).get("eco");
  if (forced === "1" || forced === "0") {
    setEco(forced === "1");
    return () => {};
  }
  let remembered = false;
  try {
    remembered = sessionStorage.getItem(KEY) === "1";
  } catch {
    remembered = false;
  }
  if (remembered) {
    setEco(true);
    return () => {};
  }
  let strikes = 0;
  let stopped = false;
  let timer = null;
  const check = async () => {
    if (stopped) return;
    const root = document.documentElement;
    const motionOff = root.dataset.motion === "reduce" || root.classList.contains("is-lite") || root.classList.contains("is-eco");
    if (!document.hidden && !motionOff) {
      const fps = await sample(SAMPLE_MS);
      window.__jarvisFps = [...(window.__jarvisFps || []), Math.round(fps)].slice(-10); // diagnóstico (DevTools)
      if (!document.hidden) strikes = nextStrikes(strikes, fps);
      if (shouldEco(strikes)) {
        setEco(true);
        return; // econômico até recarregar a página
      }
    }
    timer = setTimeout(check, strikes ? 1000 : RECHECK_MS); // medição ruim: confere de novo logo
  };
  timer = setTimeout(check, 4000); // deixa a central terminar de abrir
  return () => {
    stopped = true;
    clearTimeout(timer);
  };
}

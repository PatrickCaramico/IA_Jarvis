// V9.1.2: GIROS LENTOS A 10 QUADROS POR SEGUNDO. Antes, os fios do orbe, os anéis do reator, o anel do logo, o
// halo e o equalizador do Spotify eram animações CSS sem fim. Enquanto existe UMA animação CSS rodando, o navegador
// redesenha a central 60 vezes por segundo — e cada redesenho (planta, vidro, brilhos) é caro: medido em
// ~1 núcleo do processador inteiro com a central parada em "em espera" (no app do Desk não acontecia).
// Os giros são lentíssimos (um fio leva 28 a 70 s por volta), então 10 atualizações por segundo ficam iguais
// no olho e o navegador só redesenha quando algo muda: ~1/3 do custo (medido). Para com a aba escondida, no
// modo leve e com "reduzir movimento".

export const FPS = 10;

/** Ângulo seguinte (graus) depois de dt segundos, para uma volta a cada `period` s (negativo = ao contrário). */
export function nextAngle(prev, dt, period) {
  if (!period || !Number.isFinite(period)) return prev;
  return (((prev + (360 * dt) / period) % 360) + 360) % 360;
}

/** Valor de 0 a 1 de uma "respiração" (seno), dado o tempo e o período. */
export function breath(t, period, offset = 0) {
  return 0.5 - 0.5 * Math.cos(((t + offset) / period) * 2 * Math.PI);
}

// Período (s) de cada peça, conforme o estado da central — o mesmo de antes no CSS.
function orbSpeed(el) {
  if (el.closest(".wo-processing")) return 0.22;
  if (el.closest(".wo-speaking")) return 0.5;
  return 1;
}
function ringPeriod(el) {
  const rev = el.classList.contains("is-rev");
  const busy = el.closest('[data-state="processing"]');
  return (busy ? (rev ? 9 : 6) : rev ? 90 : 60) * (rev ? -1 : 1);
}

export const SPINS = [
  [".wo-wire", (el) => Number(el.dataset.spin || 40) * (el.dataset.dir === "-1" ? -1 : 1) * orbSpeed(el)],
  [".wo-nodes", (el) => 70 * orbSpeed(el)],
  [".hc-ring-spin", ringPeriod],
  [".jarvis-logo-spin .jarvis-logo-ring1", () => 18],
  [".jarvis-logo-spin .jarvis-logo-ring2", () => -30],
];

export function paused(doc = document, win = window) {
  const root = doc.documentElement;
  return doc.hidden || root.classList.contains("is-lite") || root.dataset.motion === "reduce"
    || Boolean(win.matchMedia && win.matchMedia("(prefers-reduced-motion: reduce)").matches);
}

let timer = null;

/** Liga o relógio (uma vez só, para a página inteira). Devolve a função que desliga. */
export function startSlowSpin() {
  if (timer || typeof document === "undefined") return () => {};
  const angles = new WeakMap();
  let last = performance.now();
  const tick = () => {
    const now = performance.now();
    const dt = Math.min(1, (now - last) / 1000);
    last = now;
    if (paused()) return;
    const t = now / 1000;
    for (const [sel, period] of SPINS) {
      for (const el of document.querySelectorAll(sel)) {
        const start = angles.has(el) ? angles.get(el) : Number(el.dataset.start || 0);
        const a = nextAngle(start, dt, period(el));
        angles.set(el, a);
        el.style.transform = `rotate(${a.toFixed(2)}deg)`;
      }
    }
    // halo do orbe "respirando" (5 s; mais rápido falando e pensando)
    for (const el of document.querySelectorAll(".wo-halo")) {
      const p = el.closest(".wo-speaking") ? 0.9 : el.closest(".wo-processing") ? 1.4 : 5;
      const b = breath(t, p);
      el.style.opacity = (0.55 + 0.45 * b).toFixed(3);
      el.style.transform = `scale(${(0.97 + 0.06 * b).toFixed(4)})`;
    }
    // equalizadores do Spotify (barras sobem e descem defasadas)
    for (const bars of document.querySelectorAll(".np-eq, .sg-eq")) {
      [...bars.children].forEach((bar, i) => {
        bar.style.transform = `scaleY(${(0.3 + 0.7 * breath(t, 0.9, i * 0.3)).toFixed(3)})`;
      });
    }
    // aurora da janela do Spotify (luzes que derivam devagar, só tocando)
    for (const el of document.querySelectorAll(".sg.is-playing .sg-bg i")) {
      const i = [...el.parentNode.children].indexOf(el);
      const p = [22, 28, 32][i] || 26;
      const x = Math.sin((t / p) * 2 * Math.PI) * 10;
      const y = Math.cos((t / (p * 1.3)) * 2 * Math.PI) * 9;
      el.style.transform = `translate(${x.toFixed(2)}%, ${y.toFixed(2)}%) scale(${(1 + 0.08 * breath(t, p)).toFixed(3)})`;
    }
  };
  timer = setInterval(tick, 1000 / FPS);
  return () => {
    clearInterval(timer);
    timer = null;
  };
}

// Relógio central (otimização 4.2): um único timer de 1 s para todos os relógios da tela,
// alinhado à virada do segundo e parado com a aba oculta. Antes cada relógio tinha o seu.
const subscribers = new Set();
let timer = null;

function tick() {
  const now = new Date();
  subscribers.forEach((fn) => fn(now));
}

function schedule() {
  clearTimeout(timer);
  timer = null;
  if (!subscribers.size || (typeof document !== "undefined" && document.hidden)) return;
  const delay = 1000 - (Date.now() % 1000) + 5;
  timer = setTimeout(() => {
    tick();
    schedule();
  }, delay);
}

if (typeof document !== "undefined") {
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) tick();
    schedule();
  });
}

export function subscribeNow(fn) {
  subscribers.add(fn);
  if (subscribers.size === 1) schedule();
  return () => {
    subscribers.delete(fn);
    if (!subscribers.size) schedule();
  };
}

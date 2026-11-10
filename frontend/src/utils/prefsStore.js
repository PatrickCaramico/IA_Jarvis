// Loja mínima das preferências carregadas do backend, para componentes profundos
// (cartão de água no chat, widgets) lerem sem precisar repassar props por toda a árvore.
import { useSyncExternalStore } from "react";

let current = {};
const listeners = new Set();

export function setPrefs(next) {
  current = { ...current, ...(next || {}) };
  listeners.forEach((fn) => fn());
}

export function getPrefs() {
  return current;
}

function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function usePrefs() {
  return useSyncExternalStore(subscribe, getPrefs, getPrefs);
}

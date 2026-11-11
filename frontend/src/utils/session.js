// V5.2: lembra, NESTE navegador, que o usuário já entrou na central.
// Serve para duas coisas:
// 1) reabrir a central (F5, nova aba, site) direto, sem a tela de bloqueio, quando o JARVIS do PC
//    ainda está liberado de uma entrada recente — o backend continua sendo quem decide (estado "unlocked");
// 2) trocar a tela longa de "PC desligado" por uma tela curta de "reconectando" para quem já usa o JARVIS.
// Nada disso é segredo: guarda só a hora da última entrada e se o botão LIGAR já funcionou aqui.

const KEY_LOGIN = "jarvis.lastLogin";
const KEY_LAUNCHER = "jarvis.launcher.ok";

// Por quanto tempo uma entrada recente reabre a central sem passar pelo bloqueio
export const RESUME_WINDOW_MS = 12 * 60 * 60 * 1000;

function read(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* navegador sem armazenamento (aba anônima): segue sem lembrar */
  }
}

export function rememberLogin(now = Date.now()) {
  write(KEY_LOGIN, String(now));
}

export function lastLoginAt() {
  const value = Number(read(KEY_LOGIN));
  return Number.isFinite(value) && value > 0 ? value : 0;
}

// Já entrou alguma vez neste navegador?
export function hasLoggedBefore() {
  return lastLoginAt() > 0;
}

// Entrou há pouco (dentro da janela) — pode reabrir direto se o backend ainda estiver liberado
export function isRecentLogin(now = Date.now(), windowMs = RESUME_WINDOW_MS) {
  const at = lastLoginAt();
  return at > 0 && now - at >= 0 && now - at < windowMs;
}

// Reabrir direto na central? Só com entrada recente aqui E o JARVIS do PC ainda liberado.
export function canResumeSession(access, now = Date.now()) {
  return Boolean(access && access.state === "unlocked" && isRecentLogin(now));
}

export function markLauncherWorks() {
  write(KEY_LAUNCHER, "1");
}

export function launcherWorks() {
  return read(KEY_LAUNCHER) === "1";
}

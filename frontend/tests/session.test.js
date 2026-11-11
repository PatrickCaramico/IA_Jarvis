import assert from "node:assert/strict";
import test from "node:test";

// localStorage de mentira (o node não tem)
const store = new Map();
globalThis.localStorage = {
  getItem: (k) => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => store.set(k, String(v)),
  removeItem: (k) => store.delete(k),
};

const { RESUME_WINDOW_MS, canResumeSession, hasLoggedBefore, isRecentLogin, launcherWorks, markLauncherWorks, rememberLogin } =
  await import("../src/utils/session.js");
const { reconnectDelay, MAX_WAIT_MS } = await import("../src/utils/reconnect.js");

test("sem entrada anterior: não é usuário de volta e não reabre direto", () => {
  store.clear();
  assert.equal(hasLoggedBefore(), false);
  assert.equal(canResumeSession({ state: "unlocked" }), false);
});

test("entrada recente + JARVIS do PC liberado: reabre direto", () => {
  store.clear();
  const now = 1_700_000_000_000;
  rememberLogin(now - 60_000);
  assert.equal(hasLoggedBefore(), true);
  assert.equal(isRecentLogin(now), true);
  assert.equal(canResumeSession({ state: "unlocked" }, now), true);
});

test("JARVIS do PC bloqueado ou visitante: nunca pula o bloqueio", () => {
  store.clear();
  const now = 1_700_000_000_000;
  rememberLogin(now - 60_000);
  assert.equal(canResumeSession({ state: "locked", effective: "unlocked" }, now), false);
  assert.equal(canResumeSession({ state: "guest" }, now), false);
  assert.equal(canResumeSession(null, now), false);
});

test("entrada antiga (fora da janela): passa pela verificação, mas continua sendo usuário de volta", () => {
  store.clear();
  const now = 1_700_000_000_000;
  rememberLogin(now - RESUME_WINDOW_MS - 1);
  assert.equal(canResumeSession({ state: "unlocked" }, now), false);
  assert.equal(hasLoggedBefore(), true);
});

test("lembra que o botão LIGAR já funcionou neste navegador", () => {
  store.clear();
  assert.equal(launcherWorks(), false);
  markLauncherWorks();
  assert.equal(launcherWorks(), true);
});

test("reconexão espera cada vez mais, até 10 s", () => {
  const mid = () => 0.5; // sem sorteio
  assert.equal(reconnectDelay(0, mid), 1000);
  assert.equal(reconnectDelay(1, mid), 2000);
  assert.equal(reconnectDelay(3, mid), 8000);
  assert.equal(reconnectDelay(10, mid), MAX_WAIT_MS);
  assert.ok(reconnectDelay(2, () => 0) >= 3200 && reconnectDelay(2, () => 1) <= 4800);
});

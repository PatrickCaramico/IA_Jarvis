import assert from "node:assert/strict";
import test from "node:test";

import {
  AUTO_CHECK_INTERVAL_MS,
  checkForUpdate,
  compareVersions,
  scheduleDailyUpdateCheck,
} from "../src/utils/updateCheck.js";

test("compara versões numericamente, não como texto", () => {
  assert.equal(compareVersions("5.10.0", "5.9.9"), 1);
  assert.equal(compareVersions("5.0.0", "5.0.0"), 0);
  assert.equal(compareVersions("4.9.9", "5.0.0"), -1);
});

test("confere a branch pelo PC (mesma fonte do ATUALIZAR) e devolve quantas versões novas", async () => {
  const calls = [];
  const result = await checkForUpdate(async (path) => {
    calls.push(path);
    return { available: true, count: 2, current: "6.7.2", latest: "6.7.4", notes: ["JARVIS 6.7.4: agenda", "JARVIS 6.7.3: memória"] };
  });
  assert.deepEqual(calls, ["/api/system/update/status?force=true"]);
  assert.equal(result.updateAvailable, true);
  assert.equal(result.count, 2);
  assert.equal(result.currentVersion, "6.7.2");
  assert.equal(result.latestVersion, "6.7.4");
  assert.equal(result.notes, "JARVIS 6.7.4: agenda\nJARVIS 6.7.3: memória");
});

test("reconhece que a versão atual já é a mais nova", async () => {
  const result = await checkForUpdate(async () => ({ available: false, count: 0, current: "6.7.4", latest: "6.7.4", notes: [] }));
  assert.equal(result.updateAvailable, false);
});

test("sem falar com o GitHub, vira erro (não diz que está em dia)", async () => {
  await assert.rejects(() => checkForUpdate(async () => ({ available: false, current: "6.7.4", message: "Não consegui falar com o GitHub agora." })));
});

test("agenda a primeira verificação automática só depois de 24 horas", (context) => {
  const originals = {
    setTimeout: globalThis.setTimeout,
    clearTimeout: globalThis.clearTimeout,
    localStorage: Object.getOwnPropertyDescriptor(globalThis, "localStorage"),
    window: Object.getOwnPropertyDescriptor(globalThis, "window"),
  };
  const scheduled = [];
  globalThis.setTimeout = (callback, delay) => {
    scheduled.push({ callback, delay });
    return 1;
  };
  globalThis.clearTimeout = () => {};
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: { getItem: () => null, setItem: () => {} },
  });
  Object.defineProperty(globalThis, "window", { configurable: true, value: { dispatchEvent: () => {} } });
  context.after(() => {
    globalThis.setTimeout = originals.setTimeout;
    globalThis.clearTimeout = originals.clearTimeout;
    if (originals.localStorage) Object.defineProperty(globalThis, "localStorage", originals.localStorage);
    else delete globalThis.localStorage;
    if (originals.window) Object.defineProperty(globalThis, "window", originals.window);
    else delete globalThis.window;
  });

  const stop = scheduleDailyUpdateCheck(async () => assert.fail("não deve checar ao abrir a central"));
  assert.equal(scheduled[0].delay, AUTO_CHECK_INTERVAL_MS);
  stop();
});

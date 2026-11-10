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

test("compara a versão do backend à release pública e retorna notas e link", async () => {
  const apiCalls = [];
  const fetchCalls = [];
  const result = await checkForUpdate(
    async (path) => {
      apiCalls.push(path);
      return { version: "5.0.0" };
    },
    async (url, options) => {
      fetchCalls.push({ url, options });
      return {
        ok: true,
        json: async () => ({
          tag_name: "v5.1.0",
          body: "Correções e melhorias.",
          html_url: "https://github.com/PatrickCaramico/IA_Jarvis/releases/tag/v5.1.0",
        }),
      };
    },
  );

  assert.deepEqual(apiCalls, ["/api/health"]);
  assert.equal(fetchCalls[0].url, "https://api.github.com/repos/PatrickCaramico/IA_Jarvis/releases/latest");
  assert.equal(result.updateAvailable, true);
  assert.equal(result.currentVersion, "5.0.0");
  assert.equal(result.latestVersion, "5.1.0");
  assert.equal(result.notes, "Correções e melhorias.");
  assert.equal(result.url, "https://github.com/PatrickCaramico/IA_Jarvis/releases/tag/v5.1.0");
});

test("reconhece que a versão atual já é a mais nova", async () => {
  const result = await checkForUpdate(
    async () => ({ version: "5.1.0" }),
    async () => ({
      ok: true,
      json: async () => ({ tag_name: "v5.1.0", html_url: "https://github.com/PatrickCaramico/IA_Jarvis/releases/tag/v5.1.0" }),
    }),
  );

  assert.equal(result.updateAvailable, false);
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

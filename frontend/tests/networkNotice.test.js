import { test } from "node:test";
import assert from "node:assert/strict";
import { networkMessage } from "../src/utils/networkNotice.js";

test("abrir o app nos dados móveis avisa", () => {
  const m = networkMessage("cellular", "cellular", "open");
  assert.equal(m.speech, "O senhor está conectado pela rede de dados móveis.");
});

test("trocar de rede avisa a mudança", () => {
  assert.equal(networkMessage("wifi", "cellular", "open").speech, "Mudança de rede, senhor. Agora o senhor está no Wi-Fi.");
  assert.equal(networkMessage("cellular", "wifi", "change").speech, "Mudança de rede, senhor. Agora o senhor está nos dados móveis.");
});

test("Wi-Fi de sempre, primeira vez ou sem rede: silêncio", () => {
  assert.equal(networkMessage("wifi", "wifi", "open"), null);
  assert.equal(networkMessage("wifi", "", "open"), null);
  assert.equal(networkMessage("none", "wifi", "change"), null);
  assert.equal(networkMessage("cellular", "cellular", "change"), null);
});

test("primeira vez já nos dados móveis avisa os dados", () => {
  assert.equal(networkMessage("cellular", "", "open").text, "Conectado pelos 📱 Dados móveis");
});

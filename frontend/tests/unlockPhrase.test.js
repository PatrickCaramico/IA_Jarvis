import { test } from "node:test";
import assert from "node:assert/strict";
import { isUnlockPhrase, matchUnlock, effectiveWakeWords } from "../src/utils/wakeWords.js";

const WAKE = effectiveWakeWords(null, "J.A.R.V.I.S.");
export const UNLOCK_YES = ["abrir central", "Abre a central", "abra a central", "liberar", "libera a central", "desbloquear",
  "desbloqueia o sistema", "destrava a tela", "entrar", "quero entrar", "me deixa entrar", "pode liberar", "abrir o jarvis",
  "liberar por favor"];
export const UNLOCK_NO = ["abrir", "abre o spotify", "abrir youtube", "que horas são", "abrir central de notificações",
  "bloquear a central", "liberar espaço no disco", "entrar no modo foco", ""];

test("frases de liberar são reconhecidas", () => {
  for (const t of UNLOCK_YES) assert.ok(isUnlockPhrase(t), t);
});

test("outros pedidos não liberam", () => {
  for (const t of UNLOCK_NO) assert.ok(!isUnlockPhrase(t), t);
});

test("com ou sem a palavra de ativação", () => {
  assert.ok(matchUnlock("abrir central", WAKE));
  assert.ok(matchUnlock("Jarvis, abrir central", WAKE));
  assert.ok(matchUnlock("ei jarvis liberar", WAKE));
  assert.ok(!matchUnlock("Jarvis, que horas são", WAKE));
  assert.ok(!matchUnlock("Jarvis", WAKE));
});

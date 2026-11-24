// V9.4: clima animado do bloqueio, tecla de acesso, Ctrl+V com imagem e o selo do modo gravar.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { pautaLabel, isLockKeyCandidate, isNight, keyLabel, lockKeyPress, pastedImage, recordingText, weatherScene } from "../src/utils/lockExtras.js";

const at = (h, m = 0) => new Date(2026, 10, 24, h, m);

test("dia e noite pelo nascer e pôr do sol", () => {
  assert.equal(isNight(at(12), "05:20", "18:40"), false);
  assert.equal(isNight(at(19), "05:20", "18:40"), true);
  assert.equal(isNight(at(5, 10), "05:20", "18:40"), true);
  assert.equal(isNight(at(21), null, null), true);
  assert.equal(isNight(at(9), undefined, ""), false);
});

test("cena do clima pelo código WMO e pela descrição", () => {
  const day = { sunrise: "05:20", sunset: "18:40" };
  assert.equal(weatherScene({ ...day, code: 0 }, at(12)), "sun");
  assert.equal(weatherScene({ ...day, code: 0 }, at(22)), "night");
  assert.equal(weatherScene({ ...day, code: 2 }, at(12)), "partly");
  assert.equal(weatherScene({ ...day, code: 2 }, at(22)), "partly-night");
  assert.equal(weatherScene({ ...day, code: 3 }, at(12)), "cloud");
  assert.equal(weatherScene({ ...day, code: 63 }, at(12)), "rain");
  assert.equal(weatherScene({ ...day, code: 95 }, at(12)), "storm");
  assert.equal(weatherScene({ ...day, code: 45 }, at(12)), "fog");
  assert.equal(weatherScene({ ...day, code: 73 }, at(12)), "snow");
  assert.equal(weatherScene({ ...day, description: "Chuva moderada" }, at(12)), "rain");
  assert.equal(weatherScene({ ...day, description: "Trovoada" }, at(12)), "storm");
  assert.equal(weatherScene({ ...day, description: "Céu limpo" }, at(12)), "sun");
  assert.equal(weatherScene(null), "cloud");
});

test("tecla de acesso: quais valem e o nome", () => {
  for (const c of ["F8", "KeyJ", "Digit7", "Numpad0", "Insert"]) assert.equal(isLockKeyCandidate(c), true, c);
  for (const c of ["Space", "Enter", "Escape", "KeyP", "ShiftLeft", "Tab", "", undefined, "ArrowUp"]) assert.equal(isLockKeyCandidate(c), false, String(c));
  assert.equal(keyLabel("KeyJ"), "J");
  assert.equal(keyLabel("Digit7"), "7");
  assert.equal(keyLabel("Numpad3"), "3 (numérico)");
  assert.equal(keyLabel("F8"), "F8");
  const ev = (code, extra = {}) => ({ code, target: { tagName: "DIV" }, ...extra });
  assert.equal(lockKeyPress(ev("KeyJ")), "KeyJ");
  assert.equal(lockKeyPress(ev("KeyJ", { ctrlKey: true })), null);
  assert.equal(lockKeyPress(ev("KeyJ", { repeat: true })), null);
  assert.equal(lockKeyPress(ev("KeyJ", { target: { tagName: "INPUT" } })), null);
  assert.equal(lockKeyPress(ev("Space")), null);
});

test("Ctrl+V: pega só imagem", () => {
  const file = { name: "x.png" };
  assert.equal(pastedImage([{ kind: "string", type: "text/plain" }, { kind: "file", type: "image/png", getAsFile: () => file }]), file);
  assert.equal(pastedImage([{ kind: "file", type: "application/pdf", getAsFile: () => file }]), null);
  assert.equal(pastedImage(null), null);
});

test("selo do modo gravar", () => {
  assert.equal(recordingText(null), "");
  assert.equal(recordingText({ active: false, steps: 3 }), "");
  assert.equal(recordingText({ active: true, label: "", steps: 0 }), "GRAVANDO · faça os pedidos");
  assert.equal(recordingText({ active: true, label: "estudo", steps: 1 }), "GRAVANDO · ESTUDO · 1 passo");
  assert.equal(recordingText({ active: true, label: "estudo", steps: 15, max: 15 }), "GRAVANDO · ESTUDO · 15 passos (cheio)");
});

test("V9.4: o ⚡ ANALISAR recebe o clique (a telemetria em volta tem pointer-events: none)", () => {
  const css = readFileSync(new URL("../src/hud-center.css", import.meta.url), "utf8");
  assert.match(css, /\.hl-orb > \.hc-telemetry \{[^}]*pointer-events: none/);
  assert.match(css, /\.hc-r-analyze \{[^}]*pointer-events: auto/);
});

test("V9.4: pauta do briefing em etiquetas curtas", () => {
  assert.equal(pautaLabel({ kind: "weather", label: "PANORAMA · CLIMA", title: "Céu limpo" }), "Clima");
  assert.equal(pautaLabel({ kind: "news", label: "RADAR · NOTÍCIAS", title: "Palmeiras" }), "Palmeiras");
  assert.equal(pautaLabel({ kind: "email", label: "COMUNICAÇÕES · E-MAIL" }), "E-mail");
  assert.equal(pautaLabel({ kind: "agenda", label: "AGENDA · HOJE" }), "Agenda");
  assert.equal(pautaLabel({ kind: "metrics", label: "MODO TORCEDOR · HOJE" }), "Modo torcedor");
  assert.equal(pautaLabel({}), "Assunto");
});

test("V9.4: a faixa do jogo tem linha própria na grade (não empurra as colunas)", () => {
  const css = readFileSync(new URL("../src/v94.css", import.meta.url), "utf8");
  assert.match(css, /\.hl-root > \.fmb-root \{ grid-column: 1 \/ -1; grid-row: 2;/);
  assert.match(css, /\.hl-root:has\(> \.fmb-root\) > \.hl-right \{ grid-row: 3; \}/);
});

import { test } from "node:test";
import assert from "node:assert/strict";
import {
  clampPct, easeInOutCubic, paceInfo, paceText, parseVolume, remainingMl, statusSentence, waterLevel,
} from "../src/utils/waterMath.js";
import { MAX_SUMMARY_WORDS, buildDailySummary, shouldSpeakSummary, spokenTime } from "../src/utils/lockSummary.js";

test("nível e porcentagem da água", () => {
  assert.equal(waterLevel(500, 2000), 0.25);
  assert.equal(waterLevel(2500, 2000), 1);
  assert.equal(waterLevel(-5, 2000), 0);
  assert.equal(clampPct(750, 2000), 38);
  assert.equal(clampPct(5000, 2000), 100);
  assert.equal(remainingMl(750, 2000), 1250);
  assert.equal(remainingMl(2500, 2000), 0);
});

test("faixa de ritmo do dia", () => {
  const at = (h, m = 0) => new Date(2026, 9, 29, h, m);
  assert.equal(paceInfo({ totalMl: 0, goalMl: 2000, now: at(7) }).status, "outside");
  const noon = paceInfo({ totalMl: 900, goalMl: 2000, startHour: 8, endHour: 22, now: at(15) });
  assert.equal(noon.expected, 1000);
  assert.equal(noon.status, "on_track");
  const ahead = paceInfo({ totalMl: 1300, goalMl: 2000, startHour: 8, endHour: 22, now: at(15) });
  assert.equal(ahead.status, "ahead");
  assert.equal(paceText(ahead), "Você está 300 ml acima do ritmo.");
  const behind = paceInfo({ totalMl: 200, goalMl: 2000, now: at(22, 30) });
  assert.equal(behind.expected, 2000);
  assert.match(paceText(behind), /1800 ml abaixo/);
});

test("valor livre em ml ou litros", () => {
  assert.equal(parseVolume("300"), 300);
  assert.equal(parseVolume("300 ml"), 300);
  assert.equal(parseVolume("0,5 L"), 500);
  assert.equal(parseVolume("1.5l"), 1500);
  assert.equal(parseVolume("2"), 2000);
  assert.equal(parseVolume("meio litro"), 500);
  assert.equal(parseVolume("10"), null);
  assert.equal(parseVolume("abc"), null);
  assert.equal(parseVolume("9 litros"), null);
});

test("frase do status igual à do backend", () => {
  assert.equal(statusSentence({ total_ml: 300, percentage: 15, goal_ml: 2000 }),
    "Hoje você já consumiu 300 ml de água (15% da sua meta de 2000 ml).");
});

test("suavização limita 0..1", () => {
  assert.equal(easeInOutCubic(-1), 0);
  assert.equal(easeInOutCubic(2), 1);
  assert.equal(easeInOutCubic(0.5), 0.5);
});

test("resumo do dia respeita a preferência", () => {
  assert.equal(shouldSpeakSummary("off", true), false);
  assert.equal(shouldSpeakSummary("first_login", false), false);
  assert.equal(shouldSpeakSummary("first_login", true), true);
  assert.equal(shouldSpeakSummary("always", false), true);
});

test("resumo cabe em ~20 s e prioriza o essencial", () => {
  const long = buildDailySummary({
    hour: 9, minute: 5,
    weather: { place: "São Paulo", temperature: 22, description: "céu parcialmente nublado" },
    tasks: [{ texto: "revisar o relatório trimestral da equipe" }, { texto: "ligar para o fornecedor de peças" }, { texto: "c" }],
    fanMatch: { opponent: "Corinthians", date: "2026-10-29T21:30:00", is_match_day: true },
    waterYesterday: { total_ml: 1800 },
    motivation: "A disciplina é a ponte entre metas e conquistas, e cada pequeno passo de hoje constrói o resultado de amanhã.",
  });
  const words = long.text.split(/\s+/).length;
  assert.ok(words <= MAX_SUMMARY_WORDS, `${words} palavras`);
  assert.ok(long.parts.includes("greeting") && long.parts.includes("weather") && long.parts.includes("tasks"));
  assert.ok(!long.parts.includes("motivation"));
  const short = buildDailySummary({ hour: 20, minute: 0, weather: null, tasks: [], waterYesterday: { total_ml: 900 } });
  assert.match(short.text, /^Boa noite, senhor\. São 20 horas em ponto\./);
  assert.match(short.text, /Ontem você bebeu 900 ml/);
  assert.equal(spokenTime(1, 1), "uma hora e 1 minuto");
});

import { effectiveWakeWords, matchWake } from "../src/utils/wakeWords.js";

test("palavra de ativação no começo da frase", () => {
  const words = effectiveWakeWords(["jarvis", "ei jarvis", "ta acordado"], "A.R.E.S");
  assert.ok(words.includes("ares") && words.includes("ei ares"));
  assert.deepEqual(matchWake("Jarvis, que horas são?", words), { matched: true, wake: "jarvis", rest: "que horas sao" });
  assert.equal(matchWake("Ei, Jarvis!", words).matched, true);
  assert.equal(matchWake("Tá acordado?", words).rest, "");
  assert.equal(matchWake("o jarvis do filme", words).matched, false);
  assert.equal(matchWake("Ares, bloquear", words).rest, "bloquear");
});

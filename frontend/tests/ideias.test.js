// V9.5.6: 💡 BLOCO DE IDEIAS nos CONTROLES (reorganizados) e o aviso ⏰ LEMBRETE quando um lembrete vence
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (p) => readFileSync(new URL(p, import.meta.url), "utf8");

test("CONTROLES reorganizados por assunto, com o Bloco de ideias em Anotar e lembrar", () => {
  const hud = read("../src/components/HudLayout.jsx");
  const titles = [...hud.matchAll(/title: "([A-ZÇÃÉÍÓÚ &]+)",\n/g)].map((m) => m[1]);
  for (const t of ["ANOTAR E LEMBRAR", "ROTINAS DO DIA", "MODOS DE AMBIENTE", "MÚSICA & SOM", "CENTRAL", "MANUTENÇÃO"]) {
    assert.ok(titles.includes(t), `faltou a seção ${t}`);
  }
  assert.ok(!titles.includes("AÇÕES RÁPIDAS") && !titles.includes("SISTEMA & HUD"));
  assert.match(hud, /id: "ideas", icon: "💡", label: "BLOCO DE IDEIAS"/);
  assert.match(hud, /case "ideas":[\s\S]{0,120}jarvis-open-ideas/);
  const app = read("../src/App.jsx");
  assert.match(app, /addEventListener\("jarvis-open-ideas"/);
  assert.match(app, /<IdeasPad api=\{api\}/);
});

test("lembrete vencido abre o aviso que fica até OK/ADIAR, com sinal", () => {
  const app = read("../src/App.jsx");
  assert.match(app, /case "reminder_due":[\s\S]{0,200}soundManager\.playAlert\(\)/);
  assert.equal((app.match(/<ReminderDue api=\{api\}/g) || []).length, 2); // no bloqueio e na central
  const rd = read("../src/components/ReminderDue.jsx");
  assert.match(rd, /\/api\/reminders\/\$\{item\.id\}\/postpone/);
  assert.match(rd, /ADIAR 10 MIN/);
  const strip = read("../src/components/RemindersStrip.jsx");
  assert.match(strip, /type === "reminder_due"/); // venceu: a faixa atualiza
});

test("Bloco de ideias mostra o Google Tarefas: sincronizado, ou o botão para conectar", () => {
  const pad = read("../src/components/IdeasPad.jsx");
  assert.match(pad, /\/api\/ideas\$\{sync \? "\?sync=1" : ""\}/); // ao abrir, traz o que foi anotado no app
  assert.match(pad, /☁ CONECTAR GOOGLE TAREFAS/);
  assert.match(pad, /google-calendar\/authorize/);
});

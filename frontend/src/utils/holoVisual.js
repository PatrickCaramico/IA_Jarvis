// V7.13: contas das animações do Holograma (sem React: testável com node).

export function fmtNum(v) {
  const abs = Math.abs(v);
  const digits = abs < 10 && !Number.isInteger(v) ? 1 : 0;
  return Number(v).toLocaleString("pt-BR", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

/** Posições do gráfico (viewBox 360 x 200): barras crescem do eixo; a linha liga os pontos. Aceita negativos (o eixo sobe). */
export function chartGeometry(dados, estilo = "barras") {
  const w = 360;
  const h = 200;
  const left = 10;
  const top = 26;
  const bottom = h - 22;
  const vals = dados.map((d) => d.valor);
  const max = Math.max(0, ...vals);
  const min = Math.min(0, ...vals);
  const span = max - min || 1;
  const y = (v) => top + ((max - v) / span) * (bottom - top);
  const base = y(0);
  const step = (w - left - 8) / dados.length;
  const points = dados.map((d, i) => ({ ...d, x: left + step * (i + 0.5), y: estilo === "linha" ? y(d.valor) : Math.min(y(d.valor), base), bw: Math.min(46, step * 0.62) }));
  // nas barras negativas, y fica no eixo e a altura vai para baixo
  if (estilo !== "linha") for (const p of points) if (p.valor < 0) p.y = base;
  const line = points.map((p, i) => `${i ? "L" : "M"}${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
  const area = points.length ? `${line} L${points[points.length - 1].x.toFixed(1)} ${base.toFixed(1)} L${points[0].x.toFixed(1)} ${base.toFixed(1)} Z` : "";
  return { w, h, left, base, points, line, area };
}

// --------------------------------------------------------------------------- trilha ambiente
// Gerada no próprio aparelho (Web Audio): acordes suaves que mudam devagar, sem música de terceiros.
// Abaixa quando o JARVIS fala (duck) e lembra se foi desligada.
const CHORDS = [[220, 277.18, 329.63], [196, 246.94, 293.66], [174.61, 220, 261.63], [196, 246.94, 329.63]];
const KEY = "jarvis.holoMusic";

export function musicPreferred(isPhone) {
  try {
    const v = localStorage.getItem(KEY);
    if (v === "on") return true;
    if (v === "off") return false;
  } catch {
    /* sem armazenamento */
  }
  return !isPhone; // no celular começa desligada
}

export function rememberMusic(on) {
  try {
    localStorage.setItem(KEY, on ? "on" : "off");
  } catch {
    /* sem armazenamento */
  }
}

export function createAmbient() {
  const Ctx = typeof window !== "undefined" ? window.AudioContext || window.webkitAudioContext : null;
  if (!Ctx) return null;
  const ctx = new Ctx();
  const master = ctx.createGain();
  master.gain.value = 0;
  const filter = ctx.createBiquadFilter();
  filter.type = "lowpass";
  filter.frequency.value = 900;
  filter.connect(master);
  master.connect(ctx.destination);
  const lfo = ctx.createOscillator();
  const lfoGain = ctx.createGain();
  lfo.frequency.value = 0.07;
  lfoGain.gain.value = 300;
  lfo.connect(lfoGain);
  lfoGain.connect(filter.frequency);
  lfo.start();
  const voices = [0, 1, 2].map(() => {
    const g = ctx.createGain();
    g.gain.value = 0.33;
    g.connect(filter);
    const oscs = [-6, 6].map((detune) => {
      const o = ctx.createOscillator();
      o.type = "triangle";
      o.detune.value = detune;
      o.connect(g);
      o.start();
      return o;
    });
    return oscs;
  });
  let chord = 0;
  const setChord = () => {
    const now = ctx.currentTime;
    CHORDS[chord % CHORDS.length].forEach((f, i) => voices[i].forEach((o) => o.frequency.setTargetAtTime(f / 2, now, 1.5)));
    chord += 1;
  };
  setChord();
  const timer = setInterval(setChord, 9000);
  let level = 0.05;
  let ducked = false;
  const apply = () => master.gain.setTargetAtTime(ducked ? level * 0.35 : level, ctx.currentTime, 0.6);
  return {
    start() {
      ctx.resume?.().catch(() => {});
      apply();
    },
    duck(on) {
      ducked = Boolean(on);
      apply();
    },
    stop() {
      master.gain.setTargetAtTime(0, ctx.currentTime, 0.3);
    },
    close() {
      clearInterval(timer);
      try {
        ctx.close();
      } catch {
        /* já fechado */
      }
    },
    setLevel(v) {
      level = v;
      apply();
    },
  };
}

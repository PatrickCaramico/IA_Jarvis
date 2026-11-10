/**
 * clapDetector.js — detecção de PALMA DUPLA a partir da energia do áudio (função pura).
 *
 * Não acessa microfone nem grava nada: recebe a energia (RMS 0..1, já filtrada em passa-alta
 * ~1 kHz) de quadros curtos (~10 ms) e o instante em ms, e devolve "double" quando reconhece
 * exatamente duas palmas. A mesma lógica existe em Python (scripts/clap_detector.py) e as duas
 * são testadas com as sequências de tests/fixtures/clap_sequences.json.
 *
 * Regras (valores iniciais, ajustáveis):
 * - piso de ruído adaptativo (média móvel); pico = energia > max(piso × fator, mínimo absoluto)
 * - fator e mínimo absoluto vêm da sensibilidade (1 = menos sensível, 10 = mais sensível)
 * - recuperação de 60 ms após cada pico; pico com mais de 120 ms é fala/ruído (descarta a sequência)
 * - palma dupla = 2 picos com intervalo de 120 a 800 ms, com ~300 ms de silêncio antes
 *   e sem novo pico logo depois (400–900 ms, proporcional ao intervalo) → rejeita 3+ palmas
 * - depois de disparar, espera `cooldownMs` (3 s na página; 30 s no Ouvinte de Palmas)
 */

export const CLAP_DEFAULTS = Object.freeze({
  minGapMs: 120,
  maxGapMs: 800,
  preSilenceMs: 300,
  postSilenceMinMs: 400,
  postSilenceMaxMs: 900,
  refractoryMs: 60,
  maxPeakMs: 120,
  cooldownMs: 3000,
  floorTauMs: 600,
});

export function sensitivityParams(sensitivity = 5) {
  const s = Math.min(10, Math.max(1, Math.round(Number(sensitivity) || 5)));
  return {
    factor: 12 - (s - 1),                 // 12× (s=1) até 3× (s=10) acima do piso
    minAbs: 0.12 - ((s - 1) * 0.1) / 9,   // 0,12 (s=1) até 0,02 (s=10) de RMS
  };
}

export function postSilenceFor(gapMs, opts = CLAP_DEFAULTS) {
  return Math.min(opts.postSilenceMaxMs, Math.max(opts.postSilenceMinMs, gapMs * 1.25));
}

export function createClapDetector(options = {}) {
  const opts = { ...CLAP_DEFAULTS, ...options };
  let { factor, minAbs } = sensitivityParams(options.sensitivity ?? 5);

  let floor = null;
  let lastT = null;
  let lastLoudEnd = -Infinity;
  let inPeak = false;
  let peakStart = 0;
  let peakTooLong = false;
  let refractoryUntil = -Infinity;
  let cooldownUntil = -Infinity;
  let claps = [];

  function onset(t) {
    inPeak = true;
    peakStart = t;
    peakTooLong = false;
    refractoryUntil = t + opts.refractoryMs;
    if (t < cooldownUntil) return;
    const quietBefore = t - lastLoudEnd;
    if (claps.length === 0) {
      if (quietBefore >= opts.preSilenceMs) claps = [t];
    } else if (claps.length === 1) {
      const gap = t - claps[0];
      if (gap < opts.minGapMs) claps = [];
      else if (gap <= opts.maxGapMs) claps.push(t);
      else claps = quietBefore >= opts.preSilenceMs ? [t] : [];
    } else {
      claps = []; // terceira palma logo em seguida: não é palma dupla
    }
  }

  function process(energy, t) {
    const e = Number.isFinite(energy) ? Math.max(0, energy) : 0;
    const dt = lastT == null ? 10 : Math.max(1, t - lastT);
    lastT = t;
    const alpha = 1 - Math.exp(-dt / opts.floorTauMs);
    if (floor == null) floor = e;
    const threshold = Math.max(floor * factor, minAbs);
    const loud = e > threshold;

    if (inPeak) {
      if (loud) {
        if (t - peakStart > opts.maxPeakMs) {
          peakTooLong = true;
          claps = [];
          floor += (e - floor) * alpha; // som contínuo: o piso acompanha
        }
      } else {
        inPeak = false;
        lastLoudEnd = t;
        if (peakTooLong) claps = [];
        peakTooLong = false;
        floor += (e - floor) * alpha;
      }
    } else if (loud && t >= refractoryUntil) {
      onset(t);
    } else if (!loud) {
      floor += (e - floor) * alpha;
    }

    if (claps.length === 2 && !inPeak) {
      const gap = claps[1] - claps[0];
      if (t - claps[1] >= postSilenceFor(gap, opts)) {
        claps = [];
        cooldownUntil = t + opts.cooldownMs;
        return "double";
      }
    }
    return null;
  }

  return {
    process,
    setSensitivity(sensitivity) {
      ({ factor, minAbs } = sensitivityParams(sensitivity));
    },
    reset() {
      floor = null;
      lastT = null;
      lastLoudEnd = -Infinity;
      inPeak = false;
      peakTooLong = false;
      refractoryUntil = -Infinity;
      cooldownUntil = -Infinity;
      claps = [];
    },
    get state() {
      return { floor, claps: [...claps], inPeak, cooldownUntil };
    },
  };
}

// ---------------------------------------------------------------- sequências de teste
// Gerador determinístico usado pelos testes (o Python usa o mesmo algoritmo).
function parkMiller(seed) {
  let state = Math.max(1, Math.floor(seed) % 2147483647);
  return () => {
    state = (state * 48271) % 2147483647;
    return state / 2147483647;
  };
}

export function expandSequence(seq, frameMs = 10) {
  const rand = parkMiller(seq.seed ?? 1);
  const frames = [];
  const total = seq.duration_ms;
  for (let t = 0; t < total; t += frameMs) {
    let base = seq.noise ?? 0.005;
    for (const ev of seq.events || []) {
      if (ev.type === "noise_level" && t >= ev.t) base = ev.level;
    }
    let e = base * (0.6 + 0.8 * rand());
    for (const ev of seq.events || []) {
      const dtEv = t - ev.t;
      if (ev.type === "clap" && dtEv >= 0 && dtEv < 30) {
        e = Math.max(e, ev.level * (1 - (dtEv / 30) * 0.7));
      } else if (ev.type === "sustained" && dtEv >= 0 && dtEv < ev.dur) {
        e = Math.max(e, ev.level);
      } else if (ev.type === "speech" && dtEv >= 0 && dtEv < ev.dur) {
        if (dtEv % 250 < 180) e = Math.max(e, ev.level);
      }
    }
    frames.push([e, t]);
  }
  return frames;
}

export function countDoubles(seq, frameMs = 10, extra = {}) {
  const det = createClapDetector({ sensitivity: seq.sensitivity ?? 5, cooldownMs: seq.cooldown_ms ?? 3000, ...extra });
  let n = 0;
  for (const [e, t] of expandSequence(seq, frameMs)) {
    if (det.process(e, t) === "double") n += 1;
  }
  return n;
}

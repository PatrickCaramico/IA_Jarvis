// V7.12: o texto de estado em cima do orbe da tela de bloqueio (igual ao vídeo).
export function orbeLabel({ phase, jarvisState, listening }) {
  if (phase === "scanning") return "ESCANEANDO";
  if (phase === "verified") return "IDENTIDADE CONFIRMADA";
  if (phase === "failed") return "ACESSO NEGADO";
  if (phase === "pin") return "LIBERAÇÃO POR PIN";
  if (jarvisState === "speaking") return "FALANDO";
  if (jarvisState === "processing") return "ANALISANDO";
  if (listening) return "OUVINDO";
  return "EM ESPERA";
}

// as curvas do orbe de linhas (TangleOrb): sempre o mesmo desenho
function rng(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

export function buildCurves(count, seed = 7121) {
  const r = rng(seed);
  return Array.from({ length: count }, () => ({
    base: 0.86 + r() * 0.16,
    k1: 2 + Math.floor(r() * 3),
    a1: 0.03 + r() * 0.05,
    s1: (r() - 0.5) * 0.5,
    p1: r() * Math.PI * 2,
    k2: 5 + Math.floor(r() * 4),
    a2: 0.01 + r() * 0.025,
    s2: (r() - 0.5) * 0.9,
    p2: r() * Math.PI * 2,
    tilt: (r() - 0.5) * 0.25,
    rot: (r() - 0.5) * 0.08,
    alpha: 0.35 + r() * 0.5,
    width: 0.7 + r() * 1.1,
  }));
}

/** Raio da curva c no ângulo t, no tempo s (segundos), com a energia e (1 = repouso). */
export function radius(c, t, s, e) {
  return c.base + e * (c.a1 * Math.sin(c.k1 * t + c.p1 + s * c.s1) + c.a2 * Math.sin(c.k2 * t + c.p2 + s * c.s2));
}

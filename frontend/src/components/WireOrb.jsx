import { useMemo } from "react";

/**
 * WireOrb — orbe de "fios" azuis (anel de fios luminosos com pontos de energia).
 * Somente visual. Estados: "idle" | "processing" | "speaking".
 * Usado só na tela principal; a tela de bloqueio continua com o ArcReactorHUD.
 */

const TWO_PI = Math.PI * 2;
const WIRES = 18;

// Gerador pseudoaleatório determinístico: o desenho é sempre o mesmo.
function makeRng(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

function buildWires() {
  const rand = makeRng(20261020);
  return Array.from({ length: WIRES }, () => {
    const radius = 150 + (rand() - 0.5) * 20;
    const a1 = 4 + rand() * 12;
    const m1 = 2 + Math.floor(rand() * 4);
    const p1 = rand() * TWO_PI;
    const a2 = 2 + rand() * 7;
    const m2 = 5 + Math.floor(rand() * 5);
    const p2 = rand() * TWO_PI;
    let d = "";
    const steps = 160;
    for (let i = 0; i < steps; i += 1) {
      const t = (i / steps) * TWO_PI;
      const r = radius + a1 * Math.sin(m1 * t + p1) + a2 * Math.sin(m2 * t + p2);
      d += `${i ? "L" : "M"}${(200 + r * Math.cos(t)).toFixed(1)} ${(200 + r * Math.sin(t)).toFixed(1)}`;
    }
    return {
      d: `${d}Z`,
      dur: 28 + rand() * 42,
      reverse: rand() > 0.5,
      delay: -rand() * 40,
      width: 0.5 + rand() * 0.8,
      opacity: 0.35 + rand() * 0.55,
    };
  });
}

// Pontos de energia sobre o anel (como na referência).
const NODES = [20, 118, 205, 292].map((deg) => {
  const t = (deg * Math.PI) / 180;
  return { x: 200 + 150 * Math.cos(t), y: 200 + 150 * Math.sin(t) };
});

// Estados do Branding Book 4.2: idle (repouso), listening, processing, speaking.
// flash: "success" | "error" | null (verde ou vermelho por um instante).
const STATE_TEXT = { idle: "EM ESPERA", listening: "OUVINDO", processing: "ANALISANDO", speaking: "FALANDO" };

export default function WireOrb({ state = "idle", flash = null }) {
  const wires = useMemo(buildWires, []);
  const label = flash === "error" ? "ERRO" : flash === "success" ? "CONCLUÍDO" : STATE_TEXT[state] || "";

  return (
    <div className={`wo wo-${state} ${flash ? `wo-flash-${flash}` : ""}`} role="img" aria-label={`Orbe do JARVIS: ${label.toLowerCase()}`}>
      <svg viewBox="0 0 400 400" aria-hidden="true">
        <defs>
          <radialGradient id="wo-glow" cx="50%" cy="50%" r="50%">
            <stop offset="55%" stopColor="currentColor" stopOpacity="0" />
            <stop offset="82%" stopColor="currentColor" stopOpacity="0.16" />
            <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
          </radialGradient>
        </defs>

        <circle className="wo-halo" cx="200" cy="200" r="190" fill="url(#wo-glow)" />
        <circle cx="200" cy="200" r="118" fill="none" stroke="currentColor" strokeOpacity="0.12" strokeWidth="1" strokeDasharray="2 7" />

        {wires.map((w, i) => (
          <g
            key={i}
            className="wo-wire"
            style={{
              "--d": w.dur,
              animationDirection: w.reverse ? "reverse" : "normal",
              animationDelay: `${w.delay}s`,
            }}
          >
            <path d={w.d} fill="none" stroke="currentColor" strokeWidth={w.width} strokeOpacity={w.opacity} />
          </g>
        ))}

        <g className="wo-nodes">
          {NODES.map((n, i) => (
            <g key={i}>
              <circle cx={n.x} cy={n.y} r="6" fill="currentColor" opacity="0.25" />
              <circle cx={n.x} cy={n.y} r="2.6" fill="#e6faff" />
            </g>
          ))}
        </g>
      </svg>
    </div>
  );
}

import FaceScanOverlay from "./FaceScanOverlay.jsx";

// Orbe estilo "Reator Arc". Estados: "idle" | "processing" | "speaking".
// Cada anel gira em uma camada própria; a velocidade e o pulso mudam conforme o estado.

const TICKS = Array.from({ length: 72 }, (_, i) => i);

// Duração (animation-duration) de cada camada por estado.
const TIMING = {
  idle: { outer: "60s", dashed: "80s", coil: "45s", pulse: "4s", core: "3s" },
  processing: { outer: "8s", dashed: "5s", coil: "2.5s", pulse: "1.1s", core: "0.6s" },
  speaking: { outer: "40s", dashed: "50s", coil: "18s", pulse: "0.7s", core: "0.5s" },
};

const TONE = {
  ok: "border-arc-100 shadow-[0_0_45px_#4fdcff]",
  fail: "border-red-400 shadow-[0_0_35px_#ef4444]",
  default: "border-arc-300 shadow-arc",
};

// photoUrl: mostra a foto de perfil no lugar do núcleo. tone: "ok" | "fail" (cor da moldura da foto).
// fanMode: ativa as cores do clube (verde Palmeiras #046538) com o escudo no centro do reator.
export default function ArcReactorHUD({
  state = "idle",
  photoUrl = null,
  tone = "default",
  fanMode = false,
  fanShieldUrl = `${import.meta.env.BASE_URL}fan/palmeiras/palmeiras_shield.png`,
  liveFrame = null, // seção 16: { frame, box, phase, ... } — câmera ao vivo dentro do orbe
  className = "",
}) {
  const t = TIMING[state] ?? TIMING.idle;
  const speaking = state === "speaking";
  const processing = state === "processing";

  // Paleta de cores: Alviverde no modo torcedor, azul Stark no modo normal
  const colors = fanMode
    ? {
        pulse: "bg-emerald-500/30",
        ripple: "border-emerald-400/70",
        ticks: "text-emerald-400/80",
        dashed1: "#10b981",
        dashed2: "#34d399",
        coilBase: "#046538",
        coilGlow: "#34d399",
        coilDrop: "drop-shadow-[0_0_14px_rgba(16,185,129,0.9)]",
        innerRing: "#10b981",
        processing: "#6ee7b7",
      }
    : {
        pulse: "bg-arc-400/25",
        ripple: "border-arc-300/60",
        ticks: "text-arc-400/70",
        dashed1: "#1fc2f5",
        dashed2: "#4fdcff",
        coilBase: "#0d5f88",
        coilGlow: "#4fdcff",
        coilDrop: "drop-shadow-[0_0_8px_rgba(31,194,245,0.8)]",
        innerRing: "#1fc2f5",
        processing: "#c9f6ff",
      };

  return (
    <div
      className={`arc-hud relative mx-auto aspect-square w-56 sm:w-64 md:w-72 max-h-[34vh] ${className}`}
      role="img"
      aria-label={`Orbe do JARVIS: ${state}`}
    >
      {/* V5.8: anel dourado */}
      <span className="arc-gold-ring" aria-hidden="true" />
      {/* Aura externa */}
      <div
        className={`absolute inset-0 animate-arc-pulse rounded-full blur-3xl ${colors.pulse}`}
        style={{ animationDuration: t.pulse }}
      />

      {/* Ondas sonoras quando está falando */}
      {speaking &&
        [0, 0.66, 1.33].map((delay) => (
          <div
            key={delay}
            className={`absolute inset-0 animate-ripple rounded-full border ${colors.ripple}`}
            style={{ animationDelay: `${delay}s` }}
          />
        ))}

      {/* Anel externo com marcações (régua) */}
      <div className={`absolute inset-0 animate-spin-slow ${colors.ticks}`} style={{ animationDuration: t.outer }}>
        <svg viewBox="0 0 200 200" className="h-full w-full">
          {TICKS.map((i) => (
            <line
              key={i}
              x1="100"
              y1="3"
              x2="100"
              y2={i % 6 === 0 ? 13 : 8}
              stroke="currentColor"
              strokeWidth={i % 6 === 0 ? 1.6 : 0.8}
              transform={`rotate(${i * 5} 100 100)`}
            />
          ))}
        </svg>
      </div>

      {/* Anel tracejado, girando ao contrário */}
      <div className="absolute inset-[7%] animate-spin-reverse" style={{ animationDuration: t.dashed }}>
        <svg viewBox="0 0 200 200" className="h-full w-full">
          <circle cx="100" cy="100" r="96" fill="none" stroke={colors.dashed1} strokeOpacity="0.45" strokeWidth="1.5" strokeDasharray="2 6" />
          <circle cx="100" cy="100" r="88" fill="none" stroke={colors.dashed2} strokeOpacity="0.8" strokeWidth="2" strokeDasharray="60 120 30 150" />
        </svg>
      </div>

      {/* Anel-bobina: 10 segmentos, como as bobinas do reator */}
      <div className="absolute inset-[18%] animate-spin-slow" style={{ animationDuration: t.coil }}>
        <svg viewBox="0 0 200 200" className={`h-full w-full ${colors.coilDrop}`}>
          <circle cx="100" cy="100" r="88" fill="none" stroke={colors.coilBase} strokeWidth="14" strokeDasharray="47.5 8.3" />
          <circle cx="100" cy="100" r="88" fill="none" stroke={colors.coilGlow} strokeOpacity="0.9" strokeWidth="3" strokeDasharray="47.5 8.3" />
          <circle cx="100" cy="100" r="70" fill="none" stroke={colors.innerRing} strokeOpacity="0.5" strokeWidth="1.2" />
        </svg>
      </div>

      {/* Anel de processamento (só aparece enquanto pensa) */}
      {processing && (
        <div className="absolute inset-[13%] animate-spin-slow" style={{ animationDuration: "1.4s" }}>
          <svg viewBox="0 0 200 200" className="h-full w-full">
            <circle cx="100" cy="100" r="94" fill="none" stroke={colors.processing} strokeWidth="2.5" strokeLinecap="round" strokeDasharray="90 500" />
          </svg>
        </div>
      )}

      {/* Centro: câmera ao vivo (escaneamento), Escudo do Palmeiras (Modo Torcedor), Foto de Perfil ou Núcleo */}
      {liveFrame?.frame ? (
        <div className="arc-live absolute inset-[17%] overflow-hidden rounded-full">
          <FaceScanOverlay scan={liveFrame} variant="orb" />
        </div>
      ) : fanMode ? (
        <div
          className="absolute inset-[26%] overflow-hidden rounded-full border-2 border-emerald-400/90 shadow-[0_0_35px_rgba(16,185,129,0.8)] bg-[#046538] flex items-center justify-center p-0.5"
        >
          <img
            src={fanShieldUrl}
            alt="Palmeiras"
            className="h-full w-full object-cover rounded-full select-none"
          />
          {/* Brilho holográfico diagonal */}
          <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-transparent via-white/20 to-transparent pointer-events-none" />
          {processing && <div className="scan-line absolute inset-x-0 top-0 h-1/2 bg-emerald-400/40" />}
        </div>
      ) : photoUrl ? (
        <div
          className={`absolute inset-[30%] overflow-hidden rounded-full border-2 transition-shadow duration-500 ${TONE[tone] ?? TONE.default}`}
        >
          <img src={photoUrl} alt="Foto de perfil" className="h-full w-full object-cover" />
          {processing && <div className="scan-line absolute inset-x-0 top-0 h-1/2" />}
        </div>
      ) : (
        <div
          className="absolute inset-[36%] animate-core-flicker rounded-full shadow-arc"
          style={{
            animationDuration: t.core,
            background: "radial-gradient(circle, #ffffff 0%, #c9f6ff 22%, #4fdcff 55%, #0a9fd6 100%)",
          }}
        >
          <div className="absolute inset-[22%] rounded-full border border-white/70" />
        </div>
      )}
    </div>
  );
}

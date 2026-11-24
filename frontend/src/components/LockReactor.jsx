import { useEffect, useMemo, useState } from "react";
import ArcReactorHUD from "./ArcReactorHUD.jsx";
import { ReactorShape, useReactor } from "./ReactorOrb.jsx";
import { cssVars } from "../utils/reactor.js";
import { lockReactorShape, reactorStateClass, secondsDelay } from "../utils/lockLook.js";

// V9.5.0: o reator da tela de bloqueio.
// - Usa o reator personalizado no 🎨 REATOR (forma, cor, brilho); sem personalização, o Reator Arc de sempre.
// - Um anel de estado em volta: pulsa ouvindo, varre reconhecendo o rosto, verde ao liberar, vermelho ao recusar.
// - Anel dos segundos: um ponteiro fino dá a volta em 60 s, no compasso do relógio (só CSS, transform).
// - Ao liberar, os anéis se abrem para fora (a central entra logo depois).
const TICKS = Array.from({ length: 60 }, (_, i) => i);

export default function LockReactor({ state = "idle", phase = "ready", listening = false, photoUrl = null, tone = "default", className = "" }) {
  const cfg = useReactor();
  const shape = lockReactorShape(cfg);
  const stateCls = reactorStateClass({ phase, listening, speaking: state === "speaking" });
  // o ponteiro acerta o segundo ao montar e quando a aba volta ao foco (a animação pausa com a aba escondida)
  const [delay, setDelay] = useState(() => secondsDelay());
  useEffect(() => {
    const sync = () => { if (!document.hidden) setDelay(secondsDelay()); };
    document.addEventListener("visibilitychange", sync);
    return () => document.removeEventListener("visibilitychange", sync);
  }, []);
  const ticks = useMemo(() => TICKS.map((i) => {
    const a = (i / 60) * Math.PI * 2;
    const r1 = i % 5 === 0 ? 90 : 93;
    return <line key={i} x1={100 + r1 * Math.sin(a)} y1={100 - r1 * Math.cos(a)} x2={100 + 97 * Math.sin(a)} y2={100 - 97 * Math.cos(a)} className={i % 5 === 0 ? "is-major" : ""} />;
  }), []);

  let core;
  if (shape === "classic") {
    core = <ArcReactorHUD state={state} photoUrl={photoUrl} tone={tone} liveFrame={null} className={className} />;
  } else if (shape === "reator") {
    // o Reator Arc com a cor escolhida (gira o tom, como na central)
    core = (
      <div className={`rx-wrap rx-reator rx-custom${cfg.contrast !== 100 ? " rx-hc" : ""}`} style={cssVars(cfg)}>
        <ArcReactorHUD state={state} photoUrl={photoUrl} tone={tone} liveFrame={null} className={className} />
      </div>
    );
  } else {
    core = (
      <div className={`lr-shape rx-wrap rx-${shape} rx-custom${cfg.glow === 0 ? " rx-noglow" : ""}${cfg.contrast !== 100 ? " rx-hc" : ""}`} style={cssVars(cfg)}>
        <ReactorShape cfg={cfg} state={state === "processing" ? "processing" : listening ? "listening" : state} />
      </div>
    );
  }

  return (
    <div className={`lr ${stateCls} lr-${shape === "classic" ? "classic" : "custom"}`} style={shape !== "classic" ? cssVars(cfg) : undefined}>
      <svg className="lr-seconds" viewBox="0 0 200 200" aria-hidden="true" focusable="false">
        <g className="lr-ticks">{ticks}</g>
      </svg>
      <span className="lr-hand" style={{ animationDelay: delay }} aria-hidden="true"><i /></span>
      <span className="lr-state" aria-hidden="true"><i /><b /></span>
      {phase === "verified" && <span className="lr-burst" aria-hidden="true"><i /><i /><i /></span>}
      {core}
    </div>
  );
}

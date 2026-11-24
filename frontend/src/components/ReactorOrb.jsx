import { useEffect, useState } from "react";
import ArcReactorHUD from "./ArcReactorHUD.jsx";
import TangleOrb from "./TangleOrb.jsx";
import WireOrb from "./WireOrb.jsx";
import { EVENT, cssVars, hexToRgb, isDefault, load } from "../utils/reactor.js";

// V9.4.2: o orbe do centro da central na forma e na cor que o senhor escolheu (🎨 REATOR). Sem personalização,
// é exatamente o orbe de fios de antes. Fica salvo neste aparelho.

/** Minimal: três anéis e um núcleo, só com CSS (transform/opacity) — a forma mais leve. */
function MinimalOrb({ state }) {
  return (
    <div className={`rxm rxm-${state}`} role="img" aria-label="Orbe do JARVIS">
      <i className="rxm-ring rxm-r1" />
      <i className="rxm-ring rxm-r2" />
      <i className="rxm-ring rxm-r3" />
      <b className="rxm-core" />
    </div>
  );
}

export function useReactor() {
  const [cfg, setCfg] = useState(load);
  useEffect(() => {
    const on = (e) => setCfg(e.detail || load());
    window.addEventListener(EVENT, on);
    return () => window.removeEventListener(EVENT, on);
  }, []);
  return cfg;
}

export function ReactorShape({ cfg, state = "idle", flash = null }) {
  const st = state === "listening" ? "listening" : state;
  if (cfg.shape === "reator") return <ArcReactorHUD state={st === "listening" ? "speaking" : st} />;
  // V9.4.2: na central, versão leve e a 30 quadros por segundo (medido: a 60 qps custava ~18x o orbe de fios)
  if (cfg.shape === "emaranhado") return <TangleOrb state={st} rgb={hexToRgb(cfg.color)} lite fps={30} />;
  if (cfg.shape === "minimal") return <MinimalOrb state={st} />;
  return <WireOrb state={st} flash={flash} wires={cfg.wires} />;
}

export default function ReactorOrb({ state = "idle", flash = null, cfg: given = null }) {
  const own = useReactor();
  const cfg = given || own;
  const custom = !isDefault(cfg);
  return (
    <div className={`rx-wrap rx-${cfg.shape}${custom ? " rx-custom" : ""}${cfg.glow === 0 ? " rx-noglow" : ""}${cfg.contrast !== 100 ? " rx-hc" : ""}`}
      style={custom ? cssVars(cfg) : undefined}>
      <ReactorShape cfg={cfg} state={state} flash={flash} />
    </div>
  );
}

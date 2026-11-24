// V8.11.1: centro da central renovado, sem mexer no reator (o orbSlot continua o mesmo):
// - linha de estado que diz o que está acontecendo, com o tempo do "pensando" e o botão de cancelar/parar
//   (antes ficava só "PROCESSANDO" piscando, e parecia travado);
// - telemetria em volta do reator: processador, memória, disco e o próximo compromisso;
// - anel de mira em volta do reator, que acompanha o estado (gira mais rápido pensando, âmbar falando).
import { useEffect, useState } from "react";
import { pctText, usageLevel } from "../utils/deskSkills.js";
import { diskText, nextAgenda, stateHint } from "../utils/hudCenter.js";

/** Segundos desde que `active` ficou verdadeiro (0 quando falso). */
function useElapsed(active) {
  const [sec, setSec] = useState(0);
  useEffect(() => {
    setSec(0);
    if (!active) return undefined;
    const t0 = Date.now();
    const t = setInterval(() => setSec(Math.floor((Date.now() - t0) / 1000)), 1000);
    return () => clearInterval(t);
  }, [active]);
  return sec;
}

/** Busca periódica que pausa com a aba escondida e some em silêncio se a rota não existir (modo nuvem). */
function usePolled(api, path, everyMs) {
  const [data, setData] = useState(null);
  useEffect(() => {
    if (!api) return undefined;
    let alive = true;
    const tick = () => {
      if (typeof document !== "undefined" && document.hidden) return;
      api(path, { timeout: 8000 }).then((d) => alive && setData(d)).catch(() => alive && setData(null));
    };
    tick();
    const t = setInterval(tick, everyMs);
    return () => { alive = false; clearInterval(t); };
  }, [api, path, everyMs]);
  return data;
}

export function StateHint({ jarvisState, listening, interim, micOk, onCancel, doing = "" }) {
  const elapsed = useElapsed(jarvisState === "processing" && !listening);
  const hint = stateHint({ state: jarvisState, listening, interim, elapsed, micOk, doing });
  return (
    <p className={`hc-hint is-${hint.tone}`} aria-live="polite">
      <span>{hint.text}</span>
      {hint.cancel && onCancel && (
        <button type="button" className="hc-cancel" onClick={onCancel} title="Cancelar (Esc)">
          ✕ {jarvisState === "speaking" ? "PARAR" : "CANCELAR"}
        </button>
      )}
    </p>
  );
}

function Readout({ side, label, value, level = "", bar = null, sub = null }) {
  return (
    <li className={`hc-readout ${level}`} data-side={side}>
      <span className="hc-r-label">{label}</span>
      <b className="hc-r-value">{value}</b>
      {bar !== null && <i className="hc-r-bar"><s style={{ width: `${Math.min(100, Math.max(0, Number(bar) || 0))}%` }} /></i>}
      {sub && <small className="hc-r-sub">{sub}</small>}
    </li>
  );
}

/** Anel e leituras em volta do reator (filhos diretos de .hl-orb; nada de <div>, que lá vira o próprio reator). */
export function OrbTelemetry({ api, connected }) {
  const sys = usePolled(api, "/api/system", 6000);
  const agenda = usePolled(api, "/api/agenda/next?limit=1", 5 * 60 * 1000);
  const next = nextAgenda(agenda?.items);
  const hasSys = connected && sys && (sys.cpu_percent != null || sys.ram_percent != null);
  return (
    <>
      <svg className="hc-ring" viewBox="0 0 200 200" aria-hidden="true" focusable="false">
        <circle className="hc-ring-ticks" cx="100" cy="100" r="97" />
        <g className="hc-ring-spin">
          <circle className="hc-ring-arc" cx="100" cy="100" r="92" pathLength="100" strokeDasharray="14 11" />
        </g>
        <g className="hc-ring-spin is-rev">
          <circle className="hc-ring-arc is-thin" cx="100" cy="100" r="88" pathLength="100" strokeDasharray="3 22" />
        </g>
      </svg>
      {hasSys && (
        <ul className="hc-telemetry" data-side="left" aria-label="Uso do PC">
          <Readout side="left" label="PROCESSADOR" value={pctText(sys.cpu_percent)} level={usageLevel(sys.cpu_percent)} bar={sys.cpu_percent} />
          <Readout side="left" label="MEMÓRIA" value={pctText(sys.ram_percent)} level={usageLevel(sys.ram_percent)} bar={sys.ram_percent} />
        </ul>
      )}
      {(hasSys || next) && (
        <ul className="hc-telemetry" data-side="right" aria-label="Disco e agenda">
          {hasSys && sys.disk_free_gb != null && <Readout side="right" label="DISCO LIVRE" value={diskText(sys.disk_free_gb)} />}
          {next && <Readout side="right" label="PRÓXIMO" value={next.when} sub={next.title} />}
        </ul>
      )}
    </>
  );
}

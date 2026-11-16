import { useEffect, useState } from "react";
import ProgressBar from "./ProgressBar.jsx";
import "../update-steps.css";

// V8.1.7: tela de ATUALIZANDO O JARVIS com as etapas de verdade (o PC conta em /api/system/update/progress):
// baixar -> montar a interface nova (com o JARVIS ainda ligado) -> reiniciar -> pronto.
// Mostra de qual versão para qual, o tempo passando e o que mudou.
const STEPS = [
  ["baixado", "Baixar a versão nova", "⬇"],
  ["interface", "Montar a interface nova", "🧩"],
  ["reiniciando", "Reiniciar os sistemas", "⟳"],
  ["pronto", "Abrir a versão nova", "✓"],
];
const ORDER = { baixando: 0, baixado: 1, interface: 1, reiniciando: 2, pronto: 3 };

export function stepState(index, etapa) {
  const at = ORDER[etapa] ?? 0;
  if (etapa === "pronto") return "done";
  if (index < at) return "done";
  return index === at ? "now" : "next";
}

export default function UpdateSteps({ updating, pct, current }) {
  const [secs, setSecs] = useState(0);
  useEffect(() => {
    const start = Date.now();
    const t = setInterval(() => setSecs(Math.round((Date.now() - start) / 1000)), 1000);
    return () => clearInterval(t);
  }, []);
  const info = updating.info || {};
  const etapa = updating.etapa || "baixado";
  const notes = (info.notas || []).slice(0, 4);
  return (
    <div className="us">
      <div className="us-head">
        <span className="us-spark" aria-hidden="true" />
        <div>
          <div className="us-title">ATUALIZANDO O JARVIS</div>
          <div className="us-ver">
            <span>v{current}</span><i>→</i><b>{info.changed === false ? "mesma versão" : "versão nova"}</b>
            {info.depois && <code>{info.depois}</code>}
          </div>
        </div>
        <span className="us-time" aria-label="Tempo">{Math.floor(secs / 60)}:{String(secs % 60).padStart(2, "0")}</span>
      </div>
      <ol className="us-steps">
        {STEPS.map(([id, label, ico], i) => {
          const st = stepState(i, etapa);
          return (
            <li key={id} className={`is-${st}`}>
              <span className="us-dot" aria-hidden="true">{st === "done" ? "✓" : ico}</span>
              <span className="us-label">{label}</span>
              {st === "now" && <span className="us-live" aria-hidden="true"><i /><i /><i /></span>}
            </li>
          );
        })}
      </ol>
      <ProgressBar pct={pct} label={updating.stage || "Atualizando"} />
      <p className="us-msg" role="status">{updating.message}</p>
      {notes.length > 0 && (
        <div className="us-notes">
          <small>O QUE MUDOU</small>
          <ul>{notes.map((n) => <li key={n}>{n.replace(/^JARVIS \d+\.\d+\.\d+:?\s*/, "")}</li>)}</ul>
        </div>
      )}
      {!updating.slow && <p className="us-foot">Leva uns segundos. Depois eu volto e faço a verificação do seu rosto.</p>}
    </div>
  );
}

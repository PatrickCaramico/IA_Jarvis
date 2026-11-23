import { useEffect, useState } from "react";
import ProgressBar from "./ProgressBar.jsx";
import { footText, versionLine, whatsNew } from "../utils/updateScreen.js";
import "../update-steps.css";

// V8.1.7: tela de ATUALIZANDO O JARVIS com as etapas de verdade (o PC conta em /api/system/update/progress):
// baixar -> montar a interface nova (com o JARVIS ainda ligado) -> reiniciar -> pronto.
// V8.12.2: anel com a porcentagem no lugar do círculo girando, "8.12.1 → 8.12.2" no lugar do código do commit,
// "O que há de novo" com os destaques do CHANGELOG baixado e o fim sem falar em verificação do rosto.
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
  const ver = versionLine(current, info);
  const news = whatsNew(info);
  const value = Math.max(0, Math.min(100, Math.round(pct || 0)));
  const foot = footText(secs, updating.slow);
  return (
    <div className={`us${etapa === "pronto" ? " is-ready" : ""}`}>
      <div className="us-head">
        <span className="us-ring" style={{ "--us-pct": `${value}%` }} aria-hidden="true">
          <b>{value}<small>%</small></b>
        </span>
        <div className="us-head-text">
          <div className="us-title">{etapa === "pronto" ? "PRONTO!" : ver.to ? `ATUALIZANDO PARA A ${ver.to}` : "ATUALIZANDO O JARVIS"}</div>
          <div className="us-ver">
            <span>v{ver.from}</span><i>→</i>
            {ver.same ? <b>mesma versão</b> : ver.to ? <b>v{ver.to}</b> : <b>versão nova</b>}
            {ver.code && <code>{ver.code}</code>}
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
      {news.length > 0 && (
        <div className="us-notes">
          <small>O QUE HÁ DE NOVO</small>
          <ul>{news.map((n) => <li key={n}>{n}</li>)}</ul>
        </div>
      )}
      {foot && <p className={`us-foot${secs >= 150 ? " is-warn" : ""}`}>{foot}</p>}
    </div>
  );
}

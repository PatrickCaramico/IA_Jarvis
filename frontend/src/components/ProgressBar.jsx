import { useEffect, useRef, useState } from "react";

// V6.1: barra de progresso 0–100% das atualizações (PC e app). "target" é até onde a etapa atual pode
// chegar; a barra anda sozinha devagar até ele (nunca para de se mexer sem motivo, nunca passa da etapa).
// "exact" mostra o valor exato (download do app, em que o número é real).
export function useCreepingProgress(target, exact = false) {
  const [pct, setPct] = useState(0);
  const ref = useRef(0);
  useEffect(() => {
    if (exact) {
      ref.current = target;
      setPct(target);
      return undefined;
    }
    const t = setInterval(() => {
      const cur = ref.current;
      if (cur >= target) return;
      // quanto mais perto do limite da etapa, mais devagar
      const step = Math.max(0.15, (target - cur) * 0.06);
      ref.current = Math.min(target, cur + step);
      setPct(ref.current);
    }, 200);
    return () => clearInterval(t);
  }, [target, exact]);
  return Math.floor(pct);
}

export default function ProgressBar({ pct, label }) {
  const value = Math.max(0, Math.min(100, Math.round(pct)));
  return (
    <div className="pg-wrap" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={value} aria-label={label || "Progresso"}>
      <div className="pg-track"><span className="pg-fill" style={{ width: `${value}%` }} /></div>
      <div className="pg-row">
        <span className="pg-label">{label}</span>
        <b className="pg-num">{value}%</b>
      </div>
    </div>
  );
}

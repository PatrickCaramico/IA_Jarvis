import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { clearBrowserCaches, isLite, measureFps, score, setLite } from "../utils/perfMode.js";

// V7.2: ⚡ OTIMIZAR. Mede e arruma o que dá para arrumar neste aparelho e no PC:
// 1) resposta do JARVIS (ping), 2) fluidez da tela (quadros por segundo), 3) caches do navegador,
// 4) sobras de áudio e memória no PC, 5) sugere (ou liga) o MODO LEVE se a tela estiver pesada.
const STEPS = [
  ["ping", "Medindo a resposta do JARVIS"],
  ["fps", "Medindo a fluidez da tela"],
  ["cache", "Limpando caches antigos do navegador"],
  ["pc", "Limpando sobras de áudio e memória no PC"],
  ["lite", "Ajustando o modo de desempenho"],
];

export default function OptimizerPanel({ api, onClose }) {
  const [state, setState] = useState({});
  const [result, setResult] = useState(null);
  const [lite, setLiteState] = useState(isLite());
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;
    const mark = (id, status, detail = "") => setState((s) => ({ ...s, [id]: { status, detail } }));
    (async () => {
      mark("ping", "run");
      const times = [];
      for (let i = 0; i < 3; i += 1) {
        const t = performance.now();
        try {
          await api("/api/health", { timeout: 5000 });
          times.push(performance.now() - t);
        } catch {
          /* sem resposta */
        }
      }
      const pingMs = times.length ? Math.round(times.reduce((a, b) => a + b, 0) / times.length) : null;
      mark("ping", pingMs == null ? "warn" : "ok", pingMs == null ? "o PC não respondeu" : `${pingMs} ms`);

      mark("fps", "run");
      const fps = await measureFps(1500);
      mark("fps", fps >= 45 ? "ok" : "warn", `${fps} quadros/s`);

      mark("cache", "run");
      const cleared = await clearBrowserCaches();
      mark("cache", "ok", cleared ? `${cleared} limpo(s)` : "já estava limpo");

      mark("pc", "run");
      try {
        const r = await api("/api/system/optimize", { method: "POST", timeout: 20_000 });
        const bits = [];
        if (r.freed_mb) bits.push(`${r.freed_mb} MB liberados`);
        if (r.audio_leftovers) bits.push(`${r.audio_leftovers} áudio(s) velho(s)`);
        mark("pc", "ok", bits.join(" · ") || "tudo em ordem");
      } catch {
        mark("pc", "skip", "PC desligado ou modo nuvem");
      }

      mark("lite", "run");
      const heavy = fps < 45;
      if (heavy && !isLite()) {
        setLite(true);
        setLiteState(true);
        mark("lite", "ok", "MODO LEVE ligado (a tela estava pesada)");
      } else {
        mark("lite", "ok", isLite() ? "modo leve ligado" : "visual completo (o aparelho aguenta)");
      }
      setResult({ score: score({ fps, pingMs }), fps, pingMs, heavy });
    })();
  }, [api]);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const toggleLite = () => {
    setLite(!lite);
    setLiteState(!lite);
  };

  const icon = { run: "◌", ok: "✓", warn: "!", skip: "–" };
  return createPortal(
    <div className="opt-overlay" role="dialog" aria-modal="true" aria-label="Otimizar o JARVIS" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="opt">
        <header className="opt-head">
          <span>⚡ OTIMIZAR</span>
          <button type="button" className="opt-x" onClick={onClose} aria-label="Fechar">✕</button>
        </header>
        <div className={`opt-gauge${result ? " is-done" : ""}`} style={{ "--pct": result ? result.score : 0 }}>
          <div>
            <strong>{result ? result.score : "…"}</strong>
            <small>{result ? (result.score >= 80 ? "TUDO VOANDO" : result.score >= 55 ? "BOM" : "PESADO") : "ANALISANDO"}</small>
          </div>
        </div>
        <ul className="opt-steps">
          {STEPS.map(([id, label]) => {
            const st = state[id];
            return (
              <li key={id} className={`is-${st?.status || "wait"}`}>
                <i aria-hidden="true">{st ? icon[st.status] : "·"}</i>
                <span>{label}</span>
                {st?.detail && <small>{st.detail}</small>}
              </li>
            );
          })}
        </ul>
        <label className="opt-lite">
          <input type="checkbox" checked={lite} onChange={toggleLite} />
          <span>
            <b>Modo leve neste aparelho</b>
            <small>Tira o efeito de vidro desfocado e os brilhos pesados. Ideal para celular e notebook mais simples.</small>
          </span>
        </label>
        {result && (
          <p className="opt-note">
            {result.pingMs != null && result.pingMs > 400
              ? "A conexão com o PC está lenta: no celular, prefira o Wi-Fi de casa; no PC, feche programas pesados."
              : "Pronto. Os caches velhos saíram e o JARVIS está ajustado para este aparelho."}
          </p>
        )}
      </div>
    </div>,
    document.body,
  );
}

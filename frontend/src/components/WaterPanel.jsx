import { useCallback, useEffect, useRef, useState } from "react";
import WaterVessel from "./WaterVessel.jsx";
import { paceInfo, paceText, parseVolume, remainingMl } from "../utils/waterMath.js";
import { usePrefs } from "../utils/prefsStore.js";
import { soundManager } from "../utils/soundEffects.js";

// Painel de hidratação (seção 18). size="compact" no cartão do chat; size="full" no painel/widget.
// Sincroniza pelo evento water_updated do WebSocket (voz, cartão ou widget fixo).

const iconFor = (ml) => (ml <= 250 ? "🥛" : ml <= 400 ? "☕" : "🍶");

export default function WaterPanel({ api, size = "full", initialData = null, onInteract }) {
  const prefs = usePrefs();
  const [data, setData] = useState(initialData || { total_ml: 0, goal_ml: 2000, percentage: 0, goal_reached: false, logs: [] });
  const [busy, setBusy] = useState(false);
  const [custom, setCustom] = useState("");
  const [showCustom, setShowCustom] = useState(false);
  const [error, setError] = useState("");
  const [, setTick] = useState(0);
  const prevTotal = useRef(data.total_ml);

  const vessel = prefs.water_vessel || "glass";
  const quick = Array.isArray(prefs.water_quick_ml) && prefs.water_quick_ml.length ? prefs.water_quick_ml : [200, 300, 500];
  const soundOn = Boolean(prefs.water_sound) && !prefs.silent_mode;
  const paceOn = prefs.water_pace_hint !== false;

  const apply = useCallback((next) => {
    if (!next) return;
    if (soundOn && next.total_ml > prevTotal.current) soundManager.playWater();
    prevTotal.current = next.total_ml;
    setData(next);
  }, [soundOn]);

  useEffect(() => {
    if (initialData) apply(initialData);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialData]);

  useEffect(() => {
    if (!initialData) api("/api/water").then(apply).catch(() => {});
    const onWs = (e) => {
      if (e.detail?.type === "water_updated" && e.detail.data) {
        apply(e.detail.data);
        onInteract?.();
      }
    };
    window.addEventListener("jarvis_ws_event", onWs);
    const t = setInterval(() => setTick((n) => n + 1), 60_000); // atualiza o ritmo do dia
    return () => { window.removeEventListener("jarvis_ws_event", onWs); clearInterval(t); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const call = async (path, body) => {
    if (busy) return;
    setBusy(true);
    setError("");
    onInteract?.();
    try {
      const res = await api(path, { method: "POST", ...(body ? { body: JSON.stringify(body) } : {}) });
      apply(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const addCustom = () => {
    const ml = parseVolume(custom);
    if (!ml) {
      setError("Valor inválido. Use, por exemplo, 350 ml ou 0,5 L.");
      return;
    }
    setCustom("");
    setShowCustom(false);
    call("/api/water/add", { ml, note: "valor personalizado" });
  };

  const total = data.total_ml || 0;
  const goal = data.goal_ml || 2000;
  const pct = Math.min(100, data.percentage ?? Math.round((total / goal) * 100));
  const reached = data.goal_reached || total >= goal;
  const last = data.last || (data.logs || [])[data.logs?.length - 1];
  const pace = paceOn ? paceText(paceInfo({ totalMl: total, goalMl: goal, startHour: data.start_hour ?? 8, endHour: data.end_hour ?? 22 })) : "";

  return (
    <div className={`wp-root wp-${size}`} onPointerDown={() => onInteract?.()}>
      {size === "full" && (
        <div className="wp-head">
          <span>💧 HIDRATAÇÃO DIÁRIA</span>
          <span className={`wp-badge ${reached ? "ok" : ""}`}>{reached ? "META ATINGIDA" : `${pct}%`}</span>
          <button
            type="button"
            className="wp-reset"
            title="Zerar consumo de hoje"
            onClick={() => { if (window.confirm("Deseja zerar o registro de hidratação de hoje?")) call("/api/water/reset"); }}
          >
            RESET
          </button>
        </div>
      )}
      <div className="wp-body">
        <WaterVessel totalMl={total} goalMl={goal} vessel={vessel} size={size} />
        <div className="wp-info">
          {size === "compact" && (
            <div className="wp-compact-head">
              <span>💧 ÍNDICE DE HIDRATAÇÃO</span>
              <span className={`wp-badge ${reached ? "ok" : ""}`}>{reached ? "META ATINGIDA" : `${pct}%`}</span>
            </div>
          )}
          <div className="wp-remaining">{reached ? "Meta do dia alcançada. Bom trabalho." : `Faltam ${remainingMl(total, goal)} ml para o objetivo`}</div>
          {last && <div className="wp-last">Último: {last.time} (+{last.ml} ml)</div>}
          {pace && <div className="wp-pace">{pace}</div>}
        </div>
      </div>

      <div className="wp-actions">
        {quick.map((ml) => (
          <button key={ml} type="button" disabled={busy} onClick={() => call("/api/water/add", { ml, note: "registro rápido" })}>
            <span aria-hidden="true">{iconFor(ml)}</span> +{ml} ml
          </button>
        ))}
        <button type="button" disabled={busy} onClick={() => setShowCustom((v) => !v)} aria-expanded={showCustom}>＋ outro</button>
        <button type="button" disabled={busy || !last} onClick={() => call("/api/water/undo")} title="Desfazer o último registro">↶ desfazer</button>
      </div>
      {showCustom && (
        <form className="wp-custom" onSubmit={(e) => { e.preventDefault(); addCustom(); }}>
          <input
            autoFocus
            value={custom}
            onChange={(e) => setCustom(e.target.value)}
            placeholder="ex.: 350 ml ou 0,5 L"
            aria-label="Quantidade de água"
          />
          <button type="submit" disabled={busy}>ADICIONAR</button>
        </form>
      )}
      {error && <div className="wp-error" role="alert">{error}</div>}
    </div>
  );
}

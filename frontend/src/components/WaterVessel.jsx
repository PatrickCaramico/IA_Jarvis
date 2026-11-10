import { useEffect, useMemo, useRef, useState } from "react";
import { easeInOutCubic } from "../utils/waterMath.js";

// Recipiente de água animado (seção 18): copo, garrafa ou tanque "reator".
// SVG puro com clipPath; anima só transform/opacity. O nível e o número contam juntos.
// Registros rápidos em sequência redirecionam a animação em andamento (não empilham).

const VESSELS = {
  glass: {
    outline: "M30 12 L38 147 Q39 154 46 154 L74 154 Q81 154 82 147 L90 12 Z",
    bottom: 151,
    top: 16,
    left: 30,
    right: 90,
  },
  bottle: {
    outline: "M50 22 L50 38 Q50 46 40 52 Q32 57 32 68 L32 146 Q32 154 40 154 L80 154 Q88 154 88 146 L88 68 Q88 57 80 52 Q70 46 70 38 L70 22 Z",
    cap: "M47 6 H73 Q75 6 75 8 V20 Q75 22 73 22 H47 Q45 22 45 20 V8 Q45 6 47 6 Z",
    bottom: 151,
    top: 30,
    left: 32,
    right: 88,
  },
  reactor: {
    outline: "M60 30 A52 52 0 1 1 59.99 30 Z",
    bottom: 134,
    top: 34,
    left: 8,
    right: 112,
    reactor: true,
  },
};

const DURATION = 1200;

function useReducedMotion() {
  const [reduced, setReduced] = useState(() =>
    typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches);
  useEffect(() => {
    const mq = window.matchMedia?.("(prefers-reduced-motion: reduce)");
    if (!mq) return undefined;
    const on = () => setReduced(mq.matches);
    mq.addEventListener?.("change", on);
    return () => mq.removeEventListener?.("change", on);
  }, []);
  return reduced;
}

let uid = 0;

export default function WaterVessel({ totalMl = 0, goalMl = 2000, vessel = "glass", size = "full", onCelebrate }) {
  const shape = VESSELS[vessel] || VESSELS.glass;
  const goal = goalMl > 0 ? goalMl : 2000;
  const reduced = useReducedMotion();
  const idRef = useRef(null);
  if (idRef.current == null) { uid += 1; idRef.current = `wv${uid}`; }
  const id = idRef.current;

  const completedFor = (ml) => Math.max(0, Math.floor(ml / goal));
  const levelFor = (ml) => {
    const done = completedFor(ml);
    const rest = ml - done * goal;
    return done > 0 && rest === 0 ? 1 : rest / goal;
  };

  const [shownMl, setShownMl] = useState(totalMl);
  const [completed, setCompleted] = useState(() => (totalMl >= goal ? Math.max(0, completedFor(totalMl) - (totalMl % goal === 0 ? 1 : 0)) : 0));
  const [level, setLevel] = useState(() => levelFor(totalMl));
  const [fx, setFx] = useState({ stream: 0, splash: 0, bubbles: [], celebrate: 0, slide: 0, fade: 0 });
  const [visible, setVisible] = useState(true);
  const rootRef = useRef(null);
  const animRef = useRef({ raf: 0, timers: [] });
  const shownRef = useRef({ ml: totalMl, level: levelFor(totalMl) });
  const firstRef = useRef(true);

  // Pausa as animações contínuas fora da tela / aba oculta
  useEffect(() => {
    const el = rootRef.current;
    const onVis = () => setVisible(!document.hidden);
    document.addEventListener("visibilitychange", onVis);
    let io;
    if (el && "IntersectionObserver" in window) {
      io = new IntersectionObserver(([entry]) => setVisible(entry.isIntersecting && !document.hidden));
      io.observe(el);
    }
    return () => { document.removeEventListener("visibilitychange", onVis); io?.disconnect(); };
  }, []);

  useEffect(() => () => {
    cancelAnimationFrame(animRef.current.raf);
    animRef.current.timers.forEach(clearTimeout);
  }, []);

  useEffect(() => {
    if (firstRef.current) { firstRef.current = false; return; }
    const anim = animRef.current;
    cancelAnimationFrame(anim.raf);
    anim.timers.forEach(clearTimeout);
    anim.timers = [];

    const fromMl = shownRef.current.ml;
    const toMl = totalMl;
    const adding = toMl > fromMl;
    const crossed = completedFor(toMl) > completedFor(fromMl) && adding && toMl >= goal;
    const later = (fn, ms) => anim.timers.push(setTimeout(fn, ms));

    if (reduced) {
      shownRef.current = { ml: toMl, level: levelFor(toMl) };
      setShownMl(toMl);
      setLevel(levelFor(toMl));
      setCompleted(toMl >= goal ? completedFor(toMl) - (toMl % goal === 0 ? 1 : 0) : 0);
      setFx((f) => ({ ...f, fade: f.fade + 1 }));
      if (crossed) onCelebrate?.();
      return;
    }

    const run = (startMl, endMl, startLevel, endLevel, duration, done) => {
      const t0 = performance.now();
      const step = (now) => {
        const p = easeInOutCubic((now - t0) / duration);
        const ml = Math.round(startMl + (endMl - startMl) * p);
        const lv = startLevel + (endLevel - startLevel) * p;
        shownRef.current = { ml, level: lv };
        setShownMl(ml);
        setLevel(lv);
        if (p < 1) anim.raf = requestAnimationFrame(step);
        else done?.();
      };
      anim.raf = requestAnimationFrame(step);
    };

    if (adding) {
      const count = 4 + Math.floor(Math.random() * 5);
      const bubbles = Array.from({ length: count }, (_, i) => ({
        key: `${Date.now()}-${i}`,
        x: shape.left + 10 + Math.random() * (shape.right - shape.left - 20),
        r: 1.2 + Math.random() * 2.2,
        delay: Math.random() * 0.5,
        dur: 0.8 + Math.random() * 0.6,
      }));
      setFx((f) => ({ ...f, stream: f.stream + 1, splash: f.splash + 1, bubbles }));
      later(() => setFx((f) => ({ ...f, bubbles: [] })), 2200);
    }

    if (crossed) {
      // 1) enche até a borda  2) comemora  3) novo recipiente vazio desliza e recebe o restante
      const goalMlCross = completedFor(toMl) * goal;
      run(fromMl, goalMlCross, shownRef.current.level, 1, DURATION, () => {
        setFx((f) => ({ ...f, celebrate: f.celebrate + 1 }));
        onCelebrate?.();
        const rest = toMl - goalMlCross;
        later(() => {
          if (rest > 0) {
            setCompleted(completedFor(toMl));
            setLevel(0);
            shownRef.current = { ml: goalMlCross, level: 0 };
            setFx((f) => ({ ...f, slide: f.slide + 1 }));
            later(() => run(goalMlCross, toMl, 0, levelFor(toMl), 700), 450);
          } else {
            setCompleted(completedFor(toMl) - 1);
          }
        }, 900);
      });
    } else {
      const targetDone = toMl >= goal ? completedFor(toMl) - (toMl % goal === 0 ? 1 : 0) : 0;
      if (targetDone !== completed) setCompleted(targetDone);
      const startLevel = targetDone !== completed ? (adding ? 0 : 1) : shownRef.current.level;
      run(fromMl, toMl, startLevel, levelFor(toMl), DURATION);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [totalMl, goal]);

  const span = shape.bottom - shape.top;
  const surfaceY = shape.bottom - Math.max(0, Math.min(1, level)) * span;
  const pct = Math.min(100, Math.round((totalMl / goal) * 100));
  const label = `${totalMl} de ${goal} ml, ${pct}%`;
  const marks = useMemo(() => [0.25, 0.5, 0.75], []);
  const paused = !visible || reduced;

  return (
    <div ref={rootRef} className={`wv-root wv-${size} ${paused ? "is-paused" : ""} ${reduced ? "is-reduced" : ""}`}>
      {completed > 0 && (
        <div className="wv-done" aria-label={`${completed} recipiente${completed > 1 ? "s" : ""} concluído${completed > 1 ? "s" : ""}`}>
          {Array.from({ length: Math.min(completed, 6) }, (_, i) => <span key={i} title="Meta concluída">✓</span>)}
          {completed > 6 && <span>+{completed - 6}</span>}
        </div>
      )}
      <svg
        viewBox="0 0 120 160"
        role="img"
        aria-label={label}
        className={`wv-svg ${fx.celebrate ? "is-celebrate" : ""}`}
        key={`slide-${fx.slide}`}
        data-slide={fx.slide > 0 ? "1" : "0"}
      >
        <defs>
          <clipPath id={`${id}-clip`}><path d={shape.outline} /></clipPath>
          <linearGradient id={`${id}-grad`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#7dd3fc" stopOpacity="0.95" />
            <stop offset="100%" stopColor="#0369a1" stopOpacity="0.98" />
          </linearGradient>
          <linearGradient id={`${id}-glass`} x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.18" />
            <stop offset="40%" stopColor="#ffffff" stopOpacity="0.02" />
            <stop offset="100%" stopColor="#ffffff" stopOpacity="0.1" />
          </linearGradient>
        </defs>

        {shape.reactor && (
          <g className="wv-reactor-rings" aria-hidden="true">
            <circle cx="60" cy="82" r="57" fill="none" stroke="currentColor" strokeOpacity="0.35" strokeWidth="1" strokeDasharray="2 5" />
            <circle cx="60" cy="82" r="56" fill="none" stroke="currentColor" strokeOpacity="0.6" strokeWidth="1.6" strokeDasharray="40 80 20 100" className="wv-ring-spin" />
          </g>
        )}

        {/* Vidro */}
        <path d={shape.outline} className="wv-glass" fill="rgba(8,47,73,0.35)" />

        {/* Água recortada no formato do recipiente */}
        <g clipPath={`url(#${id}-clip)`}>
          <g transform={`translate(0 ${surfaceY.toFixed(2)})`} className={`wv-water ${fx.fade ? "is-fade" : ""}`} key={`fade-${fx.fade}`}>
            <g className={`wv-amp ${fx.splash ? "is-splash" : ""}`} key={`splash-${fx.splash}`}>
              <path className="wv-wave wv-wave2" d="M0 0 Q30 -5 60 0 T120 0 T180 0 T240 0 V200 H0 Z" fill="#38bdf8" fillOpacity="0.45" />
              <path className="wv-wave wv-wave1" d="M0 0 Q30 4 60 0 T120 0 T180 0 T240 0 V200 H0 Z" fill={`url(#${id}-grad)`} />
            </g>
          </g>
          {fx.bubbles.map((b) => (
            <circle
              key={b.key}
              className="wv-bubble"
              cx={b.x}
              cy={shape.bottom - 4}
              r={b.r}
              style={{ "--rise": `${-(shape.bottom - surfaceY - 6)}px`, animationDelay: `${b.delay}s`, animationDuration: `${b.dur}s` }}
            />
          ))}
          {fx.stream > 0 && (
            <rect
              key={`stream-${fx.stream}`}
              className="wv-stream"
              x="58.5"
              y={shape.top - 14}
              width="3"
              height={Math.max(4, surfaceY - shape.top + 14)}
              rx="1.5"
            />
          )}
        </g>

        {/* Marcas de medida e linha da meta */}
        {!shape.reactor && (
          <g className="wv-marks" aria-hidden="true">
            {marks.map((m) => {
              const y = shape.bottom - m * span;
              return (
                <g key={m}>
                  <line x1={shape.right - 9} x2={shape.right - 3} y1={y} y2={y} />
                  {size === "full" && <text x={shape.right + 3} y={y + 2}>{Math.round(goal * m)}</text>}
                </g>
              );
            })}
          </g>
        )}
        <line className="wv-goal" x1={shape.left + 2} x2={shape.right - 2} y1={shape.top} y2={shape.top} />
        {size === "full" && <text className="wv-goal-label" x="60" y={shape.top - 3} textAnchor="middle">META {goal} ml</text>}

        {/* Contorno e brilho */}
        <path d={shape.outline} fill={`url(#${id}-glass)`} className="wv-outline" />
        {shape.cap && <path d={shape.cap} className="wv-cap" />}
        {fx.celebrate > 0 && (
          <g className="wv-drops" key={`drops-${fx.celebrate}`} aria-hidden="true">
            {[-1, -0.5, 0, 0.5, 1].map((d) => (
              <circle key={d} cx={60 + d * 18} cy={shape.top} r="2" style={{ "--dx": `${d * 22}px` }} />
            ))}
          </g>
        )}
      </svg>
      <div className="wv-readout">
        <span className="wv-ml">{shownMl}</span>
        <span className="wv-goaltext">/ {goal} ml</span>
      </div>
      <span className="sr-only" aria-live="polite">{label}</span>
    </div>
  );
}

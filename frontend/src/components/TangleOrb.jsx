import { useEffect, useRef } from "react";
import { buildCurves, radius } from "../utils/lockOrbe.js";

// V7.12: orbe de linhas entrelaçadas (tela de bloqueio estilo ORBE). Desenhado num canvas: várias curvas fechadas
// que ondulam e giram devagar, com pontos de energia correndo por elas. Reage ao estado:
// idle (respira devagar) · listening (abre um pouco) · processing (gira mais rápido) · speaking (pulsa como voz).
// tone: "ok" deixa verde (identidade confirmada), "fail" vermelho. Com "reduzir movimento", fica parado.

const COLORS = { default: [90, 205, 255], ok: [74, 222, 128], fail: [251, 113, 133] };
const ENERGY = { idle: 1, listening: 1.35, processing: 1.2, speaking: 1.7 };
const SPIN = { idle: 1, listening: 1.2, processing: 2.6, speaking: 1.4 };

// V9.4.2: rgb = [R, G, B] da cor escolhida em 🎨 REATOR (sem ele, as cores de sempre)
// V9.4.2: fps limita os quadros por segundo (na central, 30: medido, o desenho a 60 qps custava ~18x o orbe de fios)
export default function TangleOrb({ state = "idle", tone = "default", lite = false, className = "", rgb = null, fps = 0 }) {
  const canvasRef = useRef(null);
  const live = useRef({ state, tone, rgb });
  useEffect(() => {
    live.current = { state, tone, rgb };
  }, [state, tone, rgb]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const g = canvas?.getContext("2d");
    if (!g) return undefined;
    const curves = buildCurves(lite ? 9 : 15);
    const dots = Array.from({ length: lite ? 3 : 6 }, (_, i) => ({ c: (i * 5) % curves.length, u: i / 6, v: 0.025 + (i % 3) * 0.012 }));
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    let raf = 0;
    let energy = 1;
    let spin = 0;
    let last = performance.now();
    let size = 0;

    const fit = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, lite ? 1.5 : 2);
      const w = canvas.clientWidth;
      size = w;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(w * dpr);
      g.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    fit();
    const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(fit) : null;
    ro?.observe(canvas);

    const minGap = fps > 0 ? 1000 / fps - 2 : 0;
    const draw = (now) => {
      if (minGap && now - last < minGap) {
        raf = requestAnimationFrame(draw);
        return;
      }
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      const s = now / 1000;
      const { state: st, tone: tn, rgb: custom } = live.current;
      const target = (ENERGY[st] || 1) * (st === "speaking" ? 1 + 0.35 * Math.abs(Math.sin(s * 7.3) * Math.sin(s * 3.1)) : 1);
      energy += (target - energy) * Math.min(1, dt * 4);
      spin += dt * 0.12 * (SPIN[st] || 1);
      const [R, G, B] = (tn === "default" && custom) || COLORS[tn] || COLORS.default;
      const cx = size / 2;
      const rad = size * 0.4;
      g.clearRect(0, 0, size, size);
      g.globalCompositeOperation = "lighter";
      g.lineCap = "round";
      const steps = lite ? 90 : 150;
      for (const c of curves) {
        g.beginPath();
        for (let i = 0; i <= steps; i += 1) {
          const t = (i / steps) * Math.PI * 2;
          const rr = rad * radius(c, t, s, energy);
          const a = t + spin * (1 + c.rot * 10);
          const x = cx + rr * Math.cos(a);
          const y = cx + rr * Math.sin(a) * (1 + c.tilt * Math.sin(spin + c.p1));
          if (i) g.lineTo(x, y);
          else g.moveTo(x, y);
        }
        if (!lite) {
          g.strokeStyle = `rgba(${R},${G},${B},${c.alpha * 0.18})`;
          g.lineWidth = c.width * 5;
          g.stroke();
        }
        g.strokeStyle = `rgba(${R},${G},${B},${c.alpha})`;
        g.lineWidth = c.width;
        g.stroke();
      }
      for (const d of dots) {
        d.u = (d.u + dt * d.v * (SPIN[st] || 1)) % 1;
        const c = curves[d.c];
        const t = d.u * Math.PI * 2;
        const rr = rad * radius(c, t, s, energy);
        const a = t + spin * (1 + c.rot * 10);
        const x = cx + rr * Math.cos(a);
        const y = cx + rr * Math.sin(a) * (1 + c.tilt * Math.sin(spin + c.p1));
        const glow = g.createRadialGradient(x, y, 0, x, y, 14);
        glow.addColorStop(0, "rgba(235,250,255,0.95)");
        glow.addColorStop(0.25, `rgba(${R},${G},${B},0.55)`);
        glow.addColorStop(1, `rgba(${R},${G},${B},0)`);
        g.fillStyle = glow;
        g.fillRect(x - 14, y - 14, 28, 28);
      }
      g.globalCompositeOperation = "source-over";
      if (!reduce) raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(raf);
      ro?.disconnect();
    };
  }, [lite, fps]);

  return <canvas ref={canvasRef} className={`to-canvas ${className}`} aria-hidden="true" />;
}

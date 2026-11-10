import { useEffect, useMemo, useRef, useState } from "react";

function barsForState(state, listening) {
  if (listening) return [70, 92, 54, 84, 66, 96, 58, 78, 48, 88, 62, 74];
  if (state === "speaking") return [48, 76, 58, 94, 68, 86, 52, 82, 64, 90, 56, 72];
  if (state === "processing") return [24, 38, 30, 46, 28, 40, 26, 44, 32, 38, 25, 35];
  return [10, 14, 8, 18, 11, 16, 9, 13, 10, 17, 8, 12];
}

export default function AudioWaveformWidget({ api, jarvisState, listening, onClose }) {
  const [volume, setVolume] = useState(null);
  const [error, setError] = useState("");
  const [tick, setTick] = useState(0);
  const [size, setSize] = useState({ width: 288, height: 190 });
  const [position, setPosition] = useState(null);
  const resizeRef = useRef(null);
  const dragRef = useRef(null);

  useEffect(() => {
    let active = true;
    api("/api/system")
      .then((data) => active && setVolume(Number.isFinite(data.volume) && data.volume >= 0 ? data.volume : 50))
      .catch(() => active && setError("Volume do sistema indisponível."));
    return () => { active = false; };
  }, [api]);

  useEffect(() => {
    if (jarvisState === "idle" && !listening) return undefined;
    const timer = setInterval(() => setTick((current) => current + 1), 140);
    return () => clearInterval(timer);
  }, [jarvisState, listening]);

  const bars = useMemo(() => barsForState(jarvisState, listening), [jarvisState, listening]);
  const animatedBars = bars.map((height, index) => (
    Math.max(6, Math.min(100, height + (((tick + index) % 5) - 2) * 5))
  ));

  const updateVolume = async (event) => {
    const next = Number(event.target.value);
    setVolume(next);
    setError("");
    try {
      const data = await api("/api/system/volume", {
        method: "PATCH",
        body: JSON.stringify({ level: next }),
      });
      setVolume(Number.isFinite(data.volume) && data.volume >= 0 ? data.volume : next);
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    const onMove = (event) => {
      if (resizeRef.current) {
        const { startX, startY, startWidth, startHeight } = resizeRef.current;
        setSize({
          width: Math.max(240, Math.min(640, startWidth + event.clientX - startX)),
          height: Math.max(150, Math.min(window.innerHeight - 32, startHeight + event.clientY - startY)),
        });
      }
      if (dragRef.current) {
        const { startX, startY, startLeft, startTop } = dragRef.current;
        setPosition({
          left: Math.max(8, Math.min(window.innerWidth - size.width - 8, startLeft + event.clientX - startX)),
          top: Math.max(8, Math.min(window.innerHeight - size.height - 8, startTop + event.clientY - startY)),
        });
      }
    };
    const onUp = () => {
      resizeRef.current = null;
      dragRef.current = null;
      document.body.style.userSelect = "";
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
  }, []);

  const startResize = (event) => {
    event.preventDefault();
    resizeRef.current = {
      startX: event.clientX,
      startY: event.clientY,
      startWidth: size.width,
      startHeight: size.height,
    };
    document.body.style.userSelect = "none";
  };

  const startDrag = (event) => {
    if (event.button !== 0 || event.target.closest("button")) return;
    const rect = event.currentTarget.parentElement.getBoundingClientRect();
    event.preventDefault();
    dragRef.current = {
      startX: event.clientX,
      startY: event.clientY,
      startLeft: rect.left,
      startTop: rect.top,
    };
    setPosition({ left: rect.left, top: rect.top });
    document.body.style.userSelect = "none";
  };

  return (
    <section
      className="jarvis-audio-window hud-panel"
      style={{
        width: `${size.width}px`,
        height: `${size.height}px`,
        ...(position ? { left: `${position.left}px`, top: `${position.top}px`, right: "auto", bottom: "auto" } : {}),
      }}
      aria-label="Controle de áudio do JARVIS"
    >
      <header className="widget-workspace-toolbar" onPointerDown={startDrag}>
        <span>Áudio · {listening ? "ouvindo" : jarvisState === "speaking" ? "falando" : "monitor"}</span>
        <button type="button" onClick={onClose} aria-label="Fechar visualizador de áudio">×</button>
      </header>
      <div className="p-3">
        <div className="jarvis-waveform" aria-label="Visualizador da atividade de voz">
          {animatedBars.map((height, index) => (
            <span key={index} style={{ height: `${height}%` }} />
          ))}
        </div>
        <label className="mt-3 block text-xs text-arc-300/80" htmlFor="jarvis-volume">
          Volume do sistema: {volume == null ? "--" : `${volume}%`}
        </label>
        <input
          id="jarvis-volume"
          className="mt-1 w-full accent-cyan-300"
          type="range"
          min="0"
          max="100"
          value={volume ?? 50}
          onChange={updateVolume}
          disabled={volume == null}
        />
        {error && <p className="mt-1 text-xs text-amber-200/80">{error}</p>}
      </div>
      <button
        type="button"
        className="jarvis-resize-handle"
        onPointerDown={startResize}
        aria-label="Redimensionar janela de áudio"
        title="Arraste para redimensionar"
      />
    </section>
  );
}

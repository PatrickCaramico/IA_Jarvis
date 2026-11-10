import { useState, useEffect, useRef } from "react";
import { focusAudio } from "../utils/focusAudio.js";
import { soundManager } from "../utils/soundEffects.js";
import { startPolling } from "../hooks/usePolling.js";

/**
 * Widget Avançado de Modo Foco / Pomodoro Tático Stark.
 * Suporta Pomodoro com contagem regressiva, seleção de ruído branco / marrom / binaural,
 * controle de volume de fundo independente e metas de sessão.
 */
export default function FocusWidget({ api, onSend }) {
  const [status, setStatus] = useState({
    active: false,
    phase: "idle", // "work" | "break" | "idle"
    remaining_seconds: 1500,
    focus_duration: 1500,
    break_duration: 300,
  });

  const [soundMode, setSoundMode] = useState("none"); // "none" (Mudo por padrão) | "white" | "brown" | "binaural"
  const [soundVolume, setSoundVolume] = useState(0.35);
  const [completedSessions, setCompletedSessions] = useState(() => {
    return parseInt(localStorage.getItem("jarvis_focus_completed_today") || "0", 10);
  });
  const [currentGoal, setCurrentGoal] = useState("");
  const localTimerRef = useRef(null);

  // Consulta status do backend
  const fetchStatus = async () => {
    try {
      const data = await api("/api/focus");
      if (data && typeof data.active === "boolean") {
        setStatus((prev) => ({
          ...prev,
          active: data.active,
          phase: data.phase,
          remaining_seconds: data.remaining_seconds,
          focus_duration: data.focus_duration,
          break_duration: data.break_duration,
        }));
      }
    } catch {
      /* ignora erro se offline */
    }
  };

  useEffect(() => {
    return startPolling(fetchStatus, 5000); // pausa com a aba oculta
  }, []);

  // Timer local para suavizar a contagem a cada segundo
  useEffect(() => {
    if (status.active && status.remaining_seconds > 0) {
      localTimerRef.current = setInterval(() => {
        setStatus((prev) => {
          if (prev.remaining_seconds <= 1) {
            clearInterval(localTimerRef.current);
            handleCycleFinished(prev.phase);
            return { ...prev, remaining_seconds: 0, active: false, phase: "idle" };
          }
          return { ...prev, remaining_seconds: prev.remaining_seconds - 1 };
        });
      }, 1000);
    } else {
      clearInterval(localTimerRef.current);
    }
    return () => clearInterval(localTimerRef.current);
  }, [status.active]);

  // Gerenciamento do áudio ambiente (Ruído Branco / Marrom / Binaural)
  useEffect(() => {
    if (status.active && status.phase === "work" && soundMode !== "none") {
      focusAudio.play(soundMode, soundVolume);
    } else {
      focusAudio.stop();
    }
    return () => focusAudio.stop();
  }, [status.active, status.phase, soundMode]);

  const handleCycleFinished = (phase) => {
    focusAudio.stop();
    soundManager.playSuccess();
    if (phase === "work") {
      const updated = completedSessions + 1;
      setCompletedSessions(updated);
      localStorage.setItem("jarvis_focus_completed_today", updated.toString());
      if (api) {
        api("/api/speak", {
          method: "POST",
          body: JSON.stringify({
            text: "Sessão de foco concluída com sucesso, senhor! Excelente trabalho. Que tal uma pausa rápida de 5 minutos?",
          }),
        }).catch(() => {});
      }
    } else if (phase === "break") {
      if (api) {
        api("/api/speak", {
          method: "POST",
          body: JSON.stringify({
            text: "Intervalo encerrado, senhor. Sistemas prontos para retomar o foco quando desejar.",
          }),
        }).catch(() => {});
      }
    }
  };

  const handleStart = async (minutes, isBreak = false) => {
    soundManager.playClick();
    const secs = minutes * 60;
    setStatus({
      active: true,
      phase: isBreak ? "break" : "work",
      remaining_seconds: secs,
      focus_duration: isBreak ? status.focus_duration : secs,
      break_duration: isBreak ? secs : 300,
    });

    try {
      await api("/api/focus/start", {
        method: "POST",
        body: JSON.stringify({ minutes, break_minutes: 5 }),
      });
    } catch {
      /* se offline, timer local continuará normalmente */
    }
  };

  const handleStop = async () => {
    soundManager.playClick();
    focusAudio.stop();
    setStatus((prev) => ({ ...prev, active: false, phase: "idle", remaining_seconds: 0 }));
    try {
      await api("/api/focus/stop", { method: "POST" });
    } catch {
      /* ignora */
    }
  };

  const handleVolumeChange = (e) => {
    const val = parseFloat(e.target.value);
    setSoundVolume(val);
    focusAudio.setVolume(val);
  };

  const formatTime = (secs) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  };

  const progressPct =
    status.active && status.focus_duration > 0
      ? Math.max(0, Math.min(100, (1 - status.remaining_seconds / (status.phase === "work" ? status.focus_duration : status.break_duration)) * 100))
      : 0;

  return (
    <section className="hud-panel p-4 flex flex-col gap-3" aria-label="Modo Foco e Pomodoro Tático">
      {/* Cabeçalho do Pomodoro */}
      <div className="flex items-center justify-between border-b border-cyan-500/20 pb-2">
        <div className="flex items-center gap-2">
          <span className="text-base text-cyan-400">⏱</span>
          <h2 className="font-display text-sm tracking-wider text-cyan-200 uppercase font-semibold">
            Modo Foco · Pomodoro
          </h2>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-cyan-300/70 uppercase tracking-widest bg-cyan-950/40 border border-cyan-500/30 px-2 py-0.5 rounded">
            🔥 {completedSessions} {completedSessions === 1 ? "Ciclo Hoje" : "Ciclos Hoje"}
          </span>
          <span
            className={`rounded px-2 py-0.5 font-display text-[10px] uppercase tracking-wider font-bold ${
              status.phase === "work"
                ? "bg-cyan-500/20 text-cyan-200 border border-cyan-400"
                : status.phase === "break"
                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-400"
                : "bg-gray-800 text-gray-400 border border-gray-700"
            }`}
          >
            {status.phase === "work" ? "Em Foco" : status.phase === "break" ? "Pausa" : "Pronto"}
          </span>
        </div>
      </div>

      {/* Meta da Sessão */}
      <div className="flex items-center gap-2 bg-black/40 border border-cyan-500/20 rounded px-2.5 py-1.5">
        <span className="text-xs text-cyan-400">🎯</span>
        <input
          type="text"
          value={currentGoal}
          onChange={(e) => setCurrentGoal(e.target.value)}
          placeholder="Meta atual (ex: Criar relatório, estudar código...)"
          className="bg-transparent text-xs text-cyan-100 placeholder-cyan-400/40 outline-none w-full font-mono"
        />
      </div>

      {/* Display do Timer & Progresso */}
      <div className="flex flex-col items-center justify-center py-2 bg-gradient-to-b from-cyan-950/30 to-black/50 border border-cyan-500/20 rounded-lg relative overflow-hidden">
        {/* Barra de progresso sutil no topo do card */}
        <div
          className="absolute top-0 left-0 h-1 bg-gradient-to-r from-cyan-500 to-emerald-400 transition-all duration-1000"
          style={{ width: `${progressPct}%` }}
        />

        <div className="font-display text-4xl font-bold tracking-widest text-cyan-100 drop-shadow-[0_0_15px_rgba(79,220,255,0.7)] my-1">
          {formatTime(status.remaining_seconds)}
        </div>

        <p className="text-[11px] text-cyan-300/80 tracking-wider">
          {status.phase === "work"
            ? "Mantenha o foco absoluto. Notificações e distrações bloqueadas."
            : status.phase === "break"
            ? "Hora de relaxar os olhos, beber água e respirar."
            : "Selecione o tempo de foco desejado para iniciar:"}
        </p>
      </div>

      {/* Controles de Tempo (Início rápido) */}
      {!status.active ? (
        <div className="flex flex-col gap-2">
          <div className="grid grid-cols-4 gap-1.5">
            {[
              { m: 25, label: "25m Padrão" },
              { m: 45, label: "45m Profundo" },
              { m: 15, label: "15m Sprint" },
              { m: 50, label: "50m Extremo" },
            ].map(({ m, label }) => (
              <button
                key={m}
                type="button"
                onClick={() => handleStart(m)}
                className="rounded border border-cyan-500/30 bg-cyan-950/30 py-2 px-1 font-display text-[11px] font-semibold text-cyan-200 transition hover:border-cyan-400 hover:bg-cyan-500/25 active:scale-95 text-center"
              >
                {label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2 pt-1 border-t border-cyan-500/10">
            <span className="text-[10px] text-cyan-400/70 uppercase tracking-widest">Pausas:</span>
            <button
              type="button"
              onClick={() => handleStart(5, true)}
              className="rounded border border-emerald-500/40 bg-emerald-950/30 px-3 py-1 text-[11px] text-emerald-300 hover:bg-emerald-500/20"
            >
              ☕ 5m Pausa Curta
            </button>
            <button
              type="button"
              onClick={() => handleStart(15, true)}
              className="rounded border border-emerald-500/40 bg-emerald-950/30 px-3 py-1 text-[11px] text-emerald-300 hover:bg-emerald-500/20"
            >
              🌿 15m Pausa Longa
            </button>
          </div>
        </div>
      ) : (
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleStop}
            className="flex-1 rounded border border-red-500/60 bg-red-950/40 py-2 font-display text-xs tracking-wider text-red-200 transition hover:bg-red-500/30 active:scale-95 font-semibold"
          >
            ⏹ Interromper Pomodoro
          </button>
        </div>
      )}

      {/* Áudio de Concentração & Ruído Branco */}
      <div className="bg-black/40 border border-cyan-500/20 rounded p-2.5 flex flex-col gap-2 mt-1">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-cyan-400">🎧</span>
            <span className="text-[11px] font-display uppercase tracking-wider text-cyan-200 font-semibold">
              Áudio de Foco & Ruído Ambiente:
            </span>
          </div>
          <span className="text-[10px] text-cyan-400/80 font-mono">
            {soundMode === "none" ? "Mudo (Sem som)" : `${Math.round(soundVolume * 100)}%`}
          </span>
        </div>

        {/* Seletores de Sons */}
        <div className="grid grid-cols-4 gap-1.5">
          {[
            { id: "none", label: "🔇 Mudo", title: "Sem áudio de fundo" },
            { id: "white", label: "🌊 Ruído Branco", title: "Ruído branco puro para isolar barulhos" },
            { id: "brown", label: "🌧️ Ruído Marrom", title: "Grave quente e profundo (Estilo Chuva/Cachoeira)" },
            { id: "binaural", label: "🧠 Ondas 40Hz", title: "Batimento binaural de hiperfoco cognitivo" },
          ].map((item) => (
            <button
              key={item.id}
              type="button"
              title={item.title}
              onClick={() => setSoundMode(item.id)}
              className={`rounded py-1.5 px-1 font-display text-[10px] tracking-wide transition text-center ${
                soundMode === item.id
                  ? "border border-cyan-400 bg-cyan-500/30 text-white font-bold shadow-[0_0_10px_rgba(79,220,255,0.4)]"
                  : "border border-cyan-500/20 bg-void/50 text-cyan-300/70 hover:border-cyan-500/40 hover:text-cyan-100"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>

        {/* Slider de Volume (quando o áudio estiver ativado) */}
        {soundMode !== "none" && (
          <div className="flex items-center gap-2 pt-1">
            <span className="text-[10px] text-cyan-400/70">Vol:</span>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={soundVolume}
              onChange={handleVolumeChange}
              className="w-full h-1 bg-cyan-950/60 rounded-lg appearance-none cursor-pointer accent-cyan-400"
            />
          </div>
        )}
      </div>
    </section>
  );
}

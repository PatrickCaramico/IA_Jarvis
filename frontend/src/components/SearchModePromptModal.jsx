import React, { useState, useEffect, useRef } from "react";
import { soundManager } from "../utils/soundEffects.js";

/**
 * Modal Holográfico Stark: Seleção do Modo de Pesquisa
 * Permite ao usuário escolher entre API do Gemini ou Navegador Local.
 * Conta regressiva de 10s que aciona o modo padrão salvo caso não haja resposta.
 */
export default function SearchModePromptModal({ data, onSelect, onClose }) {
  const [remember, setRemember] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(data?.timeout_seconds || 10);
  const totalSeconds = data?.timeout_seconds || 10;
  const timerRef = useRef(null);

  const query = data?.query || "informações na web";
  const defaultMode = data?.default_mode || "api";

  useEffect(() => {
    soundManager.playNotification?.();

    timerRef.current = setInterval(() => {
      setSecondsLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timerRef.current);
          // Executa o modo padrão ao expirar
          onSelect(defaultMode, false);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [defaultMode, onSelect]);

  const handleChoose = (mode) => {
    if (timerRef.current) clearInterval(timerRef.current);
    soundManager.playClick?.();
    onSelect(mode, remember);
  };

  const progressPercent = Math.max(0, Math.min(100, (secondsLeft / totalSeconds) * 100));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 select-none animate-fadeIn">
      <div className="relative w-full max-w-lg rounded-xl border border-cyan-400/50 bg-gradient-to-b from-[#061b30]/95 via-[#020d1c]/98 to-[#01060e]/98 p-6 shadow-[0_0_50px_rgba(31,194,245,0.35)] text-cyan-50 font-sans">
        {/* Cantos táticos Stark HUD */}
        <div className="absolute top-2 left-2 w-3 h-3 border-t-2 border-l-2 border-cyan-400" />
        <div className="absolute top-2 right-2 w-3 h-3 border-t-2 border-r-2 border-cyan-400" />
        <div className="absolute bottom-2 left-2 w-3 h-3 border-b-2 border-l-2 border-cyan-400" />
        <div className="absolute bottom-2 right-2 w-3 h-3 border-b-2 border-r-2 border-cyan-400" />

        {/* Topo: Categoria e Fechar */}
        <div className="flex items-center justify-between border-b border-cyan-500/20 pb-3 mb-4">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
            <span className="font-['Orbitron'] text-[11px] tracking-[0.2em] uppercase font-bold text-cyan-300">
              SELEÇÃO DE MODO DE PESQUISA
            </span>
          </div>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="text-cyan-400/60 hover:text-white text-xs font-['Orbitron'] px-2 py-0.5 rounded border border-cyan-500/30 hover:bg-cyan-500/20 transition"
            >
              ✕
            </button>
          )}
        </div>

        {/* Pergunta e Termo */}
        <div className="mb-5">
          <h2 className="text-lg font-bold text-white tracking-wide mb-1 font-display">
            Como deseja realizar esta pesquisa?
          </h2>
          <p className="text-xs text-cyan-200/80 leading-relaxed">
            Termo identificado:{" "}
            <span className="font-semibold text-cyan-300 bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-500/30 font-mono">
              "{query}"
            </span>
          </p>
        </div>

        {/* Barra de Progresso / Contagem de 10s */}
        <div className="mb-5 bg-black/50 border border-cyan-500/30 rounded-lg p-2.5">
          <div className="flex items-center justify-between text-[11px] font-['Orbitron'] text-cyan-300/80 mb-1.5">
            <span>RESPOSTA AUTOMÁTICA EM</span>
            <span className="font-bold text-cyan-200">{secondsLeft}s (Padrão: {defaultMode.toUpperCase()})</span>
          </div>
          <div className="w-full h-1.5 bg-cyan-950/80 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-cyan-400 to-emerald-400 transition-all duration-1000 ease-linear shadow-[0_0_8px_#38bdf8]"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* Botões de Ação */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
          <button
            type="button"
            onClick={() => handleChoose("api")}
            className="group relative p-3.5 rounded-lg border border-cyan-400/50 bg-gradient-to-br from-cyan-950/60 to-black hover:border-cyan-300 hover:from-cyan-900/80 hover:shadow-[0_0_20px_rgba(56,189,248,0.4)] text-left transition"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-['Orbitron'] text-xs font-bold text-cyan-200 group-hover:text-white">
                API DO GEMINI
              </span>
              <span className="text-[10px] font-mono text-cyan-400 bg-cyan-900/60 px-1.5 py-0.5 rounded border border-cyan-400/30">
                IA + WEB
              </span>
            </div>
            <p className="text-[11px] text-cyan-200/70 leading-snug">
              Pesquisa aprofundada via Google Grounding com síntese estruturada e fontes.
            </p>
          </button>

          <button
            type="button"
            onClick={() => handleChoose("browser")}
            className="group relative p-3.5 rounded-lg border border-emerald-400/50 bg-gradient-to-br from-emerald-950/60 to-black hover:border-emerald-300 hover:from-emerald-900/80 hover:shadow-[0_0_20px_rgba(52,211,153,0.4)] text-left transition"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-['Orbitron'] text-xs font-bold text-emerald-200 group-hover:text-white">
                NAVEGADOR LOCAL
              </span>
              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-900/60 px-1.5 py-0.5 rounded border border-emerald-400/30">
                ZERO COTA
              </span>
            </div>
            <p className="text-[11px] text-emerald-200/70 leading-snug">
              Abre a busca no Google localmente e extrai os resultados sem gastar cota de IA.
            </p>
          </button>
        </div>

        {/* Checkbox "Lembrar minha escolha" e Dica de Voz */}
        <div className="pt-3 border-t border-cyan-500/20 flex flex-wrap items-center justify-between gap-3 text-xs">
          <label className="flex items-center gap-2 cursor-pointer text-cyan-200/80 hover:text-white select-none">
            <input
              type="checkbox"
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
              className="w-4 h-4 rounded border-cyan-400 bg-cyan-950 text-cyan-500 focus:ring-0 focus:outline-none cursor-pointer"
            />
            <span className="text-[11px]">Lembrar minha escolha para as próximas pesquisas</span>
          </label>

          <div className="text-[10px] font-mono text-cyan-400/70 flex items-center gap-1">
            <span>Dica: diga</span>
            <strong className="text-cyan-200">"API"</strong>
            <span>ou</span>
            <strong className="text-emerald-300">"Navegador"</strong>
          </div>
        </div>
      </div>
    </div>
  );
}

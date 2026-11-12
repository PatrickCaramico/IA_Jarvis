import { useCallback, useEffect, useRef, useState } from "react";
import { soundManager } from "../utils/soundEffects.js";

/**
 * Modal Holográfico Tático de Pesquisa Profunda do J.A.R.V.I.S.
 * Inspirado diretamente na interface tática Stark com apresentação de notícias do Google em tempo real.
 */
// V6.5.6: sem nenhum toque/rolagem/tecla, a janela fecha sozinha depois deste tempo (com o JARVIS
// calado). Qualquer interação recomeça a contagem; "MANTER ABERTA" desliga.
export const AUTO_CLOSE_MS = 25000;

export default function DeepSearchModal({ data, onClose, onDeepSearch, holdOpen = false, autoCloseMs = AUTO_CLOSE_MS }) {
  useEffect(() => {
    soundManager.playSuccess();
  }, []);

  const [pinned, setPinned] = useState(false);
  const [left, setLeft] = useState(autoCloseMs);
  const deadline = useRef(Date.now() + autoCloseMs);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  const touch = useCallback(() => {
    deadline.current = Date.now() + autoCloseMs;
    setLeft(autoCloseMs);
  }, [autoCloseMs]);

  // enquanto o JARVIS fala, a contagem fica parada (recomeça cheia quando ele termina)
  useEffect(() => {
    if (holdOpen) touch();
  }, [holdOpen, touch]);

  useEffect(() => {
    if (!data || pinned || !autoCloseMs) return undefined;
    const t = setInterval(() => {
      if (holdOpen || document.hidden) {
        deadline.current = Date.now() + autoCloseMs;
        setLeft(autoCloseMs);
        return;
      }
      const ms = deadline.current - Date.now();
      setLeft(Math.max(0, ms));
      if (ms <= 0) {
        clearInterval(t);
        closeRef.current?.();
      }
    }, 250);
    return () => clearInterval(t);
  }, [data, pinned, holdOpen, autoCloseMs]);

  if (!data) return null;

  const {
    title = "Pesquisa e Dados em Tempo Real",
    category = "PESQUISA · ELEIÇÃO",
    reference = "Resultados e apuração mais recente verificados na web",
    badge = "AO VIVO",
    metrics = [], // [{ rank: "01", name: "Candidato / Item", tag: "PL", value: "47%", count: "cerca de 56 milhões votos", status: "Lidera o primeiro turno" }]
    summary = "",
    bullets = [],
    sources = [],
    time = new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }),
  } = data;
  // V6.5.5: "Certo, senhor Patrick" sozinho não é resumo (a IA às vezes abre assim)
  const politeOnly = /^(certo|claro|pois n[aã]o|com prazer|perfeito|entendido|ok)[,!.\s]*(senhor)?[\s\w]{0,20}[.!]?$/i;
  const cleanSummary = summary && !politeOnly.test(summary.trim()) ? summary : "";

  return (
    <div className="dsm-overlay fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-3 sm:p-4 select-none animate-fadeIn">
      <div
        onPointerDown={touch}
        onPointerMove={touch}
        onWheel={touch}
        onScroll={touch}
        onKeyDown={touch}
        onTouchStart={touch}
        className="dsm-card relative w-full max-w-3xl max-h-[calc(100dvh-24px)] overflow-y-auto rounded-xl border border-cyan-400/50 bg-gradient-to-b from-[#061b30]/95 via-[#020d1c]/98 to-[#01060e]/98 p-4 sm:p-6 shadow-[0_0_60px_rgba(31,194,245,0.4)] text-cyan-50 font-sans"
      >
        {/* V6.5.6: barra fininha do tempo até fechar sozinha */}
        {!pinned && autoCloseMs > 0 && (
          <div className="absolute left-0 right-0 top-0 h-[2px] overflow-hidden rounded-t-xl" aria-hidden="true">
            <div
              className="h-full bg-cyan-300/70 transition-[width] duration-300 ease-linear"
              style={{ width: `${Math.round((left / autoCloseMs) * 100)}%` }}
            />
          </div>
        )}
        {/* Cantos Táticos do HUD Stark */}
        <div className="absolute top-2 left-2 w-3.5 h-3.5 border-t-2 border-l-2 border-cyan-400" />
        <div className="absolute top-2 right-2 w-3.5 h-3.5 border-t-2 border-r-2 border-cyan-400" />
        <div className="absolute bottom-2 left-2 w-3.5 h-3.5 border-b-2 border-l-2 border-cyan-400" />
        <div className="absolute bottom-2 right-2 w-3.5 h-3.5 border-b-2 border-r-2 border-cyan-400" />

        {/* Topo: Tag de Categoria e Botões de Ação */}
        <div className="flex flex-wrap items-start justify-between gap-2 border-b border-cyan-500/20 pb-3 mb-3">
          <div className="flex min-w-0 items-center gap-2">
            <span className="px-2.5 py-1 rounded bg-cyan-950/80 border border-cyan-400/40 text-cyan-300 font-['Orbitron'] text-[9px] sm:text-[10px] tracking-[0.14em] sm:tracking-[0.2em] uppercase font-bold flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
              {category}
            </span>
          </div>

          <div className="ml-auto flex items-center gap-2">
            {autoCloseMs > 0 && (
              <button
                type="button"
                onClick={() => setPinned((v) => !v)}
                aria-pressed={pinned}
                className={`px-2 py-1 rounded border text-[10px] font-['Orbitron'] tracking-wider whitespace-nowrap transition ${
                  pinned
                    ? "border-amber-300/70 bg-amber-500/15 text-amber-200"
                    : "border-cyan-500/30 text-cyan-300/70 hover:text-white hover:bg-cyan-500/20"
                }`}
                title={pinned ? "Volta a fechar sozinha quando parada" : "Não fechar sozinha"}
              >
                {pinned ? "📌 FIXADA" : holdOpen ? "LENDO…" : `FECHA EM ${Math.ceil(left / 1000)}s`}
              </button>
            )}
            {onDeepSearch && (
              <button
                type="button"
                onClick={() => onDeepSearch(title || data.query || "")}
                className="px-2.5 sm:px-3 py-1 rounded bg-cyan-500/20 hover:bg-cyan-500/40 border border-cyan-400 text-cyan-200 text-[11px] sm:text-xs font-['Orbitron'] tracking-wider flex items-center gap-1.5 whitespace-nowrap transition shadow-[0_0_10px_rgba(6,182,212,0.3)]"
                title="Aprofundar pesquisa com Inteligência Artificial"
              >
                <span>✦</span> Aprofundar com IA
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              aria-label="Fechar"
              className="text-cyan-400/70 hover:text-white px-2.5 py-1 rounded border border-cyan-500/30 hover:bg-cyan-500/20 text-xs font-['Orbitron'] whitespace-nowrap transition"
              title="Fechar Card"
            >
              ✕<span className="hidden sm:inline"> FECHAR</span>
            </button>
          </div>
        </div>

        {/* Título Principal */}
        <h1 className="dsm-title text-base sm:text-xl md:text-2xl font-bold text-white tracking-wide leading-snug mb-2 font-display text-shadow-[0_0_15px_rgba(255,255,255,0.4)]">
          {title}
        </h1>

        {/* Subtítulo & Badge de Referência / Apuração */}
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-cyan-200/70 pb-3 mb-3 border-b border-cyan-500/15">
          <span className="font-mono text-[11px]">{reference}</span>
          {badge && (
            <span className="px-2 py-0.5 rounded border border-cyan-400/60 bg-cyan-950/60 font-['Orbitron'] text-[10px] text-cyan-200 tracking-wider font-semibold">
              {badge}
            </span>
          )}
        </div>

        {/* Seção de Métricas / Porcentagens Comparativas (Estilo Eleições do Vídeo) */}
        {metrics && metrics.length > 0 && (
          <div className="flex flex-col gap-2.5 mb-4">
            {metrics.map((item, idx) => (
              <div
                key={idx}
                className="p-3 rounded-lg border border-cyan-500/30 bg-gradient-to-r from-cyan-950/40 via-black/40 to-black/60 relative overflow-hidden"
              >
                {/* Linha de progresso no fundo */}
                {item.value && (
                  <div
                    className="absolute top-0 left-0 bottom-0 bg-cyan-500/10 pointer-events-none"
                    style={{ width: item.value }}
                  />
                )}

                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:gap-3 relative z-10">
                  <div className="flex min-w-0 items-start gap-2.5">
                    {item.rank && (
                      <span className="px-2 py-0.5 rounded bg-cyan-900/60 border border-cyan-400/40 font-['Orbitron'] text-[11px] font-bold text-cyan-200">
                        {item.rank}
                      </span>
                    )}
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <strong className="text-sm md:text-base text-white font-semibold line-clamp-3">
                          {item.name === title ? "Resultado da pesquisa" : item.name}
                        </strong>
                        {item.tag && (
                          <span className="text-[10px] font-mono text-cyan-300/80 bg-cyan-950 px-1.5 py-0.5 rounded border border-cyan-500/20">
                            {item.tag}
                          </span>
                        )}
                      </div>
                      {item.count && (
                        <p className="text-[11px] text-cyan-300/60 font-mono mt-0.5">
                          {item.count}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex shrink-0 flex-row items-center gap-2 sm:flex-col sm:items-end sm:gap-1 sm:text-right">
                    <span className="text-lg md:text-2xl font-bold font-['Orbitron'] text-cyan-300 tracking-wider whitespace-nowrap">
                      {item.value}
                    </span>
                    {item.status && (
                      <span className="text-[9px] font-['Orbitron'] uppercase tracking-wider text-emerald-300 bg-emerald-950/60 border border-emerald-500/40 px-2 py-0.5 rounded">
                        {item.status}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Resumo da Notícia */}
        {cleanSummary && (
          <div className="mb-3.5">
            <div className="flex items-center gap-1.5 text-xs font-['Orbitron'] text-cyan-400 uppercase tracking-widest mb-1.5 font-bold">
              <span>◫ RESUMO</span>
            </div>
            <p className="text-xs text-cyan-100/90 leading-relaxed bg-black/40 border border-cyan-500/20 rounded-lg p-3 font-sans">
              {cleanSummary}
            </p>
          </div>
        )}

        {/* Grade 2x2 de Bullets / Pontos-Chave */}
        {bullets && bullets.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mb-4">
            {bullets.map((b, idx) => (
              <div
                key={idx}
                className="p-2.5 rounded-lg border border-cyan-500/25 bg-cyan-950/20 flex items-start gap-2 text-xs text-cyan-100/80 leading-snug"
              >
                <span className="h-2 w-2 rounded-full bg-[#5eead4] mt-1 flex-shrink-0 shadow-[0_0_8px_#5eead4]" />
                <span>{b}</span>
              </div>
            ))}
          </div>
        )}

        {/* Rodapé com Links das Fontes e Horário */}
        <div className="pt-2 border-t border-cyan-500/20 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex flex-wrap items-center gap-2">
            <span className="px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-500/30 text-[10px] font-['Orbitron'] text-cyan-400 font-bold">
              {sources.length} {sources.length === 1 ? "FONTE" : "FONTES"}
            </span>

            {sources.map((src, idx) => (
              <a
                key={idx}
                href={src.url || "#"}
                target="_blank"
                rel="noreferrer"
                className="px-2.5 py-1 rounded bg-black/40 border border-cyan-500/25 hover:border-cyan-400 hover:bg-cyan-500/20 text-[11px] text-cyan-200 flex items-center gap-1.5 transition"
                title={src.headline || src.name}
              >
                <span className="font-mono text-cyan-300 font-semibold">{src.name}</span>
                <span className="text-cyan-400 text-[10px]">↗</span>
              </a>
            ))}
          </div>

          <div className="text-[10px] font-['Orbitron'] text-cyan-400/60 tracking-wider">
            CONSULTADO EM: {time}
          </div>
        </div>
      </div>
    </div>
  );
}

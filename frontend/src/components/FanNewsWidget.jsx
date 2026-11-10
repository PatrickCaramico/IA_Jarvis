import { EmptyState, Skeleton } from "./ui/Skeleton.jsx";
import { useState, useEffect } from "react";
import { startPolling } from "../hooks/usePolling.js";

function formatRelativeTime(isoStr) {
  if (!isoStr) return "";
  try {
    const diffMs = Date.now() - new Date(isoStr).getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return "agora";
    if (diffMin < 60) return `há ${diffMin} min`;
    const diffH = Math.floor(diffMin / 60);
    if (diffH < 24) return `há ${diffH} h`;
    const diffD = Math.floor(diffMin / 24);
    return `há ${diffD} d`;
  } catch {
    return "";
  }
}

export default function FanNewsWidget({ api, onSend, compact = false }) {
  const [news, setNews] = useState([]);
  const [team, setTeam] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadNews = () => {
    if (!api) return;
    setLoading(true);
    setError("");
    api("/api/fan/news?limit=8")
      .then((data) => {
        setNews(data?.items || []);
        setTeam(data?.team || null);
      })
      .catch(() => {
        setError("Não foi possível sincronizar as notícias agora.");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    return startPolling(loadNews, 300000); // 5 minutos, pausa com a aba oculta
  }, [api]);

  return (
    <div className="flex flex-col h-full select-none text-emerald-100">
      {/* Cabeçalho do Card */}
      <div className="flex items-center justify-between pb-2 mb-2 border-b border-emerald-500/25">
        <div className="flex items-center gap-2">
          <span className="text-emerald-400 font-bold text-sm">⚽</span>
          <div>
            <h3 className="font-['Orbitron'] text-xs font-bold tracking-wider text-white">
              {team?.name ? `RADAR · ${team.name.toUpperCase()}` : "NOTÍCIAS DO PALMEIRAS"}
            </h3>
            <span className="text-[9px] text-emerald-300/70 font-mono tracking-wide">
              GE · GLOBO ESPORTE
            </span>
          </div>
        </div>
        <button
          type="button"
          onClick={loadNews}
          disabled={loading}
          className="text-xs text-emerald-400 hover:text-white px-2 py-0.5 rounded border border-emerald-500/30 bg-emerald-950/40 hover:bg-emerald-500/20 transition cursor-pointer disabled:opacity-50"
          title="Atualizar notícias"
        >
          {loading ? "⟳..." : "⟳ ATUALIZAR"}
        </button>
      </div>

      {/* Conteúdo: Lista de Manchetes */}
      {error && news.length === 0 ? (
        <div className="p-3 text-center text-xs text-emerald-300/80 bg-black/40 rounded border border-emerald-500/30 my-auto">
          <p>{error}</p>
          <a
            href="https://ge.globo.com/futebol/times/palmeiras/"
            target="_blank"
            rel="noopener noreferrer"
            className="mt-2 inline-block text-[11px] underline text-emerald-400 hover:text-white"
          >
            Abrir GE Palmeiras no navegador ↗
          </a>
        </div>
      ) : loading && news.length === 0 ? (
        <div className="my-auto p-2"><Skeleton lines={4} label="Sincronizando manchetes do GE" /></div>
      ) : news.length === 0 ? (
        <div className="my-auto">
          <EmptyState tone="green" icon="◎" title="Sem manchetes por enquanto" hint="O GE não trouxe notícias novas agora." action="Tentar novamente" onAction={loadNews} />
        </div>
      ) : (
        <ul className="flex-1 space-y-2 overflow-y-auto pr-1">
          {news.map((item, idx) => (
            <li key={idx} className="group">
              <a
                href={item.link}
                target="_blank"
                rel="noopener noreferrer"
                className="block p-2.5 rounded-lg bg-black/35 hover:bg-emerald-900/30 border border-emerald-500/20 hover:border-emerald-400/60 transition duration-150 shadow-[0_0_8px_rgba(0,0,0,0.5)]"
              >
                <div className="flex items-start justify-between gap-1.5">
                  <p className="text-xs font-medium text-emerald-50 group-hover:text-white line-clamp-2 leading-snug">
                    {item.title}
                  </p>
                  <span className="text-[10px] text-emerald-400/50 group-hover:text-emerald-300 shrink-0">
                    ↗
                  </span>
                </div>
                <div className="mt-1.5 flex items-center justify-between text-[10px] text-emerald-300/60 font-mono">
                  <span className="px-1.5 py-0.2 rounded bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-[9px]">
                    {item.source || "GE"}
                  </span>
                  {item.published && (
                    <span className="text-emerald-200/50">
                      {formatRelativeTime(item.published)}
                    </span>
                  )}
                </div>
              </a>
            </li>
          ))}
        </ul>
      )}

      {/* Rodapé Tático */}
      <div className="mt-2 pt-2 border-t border-emerald-500/20 flex items-center justify-between text-[10px] text-emerald-300/60">
        <a
          href="https://ge.globo.com/futebol/times/palmeiras/"
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-emerald-200 underline"
        >
          ge.globo.com/palmeiras ↗
        </a>
        {onSend && (
          <button
            type="button"
            onClick={() => onSend("quais são as últimas notícias do Palmeiras?")}
            className="hover:text-emerald-200 underline cursor-pointer"
          >
            Resumo pela IA ▸
          </button>
        )}
      </div>
    </div>
  );
}

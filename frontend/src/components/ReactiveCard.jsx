import { useEffect, useState, useRef } from "react";
import WaterPanel from "./WaterPanel.jsx";
import BriefingCard from "./BriefingCard.jsx";

/**
 * ReactiveCard — Renderiza cards reativos na resposta do JARVIS.
 * Suporta:
 * - Timers dinâmicos com contagem regressiva em tempo real.
 * - Suporte a arrastar e mover livremente pela tela (Draggable / Reposicionável).
 * - Notícias (Google News), Clima (Open-Meteo), Tarefas e Agenda.
 */

function timeAgo(iso) {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  if (Number.isNaN(diff)) return "";
  const min = Math.max(0, Math.round(diff / 60000));
  if (min < 1) return "agora";
  if (min < 60) return `há ${min} min`;
  const h = Math.round(min / 60);
  if (h < 24) return `há ${h} h`;
  return `há ${Math.round(h / 24)} d`;
}

// Subcomponente de Timer com contador em tempo real segundo a segundo
function LiveTimerItem({ timer }) {
  const [left, setLeft] = useState(timer.seconds_left);
  const total = timer.total_seconds || timer.seconds_left || 1;

  useEffect(() => {
    setLeft(timer.seconds_left);
    const interval = setInterval(() => {
      setLeft((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [timer.seconds_left]);

  const h = Math.floor(left / 3600);
  const m = Math.floor((left % 3600) / 60);
  const s = left % 60;
  const timeStr = `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  const pct = Math.max(0, Math.min(100, Math.round((left / total) * 100)));

  return (
    <div className="p-3 rounded-lg bg-black/60 border border-cyan-400/40 shadow-[0_0_15px_rgba(6,182,212,0.15)]">
      <div className="flex justify-between items-baseline mb-2">
        <div>
          <span className="text-xs text-white font-['Orbitron'] font-semibold block">
            {timer.label || "CONTAGEM REGRESSIVA"}
          </span>
          <span className="text-[10px] text-cyan-300/60 font-mono">
            {left > 0 ? "EM ANDAMENTO" : "FINALIZADO"}
          </span>
        </div>
        <span className={`font-['Orbitron'] text-xl font-bold tracking-widest ${left > 0 ? "text-cyan-300 animate-pulse" : "text-emerald-400"}`}>
          {timeStr}
        </span>
      </div>

      {/* Barra de progresso holográfica */}
      <div className="w-full h-2 bg-cyan-950/80 rounded-full overflow-hidden border border-cyan-500/30">
        <div
          className={`h-full transition-all duration-1000 ${left > 0 ? "bg-gradient-to-r from-cyan-500 to-[#5eead4] shadow-[0_0_10px_#5eead4]" : "bg-emerald-500 shadow-[0_0_10px_#10b981]"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex justify-between text-[10px] text-cyan-300/70 mt-1.5 font-['Orbitron']">
        <span>TEMPO RESTANTE</span>
        <span>{pct}%</span>
      </div>
    </div>
  );
}

// Subcomponente de Card de Hidratação / Índice de Água (seção 18: recipiente animado compacto)
function WaterCardItem({ initialData, api }) {
  return (
    <div className="rc-card rc-water mt-2 select-none">
      <WaterPanel api={api} size="compact" initialData={initialData} />
    </div>
  );
}

// Subcomponente de Card de Notícias do Clube / Modo Torcedor
function FanNewsCardItem({ data }) {
  const articles = data?.items || data?.articles || [];

  return (
    <div className="rc-card rc-fan-news p-3 rounded-xl border border-emerald-400/40 bg-gradient-to-b from-[#042416]/95 via-[#02180e]/95 to-black/95 shadow-[0_8px_30px_rgba(4,101,56,0.3)] mt-2 select-none">
      {/* Topo do Card */}
      <div className="flex items-center justify-between pb-2 mb-2 border-b border-emerald-500/25">
        <div className="flex items-center gap-2">
          <span className="text-base text-emerald-400">⚽</span>
          <div>
            <span className="text-[11px] font-['Orbitron'] font-bold text-white tracking-wider block">
              NOTÍCIAS DO PALMEIRAS
            </span>
            <span className="text-[9px] text-emerald-300/70 font-mono">
              GE · GLOBO ESPORTE
            </span>
          </div>
        </div>
        <span className="px-2 py-0.5 rounded-full text-[9px] font-['Orbitron'] bg-emerald-950/80 border border-emerald-400/40 text-emerald-300">
          AO VIVO
        </span>
      </div>

      {/* Lista de Manchetes */}
      <div className="flex flex-col gap-2">
        {articles.slice(0, 4).map((a, idx) => (
          <a
            key={idx}
            href={a.link || a.url || "https://ge.globo.com/futebol/times/palmeiras/"}
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 rounded-lg bg-white/[0.04] hover:bg-emerald-500/20 border border-emerald-500/20 hover:border-emerald-400/50 transition-all flex flex-col gap-1 text-left group"
          >
            <div className="flex items-center justify-between text-[9px] text-emerald-300/60 font-mono">
              <span className="text-emerald-400 font-semibold group-hover:text-emerald-200">
                {a.source || "ge.globo.com"}
              </span>
              <span>{timeAgo(a.published || a.published_at)}</span>
            </div>
            <span className="text-[11px] text-white/90 group-hover:text-white font-medium line-clamp-2 leading-snug">
              {a.title}
            </span>
          </a>
        ))}
      </div>

      {/* Rodapé com link oficial */}
      <div className="mt-2.5 pt-2 border-t border-emerald-500/20 flex items-center justify-between">
        <span className="text-[9px] text-emerald-300/60 font-mono">
          Cobertura em tempo real
        </span>
        <a
          href="https://ge.globo.com/futebol/times/palmeiras/"
          target="_blank"
          rel="noopener noreferrer"
          className="text-[10px] font-['Orbitron'] text-emerald-300 hover:text-white flex items-center gap-1 transition"
        >
          VER NO GE ↗
        </a>
      </div>
    </div>
  );
}

export default function ReactiveCard({ card, api }) {
  const [completedMap, setCompletedMap] = useState({});
  const [detached, setDetached] = useState(false);
  const [pos, setPos] = useState({ left: 40, top: 120, width: 360 });
  const cardRef = useRef(null);

  if (!card || !card.type || !card.data) return null;

  const { type, data } = card;

  // Lógica de arraste e reposicionamento livre na tela
  const handleDragStart = (e) => {
    if (e.button !== 0 || e.target.closest("button") || e.target.closest("input") || e.target.closest("a")) return;
    e.preventDefault();

    const el = cardRef.current;
    const rect = el ? el.getBoundingClientRect() : { left: 40, top: 120, width: 360 };

    const offsetX = e.clientX - rect.left;
    const offsetY = e.clientY - rect.top;

    if (!detached) {
      setDetached(true);
      setPos({
        left: rect.left,
        top: rect.top,
        width: Math.max(300, rect.width),
      });
    }

    document.body.style.userSelect = "none";
    document.body.style.cursor = "grabbing";

    const onMove = (moveEv) => {
      setPos({
        left: Math.max(8, Math.min(window.innerWidth - 80, moveEv.clientX - offsetX)),
        top: Math.max(8, Math.min(window.innerHeight - 50, moveEv.clientY - offsetY)),
        width: rect.width || 360,
      });
    };

    const onUp = () => {
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };

    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  };

  // 0. CARD DE TIMER / CONTAGEM REGRESSIVA (CONTADOR DINÂMICO AO VIVO & ARRASTÁVEL)
  if (type === "timer") {
    const timers = data.timers || [];
    return (
      <div
        ref={cardRef}
        className={`rc-card rc-timer border border-cyan-400/50 bg-[#061426]/95 backdrop-blur-md p-3.5 rounded-xl shadow-[0_0_30px_rgba(31,194,245,0.35)] select-none ${
          detached ? "fixed z-50 border-cyan-400" : "my-2"
        }`}
        style={detached ? { left: `${pos.left}px`, top: `${pos.top}px`, width: `${pos.width}px` } : undefined}
      >
        <div
          onPointerDown={handleDragStart}
          className="rc-head flex justify-between items-center mb-3 pb-2 border-b border-cyan-500/30 font-['Orbitron'] text-xs text-cyan-300 cursor-grab active:cursor-grabbing"
          title="Clique e arraste para mover o timer pela tela"
        >
          <span className="rc-tag flex items-center gap-1.5">
            <span className="text-[10px] opacity-70">⠿</span>
            <span className="inline-block w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
            CRONÔMETRO · CONTAGEM
          </span>
          <div className="flex items-center gap-1.5">
            <span className="rc-source text-[9px] text-cyan-400/60 font-mono">STARK TIMERS</span>
            {detached && (
              <button
                type="button"
                onClick={() => setDetached(false)}
                className="text-[9px] font-['Orbitron'] px-1 py-0.5 rounded border border-cyan-500/30 text-cyan-300 hover:text-white"
                title="Voltar ao chat"
              >
                ↺
              </button>
            )}
          </div>
        </div>
        <div className="space-y-2.5">
          {timers.map((t) => (
            <LiveTimerItem key={t.id} timer={t} />
          ))}
        </div>
      </div>
    );
  }

  // 1. CARD DE CLIMA (ARRASTÁVEL)
  if (type === "weather") {
    return (
      <div
        ref={cardRef}
        className={`rc-card rc-weather ${detached ? "fixed z-50 shadow-[0_0_30px_rgba(31,194,245,0.35)]" : ""}`}
        style={detached ? { left: `${pos.left}px`, top: `${pos.top}px`, width: `${pos.width}px` } : undefined}
      >
        <div
          onPointerDown={handleDragStart}
          className="rc-head cursor-grab active:cursor-grabbing flex justify-between items-center"
          title="Clique e arraste para mover o clima pela tela"
        >
          <span className="rc-tag flex items-center gap-1">
            <span className="text-[10px] opacity-70">⠿</span> TEMPO REAL
          </span>
          <div className="flex items-center gap-1">
            <span className="rc-source">{data.city} · Open-Meteo</span>
            {detached && (
              <button
                type="button"
                onClick={() => setDetached(false)}
                className="text-[9px] font-['Orbitron'] px-1 py-0.5 rounded border border-cyan-500/30 text-cyan-300 hover:text-white"
                title="Voltar ao chat"
              >
                ↺
              </button>
            )}
          </div>
        </div>
        <div className="rc-weather-main">
          <span className="rc-weather-temp">{data.temperature}°C</span>
          <div className="rc-weather-details">
            <strong>{data.description}</strong>
            <small>Sensação {data.apparent_temperature}°C · Vento {data.wind_speed} km/h</small>
            <small>Mín {data.minimum}°C / Máx {data.maximum}°C</small>
          </div>
        </div>
      </div>
    );
  }

  // 2. CARD DE NOTÍCIAS
  if (type === "news") {
    const articles = data.articles || [];
    return (
      <div className="rc-card rc-news">
        <div className="rc-head">
          <span className="rc-tag">RADAR DE NOTÍCIAS</span>
          <span className="rc-source">Google News · {articles.length} manchetes</span>
        </div>
        <div className="rc-news-list">
          {articles.map((a, idx) => (
            <a
              key={idx}
              href={a.url}
              target="_blank"
              rel="noopener noreferrer"
              className="rc-news-item"
            >
              <div className="rc-news-meta">
                <span className="rc-news-source">{a.source || "Fonte"}</span>
                <span className="rc-news-time">{timeAgo(a.published_at)}</span>
              </div>
              <span className="rc-news-title">{a.title}</span>
            </a>
          ))}
        </div>
      </div>
    );
  }

  // 3. CARD DE TAREFAS
  if (type === "tasks") {
    const items = data.items || [];
    const toggleTask = (task) => {
      const nextDone = !Boolean(completedMap[task.id] ?? task.done);
      setCompletedMap((m) => ({ ...m, [task.id]: nextDone }));
      if (api) {
        api(`/api/tasks/${task.id}`, {
          method: "PATCH",
          body: JSON.stringify({ done: nextDone }),
        }).catch(() => {
          setCompletedMap((m) => ({ ...m, [task.id]: !nextDone }));
        });
      }
    };
    return (
      <div className="rc-card rc-tasks">
        <div className="rc-head">
          <span className="rc-tag">SUAS TAREFAS</span>
          <span className="rc-source">{items.length} pendência{items.length === 1 ? "" : "s"}</span>
        </div>
        <div className="rc-task-list">
          {items.map((t) => {
            const isDone = Boolean(completedMap[t.id] ?? t.done);
            return (
              <label key={t.id} className={`rc-task-item ${isDone ? "is-done" : ""}`}>
                <input
                  type="checkbox"
                  checked={isDone}
                  onChange={() => toggleTask(t)}
                />
                <span>{t.text}</span>
              </label>
            );
          })}
        </div>
      </div>
    );
  }

  // 4. CARD DE AGENDA / CALENDÁRIO
  if (type === "calendar") {
    const events = data.events || [];
    return (
      <div className="rc-card rc-calendar">
        <div className="rc-head">
          <span className="rc-tag">AGENDA</span>
          <span className="rc-source">{events.length} compromisso{events.length === 1 ? "" : "s"}</span>
        </div>
        <div className="rc-event-list">
          {events.map((e, idx) => (
            <div key={idx} className="rc-event-item">
              <span className="rc-event-time">{e.start || "Hoje"}</span>
              <span className="rc-event-summary">{e.summary || "Sem título"}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // 5. CARD DE PESQUISA / GUIA / RECEITA TÁTICA (deep_search)
  if (type === "deep_search") {
    const title = data.title || "Resultado da Pesquisa";
    const category = data.category || "PESQUISA";
    const badge = data.badge || "VERIFICADO";

    const handleOpenModal = () => {
      window.dispatchEvent(new CustomEvent("jarvis_open_deep_search", { detail: data }));
    };

    return (
      <div className="rc-card rc-deep-search p-3 rounded-lg border border-cyan-400/40 bg-gradient-to-r from-cyan-950/70 via-black/80 to-black/90 shadow-[0_0_15px_rgba(31,194,245,0.2)] mt-2">
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            <span className="text-[10px] font-['Orbitron'] font-bold text-cyan-300 tracking-wider">
              {category}
            </span>
          </div>
          <span className="px-1.5 py-0.5 rounded bg-cyan-900/60 border border-cyan-400/30 text-[9px] font-['Orbitron'] text-cyan-200">
            {badge}
          </span>
        </div>
        <strong className="text-xs text-white block font-semibold mb-1">
          {title}
        </strong>
        {data.summary && (
          <p className="text-[11px] text-cyan-100/75 line-clamp-2 mb-2 font-sans">
            {data.summary}
          </p>
        )}
        <button
          type="button"
          onClick={handleOpenModal}
          className="w-full py-1.5 px-3 rounded bg-cyan-500/20 hover:bg-cyan-500/35 border border-cyan-400/60 text-[10px] font-['Orbitron'] text-cyan-200 hover:text-white flex items-center justify-center gap-1.5 transition tracking-wider shadow-[0_0_8px_rgba(6,182,212,0.3)]"
        >
          <span>◫</span> ABRIR PAINEL COMPLETO
        </button>
      </div>
    );
  }

  // 6. CARD DE HIDRATAÇÃO / ÍNDICE DE ÁGUA
  if (type === "water") {
    return <WaterCardItem initialData={data} api={api} />;
  }

  // 7. CARD DE NOTÍCIAS DO PALMEIRAS / MODO TORCEDOR
  if (type === "fan_news") {
    return <FanNewsCardItem data={data} />;
  }

  // 8. V4.3: RESUMO DO BRIEFING "BOM DIA" (versão compacta dos cards no Canal Ativo)
  if (type === "briefing") {
    return (
      <div className="bf-chat">
        {(data.cards || []).map((c, idx) => (
          <BriefingCard key={idx} card={c} compact />
        ))}
      </div>
    );
  }

  return null;
}

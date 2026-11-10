import { useCallback, useEffect, useState } from "react";
import { APP_VERSION } from "../utils/version.js";

export default function ScreensPopout() {
  const [activeTab, setActiveTab] = useState(() => {
    return localStorage.getItem("jarvis_display_secondary_tab") || "standby";
  });

  const [isUnlocking, setIsUnlocking] = useState(false);

  const [data, setData] = useState({
    news: [],
    weather: null,
    finance: [],
    tasks: [],
    media: [
      { id: 1, title: "Iron Man (Clássico Stark)", type: "Filme", genre: "Sci-Fi / Ação", rating: "9.4", status: "Favorito" },
      { id: 2, title: "Mr. Robot", type: "Série", genre: "Tech / Cyberpunk", rating: "9.1", status: "Continuar" },
      { id: 3, title: "Oppenheimer", type: "Filme", genre: "Drama Histórico", rating: "8.9", status: "Assistido" },
      { id: 4, title: "Severance", type: "Série", genre: "Sci-Fi Psicológico", rating: "8.7", status: "Recomendado" },
    ],
    loading: true,
  });

  const API_URL = import.meta.env.VITE_API_URL || `${window.location.protocol}//${window.location.hostname}:8000`;

  // Sincroniza em tempo real com os comandos do Hub Principal
  useEffect(() => {
    const handleStorage = (e) => {
      if (e.key === "jarvis_display_secondary_tab" && e.newValue) {
        if (e.newValue !== "standby" && e.newValue !== "blank") {
          // Dispara a animação de desbloqueio do Vídeo 3
          setIsUnlocking(true);
          setTimeout(() => {
            setActiveTab(e.newValue);
            setIsUnlocking(false);
          }, 900);
        } else {
          setActiveTab(e.newValue);
        }
      }
    };
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  const unlockTo = (tab) => {
    setIsUnlocking(true);
    setTimeout(() => {
      setActiveTab(tab);
      localStorage.setItem("jarvis_display_secondary_tab", tab);
      setIsUnlocking(false);
    }, 900);
  };

  const lockStandby = () => {
    setActiveTab("standby");
    localStorage.setItem("jarvis_display_secondary_tab", "standby");
  };

  const fetchData = useCallback(async () => {
    try {
      const [newsRes, weatherRes, financeRes, tasksRes] = await Promise.allSettled([
        fetch(`${API_URL}/api/news?category=tecnologia&limit=8`).then((r) => r.json()),
        fetch(`${API_URL}/api/weather`).then((r) => r.json()),
        fetch("https://economia.awesomeapi.com.br/json/last/USD-BRL,EUR-BRL,BTC-BRL").then((r) => r.json()),
        fetch(`${API_URL}/api/tasks`).then((r) => r.json()),
      ]);

      setData((prev) => ({
        ...prev,
        news: newsRes.status === "fulfilled" && newsRes.value?.news ? newsRes.value.news : [],
        weather: weatherRes.status === "fulfilled" ? weatherRes.value : null,
        finance: financeRes.status === "fulfilled" ? Object.values(financeRes.value || {}) : [],
        tasks: tasksRes.status === "fulfilled" && tasksRes.value?.tasks ? tasksRes.value.tasks : [],
        loading: false,
      }));
    } catch {
      setData((prev) => ({ ...prev, loading: false }));
    }
  }, [API_URL]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 20000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // ==========================================
  // TELA DE STANDBY / BLOQUEIO (VÍDEO 3)
  // Anel holográfico + Cadeado central + Animação de Giro
  // ==========================================
  if (activeTab === "standby" || activeTab === "blank") {
    return (
      <div className="h-screen w-screen overflow-hidden bg-[#020813] text-[#c9f6ff] p-6 flex flex-col justify-between items-center select-none relative">
        {/* Cantos Táticos do Monitor Auxiliar */}
        <div className="absolute top-4 left-4 w-6 h-6 border-t-2 border-l-2 border-cyan-400" />
        <div className="absolute top-4 right-4 w-6 h-6 border-t-2 border-r-2 border-cyan-400" />
        <div className="absolute bottom-4 left-4 w-6 h-6 border-b-2 border-l-2 border-cyan-400" />
        <div className="absolute bottom-4 right-4 w-6 h-6 border-b-2 border-r-2 border-cyan-400" />

        {/* Topo */}
        <div className="pt-2 text-center">
          <div className="font-['Orbitron'] text-xs tracking-[0.35em] text-cyan-400">
            EM ESPERA
          </div>
          <div className="text-[10px] text-cyan-300/50 font-['Orbitron'] tracking-widest mt-0.5">
            VOZ, AGENDA, E-MAILS E TELEMETRIA · DADOS ATIVOS
          </div>
        </div>

        {/* Centro: O Anel Holográfico de Desbloqueio Tático */}
        <div className={`relative flex items-center justify-center transition-all duration-700 ${isUnlocking ? "scale-125 opacity-0" : "scale-100 opacity-100"}`}>
          {/* Anéis giratórios */}
          <div className="absolute w-80 h-80 rounded-full border border-cyan-500/25 animate-spin" style={{ animationDuration: "30s" }} />
          <div className="absolute w-64 h-64 rounded-full border-2 border-dashed border-cyan-400/40 animate-spin" style={{ animationDuration: "15s", animationDirection: "reverse" }} />
          <div className="absolute w-52 h-52 rounded-xl border border-cyan-500/30 rotate-45" />

          {/* Placa Central com Cadeado */}
          <div
            onClick={() => unlockTo("command")}
            className="cursor-pointer group relative w-48 h-48 rounded-2xl bg-cyan-950/40 border border-cyan-400/50 shadow-[0_0_40px_rgba(31,194,245,0.25)] flex flex-col items-center justify-center p-4 backdrop-blur-md hover:border-cyan-300 hover:shadow-[0_0_50px_rgba(31,194,245,0.5)] transition-all"
          >
            {/* Ícone do Cadeado Holográfico */}
            <div className="h-12 w-12 rounded-full border border-cyan-400/60 bg-cyan-900/40 flex items-center justify-center mb-3 group-hover:scale-110 transition">
              <span className="text-xl">🔒</span>
            </div>
            <span className="text-[10px] font-['Orbitron'] tracking-[0.2em] text-cyan-400/70 uppercase">
              STANDBY
            </span>
            <strong className="text-xs font-['Orbitron'] tracking-widest text-white mt-1 text-center">
              Centro de Comando
            </strong>
            <span className="text-[9px] text-cyan-300/40 mt-1 font-['Orbitron']">
              AGUARDANDO ATIVAÇÃO
            </span>
          </div>
        </div>

        {/* Rodapé */}
        <div className="pb-2 flex flex-col items-center gap-2">
          <button
            onClick={() => unlockTo("command")}
            className="px-4 py-1.5 rounded border border-cyan-500/40 bg-cyan-950/40 text-xs font-['Orbitron'] text-cyan-200 hover:bg-cyan-500/20 shadow-[0_0_15px_rgba(31,194,245,0.2)]"
          >
            DESBLOQUEAR TELA AUXILIAR
          </button>
          <span className="text-[9px] text-cyan-400/40 font-['Orbitron']">
            JARVIS · LINK SINCRONIZADO COM O HUB PRINCIPAL
          </span>
        </div>
      </div>
    );
  }

  // ==========================================
  // TELA DESBLOQUEADA: HUB MULTI-MONITOR ATIVO
  // ==========================================
  return (
    <div className="h-screen w-screen overflow-hidden bg-[#020813] text-[#c9f6ff] p-5 flex flex-col font-sans select-none relative animate-fadeIn">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_50%,rgba(10,124,174,0.15),transparent_70%)] pointer-events-none" />

      {/* Topo Tático */}
      <header className="flex items-center justify-between pb-3 border-b border-[#1fc2f5]/30 mb-4 z-10">
        <div className="flex items-center gap-3">
          <span className="h-3.5 w-3.5 rounded-full bg-[#5eead4] shadow-[0_0_12px_#5eead4] animate-pulse" />
          <div>
            <h1 className="font-['Orbitron'] text-lg font-bold tracking-widest text-white leading-none">
              J.A.R.V.I.S.
            </h1>
            <span className="text-[10px] text-[#4fdcff] tracking-[0.2em] font-['Orbitron']">
              MONITOR SECUNDÁRIO · OPERACIONAL
            </span>
          </div>
        </div>

        {/* Abas */}
        <div className="flex gap-2">
          {[
            ["command", "CENTRAL TÁTICA"],
            ["media", "FILMES & SÉRIES"],
            ["news", "RADAR NOTÍCIAS"],
            ["finance", "MERCADO & CÂMBIO"],
            ["tasks", "TAREFAS"],
          ].map(([id, label]) => (
            <button
              key={id}
              onClick={() => {
                setActiveTab(id);
                localStorage.setItem("jarvis_display_secondary_tab", id);
              }}
              className={`px-3 py-1.5 text-xs font-['Orbitron'] tracking-wider rounded border transition-all ${
                activeTab === id
                  ? "bg-[#1fc2f5]/30 border-[#4fdcff] text-white shadow-[0_0_15px_rgba(31,194,245,0.45)]"
                  : "bg-[#020813]/60 border-[#1fc2f5]/20 text-[#c9f6ff]/70 hover:bg-[#1fc2f5]/15"
              }`}
            >
              {label}
            </button>
          ))}
          <button
            onClick={lockStandby}
            title="Bloquear / Colocar em espera"
            className="px-2.5 py-1.5 text-xs font-['Orbitron'] border border-cyan-500/40 text-cyan-300 hover:bg-cyan-500/20 rounded ml-2"
          >
            🔒 BLOQUEAR
          </button>
        </div>
      </header>

      {/* Conteúdo Dinâmico */}
      <main className="flex-1 overflow-y-auto pr-1 grid gap-4 grid-cols-1 md:grid-cols-2 z-10">
        {activeTab === "command" && (
          <>
            <div className="hud-panel p-4 rounded border border-[#1fc2f5]/30 bg-[#082037]/50 flex flex-col justify-between">
              <span className="text-xs font-['Orbitron'] tracking-widest text-[#4fdcff]">SENSORES ATMOSFÉRICOS</span>
              {data.weather ? (
                <div className="flex items-center justify-between my-2">
                  <div className="text-5xl font-['Orbitron'] font-bold text-white tracking-wider">
                    {data.weather.temperature}°
                  </div>
                  <div className="text-right text-xs leading-relaxed">
                    <p className="text-white font-bold text-sm">{data.weather.description}</p>
                    <p className="text-[#c9f6ff]/80">Sensação: {data.weather.apparent_temperature}°</p>
                    <p className="text-[#c9f6ff]/80">Chuva: {data.weather.rain_probability ?? 0}%</p>
                    <p className="text-emerald-400">Máx {data.weather.maximum}° · Mín {data.weather.minimum}°</p>
                  </div>
                </div>
              ) : (
                <p className="text-xs opacity-60">Sincronizando satélites...</p>
              )}
              <span className="text-[10px] text-[#4fdcff]/60 tracking-wider">LOCAL: SÃO PAULO · BRASÍLIA TZ</span>
            </div>

            <div className="hud-panel p-4 rounded border border-[#1fc2f5]/30 bg-[#082037]/50 flex flex-col justify-between">
              <span className="text-xs font-['Orbitron'] tracking-widest text-[#4fdcff]">MERCADO FINANCEIRO</span>
              <div className="space-y-2 my-2">
                {data.finance.slice(0, 3).map((f) => (
                  <div key={f.code} className="flex justify-between items-center text-xs p-1.5 rounded bg-black/30 border border-cyan-500/10">
                    <span className="font-bold text-white font-['Orbitron']">{f.code}/BRL</span>
                    <span className="font-mono text-[#5eead4] text-sm">R$ {Number(f.bid).toFixed(2)}</span>
                    <span className={`font-semibold ${Number(f.pctChange) >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                      {Number(f.pctChange) >= 0 ? `+${f.pctChange}%` : `${f.pctChange}%`}
                    </span>
                  </div>
                ))}
              </div>
              <span className="text-[10px] text-[#4fdcff]/60 tracking-wider">FONTE: AWESOMEAPI · FEED VERIFICADO</span>
            </div>

            <div className="hud-panel p-4 rounded border border-[#1fc2f5]/30 bg-[#082037]/50">
              <span className="text-xs font-['Orbitron'] tracking-widest text-[#4fdcff] mb-2 block">
                RADAR DE ENTRETENIMENTO · FILMES & SÉRIES
              </span>
              <div className="space-y-2">
                {data.media.slice(0, 3).map((m) => (
                  <div key={m.id} className="p-2 rounded bg-black/40 border border-cyan-500/15 flex justify-between items-center text-xs">
                    <div>
                      <strong className="text-white">{m.title}</strong>
                      <p className="text-[10px] text-cyan-300/60">{m.genre}</p>
                    </div>
                    <span className="px-2 py-0.5 rounded bg-cyan-950 border border-cyan-500/30 text-cyan-300 font-['Orbitron'] text-[10px]">
                      ★ {m.rating}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="hud-panel p-4 rounded border border-[#1fc2f5]/30 bg-[#082037]/50">
              <span className="text-xs font-['Orbitron'] tracking-widest text-[#4fdcff] mb-2 block">
                PRODUTIVIDADE · TAREFAS ATIVAS
              </span>
              <div className="space-y-2">
                {data.tasks.slice(0, 4).map((t, i) => (
                  <div key={t.id || i} className="p-2 rounded bg-black/40 border border-cyan-500/15 text-xs flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-[#1fc2f5]" />
                    <span className="text-white truncate">{t.texto || t.text}</span>
                  </div>
                ))}
                {data.tasks.length === 0 && <p className="text-xs opacity-60">Nenhuma tarefa pendente no momento.</p>}
              </div>
            </div>
          </>
        )}

        {activeTab === "media" && (
          <div className="col-span-1 md:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.media.map((m) => (
              <div key={m.id} className="hud-panel p-4 rounded border border-[#1fc2f5]/30 bg-[#082037]/40 flex justify-between items-center">
                <div>
                  <span className="text-[10px] font-['Orbitron'] text-cyan-400 uppercase tracking-widest">{m.type}</span>
                  <h3 className="text-base font-bold text-white mt-0.5">{m.title}</h3>
                  <p className="text-xs text-cyan-200/70">{m.genre}</p>
                </div>
                <div className="text-right">
                  <div className="font-['Orbitron'] text-lg font-bold text-[#5eead4]">★ {m.rating}</div>
                  <span className="text-[10px] text-cyan-300/80 px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-500/30">
                    {m.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === "news" && (
          <div className="col-span-1 md:col-span-2 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {data.news.map((item, idx) => (
              <a
                key={idx}
                href={item.link}
                target="_blank"
                rel="noreferrer"
                className="hud-panel p-3.5 rounded border border-[#1fc2f5]/25 bg-[#082037]/35 hover:border-[#4fdcff] transition-all flex flex-col justify-between"
              >
                <p className="text-xs text-white line-clamp-3 leading-relaxed mb-3">{item.title}</p>
                <span className="text-[10px] text-[#4fdcff]/80 font-['Orbitron']">{item.source || "GOOGLE NEWS"}</span>
              </a>
            ))}
          </div>
        )}

        {activeTab === "finance" && (
          <div className="col-span-1 md:col-span-2 grid grid-cols-1 md:grid-cols-3 gap-4">
            {data.finance.map((f, idx) => (
              <div key={idx} className="hud-panel p-4 rounded border border-[#1fc2f5]/30 bg-[#082037]/50">
                <span className="text-xs font-['Orbitron'] tracking-widest text-[#4fdcff] block mb-1">{f.name}</span>
                <p className="text-3xl font-mono text-white mb-2">R$ {Number(f.bid).toFixed(2)}</p>
                <div className="flex justify-between text-xs text-[#c9f6ff]/70 pt-2 border-t border-cyan-500/15">
                  <span>Máx: R$ {Number(f.high).toFixed(2)}</span>
                  <span>Mín: R$ {Number(f.low).toFixed(2)}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === "tasks" && (
          <div className="col-span-1 md:col-span-2 space-y-2">
            {data.tasks.map((t, idx) => (
              <div key={t.id || idx} className="hud-panel p-3.5 rounded border border-[#1fc2f5]/25 bg-[#082037]/40 flex items-center justify-between">
                <span className="text-sm text-white font-medium">{t.texto || t.text}</span>
                <span className="text-xs text-[#5eead4] font-['Orbitron'] px-2 py-0.5 rounded bg-emerald-950/40 border border-emerald-500/30">
                  PENDENTE
                </span>
              </div>
            ))}
          </div>
        )}
      </main>

      <footer className="mt-3 pt-2.5 border-t border-[#1fc2f5]/20 flex justify-between items-center text-[11px] text-[#c9f6ff]/60 z-10 font-['Orbitron']">
        <span>SISTEMA DE DISPLAY MULTI-TELA · JARVIS v{APP_VERSION}</span>
        <button
          onClick={() => {
            if (document.fullscreenElement) document.exitFullscreen?.();
            else document.documentElement.requestFullscreen?.();
          }}
          className="hover:text-white px-3 py-1 rounded border border-[#1fc2f5]/40 hover:bg-cyan-500/10 text-[10px]"
        >
          MODO TELA CHEIA (F11)
        </button>
      </footer>
    </div>
  );
}

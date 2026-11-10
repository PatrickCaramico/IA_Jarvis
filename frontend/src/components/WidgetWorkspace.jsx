import { useState } from "react";
import StatusPanel from "./StatusPanel.jsx";
import AboutWidget from "./AboutWidget.jsx";
import AppLauncher from "./AppLauncher.jsx";
import ShortcutsWidget from "./ShortcutsWidget.jsx";
import TodoWidget from "./TodoWidget.jsx";
import FocusWidget from "./FocusWidget.jsx";
import SystemMonitorWidget from "./SystemMonitorWidget.jsx";
import MemoryWidget from "./MemoryWidget.jsx";
import CalendarWidget from "./CalendarWidget.jsx";
import WeatherWidget from "./WeatherWidget.jsx";
import SpotifyWidget from "./SpotifyWidget.jsx";
import FanNewsWidget from "./FanNewsWidget.jsx";
import FanScoreWidget from "./FanScoreWidget.jsx";
import WaterWidget from "./WaterWidget.jsx";

const WIDGET_CATALOG = [
  { key: "status", title: "Painel de Status", category: "Sistema", icon: "⬡", desc: "Diagnóstico dos motores de IA, visão e áudio" },
  { key: "tasks", title: "Lista de Tarefas", category: "Produtividade", icon: "◻", desc: "Gerenciamento e conclusão de tarefas operacionais" },
  { key: "focus", title: "Modo Foco / Pomodoro", category: "Produtividade", icon: "◎", desc: "Cronômetro tático de ciclos produtivos" },
  { key: "water", title: "Hidratação Diária", category: "Sensores", icon: "💧", desc: "Meta e monitor de consumo diário de água" },
  { key: "launcher", title: "Abrir Programas", category: "Produtividade", icon: "⊞", desc: "Execução rápida de softwares locais" },
  { key: "shortcuts", title: "Atalhos Rápidos", category: "Produtividade", icon: "⌨", desc: "Abertura conjunta de links e rotinas" },
  { key: "monitor", title: "Monitor de Recursos", category: "Sistema", icon: "⬡", desc: "CPU, Memória RAM e status de hardware" },
  { key: "memory", title: "Memória do JARVIS", category: "Sistema", icon: "◈", desc: "Fatos e anotações gravados na IA" },
  { key: "weather", title: "Clima & Sensores", category: "Sensores", icon: "◌", desc: "Previsão, sensação térmica e chuva" },
  { key: "spotify", title: "Controles Spotify", category: "Multimídia", icon: "♫", desc: "Player e controle de faixas em reprodução" },
  { key: "fan_news", title: "Notícias do Clube", category: "Torcedor", icon: "⚽", desc: "Manchetes do Palmeiras em tempo real (GE)" },
  { key: "fan_score", title: "Placar & Agenda", category: "Torcedor", icon: "🏆", desc: "Placar ao vivo e contagem regressiva de partidas" },
  { key: "about", title: "Sobre Mim", category: "Perfil", icon: "◈", desc: "Informações personalizadas do operador" },
  { key: "calendar", title: "Google Calendar", category: "Produtividade", icon: "◷", desc: "Sincronização da agenda tática" },
];

export default function WidgetWorkspace({
  activeWidgets = [],
  layout,
  onLayoutChange,
  onClose,
  onSend,
  api,
  apiWithBase,
  steps,
  connected,
  services,
}) {
  const [selectedCategory, setSelectedCategory] = useState("TODOS");
  const [activeWidgetKey, setActiveWidgetKey] = useState(() => activeWidgets[0] || "status");

  const categories = ["TODOS", "Produtividade", "Sistema", "Sensores", "Multimídia", "Perfil", "Torcedor"];

  const filteredWidgets = WIDGET_CATALOG.filter((w) =>
    selectedCategory === "TODOS" ? true : w.category === selectedCategory
  );

  const speak = (text) => {
    if (api) {
      api("/api/speak", { method: "POST", body: JSON.stringify({ text }) }).catch(() => {});
    }
  };

  const handleSelectWidget = (widget) => {
    setActiveWidgetKey(widget.key);
    speak(`Visualizando widget ${widget.title}, senhor.`);
  };

  const renderActiveWidget = () => {
    const props = { api, onSend };
    switch (activeWidgetKey) {
      case "status":
        return <StatusPanel steps={steps} connected={connected} services={services} api={api} />;
      case "tasks":
        return <TodoWidget {...props} />;
      case "focus":
        return <FocusWidget {...props} />;
      case "launcher":
        return <AppLauncher onSend={onSend} />;
      case "shortcuts":
        return <ShortcutsWidget {...props} />;
      case "monitor":
        return <SystemMonitorWidget {...props} />;
      case "memory":
        return <MemoryWidget {...props} />;
      case "weather":
        return <WeatherWidget api={api} />;
      case "water":
        return <WaterWidget api={api} onSend={onSend} />;
      case "spotify":
        return <SpotifyWidget api={apiWithBase} onSend={onSend} />;
      case "fan_news":
        return <FanNewsWidget api={api} onSend={onSend} />;
      case "fan_score":
        return <FanScoreWidget api={api} onSend={onSend} />;
      case "about":
        return <AboutWidget {...props} />;
      case "calendar":
        return <CalendarWidget api={apiWithBase} />;
      default:
        return <StatusPanel steps={steps} connected={connected} services={services} api={api} />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-6 select-none">
      <div className="relative w-full max-w-6xl h-[88vh] rounded-xl border border-cyan-500/40 bg-gradient-to-b from-[#082037]/95 via-[#041224]/95 to-[#020813]/98 flex flex-col overflow-hidden shadow-[0_0_50px_rgba(31,194,245,0.25)]">
        {/* Cantos Táticos */}
        <div className="absolute top-2 left-2 w-4 h-4 border-t-2 border-l-2 border-cyan-400 pointer-events-none" />
        <div className="absolute top-2 right-2 w-4 h-4 border-t-2 border-r-2 border-cyan-400 pointer-events-none" />
        <div className="absolute bottom-2 left-2 w-4 h-4 border-b-2 border-l-2 border-cyan-400 pointer-events-none" />
        <div className="absolute bottom-2 right-2 w-4 h-4 border-b-2 border-r-2 border-cyan-400 pointer-events-none" />

        {/* Topo do Painel */}
        <header className="flex items-center justify-between px-6 py-4 border-b border-cyan-500/20 bg-black/40">
          <div className="flex items-center gap-3">
            <span className="h-3 w-3 rounded-full bg-[#5eead4] shadow-[0_0_10px_#5eead4] animate-pulse" />
            <div>
              <h2 className="font-['Orbitron'] text-xl font-bold tracking-widest text-white leading-none">
                CENTRAL DE WIDGETS
              </h2>
              <span className="text-[10px] text-cyan-400 tracking-[0.25em] font-['Orbitron']">
                JARVIS · WORKSPACE GERENCIADOR
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => {
                  setSelectedCategory(cat);
                  speak(`Filtrando categoria ${cat}.`);
                }}
                className={`px-3 py-1 text-xs font-['Orbitron'] tracking-wider rounded border transition ${
                  selectedCategory === cat
                    ? "bg-cyan-500/30 border-cyan-400 text-white shadow-[0_0_10px_rgba(31,194,245,0.3)]"
                    : "border-cyan-500/20 text-cyan-300/60 hover:text-cyan-100 hover:border-cyan-400/50"
                }`}
              >
                {cat.toUpperCase()}
              </button>
            ))}
            <button
              onClick={onClose}
              className="ml-4 px-3 py-1 rounded border border-rose-500/40 text-rose-300 font-['Orbitron'] text-xs hover:bg-rose-500/20"
            >
              ✕ FECHAR
            </button>
          </div>
        </header>

        {/* Corpo: Duas Colunas Organizadas */}
        <div className="flex-1 flex overflow-hidden p-6 gap-6">
          {/* Coluna Esquerda: Lista de Widgets em Cards */}
          <div className="w-1/3 flex flex-col gap-2 overflow-y-auto pr-2">
            <span className="text-xs font-['Orbitron'] tracking-wider text-cyan-400/70 mb-1">
              MÓDULOS DISPONÍVEIS
            </span>
            {filteredWidgets.map((item) => {
              const isSelected = activeWidgetKey === item.key;
              return (
                <button
                  key={item.key}
                  onClick={() => handleSelectWidget(item)}
                  className={`text-left p-3.5 rounded-lg border transition-all flex items-start gap-3 ${
                    isSelected
                      ? "border-cyan-400 bg-cyan-950/60 shadow-[0_0_20px_rgba(31,194,245,0.25)] translate-x-1"
                      : "border-cyan-500/20 bg-black/40 hover:border-cyan-400/50 hover:bg-cyan-950/20"
                  }`}
                >
                  <span className="text-xl text-cyan-400 mt-0.5">{item.icon}</span>
                  <div className="flex-1">
                    <div className="flex justify-between items-center">
                      <strong className="font-['Orbitron'] text-xs text-white tracking-wide">
                        {item.title}
                      </strong>
                      <span className="text-[9px] text-[#5eead4] font-['Orbitron'] border border-[#5eead4]/30 px-1.5 py-0.5 rounded">
                        {item.category}
                      </span>
                    </div>
                    <p className="text-[11px] text-cyan-200/60 line-clamp-2 mt-1 leading-snug">
                      {item.desc}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Coluna Direita: O Widget em Alta Resolução */}
          <div className="flex-1 rounded-lg border border-cyan-500/30 bg-black/50 p-6 flex flex-col overflow-y-auto shadow-inner relative">
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-cyan-500/20">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-cyan-400" />
                <h3 className="font-['Orbitron'] text-sm font-bold text-white tracking-widest uppercase">
                  {WIDGET_CATALOG.find((w) => w.key === activeWidgetKey)?.title || "VISUALIZAÇÃO"}
                </h3>
              </div>
              <span className="text-[10px] text-cyan-400/60 font-['Orbitron']">
                EXIBIÇÃO AO VIVO
              </span>
            </div>

            <div className="flex-1 flex flex-col justify-start">
              {renderActiveWidget()}
            </div>
          </div>
        </div>

        {/* Rodapé Tático */}
        <footer className="px-6 py-2.5 border-t border-cyan-500/20 bg-black/40 flex justify-between items-center text-[11px] text-cyan-300/60 font-['Orbitron']">
          <span>SELECIONE UM WIDGET PARA INTERAGIR EM TEMPO REAL</span>
          <span>SISTEMA TÁTICO OPERACIONAL</span>
        </footer>
      </div>
    </div>
  );
}

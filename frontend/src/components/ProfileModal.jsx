import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { APP_VERSION } from "../utils/version.js";

import { checkForUpdate, saveUpdateResult } from "../utils/updateCheck.js";

export default function ProfileModal({
  photoUrl,
  name,
  activeWidgets,
  onWidgetsChange,
  onOpenSettings,
  onOpenQr,
  onOpenWidgets,
  onOpenMonitors,
  onOpenMicrophone,
  onClose,
  api,
}) {
  const [updateState, setUpdateState] = useState({ busy: false, text: "", available: false, latest: "" });
  const checkUpdates = async () => {
    setUpdateState({ busy: true, text: "", available: false, latest: "" });
    try {
      const r = await checkForUpdate(api);
      saveUpdateResult(r);
      window.dispatchEvent(new CustomEvent("jarvis-update-check", { detail: r })); // acende a bolinha do ATUALIZAR
      setUpdateState({
        busy: false,
        available: r.updateAvailable,
        latest: r.latestVersion,
        text: r.updateAvailable
          ? `${r.count > 1 ? `${r.count} versões novas` : "Versão nova"}: ${r.latestVersion} (este PC: ${r.currentVersion})`
          : `Em dia: versão ${r.currentVersion}`,
      });
    } catch {
      setUpdateState({ busy: false, text: "Não consegui conferir agora (o JARVIS do PC precisa estar ligado).", available: false, latest: "" });
    }
  };
  const [activeTab, setActiveTab] = useState("perfil"); // "perfil" | "widgets" | "lazer"

  const allWidgets = [
    { key: "status", label: "Painel de Status", desc: "Status dos serviços e conexões" },
    { key: "tasks", label: "Lista de Tarefas", desc: "Gerencie pendências diárias" },
    { key: "focus", label: "Modo Foco / Pomodoro", desc: "Ciclos de produtividade" },
    { key: "launcher", label: "Abrir Programas", desc: "Acesso rápido a aplicativos" },
    { key: "shortcuts", label: "Atalhos Rápidos", desc: "Rotinas e URLs agrupadas" },
    { key: "monitor", label: "Monitoramento de Sistema", desc: "Uso de hardware e memória" },
    { key: "weather", label: "Clima & Sensores", desc: "Temperatura e previsão" },
    { key: "spotify", label: "Controles Spotify", desc: "Player multimídia de música" },
    { key: "about", label: "Sobre Mim", desc: "Dados personalizados do usuário" },
  ];

  // Esc fecha a janela
  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const speak = (text) => {
    if (api) {
      api("/api/speak", { method: "POST", body: JSON.stringify({ text }) }).catch(() => {});
    }
  };

  const handleTabChange = (tab, tabName) => {
    setActiveTab(tab);
    speak(`Acessando ${tabName}, senhor.`);
  };

  const toggleWidget = (key, label) => {
    const isEnabling = !activeWidgets.includes(key);
    const next = isEnabling
      ? [...activeWidgets, key]
      : activeWidgets.filter((w) => w !== key);

    onWidgetsChange(next);
    speak(isEnabling ? `Widget ${label} ativado no painel.` : `Widget ${label} desativado.`);
  };

  const executeAction = (text, speech) => {
    speak(speech);
    if (api) {
      api("/api/chat", { method: "POST", body: JSON.stringify({ message: text }) }).catch(() => {});
    }
  };

  // V5.4: desenhada direto no <body> (portal). Dentro do cabeçalho, que tem efeito de vidro, o
  // "fixed" ficava preso a ele: a janela aparecia cortada no topo em vez de cobrir a tela.
  return createPortal(
    // V5.4: a janela rola quando é mais alta que a tela (antes ficava centralizada e o topo sumia)
    <div
      className="fixed inset-0 z-50 overflow-y-auto overscroll-contain bg-black/80 backdrop-blur-md select-none animate-fadeIn"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      role="dialog"
      aria-modal="true"
      aria-label="Perfil e controles"
    >
     <div className="flex min-h-full items-center justify-center p-4 sm:p-6" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="relative w-full max-w-2xl rounded-xl border border-cyan-500/40 bg-gradient-to-b from-[#082037]/95 via-[#041224]/95 to-[#020813]/98 p-6 shadow-[0_0_50px_rgba(31,194,245,0.3)]">
        {/* Cantos Táticos */}
        <div className="absolute top-2 left-2 w-3.5 h-3.5 border-t-2 border-l-2 border-cyan-400 pointer-events-none" />
        <div className="absolute top-2 right-2 w-3.5 h-3.5 border-t-2 border-r-2 border-cyan-400 pointer-events-none" />
        <div className="absolute bottom-2 left-2 w-3.5 h-3.5 border-b-2 border-l-2 border-cyan-400 pointer-events-none" />
        <div className="absolute bottom-2 right-2 w-3.5 h-3.5 border-b-2 border-r-2 border-cyan-400 pointer-events-none" />

        {/* Topo do Modal com Avatar em Destaque */}
        <header className="flex items-center justify-between border-b border-cyan-500/20 pb-4 mb-4">
          <div className="flex items-center gap-4">
            <div className="relative h-16 w-16 rounded-full border-2 border-cyan-400 overflow-hidden shadow-[0_0_18px_rgba(31,194,245,0.4)]">
              <img src={photoUrl} alt={name} className="h-full w-full object-cover" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-['Orbitron'] text-xl font-bold text-white tracking-wider">
                  {name || "Patrick"}
                </h2>
                <span className="text-[10px] text-[#5eead4] border border-[#5eead4]/40 px-2 py-0.5 rounded font-['Orbitron']">
                  OPERADOR
                </span>
              </div>
              <p className="text-xs text-cyan-300/60 font-['Orbitron'] mt-0.5">
                NÍVEL DE ACESSO: JARVIS · ADMINISTRADOR
              </p>
            </div>
          </div>

          <button
            onClick={() => {
              speak("Fechando perfil.");
              onClose();
            }}
            className="px-3 py-1.5 rounded border border-cyan-500/30 text-cyan-300 hover:text-white hover:bg-cyan-500/20 text-xs font-['Orbitron']"
          >
            ✕ FECHAR
          </button>
        </header>

        {/* Abas */}
        <div className="grid grid-cols-3 gap-2 mb-5 p-1 bg-black/40 border border-cyan-500/20 rounded">
          {[
            ["perfil", "Controle & Ações", "central de controle"],
            ["widgets", "Gerenciar Widgets", "gerenciador de widgets"],
            ["lazer", "Lazer & Filmes", "central de entretenimento e lazer"],
          ].map(([id, label, speechLabel]) => (
            <button
              key={id}
              onClick={() => handleTabChange(id, speechLabel)}
              className={`py-2 text-xs font-['Orbitron'] tracking-wider rounded transition-all ${
                activeTab === id
                  ? "bg-cyan-500/30 text-white font-bold border border-cyan-400 shadow-[0_0_12px_rgba(31,194,245,0.35)]"
                  : "text-cyan-300/60 hover:text-cyan-200"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Aba 1: Perfil e Atalhos Globais */}
        {activeTab === "perfil" && (
          <div className="space-y-3">
            <span className="text-xs font-['Orbitron'] tracking-wider text-cyan-300 block mb-2">
              PAINÉIS DO SISTEMA
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                onClick={() => {
                  speak("Abrindo configurações gerais do JARVIS.");
                  onClose();
                  onOpenSettings();
                }}
                className="p-3.5 rounded-lg border border-cyan-500/30 bg-black/40 hover:border-cyan-400 hover:bg-cyan-950/40 text-left transition"
              >
                <strong className="block text-sm font-['Orbitron'] text-white">⚙ Configurações</strong>
                <p className="text-xs text-cyan-200/60 mt-1">Voz, IA, temas e dispositivos de vídeo</p>
              </button>

              <button
                onClick={() => {
                  speak("Abrindo central de telas e monitores.");
                  onClose();
                  onOpenMonitors();
                }}
                className="p-3.5 rounded-lg border border-cyan-500/30 bg-black/40 hover:border-cyan-400 hover:bg-cyan-950/40 text-left transition"
              >
                <strong className="block text-sm font-['Orbitron'] text-white">▥ Monitores</strong>
                <p className="text-xs text-cyan-200/60 mt-1">Configurar e mover telas auxiliares</p>
              </button>

              <button
                onClick={() => {
                  speak("Abrindo painel geral de widgets.");
                  onClose();
                  onOpenWidgets();
                }}
                className="p-3.5 rounded-lg border border-cyan-500/30 bg-black/40 hover:border-cyan-400 hover:bg-cyan-950/40 text-left transition"
              >
                <strong className="block text-sm font-['Orbitron'] text-white">▦ Central de Widgets</strong>
                <p className="text-xs text-cyan-200/60 mt-1">Organizar e visualizar módulos no HUD</p>
              </button>

              <button
                onClick={() => {
                  speak("Abrindo seleção de microfone do sistema.");
                  onClose();
                  onOpenMicrophone();
                }}
                className="p-3.5 rounded-lg border border-cyan-500/30 bg-black/40 hover:border-cyan-400 hover:bg-cyan-950/40 text-left transition"
              >
                <strong className="block text-sm font-['Orbitron'] text-white">🎙 Mudar Microfone</strong>
                <p className="text-xs text-cyan-200/60 mt-1">Alterar dispositivo de entrada de áudio</p>
              </button>

              <button
                onClick={() => {
                  speak("Gerando código QR para o seu celular.");
                  onClose();
                  onOpenQr();
                }}
                className="p-3.5 rounded-lg border border-cyan-500/30 bg-black/40 hover:border-cyan-400 hover:bg-cyan-950/40 text-left transition"
              >
                <strong className="block text-sm font-['Orbitron'] text-white">📱 Acesso Mobile</strong>
                <p className="text-xs text-cyan-200/60 mt-1">Conectar smartphone na mesma rede</p>
              </button>

              {/* V6.8.3: verificar atualizações (mesma fonte do ⟳ ATUALIZAR) */}
              <button
                onClick={checkUpdates}
                disabled={updateState.busy}
                className="p-3.5 rounded-lg border border-cyan-500/30 bg-black/40 hover:border-cyan-400 hover:bg-cyan-950/40 text-left transition disabled:opacity-60"
              >
                <strong className="block text-sm font-['Orbitron'] text-white">↻ Verificar atualizações</strong>
                <p className="text-xs text-cyan-200/60 mt-1">{updateState.busy ? "Conferindo no GitHub…" : updateState.text || "Ver se há versão nova do JARVIS"}</p>
              </button>
              {updateState.available && (
                <button
                  onClick={() => { onClose(); window.dispatchEvent(new CustomEvent("jarvis-run-update")); }}
                  className="p-3.5 rounded-lg border border-amber-400/70 bg-amber-500/10 hover:bg-amber-500/20 text-left transition"
                >
                  <strong className="block text-sm font-['Orbitron'] text-amber-100">⟳ Atualizar agora</strong>
                  <p className="text-xs text-amber-100/70 mt-1">Baixa a versão {updateState.latest} e reinicia (cerca de 1 min)</p>
                </button>
              )}
            </div>
          </div>
        )}

        {/* Aba 2: Gerenciar Widgets com Fala */}
        {activeTab === "widgets" && (
          <div className="space-y-2">
            <span className="text-xs font-['Orbitron'] tracking-wider text-cyan-300 block mb-1">
              SELEÇÃO DE WIDGETS ATIVOS
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-56 overflow-y-auto pr-1">
              {allWidgets.map((w) => {
                const isActive = activeWidgets.includes(w.key);
                return (
                  <button
                    key={w.key}
                    onClick={() => toggleWidget(w.key, w.label)}
                    className={`p-2.5 rounded border text-left flex justify-between items-center transition ${
                      isActive
                        ? "border-cyan-400 bg-cyan-950/50 shadow-[0_0_10px_rgba(31,194,245,0.2)]"
                        : "border-cyan-500/20 bg-black/30 hover:border-cyan-400/50"
                    }`}
                  >
                    <div>
                      <strong className="block text-xs text-white">{w.label}</strong>
                      <span className="text-[10px] text-cyan-300/50">{w.desc}</span>
                    </div>
                    <span className={`text-[10px] font-['Orbitron'] px-2 py-0.5 rounded border ${
                      isActive ? "border-[#5eead4] text-[#5eead4] bg-emerald-950/40" : "border-cyan-500/20 text-cyan-400/40"
                    }`}>
                      {isActive ? "ATIVO" : "INATIVO"}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Aba 3: Lazer, Filmes, Séries e Produtividade */}
        {activeTab === "lazer" && (
          <div className="space-y-3">
            <span className="text-xs font-['Orbitron'] tracking-wider text-cyan-300 block mb-1">
              COMANDOS RÁPIDOS DE ENTRETENIMENTO
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                onClick={() => {
                  onClose();
                  executeAction("Recomende um filme clássico de ficção científica para hoje", "Consultando os melhores filmes de ficção para você, senhor.");
                }}
                className="p-3 rounded-lg border border-cyan-500/30 bg-black/40 hover:border-cyan-400 text-left transition"
              >
                <span className="text-xl block mb-1">🎬</span>
                <strong className="text-xs text-white font-['Orbitron'] block">Indicação de Filme</strong>
                <p className="text-[11px] text-cyan-200/60 mt-0.5">Sugestão de Sci-Fi e Ação via IA</p>
              </button>

              <button
                onClick={() => {
                  onClose();
                  executeAction("Recomende uma série excelente de tecnologia ou suspense", "Buscando séries recomendadas sobre tecnologia, senhor.");
                }}
                className="p-3 rounded-lg border border-cyan-500/30 bg-black/40 hover:border-cyan-400 text-left transition"
              >
                <span className="text-xl block mb-1">📺</span>
                <strong className="text-xs text-white font-['Orbitron'] block">Indicação de Série</strong>
                <p className="text-[11px] text-cyan-200/60 mt-0.5">Séries envolventes e maratonáveis</p>
              </button>

              <button
                onClick={() => {
                  onClose();
                  executeAction("Inicie o timer de foco pomodoro de 25 minutos", "Iniciando ciclo Pomodoro de 25 minutos. Concentração total.");
                }}
                className="p-3 rounded-lg border border-cyan-500/30 bg-black/40 hover:border-cyan-400 text-left transition"
              >
                <span className="text-xl block mb-1">⏱</span>
                <strong className="text-xs text-white font-['Orbitron'] block">Modo Foco 25m</strong>
                <p className="text-[11px] text-cyan-200/60 mt-0.5">Ciclo tático com contagem regressiva</p>
              </button>

              <button
                onClick={() => {
                  onClose();
                  executeAction("Toque minhas músicas no Spotify", "Conectando ao Spotify e preparando reprodução.");
                }}
                className="p-3 rounded-lg border border-emerald-500/30 bg-black/40 hover:border-emerald-400 text-left transition"
              >
                <span className="text-xl block mb-1">🎵</span>
                <strong className="text-xs text-emerald-200 font-['Orbitron'] block">Spotify Player</strong>
                <p className="text-[11px] text-emerald-300/60 mt-0.5">Músicas e podcasts favoritos</p>
              </button>
            </div>
          </div>
        )}

        {/* Rodapé */}
        <footer className="mt-5 pt-3 border-t border-cyan-500/20 flex justify-between items-center text-[10px] text-cyan-400/50 font-['Orbitron']">
          <span>JARVIS · INTERFACE INTERATIVA COM VOZ</span>
          <span>J.A.R.V.I.S. v{APP_VERSION}</span>
        </footer>
      </div>
     </div>
    </div>,
    document.body,
  );
}

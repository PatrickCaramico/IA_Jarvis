import NowPlaying from "./NowPlaying.jsx";
import { onSpeakingChange, setSpeakerOn, speakerOn, speakHere, stopHere } from "../utils/speakHere.js";
import { IS_JARVIS_APP, appNotificationsEnabled, setAppNotifications } from "../utils/device.js";
import { APP_VERSION } from "../utils/version.js";
import { useEffect, useMemo, useRef, useState } from "react";
import MotivationWidget from "./MotivationWidget.jsx";
import ReactiveCard from "./ReactiveCard.jsx";
import BriefingStage, { VoiceHints } from "./BriefingStage.jsx";
import FanNewsWidget from "./FanNewsWidget.jsx";
import FanScoreWidget from "./FanScoreWidget.jsx";
import FanMatchBanner from "./FanMatchBanner.jsx";
import "../hud-layout.css";
import { startPolling } from "../hooks/usePolling.js";
import useNow from "../hooks/useNow.js";
import lazyComponent from "../utils/lazyComponent.jsx";
import JarvisLogo from "./JarvisLogo.jsx";

// Carregados sob demanda (otimização 4.2: pacote inicial menor)
const ScreensOverlay = lazyComponent(() => import("./ScreensOverlay.jsx"));

const TIME_ZONE = "America/Sao_Paulo";

const SERVICE_DEFS = [
  ["ai", "IA"],
  ["microphone", "Microfone"],
  ["camera", "Câmera"],
  ["internet", "Internet"],
  ["backend", "Backend"],
];

const BRASILIA_CLOCK = new Intl.DateTimeFormat("pt-BR", {
  timeZone: TIME_ZONE,
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});

const RIGHT_IDLE_MS = 3 * 60 * 1000; // V4.2.2: coluna direita recolhe após 3 min sem conversa

// V4.4: data curta embaixo do relógio do cabeçalho ("QUA · 04 NOV")
const BRASILIA_DATE = new Intl.DateTimeFormat("pt-BR", { timeZone: TIME_ZONE, weekday: "short", day: "2-digit", month: "short" });

function useBrasiliaClock() {
  const now = useNow();
  const parts = Object.fromEntries(BRASILIA_DATE.formatToParts(now).map((p) => [p.type, p.value.replace(".", "")]));
  return [BRASILIA_CLOCK.format(now), `${parts.weekday} · ${parts.day} ${parts.month}`.toUpperCase()];
}

function spectrumBase(state, listening) {
  if (listening) return [70, 92, 54, 84, 66, 96, 58, 78, 48, 88, 62, 74];
  if (state === "speaking") return [48, 76, 58, 94, 68, 86, 52, 82, 64, 90, 56, 72];
  if (state === "processing") return [24, 38, 30, 46, 28, 40, 26, 44, 32, 38, 25, 35];
  return [10, 14, 8, 18, 11, 16, 9, 13, 10, 17, 8, 12];
}

function useSpectrum(jarvisState, listening) {
  const [tick, setTick] = useState(0);
  const active = listening || jarvisState !== "idle";
  useEffect(() => {
    if (!active) return undefined;
    const id = setInterval(() => setTick((t) => t + 1), 140);
    return () => clearInterval(id);
  }, [active]);
  const base = useMemo(() => spectrumBase(jarvisState, listening), [jarvisState, listening]);
  return Array.from({ length: 36 }, (_, i) => {
    const h = base[i % base.length] + (((tick + i) % 5) - 2) * 5;
    return Math.max(6, Math.min(100, h));
  });
}

// V4.5: o Canal Ativo guarda as últimas mensagens neste navegador e abre com as conversas anteriores
const CHAT_KEY = "jarvis_chat_log";

function loadPreviousChat() {
  try {
    const saved = JSON.parse(localStorage.getItem(CHAT_KEY) || "[]");
    const old = saved.filter((m) => m.role !== "divider").slice(-30).map((m) => ({ ...m, old: true, cards: [] }));
    return old.length ? [...old, { id: "divider", role: "divider", text: "CONVERSAS ANTERIORES ▲" }] : [];
  } catch {
    return [];
  }
}

function useConversationLog(userText, response, error, responseCards = []) {
  const [log, setLog] = useState(loadPreviousChat);
  useEffect(() => {
    try {
      const keep = log.filter((m) => m.role === "user" || m.role === "jarvis").slice(-40)
        .map(({ id, role, text, at }) => ({ id, role, text, at }));
      localStorage.setItem(CHAT_KEY, JSON.stringify(keep));
    } catch {
      /* sem armazenamento: só não lembra */
    }
  }, [log]);
  const add = (role, text, cards = []) =>
    setLog((current) => {
      const last = current[current.length - 1];
      if (last && last.role === role && last.text === text) return current;
      return [...current, { id: `${Date.now()}-${Math.random()}`, role, text, cards, at: Date.now() }].slice(-70);
    });

  useEffect(() => {
    if (userText) add("user", userText);
  }, [userText]);

  useEffect(() => {
    if (response) add("jarvis", response, responseCards);
  }, [response, responseCards]);

  useEffect(() => {
    if (error) add("error", error);
  }, [error]);

  return log;
}

function Typed({ text }) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    let i = 0;
    setCount(0);
    const id = setInterval(() => {
      i += 1;
      setCount(i);
      if (i >= text.length) clearInterval(id);
    }, 22);
    return () => clearInterval(id);
  }, [text]);
  return (
    <>
      {text.slice(0, count)}
      {count < text.length && <span className="hl-caret" />}
    </>
  );
}

/**
 * Panel móvel e redimensionável com suporte a mover para a Tela 2 (monitor secundário).
 */
// V5.5: 🔊 em cada resposta do JARVIS: fala o texto NESTE aparelho (celular ou navegador). ■ para.
function useSpeakingId() {
  const [id, setId] = useState(null);
  useEffect(() => onSpeakingChange(setId), []);
  return id;
}

function SpeakButton({ id, text }) {
  const speaking = useSpeakingId() === id;
  const [failed, setFailed] = useState(false);
  return (
    <button
      type="button"
      className={`hl-speak${speaking ? " is-on" : ""}${failed ? " is-err" : ""}`}
      onClick={() => {
        if (speaking) { stopHere(); return; }
        setFailed(false);
        speakHere(text, id).catch(() => setFailed(true));
      }}
      title={speaking ? "Parar a leitura" : "Ouvir esta resposta neste aparelho"}
      aria-label={speaking ? "Parar a leitura" : "Ouvir esta resposta"}
    >
      {speaking ? "■" : "🔊"}
    </button>
  );
}

// V5.5: barra do chat: alto-falante (lê as respostas novas sozinho, neste aparelho) e, no app, avisos.
function ChatTools() {
  const [speaker, setSpeaker] = useState(speakerOn);
  const [notif, setNotif] = useState(() => (IS_JARVIS_APP ? appNotificationsEnabled() : false));
  useEffect(() => {
    const onSpeaker = () => setSpeaker(speakerOn());
    window.addEventListener("jarvis_speaker_change", onSpeaker);
    return () => window.removeEventListener("jarvis_speaker_change", onSpeaker);
  }, []);
  return (
    <div className="hl-chat-tools" role="toolbar" aria-label="Opções do chat">
      <button
        type="button"
        className={`hl-chat-tool${speaker ? " is-on" : ""}`}
        aria-pressed={speaker}
        onClick={() => {
          const next = !speaker;
          setSpeakerOn(next);
          setSpeaker(next);
          if (!next) stopHere();
          window.dispatchEvent(new Event("jarvis_speaker_change"));
        }}
        title="Ler as respostas em voz alta neste aparelho"
      >
        {speaker ? "🔊" : "🔈"} ALTO-FALANTE {speaker ? "LIGADO" : "DESLIGADO"}
      </button>
      {IS_JARVIS_APP && (
        <button
          type="button"
          className={`hl-chat-tool${notif ? " is-on" : ""}`}
          aria-pressed={notif}
          onClick={() => {
            const next = !notif;
            setAppNotifications(next);
            setNotif(next);
          }}
          title="Avisos do JARVIS na barra do celular (lembretes, água, alarmes, jogo)"
        >
          📳 AVISOS {notif ? "LIGADOS" : "DESLIGADOS"}
        </button>
      )}
    </div>
  );
}

function Panel({ id, title, tag, className = "", onMoveToSecondary, children }) {
  const [detached, setDetached] = useState(false);
  const [pos, setPos] = useState({ left: 100, top: 100, width: 340, height: "auto" });
  const posRef = useRef(pos);
  const panelRef = useRef(null);
  posRef.current = pos;

  const handleDragStart = (e) => {
    if (e.button !== 0 || e.target.closest("button") || e.target.closest("input")) return;
    e.preventDefault();

    const panelEl = panelRef.current;
    if (!panelEl) return;
    const rect = panelEl.getBoundingClientRect();

    // Se estiver na coluna lateral, calcula a posição exata atual na tela
    const initialLeft = detached ? posRef.current.left : rect.left;
    const initialTop = detached ? posRef.current.top : rect.top;
    const initialWidth = detached ? posRef.current.width : rect.width;
    const initialHeight = detached ? posRef.current.height : rect.height;

    // Distância do cursor em relação ao canto superior esquerdo do widget
    const offsetX = e.clientX - rect.left;
    const offsetY = e.clientY - rect.top;

    if (!detached) {
      setDetached(true);
      setPos({
        left: initialLeft,
        top: initialTop,
        width: initialWidth,
        height: initialHeight,
      });
    }

    document.body.style.userSelect = "none";
    document.body.style.cursor = "grabbing";

    const onMove = (moveEv) => {
      // Movimento suave 1:1 travado no ponteiro do mouse
      const newLeft = moveEv.clientX - offsetX;
      const newTop = moveEv.clientY - offsetY;

      setPos((prev) => ({
        ...prev,
        left: Math.max(8, Math.min(window.innerWidth - 80, newLeft)),
        top: Math.max(8, Math.min(window.innerHeight - 50, newTop)),
      }));
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

  const handleResizeStart = (e) => {
    e.stopPropagation();
    e.preventDefault();
    const startX = e.clientX;
    const startY = e.clientY;
    const initialWidth = typeof posRef.current.width === "number" ? posRef.current.width : 340;
    const initialHeight = typeof posRef.current.height === "number" ? posRef.current.height : 220;

    document.body.style.userSelect = "none";
    document.body.style.cursor = "se-resize";

    const onResize = (moveEv) => {
      setPos((prev) => ({
        ...prev,
        width: Math.max(260, Math.min(window.innerWidth - prev.left - 10, initialWidth + (moveEv.clientX - startX))),
        height: Math.max(140, Math.min(window.innerHeight - prev.top - 10, initialHeight + (moveEv.clientY - startY))),
      }));
    };

    const onResizeUp = () => {
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
      window.removeEventListener("pointermove", onResize);
      window.removeEventListener("pointerup", onResizeUp);
    };

    window.addEventListener("pointermove", onResize);
    window.addEventListener("pointerup", onResizeUp);
  };

  return (
    <section
      ref={panelRef}
      className={`hl-panel ${className} ${detached ? "fixed z-40 shadow-[0_0_30px_rgba(31,194,245,0.45)] border-cyan-400 bg-[#061426]/95 backdrop-blur-md" : ""}`}
      style={detached ? { left: `${pos.left}px`, top: `${pos.top}px`, width: `${pos.width}px`, height: pos.height === "auto" ? "auto" : `${pos.height}px` } : undefined}
    >
      <header
        className="hl-panel-head cursor-grab active:cursor-grabbing select-none"
        onPointerDown={handleDragStart}
        title="Arraste para mover o widget pelo HUD"
      >
        <span className="flex items-center gap-1.5">
          <span className="text-[10px] opacity-70">⠿</span>
          {title}
        </span>
        <div className="flex items-center gap-1">
          {tag != null && <em>{tag}</em>}
          {onMoveToSecondary && (
            <button
              type="button"
              onClick={() => onMoveToSecondary(id || title)}
              className="px-1 text-[11px] text-cyan-400/60 hover:text-white hover:bg-cyan-500/20 rounded transition"
              title="Mover para o Monitor Secundário"
            >
              ⧉
            </button>
          )}
          {detached && (
            <button
              type="button"
              onClick={() => setDetached(false)}
              className="px-1.5 py-0.5 rounded text-[9px] font-['Orbitron'] border border-cyan-500/20 text-cyan-400/80 hover:text-white hover:bg-cyan-500/20"
              title="Fixar de volta no painel lateral"
            >
              ↺ FIXAR
            </button>
          )}
        </div>
      </header>
      {children != null && <div className="hl-panel-body">{children}</div>}

      {detached && (
        <div
          onPointerDown={handleResizeStart}
          className="absolute bottom-0 right-0 w-4 h-4 cursor-se-resize border-r-2 border-b-2 border-cyan-400 rounded-br pointer-events-auto"
          title="Redimensionar widget"
        />
      )}
    </section>
  );
}

function WeatherPanel({ api, onMoveToSecondary }) {
  const [weather, setWeather] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    const load = () =>
      api("/api/weather")
        .then((data) => {
          if (active) {
            setWeather(data);
            setError(false);
          }
        })
        .catch(() => active && setError(true));
    const stop = startPolling(load, 10 * 60 * 1000);
    return () => {
      active = false;
      stop();
    };
  }, [api]);

  return (
    <Panel id="clima" title="SENSORES · CLIMA" tag={weather?.place ?? (error ? "OFFLINE" : "...")} onMoveToSecondary={onMoveToSecondary}>
      {weather ? (
        <div className="hl-weather">
          <div className="hl-gauge">
            <strong>{weather.temperature}°</strong>
          </div>
          <div className="hl-weather-data">
            <span>{weather.description}</span>
            <span>SENSAÇÃO {weather.apparent_temperature}°</span>
            <span>MÁX {weather.maximum}° · MÍN {weather.minimum}°</span>
            <span>CHUVA {weather.rain_probability ?? "--"}%</span>
          </div>
        </div>
      ) : (
        <p className="hl-muted">{error ? "Clima indisponível." : "Consultando o clima..."}</p>
      )}
    </Panel>
  );
}

const WHO = { user: "VOCÊ ▸", jarvis: "JARVIS ▸", error: "ERRO ▸" };

function HudControlsMenu({
  zenMode,
  onToggleZen,
  onOpenWidgets,
  onOpenSettings,
  onCommand,
  fanModeEnabled = false,
}) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    const handleKeyDown = (e) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("pointerdown", handleClickOutside);
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("pointerdown", handleClickOutside);
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  return (
    <div
      ref={menuRef}
      className="relative z-40"
    >
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className={`hl-btn flex items-center gap-2 px-3.5 py-1.5 font-['Orbitron'] font-semibold tracking-wider rounded-full border transition-all duration-150 select-none cursor-pointer ${
          open
            ? fanModeEnabled
              ? "border-emerald-400 text-white bg-emerald-600/30 shadow-[0_0_16px_rgba(52,211,153,0.5)]"
              : "border-cyan-400 text-white bg-cyan-500/25 shadow-[0_0_14px_rgba(79,220,255,0.45)]"
            : fanModeEnabled
            ? "border-emerald-500/40 text-emerald-200 bg-[#02180d]/85 hover:border-emerald-300 hover:bg-emerald-950/50"
            : "border-cyan-400/40 text-cyan-200 bg-[#06182c]/80 hover:border-cyan-300 hover:bg-cyan-950/40"
        }`}
        title="Controles do HUD e Modos de Ambiente"
        aria-expanded={open}
      >
        <span>⚡ CONTROLES</span>
        <span className={`text-[10px] opacity-75 transition-transform duration-150 ${open ? "rotate-180" : ""}`}>▾</span>
      </button>

      {open && (
        <div
          className={`absolute top-[calc(100%+8px)] left-1/2 -translate-x-1/2 w-72 rounded-2xl border p-3 z-50 shadow-[0_12px_40px_rgba(0,0,0,0.9)] backdrop-blur-xl transition-all ${
            fanModeEnabled
              ? "border-emerald-400/40 bg-[#02160d]/95 shadow-[0_0_25px_rgba(4,101,56,0.35)]"
              : "border-cyan-400/50 bg-[#030e1c]/95 shadow-[0_0_25px_rgba(31,194,245,0.25)]"
          }`}
        >
          {/* Header do Menu */}
          <div className="flex items-center justify-between pb-2 mb-2 border-b border-cyan-500/20">
            <span className="text-[10px] font-['Orbitron'] tracking-[0.16em] text-cyan-300/80 font-bold">
              PAINEL DE CONTROLE RÁPIDO
            </span>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="text-cyan-400/60 hover:text-white p-1 rounded hover:bg-cyan-500/20 text-xs font-mono transition"
              title="Fechar"
            >
              ✕
            </button>
          </div>

          {/* Seção 1: Modos de Ambiente */}
          <div className="text-[9px] font-['Orbitron'] tracking-[0.14em] text-cyan-400/60 px-1 mb-1.5 font-semibold">
            MODOS DE AMBIENTE
          </div>
          <div className="flex flex-col gap-1 mb-3">
            <button
              type="button"
              onClick={() => {
                onCommand && onCommand("modo cinema");
                setOpen(false);
              }}
              className="flex items-center gap-3 px-2.5 py-2 rounded-xl text-left text-xs text-cyan-100 hover:text-white hover:bg-cyan-500/20 border border-transparent hover:border-cyan-400/30 transition cursor-pointer active:scale-98"
            >
              <span className="text-base">🎬</span>
              <div>
                <strong className="block font-['Orbitron'] text-[11px] tracking-wide">MODO CINEMA</strong>
                <small className="text-[9px] text-cyan-300/60 block">Volume 45% · Brilho 35%</small>
              </div>
            </button>
            <button
              type="button"
              onClick={() => {
                onCommand && onCommand("modo trabalho");
                setOpen(false);
              }}
              className="flex items-center gap-3 px-2.5 py-2 rounded-xl text-left text-xs text-cyan-100 hover:text-white hover:bg-cyan-500/20 border border-transparent hover:border-cyan-400/30 transition cursor-pointer active:scale-98"
            >
              <span className="text-base">💼</span>
              <div>
                <strong className="block font-['Orbitron'] text-[11px] tracking-wide">MODO FOCO</strong>
                <small className="text-[9px] text-cyan-300/60 block">Volume 30% · Brilho 85%</small>
              </div>
            </button>
            <button
              type="button"
              onClick={() => {
                onCommand && onCommand("modo normal");
                setOpen(false);
              }}
              className="flex items-center gap-3 px-2.5 py-2 rounded-xl text-left text-xs text-cyan-100 hover:text-white hover:bg-cyan-500/20 border border-transparent hover:border-cyan-400/30 transition cursor-pointer active:scale-98"
            >
              <span className="text-base">⚡</span>
              <div>
                <strong className="block font-['Orbitron'] text-[11px] tracking-wide">MODO NORMAL</strong>
                <small className="text-[9px] text-cyan-300/60 block">Volume e brilho padrão</small>
              </div>
            </button>
            <button
              type="button"
              onClick={() => {
                onCommand && onCommand(fanModeEnabled ? "desativar modo torcedor" : "ativar modo torcedor");
                setOpen(false);
              }}
              className={`flex items-center gap-3 px-2.5 py-2 rounded-xl text-left text-xs transition cursor-pointer active:scale-98 border ${
                fanModeEnabled
                  ? "bg-emerald-950/60 border-emerald-400/40 text-emerald-200 hover:bg-emerald-900/60"
                  : "text-cyan-100 hover:text-white hover:bg-cyan-500/20 border-transparent hover:border-cyan-400/30"
              }`}
            >
              <span className="text-base">⚽</span>
              <div>
                <strong className="block font-['Orbitron'] text-[11px] tracking-wide text-emerald-300">
                  MODO TORCEDOR {fanModeEnabled ? "(ATIVO)" : ""}
                </strong>
                <small className="text-[9px] text-emerald-200/70 block">
                  {fanModeEnabled ? "Desativar modo clube" : "Palmeiras · Glassmorphism"}
                </small>
              </div>
            </button>
          </div>

          <div className="flex flex-col gap-1 -mt-2 mb-3">
            <button
              type="button"
              onClick={() => {
                onCommand && onCommand("modo sentinela");
                setOpen(false);
              }}
              className="flex items-center gap-3 px-2.5 py-2 rounded-xl text-left text-xs text-cyan-100 hover:text-white hover:bg-amber-500/15 border border-transparent hover:border-amber-400/40 transition cursor-pointer active:scale-98"
              title="Bloqueia a central e entra no Modo Sentinela"
            >
              <span className="text-base">🛡️</span>
              <div>
                <strong className="block font-['Orbitron'] text-[11px] tracking-wide text-amber-300">MODO SENTINELA</strong>
                <small className="text-[9px] text-amber-200/70 block">Bloqueia e fica ouvindo "Jarvis"</small>
              </div>
            </button>
          </div>

          {/* Seção 2: Saúde e Hidratação */}
          <div className="text-[9px] font-['Orbitron'] tracking-[0.14em] text-cyan-400/60 px-1 mb-1.5 font-semibold">
            SAÚDE & SENSORES
          </div>
          <div className="flex flex-col gap-1 mb-3">
            <button
              type="button"
              onClick={() => {
                onCommand && onCommand("índice de água");
                setOpen(false);
              }}
              className="flex items-center gap-3 px-2.5 py-2 rounded-xl text-left text-xs text-cyan-100 hover:text-white hover:bg-sky-500/20 border border-transparent hover:border-sky-400/40 transition cursor-pointer active:scale-98"
            >
              <span className="text-base">💧</span>
              <div>
                <strong className="block font-['Orbitron'] text-[11px] tracking-wide text-sky-300">
                  ÍNDICE DE ÁGUA
                </strong>
                <small className="text-[9px] text-sky-200/60 block">Consultar hidratação e registrar doses</small>
              </div>
            </button>
          </div>

          {/* Seção 3: Interface HUD */}
          <div className="text-[9px] font-['Orbitron'] tracking-[0.14em] text-cyan-400/60 px-1 mb-1.5 font-semibold">
            INTERFACE & HUD
          </div>
          <div className="flex flex-col gap-1">
            <button
              type="button"
              onClick={() => {
                onToggleZen();
                setOpen(false);
              }}
              className="flex items-center gap-3 px-2.5 py-2 rounded-xl text-left text-xs text-cyan-100 hover:text-white hover:bg-cyan-500/20 border border-transparent hover:border-cyan-400/30 transition cursor-pointer active:scale-98"
            >
              <span className="text-base">{zenMode ? "◫" : "⛶"}</span>
              <div>
                <strong className="block font-['Orbitron'] text-[11px] tracking-wide">
                  {zenMode ? "RESTAURAR HUD" : "ÁREA LIMPA (ZEN)"}
                </strong>
                <small className="text-[9px] text-cyan-300/60 block">
                  {zenMode ? "Exibir todos os painéis" : "Apenas Orbe central"}
                </small>
              </div>
            </button>
            <button
              type="button"
              onClick={() => {
                onOpenWidgets();
                setOpen(false);
              }}
              className="flex items-center gap-3 px-2.5 py-2 rounded-xl text-left text-xs text-cyan-100 hover:text-white hover:bg-cyan-500/20 border border-transparent hover:border-cyan-400/30 transition cursor-pointer active:scale-98"
            >
              <span className="text-base">◫</span>
              <div>
                <strong className="block font-['Orbitron'] text-[11px] tracking-wide">GERENCIAR WIDGETS</strong>
                <small className="text-[9px] text-cyan-300/60 block">Organizar painéis na tela</small>
              </div>
            </button>
            {onOpenSettings && (
              <button
                type="button"
                onClick={() => {
                  onOpenSettings();
                  setOpen(false);
                }}
                className="flex items-center gap-3 px-2.5 py-2 rounded-xl text-left text-xs text-cyan-100 hover:text-white hover:bg-cyan-500/20 border border-transparent hover:border-cyan-400/30 transition cursor-pointer active:scale-98"
              >
                <span className="text-base">⚙</span>
                <div>
                  <strong className="block font-['Orbitron'] text-[11px] tracking-wide">AJUSTES DO SISTEMA</strong>
                  <small className="text-[9px] text-cyan-300/60 block">Configurações gerais e IA</small>
                </div>
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function HudLayout({
  aiName,
  stateLabel,
  jarvisState,
  listening,
  interim,
  connected,
  services = {},
  sessionClock,
  busy,
  api,
  userText,
  response,
  responseCards = [],
  error,
  audioVisible,
  onToggleAudio,
  onOpenSpotify,
  onOpenWidgets,
  onOpenMonitors,
  onOpenSideNav,
  screensTab = null,
  onOpenScreens,
  onCloseScreens,
  onExit,
  onCancel,
  onToggleMic,
  zenMode = false,
  onToggleZen,
  onOpenSettings,
  onOpenGodsEye,
  onCommand,
  showConversation = false,
  profileSlot,
  orbSlot,
  commandSlot,
  tasksSlot,
  fanModeEnabled = false,
  fanTeam = "palmeiras",
  briefing = null,
  onCloseBriefing,
  onSkipBriefing,
  photoUrl = "",
  devices = [],
}) {
  const [clock, todayLabel] = useBrasiliaClock();
  const [screensOpen, setScreensOpen] = useState(false);
  const [leftOpen, setLeftOpen] = useState(true);
  const [booting, setBooting] = useState(true);
  // V4.3: durante o briefing e as telas por assunto a central fica limpa (classe hl-briefing):
  // as colunas laterais somem e o centro ocupa a largura toda, como no vídeo de referência.
  const briefingRunning = briefing?.phase === "running";

  // Seta para a direita pula para o próximo assunto (fora de campos de texto)
  useEffect(() => {
    if (!briefingRunning || !onSkipBriefing) return undefined;
    const onKey = (e) => {
      if (e.key !== "ArrowRight" || e.target.closest?.("input, textarea, [contenteditable]")) return;
      e.preventDefault();
      onSkipBriefing();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [briefingRunning, onSkipBriefing]);

  useEffect(() => {
    // Exibe as duas colunas durante a inicialização (10s) e depois recolhe as duas:
    // V4.4: em espera fica só o orbe e a faixa DIGA:, como na tela limpa do briefing
    const timer = setTimeout(() => {
      setLeftOpen(false);
      setRightOpen(false);
      setBooting(false);
    }, 10000);
    return () => clearTimeout(timer);
  }, []);

  // V4.4: ao fechar a fileira do briefing, volta para o modo em espera limpo (as duas colunas recolhidas)
  const hadBriefing = useRef(false);
  useEffect(() => {
    if (briefing) {
      hadBriefing.current = true;
    } else if (hadBriefing.current) {
      hadBriefing.current = false;
      setLeftOpen(false);
      setRightOpen(false);
    }
  }, [briefing]);

  const bars = useSpectrum(jarvisState, listening);
  const log = useConversationLog(userText, response, error, responseCards);
  // V5.5: alto-falante do chat ligado: cada resposta NOVA do JARVIS é lida neste aparelho
  const spokenRef = useRef(null);
  useEffect(() => {
    const last = log[log.length - 1];
    if (!last || last.role !== "jarvis" || last.old || !last.text) return;
    if (spokenRef.current === null) { spokenRef.current = last.id; return; } // não lê o que já estava na tela
    if (spokenRef.current === last.id) return;
    spokenRef.current = last.id;
    if (speakerOn()) speakHere(last.text, last.id).catch(() => {});
  }, [log]);

  // V4.2.2: a coluna direita (Clima e Canal Ativo) recolhe após 3 min sem conversa, como a esquerda.
  // V4.4: reabre só quando VOCÊ fala ou envia um pedido (não a cada fala do JARVIS) e nunca durante
  // o briefing; assim o modo em espera fica só com o orbe. Mexer nela (digitar, clicar) conta como uso.
  const [rightOpen, setRightOpen] = useState(true);
  const [rightActivity, setRightActivity] = useState(0);
  const touchRight = () => setRightActivity((n) => n + 1);
  const lastMsg = log.length ? log[log.length - 1] : null;
  const lastMsgId = lastMsg ? lastMsg.id : null; // a lista guarda só 50: o id muda sempre
  const lastFromUser = lastMsg?.role === "user";
  useEffect(() => {
    if (briefing) return;
    if (listening || (lastFromUser && lastMsgId)) setRightOpen(true);
  }, [lastMsgId, lastFromUser, listening, briefing]);
  useEffect(() => {
    if (!rightOpen || listening || busy) return undefined;
    const t = setTimeout(() => setRightOpen(false), RIGHT_IDLE_MS);
    return () => clearTimeout(t);
  }, [rightOpen, rightActivity, lastMsgId, listening, busy, interim]);
  const listRef = useRef(null);
  const talking = jarvisState === "speaking";
  const voiceTag = listening ? "OUVINDO" : talking ? "FALANDO" : jarvisState === "processing" ? "PROCESSANDO" : "SILÊNCIO";
  const micOk = services.microphone === true;
  const waiting = busy && !listening && log.length > 0 && log[log.length - 1].role === "user";

  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [log, listening, interim, waiting]);

  const handleMoveToSecondary = (widgetId) => {
    let targetTab = "command";
    const id = String(widgetId).toLowerCase();
    if (id.includes("clima") || id.includes("weather") || id.includes("sensores")) targetTab = "command";
    else if (id.includes("tarefa") || id.includes("tasks")) targetTab = "tasks";
    else if (id.includes("noticia") || id.includes("news")) targetTab = "news";
    else if (id.includes("financeiro") || id.includes("finance")) targetTab = "finance";
    else if (id.includes("filme") || id.includes("media") || id.includes("serie")) targetTab = "media";

    window.open(
      `${window.location.origin}${import.meta.env.BASE_URL}?display=secondary`,
      "jarvis-secondary-display",
      "width=1280,height=720,left=1920,top=0"
    );

    localStorage.setItem("jarvis_display_secondary_tab", targetTab);
    window.dispatchEvent(new StorageEvent("storage", { key: "jarvis_display_secondary_tab", newValue: targetTab }));

    if (api) {
      api("/api/speak", {
        method: "POST",
        body: JSON.stringify({ text: `Movendo widget ${widgetId} para o monitor secundário. Layout tático estendido carregado.` })
      }).catch(() => {});
    }
  };

  return (
    <div className={`hl-root${zenMode && !showConversation ? " hl-zen" : zenMode && showConversation ? " hl-zen hl-zen-chat" : ""}${!leftOpen && !zenMode ? " hl-left-hidden" : ""}${!rightOpen && !zenMode ? " hl-right-hidden" : ""}${briefing ? " hl-briefing" : ""}`}>
      {!rightOpen && !zenMode && (
        <button
          type="button"
          onClick={() => setRightOpen(true)}
          className="hl-right-tab-trigger"
          title="Clique para abrir Clima e Canal Ativo"
        >
          <span>◀ CLIMA & CANAL ATIVO</span>
        </button>
      )}
      {/* Botão de expansão lateral quando a coluna esquerda estiver recolhida */}
      {!leftOpen && !zenMode && (
        <button
          type="button"
          onClick={() => setLeftOpen(true)}
          className="hl-left-tab-trigger"
          title="Clique para abrir Telemetria e Serviços"
        >
          <span>▶ TELEMETRIA & SERVIÇOS</span>
        </button>
      )}

      {/* ===== Barra superior (V4.4: três zonas, controles no centro exato) ===== */}
      <header className="hl-top">
        <div className="hl-brand">
          <button
            type="button"
            className="hl-icon-btn"
            onClick={onOpenSideNav}
            title="Menu de navegação"
            aria-label="Abrir o menu de navegação"
          >
            ☰
          </button>
          <JarvisLogo size={30} spin />
          <span className="hl-brand-name">
            <strong>{aiName}</strong>
            <small>ASSISTENTE PESSOAL · v{APP_VERSION}</small>
          </span>
        </div>

        <div className="hl-top-center">
          <HudControlsMenu
            zenMode={zenMode}
            onToggleZen={onToggleZen}
            onOpenWidgets={onOpenWidgets}
            onOpenSettings={onOpenSettings}
            onCommand={onCommand}
            fanModeEnabled={fanModeEnabled}
          />
        </div>

        <div className="hl-top-right">
          <span
            className={`hl-status${connected ? "" : " is-off"}`}
            title={`Servidor ${connected ? "online" : "offline"} · voz: ${voiceTag.toLowerCase()}`}
          >
            <i aria-hidden="true" />
            <b>{connected ? "SISTEMA ONLINE" : "SISTEMA OFFLINE"}</b>
            <span className="hl-status-sep" aria-hidden="true">·</span>
            <em className={`hl-voice-${jarvisState}${listening ? " is-listening" : ""}`}>VOZ {voiceTag === "SILÊNCIO" ? "LIVRE" : voiceTag}</em>
          </span>
          <span className="hl-clockbox">
            <time className="hl-clock">{clock}</time>
            <small>{todayLabel}</small>
          </span>
          <span className="hl-actions" role="group" aria-label="Atalhos">
            <button
              type="button"
              className={`hl-act${audioVisible ? " is-active" : ""}`}
              onClick={onToggleAudio}
              aria-pressed={audioVisible}
              title="Alternar visualizador de áudio"
            >
              <i aria-hidden="true">♫</i>ÁUDIO
            </button>
            <button type="button" className="hl-act" onClick={onOpenSpotify} title="Spotify">
              <i aria-hidden="true">◉</i>SPOTIFY
            </button>
          </span>
          {(busy || listening) && (
            <button type="button" className="hl-btn hl-btn-danger" onClick={onCancel} title="Cancelar ação atual (Esc)">
              ✕ CANCELAR
            </button>
          )}
          <button
            type="button"
            className="hl-btn hl-btn-power"
            onClick={onExit}
            title="Sair / Tela de Bloqueio"
          >
            ⏻ SAIR
          </button>
          {profileSlot}
        </div>
      </header>

      {/* Banner superior de Dia de Jogo no Modo Torcedor */}
      {fanModeEnabled && <FanMatchBanner api={api} onSend={onCommand} />}

      {/* ===== Coluna esquerda ===== */}
      <aside className="hl-col hl-left">
        <div className="flex items-center justify-between px-1 mb-[-4px]">
          <span className="text-[10px] font-['Orbitron'] tracking-wider text-cyan-400/70">
            {booting ? "INICIALIZAÇÃO DO SISTEMA" : "DIAGNÓSTICO & TELEMETRIA"}
          </span>
          <button
            type="button"
            onClick={() => setLeftOpen(false)}
            className="text-[10px] font-['Orbitron'] text-cyan-400/50 hover:text-cyan-200 transition px-1"
            title="Recolher painel lateral"
          >
            ◀ RECOLHER
          </button>
        </div>
        <Panel id="telemetria-voz" title="TELEMETRIA · VOZ" tag={listening ? "AO VIVO" : talking ? "FALANDO" : "EM ESPERA"} onMoveToSecondary={handleMoveToSecondary}>
          <div className="flex flex-col gap-2">
            <div className="hl-spectrum" aria-label="Visualizador de atividade vocal">
              {bars.map((h, i) => (
                <span key={i} style={{ height: `${h}%` }} />
              ))}
            </div>
            <p className="hl-voice text-xs truncate" title={listening ? (interim || "Ouvindo…") : "Canal de áudio em espera"}>
              {listening ? (interim || "Ouvindo…") : talking ? "JARVIS sintetizando resposta…" : "—"}
            </p>
          </div>
        </Panel>

        <Panel id="servicos" title="NÚCLEO · SERVIÇOS" tag={connected ? "OPERACIONAL" : "DEGRADADO"} onMoveToSecondary={handleMoveToSecondary}>
          <ul className="hl-services">
            {SERVICE_DEFS.map(([key, label]) => {
              const online = key === "backend" ? connected && services[key] !== false : services[key] === true;
              return (
                <li key={key} title={`${label}: ${online ? "ONLINE" : "OFFLINE"}`}>
                  <span>{label}</span>
                  <b className={online ? "ok" : "off"}>{online ? "●" : "○"}</b>
                </li>
              );
            })}
          </ul>
          {/* V5.5: aparelhos com a central aberta agora */}
          {devices && devices.length > 0 && (
            <div className="hl-devices" aria-label="Aparelhos conectados">
              <span className="hl-devices-label">APARELHOS CONECTADOS</span>
              <ul>
                {devices.map((dv) => (
                  <li key={`${dv.kind}-${dv.ip}-${dv.name}`} className={`is-${dv.kind}`} title={dv.ip}>
                    <i aria-hidden="true">{dv.kind === "pc" ? "🖥" : dv.kind === "app" ? "📱" : "🌐"}</i>
                    {dv.name}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Panel>

        {fanModeEnabled && (
          <>
            <Panel id="fan-score" title="PALMEIRAS · PARTIDA" tag="AO VIVO" onMoveToSecondary={handleMoveToSecondary}>
              <FanScoreWidget api={api} onSend={onCommand} compact={true} />
            </Panel>
            <Panel id="fan-news" title="NOTÍCIAS · PALMEIRAS" tag="GE" onMoveToSecondary={handleMoveToSecondary}>
              <div className="max-h-[190px] overflow-y-auto">
                <FanNewsWidget api={api} onSend={onCommand} compact={true} />
              </div>
            </Panel>
          </>
        )}

        <Panel id="tarefas" title="TAREFAS" className="hl-tasks flex-1 min-h-[160px]" onMoveToSecondary={handleMoveToSecondary}>
          <div className="hl-tasks-body">{tasksSlot}</div>
        </Panel>
      </aside>

      {/* ===== Centro ===== */}
      <main className="hl-center">
        <div className={`hl-state ${jarvisState}`}>{stateLabel.toUpperCase()}</div>
        <div className="hl-ticks" aria-hidden="true" />
        <div className="hl-orb">
          {orbSlot}
          {/* V4.3: identificação no orbe enquanto o JARVIS cumprimenta (início do briefing) */}
          {briefingRunning && briefing.index < 0 && photoUrl && (
            <span className="bf-identity" aria-hidden="true">
              <img src={photoUrl} alt="" onError={(e) => { e.currentTarget.parentElement.style.display = "none"; }} />
            </span>
          )}
          {onOpenGodsEye && (
            <button type="button" className="hl-gods-eye-trigger" onClick={onOpenGodsEye} title="Abrir Olho de Deus (G)">
              ◉ OLHO DE DEUS
            </button>
          )}
        </div>
        {!briefing && <div className="hl-quote"><MotivationWidget /></div>}
        {!briefing && !busy && <VoiceHints onSay={onCommand} />}
        <BriefingStage briefing={briefing} onClose={onCloseBriefing} onSkip={onSkipBriefing} onSay={onCommand} />
      </main>

      {/* ===== Coluna direita ===== */}
      <aside className="hl-col hl-right" onPointerDown={touchRight} onKeyDown={touchRight} onWheel={touchRight}>
        <div className="flex items-center justify-end px-1 mb-[-4px]">
          <button
            type="button"
            onClick={() => setRightOpen(false)}
            className="text-[10px] font-['Orbitron'] text-cyan-400/50 hover:text-cyan-200 transition px-1"
            title="Recolher painel lateral"
          >
            RECOLHER ▶
          </button>
        </div>
        <WeatherPanel api={api} onMoveToSecondary={handleMoveToSecondary} />
        <NowPlaying api={api} variant="hud" controls />
        <Panel id="chat" title="JARVIS · CANAL ATIVO" tag={busy ? "OCUPADO" : "PRONTO"} className="hl-channel" onMoveToSecondary={handleMoveToSecondary}>
          <ChatTools />
          <div className="hl-messages" ref={listRef} aria-live="polite" aria-label="Conversa">
            {log.length === 0 && !listening && (
              <p className="hl-msg hl-muted">Digite abaixo ou aperte a barra de espaço para falar.</p>
            )}
            {log.map((m) => m.role === "divider" ? (
              <p key={m.id} className="hl-msg hl-msg-divider" role="separator">{m.text}</p>
            ) : (
              <div key={m.id} className={`hl-msg ${m.role}${m.old ? " is-old" : ""}`}>
                <p style={{ margin: 0 }}>
                  <b>{WHO[m.role]}</b>{" "}
                  {m.role === "jarvis" && !m.old ? <Typed text={m.text} /> : m.text}
                  {m.role === "jarvis" && m.text && <SpeakButton id={m.id} text={m.text} />}
                </p>
                {m.cards && m.cards.length > 0 && (
                  <div className="hl-reactive-cards">
                    {m.cards.map((c, idx) => (
                      <ReactiveCard key={idx} card={c} api={api} />
                    ))}
                  </div>
                )}
              </div>
            ))}
            {listening && (
              <p className="hl-msg user live"><b>VOCÊ ▸</b> Ouvindo… {interim}</p>
            )}
            {waiting && <p className="hl-msg hl-muted">Preparando sua resposta…</p>}
          </div>
          <div className="hl-command">{commandSlot}</div>
        </Panel>
      </aside>

      {/* ===== Barra inferior ===== */}
      <footer className="hl-bottom">
        <button type="button" className="hl-btn" onClick={() => onOpenScreens ? onOpenScreens("command") : setScreensOpen(true)}>TELAS</button>
        <button
          type="button"
          className={`hl-mic ${listening ? "live" : ""}`}
          onClick={onToggleMic}
          aria-label={listening ? "Parar de ouvir" : "Falar com o JARVIS"}
          title="Falar (barra de espaço)"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
            <rect x="9" y="3" width="6" height="11" rx="3" />
            <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
          </svg>
        </button>
        <span className="hl-muted">NUVEM · IA {services.ai === true ? "ONLINE" : "OFFLINE"}</span>
      </footer>

      {(screensOpen || Boolean(screensTab)) && (
        <ScreensOverlay
          api={api}
          services={services}
          connected={connected}
          initialTab={screensTab || "command"}
          onClose={() => {
            setScreensOpen(false);
            if (onCloseScreens) onCloseScreens();
          }}
          onOpenMonitors={onOpenMonitors}
          onSend={onCommand}
        />
      )}
    </div>
  );
}

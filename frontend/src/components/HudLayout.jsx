import NowPlaying from "./NowPlaying.jsx";
import ShoppingList from "./ShoppingList.jsx";
import VoiceButton from "./VoiceButton.jsx";
import HudMissions, { useDeskProgress } from "./HudMissions.jsx";
import { missionsTag } from "../utils/hudProgress.js";
import CountdownWidget from "./CountdownWidget.jsx";
import { clearQueue, onSpeakingChange, speakHere, stopHere } from "../utils/speakHere.js";
import { BACKEND_ON_THIS_PC, setVoiceHere, voiceHere } from "../utils/api.js";
import { IS_JARVIS_APP, appNotificationsEnabled, setAppNotifications } from "../utils/device.js";
import { APP_VERSION } from "../utils/version.js";
import { useEffect, useMemo, useRef, useState } from "react";
import MotivationWidget from "./MotivationWidget.jsx";
import ReactiveCard from "./ReactiveCard.jsx";
import BriefingStage, { VoiceHints } from "./BriefingStage.jsx";
import RemindersStrip from "./RemindersStrip.jsx";
import { OrbTelemetry, StateHint } from "./HudCenter.jsx";
import { micCaption } from "../utils/hudCenter.js";
import { wasStreamed } from "../utils/streamState.js";
import { copyText } from "../utils/copyText.js";
import FanNewsWidget from "./FanNewsWidget.jsx";
import FanScoreWidget from "./FanScoreWidget.jsx";
import FanMatchBanner from "./FanMatchBanner.jsx";
import "../hud-layout.css";
import "../hud-center.css"; // V8.11.1: centro renovado
import { startPolling } from "../hooks/usePolling.js";
import useNow from "../hooks/useNow.js";
import lazyComponent from "../utils/lazyComponent.jsx";
import JarvisLogo from "./JarvisLogo.jsx";
import NewsWindow from "./NewsWindow.jsx";
import ZenGlance from "./ZenGlance.jsx";
import ChatPeek from "./ChatPeek.jsx";
import { peekEnabled, setPeekEnabled } from "../utils/chatPeek.js";
import { applyBackground } from "../utils/theme.js";

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

const RIGHT_IDLE_MS = 90 * 1000; // V4.2.2: coluna direita recolhe sem conversa (V6.5.18: 90 s; antes 3 min)

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

export function useConversationLog(userText, response, error, responseCards = []) { // V8.0: também no Modo Desk
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
  // V6.5.16: LIMPAR conversa ("today" = só hoje; "all" = tudo). Vem do botão ou de outro aparelho.
  useEffect(() => {
    const onClear = (e) => {
      const scope = e.detail?.scope || "today";
      if (scope === "all") {
        setLog([]);
        return;
      }
      const start = new Date();
      start.setHours(0, 0, 0, 0);
      setLog((cur) => {
        const kept = cur.filter((m) => m.role !== "divider" && (m.at || 0) < start.getTime());
        return kept.length ? [...kept, { id: "divider", role: "divider", text: "CONVERSAS ANTERIORES ▲" }] : [];
      });
    };
    window.addEventListener("jarvis-chat-clear", onClear);
    return () => window.removeEventListener("jarvis-chat-clear", onClear);
  }, []);
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
  // V8.13: resposta que já apareceu pelo streaming não é "digitada" de novo; as outras terminam em ~1 s
  // (antes: 22 ms por letra, quase 7 s numa resposta de 300 letras).
  const instant = wasStreamed(text);
  const [count, setCount] = useState(instant ? text.length : 0);
  useEffect(() => {
    if (wasStreamed(text)) {
      setCount(text.length);
      return undefined;
    }
    let i = 0;
    setCount(0);
    const step = Math.max(1, Math.ceil(text.length / 50));
    const id = setInterval(() => {
      i += step;
      setCount(Math.min(i, text.length));
      if (i >= text.length) clearInterval(id);
    }, 20);
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
        if (speaking) { clearQueue(); stopHere(); return; }
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

// V8.13: 📋 copia a resposta (vira ✓ por um instante)
function CopyButton({ text }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      className={`hl-speak hl-copy${done ? " is-on" : ""}`}
      onClick={async () => {
        if (await copyText(text)) {
          setDone(true);
          setTimeout(() => setDone(false), 1500);
        }
      }}
      title={done ? "Copiado" : "Copiar a resposta"}
      aria-label={done ? "Copiado" : "Copiar a resposta"}
    >
      {done ? "✓" : "📋"}
    </button>
  );
}

// V5.7: atalhos do celular: um toque manda o pedido (ou faz o PC falar o que você digitar)
const PHONE_ACTIONS = [
  { icon: "☀", label: "Bom dia", say: "bom dia" },
  { icon: "💧", label: "+250 ml", say: "bebi 250 ml de água" },
  { icon: "☑", label: "Tarefas", say: "quais são minhas tarefas" },
  { icon: "⏰", label: "Alarmes", say: "quais são meus alarmes" },
  { icon: "🛒", label: "Lista", say: "o que tem na lista de compras" },
  { icon: "☁", label: "Clima", say: "como está o clima" },
  { icon: "⏸", label: "Pausar música", say: "pausar a música no spotify" },
  { icon: "🔒", label: "Bloquear PC", say: "bloquear a tela", confirm: "Bloquear a tela do computador?" },
];

// V5.5/5.7: barra do chat. Fora do PC: onde a voz sai (neste aparelho ou no PC), avisos do app,
// atalhos rápidos e "falar no PC". No próprio PC a voz já sai na caixa dele: a barra some.
// V6.5.16: botão LIMPAR do Canal Ativo, com a pergunta "só hoje ou todo o período?"
function ChatClear({ api }) {
  const [asking, setAsking] = useState(false);
  const [note, setNote] = useState("");
  const clear = async (scope) => {
    setAsking(false);
    window.dispatchEvent(new CustomEvent("jarvis-chat-clear", { detail: { scope } }));
    try {
      await api("/api/chat/clear", { method: "POST", body: JSON.stringify({ scope }) });
    } catch {
      /* a tela já limpou; o PC limpa na próxima */
    }
    setNote(scope === "all" ? "Conversa apagada." : "Conversa de hoje apagada.");
    setTimeout(() => setNote(""), 2500);
  };
  return (
    <div className="hl-chat-clear">
      {!asking ? (
        <button type="button" className="hl-chat-clear-btn" onClick={() => setAsking(true)} title="Apagar a conversa">
          🗑 LIMPAR
        </button>
      ) : (
        <div className="hl-chat-clear-ask" role="group" aria-label="Apagar a conversa">
          <span>Apagar qual conversa?</span>
          <button type="button" onClick={() => clear("today")}>Só a de hoje</button>
          <button type="button" className="is-danger" onClick={() => clear("all")}>Todo o período</button>
          <button type="button" className="is-ghost" onClick={() => setAsking(false)}>Cancelar</button>
        </div>
      )}
      {note && <span className="hl-chat-clear-note" role="status">{note}</span>}
    </div>
  );
}

function ChatTools({ api, onCommand }) {
  const [here, setHere] = useState(voiceHere);
  const [notif, setNotif] = useState(() => (IS_JARVIS_APP ? appNotificationsEnabled() : false));
  const [pcMsg, setPcMsg] = useState(null); // null | "" (digitando) | texto
  const [sent, setSent] = useState("");
  if (BACKEND_ON_THIS_PC) return null;

  const sayOnPc = async () => {
    const text = (pcMsg || "").trim();
    if (!text) return;
    try {
      await api("/api/speak/pc", { method: "POST", body: JSON.stringify({ text }) });
      setSent("Falado no PC.");
    } catch {
      setSent("Não consegui falar no PC.");
    }
    setPcMsg(null);
    setTimeout(() => setSent(""), 2500);
  };

  return (
    <div className="hl-chat-tools-wrap">
      <div className="hl-chat-tools" role="toolbar" aria-label="Opções do chat">
        <button
          type="button"
          className={`hl-chat-tool${here ? " is-on" : ""}`}
          aria-pressed={here}
          onClick={() => {
            const next = !here;
            setVoiceHere(next);
            setHere(next);
            if (!next) { clearQueue(); stopHere(); }
          }}
          title="Onde a voz do JARVIS sai quando você pede por aqui"
        >
          {here ? "🔊 VOZ NESTE APARELHO" : "🖥 VOZ NO PC"}
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
        <button type="button" className="hl-chat-tool" onClick={() => setPcMsg(pcMsg === null ? "" : null)} title="O PC fala em voz alta o que você digitar">
          📢 FALAR NO PC
        </button>
      </div>
      {pcMsg !== null && (
        <div className="hl-pc-say">
          <input
            value={pcMsg}
            onChange={(e) => setPcMsg(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") sayOnPc(); }}
            placeholder="O que o PC deve falar? (ex.: O jantar está pronto!)"
            maxLength={300}
            autoFocus
          />
          <button type="button" className="hl-chat-tool is-on" onClick={sayOnPc} disabled={!pcMsg.trim()}>FALAR</button>
        </div>
      )}
      {sent && <p className="hl-pc-sent" role="status">{sent}</p>}
      {onCommand && (
        <div className="hl-quick" aria-label="Atalhos rápidos">
          {PHONE_ACTIONS.map((a) => (
            <button
              key={a.say}
              type="button"
              className="hl-quick-btn"
              onClick={() => { if (!a.confirm || window.confirm(a.confirm)) onCommand(a.say); }}
            >
              <i aria-hidden="true">{a.icon}</i>{a.label}
            </button>
          ))}
        </div>
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

// V6.5.5: painel CONTROLES com mais funções, em grade compacta por seção.
// Cada item ou manda um comando (o mesmo que falar) ou faz uma ação direta na tela.
const CONTROL_SECTIONS = [
  {
    title: "MODOS DE AMBIENTE",
    items: [
      { icon: "🎬", label: "CINEMA", sub: "Vol 45% · brilho 35%", cmd: "modo cinema" },
      { icon: "💼", label: "FOCO", sub: "Vol 30% · brilho 85%", cmd: "modo trabalho" },
      { icon: "⚡", label: "NORMAL", sub: "Volume e brilho padrão", cmd: "modo normal" },
      { id: "fan", icon: "⚽", label: "TORCEDOR", tone: "emerald" },
      { icon: "🛡️", label: "SENTINELA", sub: "Bloqueia a central e fica ouvindo \"Jarvis\"", cmd: "modo sentinela", tone: "amber", wide: true },
    ],
  },
  {
    title: "ROTINAS",
    items: [
      { icon: "📋", label: "RESUMO AGORA", sub: "Pela hora do dia", cmd: "resumo" },
      { icon: "🌙", label: "DORMIR", sub: "Rotina da noite", cmd: "vou dormir" },
      { icon: "🚪", label: "SAINDO DE CASA", sub: "Clima e compras", cmd: "estou saindo" },
      { icon: "⏱", label: "TIMER 5 MIN", sub: "Avisa em 5 minutos", cmd: "timer de 5 minutos" },
    ],
  },
  {
    title: "AÇÕES RÁPIDAS",
    items: [
      { id: "news", icon: "📰", label: "NOTÍCIAS", sub: "Seus temas e busca" },
      { icon: "🛒", label: "COMPRAS", sub: "O que tem na lista", cmd: "o que tem na lista de compras" },
      { icon: "🥤", label: "BEBI UM COPO", sub: "Registra 250 ml", cmd: "bebi um copo de água", tone: "sky" },
      { icon: "💧", label: "ÍNDICE DE ÁGUA", sub: "Hidratação de hoje", cmd: "índice de água", tone: "sky" },
      { id: "reminder", icon: "⏰", label: "NOVO LEMBRETE", sub: "Fica visível na central", tone: "amber" }, // V9.4.2
    ],
  },
  {
    title: "MÚSICA & SOM",
    cols: 3,
    items: [
      { icon: "▶", label: "TOCAR", sub: "Spotify", cmd: "tocar spotify" },
      { icon: "⏸", label: "PAUSAR", sub: "Spotify", cmd: "pausar spotify" },
      { icon: "⏭", label: "PRÓXIMA", sub: "Spotify", cmd: "próxima no spotify" },
      { icon: "🔇", label: "MUDO", sub: "Som do PC", cmd: "silenciar o som" },
      { icon: "🔉", label: "VOL −", sub: "Som do PC", cmd: "diminuir o volume" },
      { icon: "🔊", label: "VOL +", sub: "Som do PC", cmd: "aumentar o volume" },
    ],
  },
  {
    title: "SISTEMA & HUD",
    items: [
      { id: "lock", icon: "🔒", label: "BLOQUEAR", sub: "Volta à tela de bloqueio", tone: "amber" },
      { id: "agents", icon: "🤖", label: "AGENTES", sub: "Rotas, pesquisa e chat" },
      { id: "desk", icon: "🖥", label: "MODO DESK", sub: "O JARVIS como app de assistente (V8)" },
      { id: "desktop_app", icon: "⬇", label: "APP PARA WINDOWS", sub: "Janela própria e ilha no topo" },
      { id: "branding", icon: "📘", label: "BRANDING BOOK", sub: "Identidade visual do JARVIS" }, // V7.2
      { id: "optimize", icon: "⚡", label: "OTIMIZAR", sub: "Medir e deixar mais rápido" }, // V7.2
      { id: "notes", icon: "📝", label: "NOTAS DA VERSÃO", sub: "O que mudou em cada versão" }, // V7.3
      { id: "holo_saved", icon: "⭐", label: "HOLOGRAMAS SALVOS", sub: "Rever apresentações e receitas" }, // V7.14
      { id: "diagnostic", icon: "🩺", label: "DIAGNÓSTICO", sub: "Testar IA, voz, internet e mais" }, // V7.4
      { id: "logs", icon: "📜", label: "LOGS", sub: "Registros e erros do JARVIS" }, // V9.4.2
      // V6.6.5: app Android: espelha a tela do JARVIS numa TV (Chromecast, Smart TV, Miracast)
      { id: "cast", icon: "📺", label: "TRANSMITIR", sub: "Para a TV ou outro aparelho" },
      { id: "silent", icon: "🤫", label: "SILENCIOSO" },
      { id: "background", icon: "🌌", label: "TROCAR FUNDO", sub: "Grade, universo, clássico" },
      { id: "zen", icon: "⛶", label: "ÁREA LIMPA" },
      { id: "widgets", icon: "◫", label: "WIDGETS", sub: "Organizar painéis" },
      { id: "settings", icon: "⚙", label: "AJUSTES", sub: "Configurações e IA" },
    ],
  },
];

// V6.6.5: TRANSMITIR só aparece no app Android que sabe abrir a transmissão de tela
function canCast() {
  try {
    return typeof window !== "undefined" && typeof window.JarvisApp?.cast === "function";
  } catch {
    return false;
  }
}

const CONTROL_TONES = {
  cyan: "text-cyan-100 border-cyan-500/15 hover:border-cyan-300/60 hover:bg-cyan-500/15",
  emerald: "text-emerald-200 border-emerald-500/25 hover:border-emerald-300/70 hover:bg-emerald-500/15",
  amber: "text-amber-200 border-amber-500/25 hover:border-amber-300/70 hover:bg-amber-500/15",
  sky: "text-sky-200 border-sky-500/25 hover:border-sky-300/70 hover:bg-sky-500/15",
  on: "text-white border-cyan-300 bg-cyan-500/25 shadow-[0_0_10px_rgba(79,220,255,0.35)]",
};

function HudControlsMenu({
  zenMode,
  onToggleZen,
  onOpenWidgets,
  onOpenSettings,
  onCommand,
  fanModeEnabled = false,
  api,
  placement = "down", // V6.5.5: "up" = abre para cima (rodapé do celular)
  onLock = null, // V6.5.12: BLOQUEAR (mesmo do botão do topo)
}) {
  const [open, setOpen] = useState(false);
  const [silent, setSilent] = useState(null);
  const [flash, setFlash] = useState("");
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

  // ao abrir, lê o modo silencioso de agora (o botão mostra ligado/desligado)
  useEffect(() => {
    if (!open || !api) return;
    api("/api/prefs").then((p) => setSilent(Boolean(p.silent_mode))).catch(() => {});
  }, [open, api]);

  useEffect(() => {
    if (!flash) return undefined;
    const t = setTimeout(() => setFlash(""), 2200);
    return () => clearTimeout(t);
  }, [flash]);

  const run = async (item) => {
    if (item.cmd) {
      if (onCommand) onCommand(item.cmd);
      setOpen(false);
      return;
    }
    switch (item.id) {
      case "fan":
        if (onCommand) onCommand(fanModeEnabled ? "desativar modo torcedor" : "ativar modo torcedor");
        setOpen(false);
        break;
      case "news":
        window.dispatchEvent(new CustomEvent("jarvis-open-news"));
        setOpen(false);
        break;
      case "silent": {
        if (!api) break;
        const next = !silent;
        setSilent(next);
        try {
          await api("/api/prefs", { method: "PATCH", body: JSON.stringify({ silent_mode: next }) });
          setFlash(next ? "Modo silencioso ligado: o JARVIS não fala." : "Modo silencioso desligado.");
        } catch {
          setSilent(!next);
          setFlash("Não consegui mudar agora.");
        }
        break;
      }
      case "background":
        if (!api) break;
        {
          const order = ["blueprint", "space", "classic"];
          const names = { blueprint: "Blueprint", space: "Universo", classic: "Clássico" };
          const cur = document.documentElement.dataset.sky === "space" ? "space" : (document.documentElement.dataset.bg || "blueprint");
          const next = order[(order.indexOf(cur) + 1) % order.length];
          applyBackground(next);
          setFlash(`Fundo: ${names[next]}.`);
          try {
            await api("/api/background", { method: "POST", body: JSON.stringify({ style: next }) });
          } catch {
            /* sem o PC agora: vale só nesta tela */
          }
        }
        break;
      case "zen":
        onToggleZen();
        setOpen(false);
        break;
      case "widgets":
        onOpenWidgets();
        setOpen(false);
        break;
      case "settings":
        if (onOpenSettings) onOpenSettings();
        setOpen(false);
        break;
      case "agents":
        setOpen(false);
        window.dispatchEvent(new CustomEvent("jarvis-open-agents"));
        break;
      case "branding":
        setOpen(false);
        window.dispatchEvent(new CustomEvent("jarvis-open-branding"));
        break;
      case "optimize":
        setOpen(false);
        window.dispatchEvent(new CustomEvent("jarvis-open-optimizer"));
        break;
      case "notes":
        setOpen(false);
        window.dispatchEvent(new CustomEvent("jarvis-open-notes"));
        break;
      case "logs": // V9.4.2
        setOpen(false);
        window.dispatchEvent(new CustomEvent("jarvis-open-logs"));
        break;
      case "reminder": // V9.4.2
        setOpen(false);
        window.dispatchEvent(new CustomEvent("jarvis-new-reminder"));
        break;
      case "desktop_app":
        setOpen(false);
        window.dispatchEvent(new CustomEvent("jarvis-desktop-download"));
        break;
      case "desk":
        setOpen(false);
        window.dispatchEvent(new CustomEvent("jarvis-desk-toggle", { detail: true }));
        break;
      case "holo_saved":
        setOpen(false);
        window.dispatchEvent(new CustomEvent("jarvis-open-holo-saved"));
        break;
      case "diagnostic":
        setOpen(false);
        window.dispatchEvent(new CustomEvent("jarvis-open-diagnostic"));
        break;
      case "cast":
        setOpen(false);
        try {
          window.JarvisApp?.cast?.();
        } catch {
          /* fora do app */
        }
        break;
      case "lock": // V6.5.12: no celular não havia um jeito claro de voltar ao bloqueio
        setOpen(false);
        if (onLock) onLock();
        else if (onCommand) onCommand("modo bloqueio");
        break;
      default:
        break;
    }
  };

  const describe = (item) => {
    if (item.id === "fan") {
      return { label: fanModeEnabled ? "TORCEDOR · ATIVO" : "TORCEDOR", sub: fanModeEnabled ? "Desativar modo clube" : "Palmeiras", on: fanModeEnabled };
    }
    if (item.id === "silent") {
      return { label: "SILENCIOSO", sub: silent === null ? "…" : silent ? "Ligado · toque p/ falar" : "Desligado", on: Boolean(silent) };
    }
    if (item.id === "zen") {
      return { label: zenMode ? "RESTAURAR HUD" : "ÁREA LIMPA", sub: zenMode ? "Mostrar os painéis" : "Só o orbe", on: zenMode };
    }
    return { label: item.label, sub: item.sub, on: false };
  };

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
          className={`hl-controls-panel absolute ${placement === "up" ? "bottom-[calc(100%+10px)] right-0" : "top-[calc(100%+8px)] left-1/2 -translate-x-1/2"} w-[360px] max-w-[calc(100vw-24px)] max-h-[calc(100dvh-110px)] overflow-y-auto rounded-2xl border p-3 z-50 shadow-[0_12px_40px_rgba(0,0,0,0.9)] backdrop-blur-xl ${
            fanModeEnabled
              ? "border-emerald-400/40 bg-[#02160d]/95 shadow-[0_0_25px_rgba(4,101,56,0.35)]"
              : "border-cyan-400/50 bg-[#030e1c]/95 shadow-[0_0_25px_rgba(31,194,245,0.25)]"
          }`}
          role="menu"
          aria-label="Painel de controle rápido"
        >
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

          {flash && (
            <div className="mb-2 rounded-lg border border-cyan-400/40 bg-cyan-500/10 px-2.5 py-1.5 text-[11px] text-cyan-100" role="status">
              {flash}
            </div>
          )}

          {CONTROL_SECTIONS.map((section) => (
            <div key={section.title} className="mb-2.5 last:mb-0">
              <div className="text-[9px] font-['Orbitron'] tracking-[0.14em] text-cyan-400/60 px-1 mb-1.5 font-semibold">
                {section.title}
              </div>
              <div className={`grid gap-1.5 ${section.cols === 3 ? "grid-cols-3" : "grid-cols-2"}`}>
                {section.items
                  .filter((item) => item.id !== "settings" || onOpenSettings)
                  .filter((item) => item.id !== "cast" || canCast())
                  .map((item) => {
                    const d = describe(item);
                    const toggle = item.id === "silent" || item.id === "zen" || item.id === "fan";
                    return (
                      <button
                        key={item.label}
                        type="button"
                        role="menuitem"
                        onClick={() => run(item)}
                        aria-pressed={toggle ? d.on : undefined}
                        className={`flex min-w-0 items-center gap-2 rounded-xl border bg-black/20 px-2 py-1.5 text-left transition cursor-pointer active:scale-[0.97] ${item.wide ? "col-span-2" : ""} ${
                          d.on ? CONTROL_TONES.on : CONTROL_TONES[item.tone || "cyan"]
                        }`}
                      >
                        <span className="text-[15px] leading-none shrink-0" aria-hidden="true">{item.icon}</span>
                        <span className="min-w-0">
                          <strong className="block truncate font-['Orbitron'] text-[10px] tracking-wide">{d.label}</strong>
                          {d.sub && <small className="block truncate text-[9px] opacity-60">{d.sub}</small>}
                        </span>
                      </button>
                    );
                  })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function HudLayout({
  aiName,
  updateInfo = null, // V6.7.2: { count, latest, notes } quando há versão nova (bolinha no ⟳ ATUALIZAR)
  onUpdate = null,
  onCheckUpdate = null, // V8.12.1: ⟳ ATUALIZAR sempre no topo (confere e atualiza no PC; recarrega no site)
  onOpenPalette = null, // V9.0: botão COMANDOS (o mesmo do Ctrl+K)
  doing = "", // V9.1.2: o que ele está fazendo agora
  userName = "", // V6.5.15: saudação da tela de espera
  onChatActivity = null, // V6.5.18: mexeu no chat (rolar, digitar): segura aberto na Área Limpa
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
  streamText = "", // V8.13: resposta chegando em pedaços
  onStop = null, // V8.13: botão PARAR do chat
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
  onOpenAgents = null, // V6.8.3: Central de Agentes (ao lado do Olho de Deus)
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
  countdowns = [],
  onRemoveCountdown,
}) {
  const [clock, todayLabel] = useBrasiliaClock();
  const [screensOpen, setScreensOpen] = useState(false);
  // V6.5: janela de notícias (botão NOTÍCIAS e toque no aviso de notícia do celular)
  const [newsOpen, setNewsOpen] = useState(false);
  useEffect(() => {
    const open = () => setNewsOpen(true);
    window.addEventListener("jarvis-open-news", open);
    return () => window.removeEventListener("jarvis-open-news", open);
  }, []);
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
  const progress = useDeskProgress(api, response); // V8.12.5: XP e missões do dia (os mesmos do Modo Desk)
  // V5.7: a voz das respostas vem do PC para o aparelho que pediu (evento speak_on_device, App.jsx)

  // V4.2.2: a coluna direita (Clima e Canal Ativo) recolhe após 3 min sem conversa, como a esquerda.
  // V4.4: reabre só quando VOCÊ fala ou envia um pedido (não a cada fala do JARVIS) e nunca durante
  // o briefing; assim o modo em espera fica só com o orbe. Mexer nela (digitar, clicar) conta como uso.
  const [rightOpen, setRightOpen] = useState(true);
  const [updChecking, setUpdChecking] = useState(false); // V8.12.1: ⟳ ATUALIZAR do topo
  const [updNote, setUpdNote] = useState("");
  useEffect(() => {
    if (!updNote) return undefined;
    const t = setTimeout(() => setUpdNote(""), 6000);
    return () => clearTimeout(t);
  }, [updNote]);
  const [rightActivity, setRightActivity] = useState(0);
  const touchRight = () => {
    setRightActivity((n) => n + 1);
    if (onChatActivity) onChatActivity();
  };
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
  const [peekOn, setPeekOn] = useState(peekEnabled); // V9.4.5: transcrição ao vivo
  const talking = jarvisState === "speaking";
  const voiceTag = listening ? "OUVINDO" : talking ? "FALANDO" : jarvisState === "processing" ? "PROCESSANDO" : "SILÊNCIO";
  const micOk = services.microphone === true;
  const waiting = busy && !listening && log.length > 0 && log[log.length - 1].role === "user";

  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [log, listening, interim, waiting, streamText]);

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
    <div className={`hl-root${zenMode && !showConversation ? " hl-zen" : zenMode && showConversation ? " hl-zen hl-zen-chat" : ""}${!leftOpen && !zenMode ? " hl-left-hidden" : ""}${!rightOpen && !zenMode ? " hl-right-hidden" : ""}${briefing ? " hl-briefing" : ""}${briefing?.phase === "done" ? " hl-briefing-done" : ""}`}>
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
      {/* V8.12.1: coluna direita recolhida: o Spotify continua à vista, flutuando no canto */}
      {!rightOpen && !zenMode && !briefing && (
        <aside className="hl-spotify-float" aria-label="Spotify">
          <NowPlaying api={api} variant="hud" controls always onOpen={onOpenSpotify} />
        </aside>
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
            api={api}
            onLock={onExit}
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
            <VoiceButton api={api} /> {/* V8.13: trocar a voz (e a música de entrada) ao lado do ÁUDIO */}
            {/* V8.12.1: sempre aqui, ao lado do ÁUDIO; a bolinha diz quantas versões novas há (antes o botão só
                aparecia quando o PC já sabia de versão nova, e no site nunca) */}
            {onCheckUpdate && (
              <button
                type="button"
                className={`hl-act hl-act-update${updateInfo ? " has-update" : ""}`}
                disabled={updChecking}
                onClick={async () => {
                  setUpdChecking(true);
                  try {
                    setUpdNote(await onCheckUpdate());
                  } finally {
                    setUpdChecking(false);
                  }
                }}
                title={updateInfo ? [`Versão ${updateInfo.latest} disponível`, ...(updateInfo.notes || [])].join("\n") : "Procurar e instalar a versão mais nova do JARVIS"}
              >
                <i aria-hidden="true" className={updChecking ? "is-spinning" : ""}>⟳</i>{updChecking ? "CONFERINDO" : "ATUALIZAR"}
                {updateInfo && (
                  <span className="upd-badge" aria-label={`${updateInfo.count} ${updateInfo.count === 1 ? "atualização disponível" : "atualizações disponíveis"}`}>{updateInfo.count}</span>
                )}
              </button>
            )}
            {updNote && <span className="hl-upd-note" role="status">{updNote}</span>}
            <button type="button" className="hl-act" onClick={onOpenSpotify} title="Spotify">
              <i aria-hidden="true">◉</i>SPOTIFY
            </button>
            {/* V6.5.18: trocar o fundo direto da central (Blueprint -> Universo -> Clássico) */}
            <button
              type="button"
              className="hl-act"
              onClick={async () => {
                const order = ["blueprint", "space", "classic"];
                const cur = document.documentElement.dataset.sky === "space" ? "space" : (document.documentElement.dataset.bg || "blueprint");
                const next = order[(order.indexOf(cur) + 1) % order.length];
                applyBackground(next); // troca na hora; o PC salva para os outros aparelhos
                try {
                  await api("/api/background", { method: "POST", body: JSON.stringify({ style: next }) });
                } catch {
                  /* sem o PC agora: vale só nesta tela */
                }
              }}
              title="Trocar o fundo (Blueprint, Universo, Clássico)"
            >
              <i aria-hidden="true">▦</i>FUNDO
            </button>
          </span>
          {/* V6.7.2: só aparece quando há versão nova; o número diz quantas */}
          {updateInfo && onUpdate && !onCheckUpdate && (
            <button
              type="button"
              className="hl-btn hl-btn-update"
              onClick={() => {
                if (window.confirm(`Atualizar o JARVIS para a versão ${updateInfo.latest}? Ele baixa a versão nova e reinicia (cerca de 1 minuto).`)) onUpdate();
              }}
              title={[`Versão ${updateInfo.latest} disponível`, ...(updateInfo.notes || [])].join("\n")}
            >
              ⟳ ATUALIZAR
              <span className="upd-badge" aria-label={`${updateInfo.count} ${updateInfo.count === 1 ? "atualização disponível" : "atualizações disponíveis"}`}>{updateInfo.count}</span>
            </button>
          )}
          {(busy || listening) && (
            <button type="button" className="hl-btn hl-btn-danger" onClick={onCancel} title="Cancelar ação atual (Esc)">
              ✕ CANCELAR
            </button>
          )}
          <button
            type="button"
            className="hl-btn hl-btn-power"
            onClick={onExit}
            title="Bloquear a central (volta para a tela de bloqueio)"
          >
            🔒 BLOQUEAR
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
      {/* V8.11.1: data-state pinta o brilho atrás do reator (ciano em espera, mais forte pensando, âmbar falando) */}
      <main className="hl-center" data-state={listening ? "listening" : jarvisState}>
        {/* V6.5.15: Área Limpa vira um "smart display": relógio, clima da semana, próximos, água, compras e manchetes */}
        {zenMode && !briefingRunning && <ZenGlance api={api} name={userName} onCommand={onCommand} />}
        <div className={`hl-state ${jarvisState}`}>{stateLabel.toUpperCase()}</div>
        <div className="hl-ticks" aria-hidden="true"><i /></div>
        {/* V8.11.1: o que está acontecendo agora, com o tempo do "pensando" e o cancelar à mão */}
        {!briefing && <StateHint jarvisState={jarvisState} listening={listening} interim={interim} micOk={micOk} onCancel={onCancel} doing={doing} />}
        <div className="hl-orb">
          {orbSlot}
          {!briefing && !zenMode && <OrbTelemetry api={api} connected={connected} onAnalyze={onCommand ? () => onCommand("faz uma auto análise") : null} onCommand={onCommand} />}
          {/* V4.3: identificação no orbe enquanto o JARVIS cumprimenta (início do briefing) */}
          {briefingRunning && briefing.index < 0 && photoUrl && (
            <span className="bf-identity" aria-hidden="true">
              <img src={photoUrl} alt="" onError={(e) => { e.currentTarget.parentElement.style.display = "none"; }} />
            </span>
          )}
        </div>
        {/* V7.4.1: atalhos logo ABAIXO do orbe (antes ficavam por cima, no meio dele) */}
        {(onOpenGodsEye || onOpenAgents) && (
          <nav className="hl-orb-actions" aria-label="Atalhos da central">
            {onOpenGodsEye && (
              <button type="button" className="hl-gods-eye-trigger" onClick={onOpenGodsEye} title="Abrir Olho de Deus (G)">
                ◉ OLHO DE DEUS
              </button>
            )}
            {onOpenAgents && (
              <button type="button" className="hl-agents-trigger" onClick={onOpenAgents} title="Central de Agentes: rotas, pesquisa e chat">
                🤖 AGENTES
              </button>
            )}
            <button type="button" className="hl-agents-trigger" onClick={() => window.dispatchEvent(new CustomEvent("jarvis-desk-toggle", { detail: true }))} title="Modo Desk: o JARVIS como app de assistente pessoal (V8)">
              🖥 MODO DESK
            </button>
            <button type="button" className="hl-agents-trigger" onClick={() => window.dispatchEvent(new CustomEvent("jarvis-desktop-download"))} title="App do JARVIS para Windows, com a ilha no topo da tela">
              ⬇ APP WINDOWS
            </button>
            <button type="button" className="hl-agents-trigger" onClick={() => window.dispatchEvent(new CustomEvent("jarvis-open-reactor"))} title="Personalizar o reator: forma, cor, contraste e brilho (V9.4.2)">
              🎨 REATOR
            </button>
            <button type="button" className="hl-agents-trigger" onClick={() => window.dispatchEvent(new CustomEvent("jarvis-open-branding"))} title="Branding Book: identidade visual do JARVIS">
              📘 BRANDING
            </button>
            <button type="button" className="hl-agents-trigger" onClick={() => window.dispatchEvent(new CustomEvent("jarvis-open-diagnostic"))} title="Diagnóstico: testar IA, voz, internet, microfone e câmera">
              🩺 DIAGNÓSTICO
            </button>
          </nav>
        )}
        {/* V5.6: contagens regressivas pedidas por voz, logo abaixo do orbe */}
        {!briefing && <CountdownWidget items={countdowns} onRemove={onRemoveCountdown} />}
        {!briefing && !zenMode && api && <RemindersStrip api={api} /* V9.4.2: lembretes visíveis na central */ />}
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
        <NowPlaying api={api} variant="hud" controls always onOpen={onOpenSpotify} /> {/* V8.12: sempre visível */}
        {/* V8.12.5: nível, XP, ofensiva e missões do dia, como no Modo Desk */}
        <Panel id="missoes" title="PROGRESSO · MISSÕES" tag={missionsTag(progress.missions)} className="hl-missions" onMoveToSecondary={handleMoveToSecondary}>
          <HudMissions api={api} level={progress.level} missions={progress.missions} onMissions={progress.onMissions} />
        </Panel>
        <Panel id="chat" title="JARVIS · CANAL ATIVO" tag={busy ? "OCUPADO" : "PRONTO"} className="hl-channel" onMoveToSecondary={handleMoveToSecondary}>
          <ChatTools api={api} onCommand={onCommand} />
          {/* V9.4.5: liga e desliga a transcrição ao vivo (a janela de vidro que abre quando ele fala) */}
          <button type="button" className={`hl-peek-toggle${peekOn ? " is-on" : ""}`} aria-pressed={peekOn}
            onClick={() => setPeekOn(setPeekEnabled(!peekOn))}
            title={peekOn ? "A conversa abre numa janela maior quando o JARVIS fala. Toque para desligar." : "Toque para a conversa abrir numa janela maior quando o JARVIS falar."}>
            ◉ TRANSCRIÇÃO {peekOn ? "LIGADA" : "DESLIGADA"}
          </button>
          {log.length > 0 && <ChatClear api={api} />}
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
                  {m.role === "jarvis" && m.text && <CopyButton text={m.text} />}
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
            {/* V8.13: a resposta aparece enquanto a IA escreve */}
            {streamText ? (
              <div className="hl-msg jarvis is-streaming" aria-live="off">
                <p style={{ margin: 0 }}><b>{WHO.jarvis}</b> {streamText}<span className="hl-caret" /></p>
              </div>
            ) : waiting && <p className="hl-msg hl-muted">Preparando sua resposta…</p>}
            {onStop && (busy || jarvisState === "speaking" || streamText) && (
              <button type="button" className="hl-stop" onClick={onStop} title="Parar a resposta e a fala (Esc)">■ PARAR</button>
            )}
          </div>
          <div className="hl-command">{commandSlot}</div>
        </Panel>
        {/* V6.0: lista de compras (voz: "Jarvis, coloca leite na lista") */}
        <Panel id="compras" title="LISTA DE COMPRAS" tag="🛒" className="hl-shop" onMoveToSecondary={handleMoveToSecondary}>
          <ShoppingList api={api} />
        </Panel>
      </aside>

      {/* ===== Barra inferior ===== */}
      <footer className="hl-bottom">
        <span className="hl-btns">
          <button type="button" className="hl-btn" onClick={() => onOpenScreens ? onOpenScreens("command") : setScreensOpen(true)}>TELAS</button>
          <button type="button" className="hl-btn" onClick={() => setNewsOpen(true)}>NOTÍCIAS</button>
          {onOpenPalette && ( /* V9.0: paleta de comandos (o mesmo do Ctrl+K) */
            <button type="button" className="hl-btn hl-btn-cmdk" onClick={onOpenPalette} title="Paleta de comandos (Ctrl+K)" data-testid="cmdk-btn">
              ⌕ COMANDOS <kbd>Ctrl K</kbd>
            </button>
          )}
        </span>
        {/* V8.11.1: o microfone só abre no toque; a legenda diz em que pé ele está */}
        <span className={`hc-mic-wrap is-${listening ? "listening" : jarvisState}`}>
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
          <small className="hc-mic-cap" aria-hidden="true">{micCaption({ listening, state: jarvisState })}</small>
        </span>
        <span className="hl-muted">NUVEM · IA {services.ai === true ? "ONLINE" : "OFFLINE"}</span>
        {/* V6.5.5: no celular, o CONTROLES (que fica no topo do PC) mora aqui no rodapé */}
        <span className="hl-ctrl-mobile">
          <HudControlsMenu
            zenMode={zenMode}
            onToggleZen={onToggleZen}
            onOpenWidgets={onOpenWidgets}
            onOpenSettings={onOpenSettings}
            onCommand={onCommand}
            fanModeEnabled={fanModeEnabled}
            api={api}
            placement="up"
            onLock={onExit}
          />
        </span>
      </footer>

      <ChatPeek
        log={log}
        enabled={peekOn}
        speaking={talking}
        listening={listening}
        interim={interim}
        streamText={streamText}
        zen={zenMode}
        briefing={Boolean(briefing)}
        TextComp={Typed}
        onOpenChat={() => { setRightOpen(true); touchRight(); }}
      />
      {newsOpen && <NewsWindow api={api} onClose={() => setNewsOpen(false)} />}
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

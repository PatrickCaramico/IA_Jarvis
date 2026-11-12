import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import ArcReactorHUD from "./components/ArcReactorHUD.jsx";
import WireOrb from "./components/WireOrb.jsx";
import LockScreen, { BlueprintStamp } from "./components/LockScreen.jsx";
import EnrollScreen from "./components/EnrollScreen.jsx";
import CommandBar from "./components/CommandBar.jsx";
import ProfileMenu from "./components/ProfileMenu.jsx";
import TodoWidget from "./components/TodoWidget.jsx";
import FocusWidget from "./components/FocusWidget.jsx";
import MicrophoneSelectModal from "./components/MicrophoneSelectModal.jsx";
import WeatherWidget from "./components/WeatherWidget.jsx";
import AudioWaveformWidget from "./components/AudioWaveformWidget.jsx";
import DigitalClockWidget from "./components/DigitalClockWidget.jsx";
import SpotifyWidget from "./components/SpotifyWidget.jsx";
import MotivationWidget, { getMotivationMessage } from "./components/MotivationWidget.jsx";
import HudLayout from "./components/HudLayout.jsx";
import SideNav from "./components/SideNav.jsx";
import FanModeBackground from "./components/FanModeBackground.jsx";
import FanNewsWidget from "./components/FanNewsWidget.jsx";
import FanScoreWidget from "./components/FanScoreWidget.jsx";
import FanGoalOverlay from "./components/FanGoalOverlay.jsx";
import NewProfileScreen from "./components/NewProfileScreen.jsx";
import AlarmOverlay from "./components/AlarmOverlay.jsx";
import ProfileWelcome from "./components/ProfileWelcome.jsx";
import WaterWidget from "./components/WaterWidget.jsx";
import FaceRecheckPanel from "./components/FaceRecheckPanel.jsx";
import GuestScreen from "./components/GuestScreen.jsx";
import useSpeechRecognition from "./hooks/useSpeechRecognition.js";
import useClapDetector from "./hooks/useClapDetector.js";
import useSentinelListener from "./hooks/useSentinelListener.js";
import { setPrefs as setPrefsStore } from "./utils/prefsStore.js";
import { effectiveWakeWords, stripWake } from "./utils/wakeWords.js";
import { buildDailySummary, shouldSpeakSummary } from "./utils/lockSummary.js";
import { statusSentence } from "./utils/waterMath.js";
import { subscribeNow } from "./hooks/useNow.js";
import { soundManager } from "./utils/soundEffects.js";
import { API_URL, BACKEND_ON_THIS_PC, api, clientId, getJarvisToken, hasMemoryToken, publicUrl, setJarvisToken } from "./utils/api.js";
import { enqueueHere } from "./utils/speakHere.js";
import { scheduleDailyUpdateCheck } from "./utils/updateCheck.js";
import { applyAccessibility, applyBackground, applyFanMode, applyTheme } from "./utils/theme.js";
import { IS_JARVIS_APP } from "./utils/device.js";
import useJarvisSocket from "./hooks/useJarvisSocket.js";
import useSearchIndicator from "./hooks/useSearchIndicator.js";
import WaterAutoClose from "./components/WaterAutoClose.jsx";
import NotificationTray from "./components/NotificationTray.jsx";
import lazyComponent from "./utils/lazyComponent.jsx";
import OfflineBanner from "./components/ui/OfflineBanner.jsx";
import ProgressBar, { useCreepingProgress } from "./components/ProgressBar.jsx";
import WelcomeLogo from "./components/WelcomeLogo.jsx";
import { APP_VERSION } from "./utils/version.js";
import { tabTitle } from "./utils/tabTitle.js";
import { canResumeSession, hasLoggedBefore, launcherWorks, markLauncherWorks, rememberLogin } from "./utils/session.js";
import GodsEye from "./godseye/GodsEye.jsx";

// Carregados sob demanda (otimização 4.2: pacote inicial menor)
const SettingsPanel = lazyComponent(() => import("./components/SettingsPanel.jsx"));
const DeviceTestModal = lazyComponent(() => import("./components/DeviceTestModal.jsx"));
const NetworkQrModal = lazyComponent(() => import("./components/NetworkQrModal.jsx"));
const WidgetWorkspace = lazyComponent(() => import("./components/WidgetWorkspace.jsx"));
const MonitorPanel = lazyComponent(() => import("./components/MonitorPanel.jsx"));
const LogReportWidget = lazyComponent(() => import("./components/LogReportWidget.jsx"));
const Onboarding = lazyComponent(() => import("./components/Onboarding.jsx"));
const BioScanModal = lazyComponent(() => import("./components/BioScanModal.jsx"));
const DeepSearchModal = lazyComponent(() => import("./components/DeepSearchModal.jsx"));
const SearchModePromptModal = lazyComponent(() => import("./components/SearchModePromptModal.jsx"));

const STATE_LABEL = { idle: "Em espera", processing: "Processando", speaking: "Falando" };

export default function App() {
  // boot -> (enroll | lock) -> main
  const [screen, setScreen] = useState("boot");
  const [bootError, setBootError] = useState("");
  const [bootOffline, setBootOffline] = useState(false); // backend do PC desligado (sem resposta)
  // Botão LIGAR O JARVIS (atalho jarvis://): "" | "trying" | "opening" | "missing"
  const [launchState, setLaunchState] = useState("");
  // V5.1: alarme tocando (evento "alarm" do backend): { id, hora, rotulo, snooze_minutes } ou null
  const [alarm, setAlarm] = useState(null);
  const alarmRef = useRef(null);
  alarmRef.current = alarm;
  // Botão ATUALIZAR: null | { message } enquanto baixa a versão nova e reinicia
  const [updating, setUpdating] = useState(null);
  const [lockPhase, setLockPhase] = useState("ready"); // ready | scanning | verified | failed
  const [lockMessage, setLockMessage] = useState("");
  const [name, setName] = useState("");
  const [photoVersion, setPhotoVersion] = useState(() => Date.now());
  const [enrollError, setEnrollError] = useState("");
  // V4.5: perfis por pessoa — nome de quem acabou de criar o perfil (mostra o painel de boas-vindas)
  const [welcomeName, setWelcomeName] = useState(null);
  const [saving, setSaving] = useState(false);

  const [jarvisState, setJarvisState] = useState("idle"); // idle | processing | speaking
  const [steps, setSteps] = useState({});
  const [userText, setUserText] = useState("");
  const [response, setResponse] = useState("");
  const [responseCards, setResponseCards] = useState([]);
  // V4.3: briefing "bom dia" em etapas (null | {phase: "running" | "done", tabs, current, cards...})
  const [briefing, setBriefing] = useState(null);
  const [error, setError] = useState("");
  const [connected, setConnected] = useState(false);

  // Preferências (Fase 1)
  const [aiName, setAiName] = useState("J.A.R.V.I.S.");
  const [activeWidgets, setActiveWidgets] = useState(["status", "about"]);
  const [fanModeEnabled, setFanModeEnabled] = useState(false);
  const [fanTeam, setFanTeam] = useState("palmeiras");
  const [showSettings, setShowSettings] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(() => localStorage.getItem("jarvis.onboarding.done") !== "1");
  const [services, setServices] = useState({});
  const [deviceTest, setDeviceTest] = useState(null);
  const [showNetworkQr, setShowNetworkQr] = useState(false);
  const [showMicrophoneSelect, setShowMicrophoneSelect] = useState(false);
  const [microphoneId, setMicrophoneId] = useState(() => localStorage.getItem("jarvis.microphone.id") || "");
  const [networkAccessUrl, setNetworkAccessUrl] = useState("");
  const [showWidgetWorkspace, setShowWidgetWorkspace] = useState(false);
  const [widgetLayout, setWidgetLayout] = useState({});
  const [showMonitorPanel, setShowMonitorPanel] = useState(false);
  const [floatingWindows, setFloatingWindows] = useState([]);
  const [showAudioWidget, setShowAudioWidget] = useState(false);
  const [showLogReport, setShowLogReport] = useState(false);
  const [showSideNav, setShowSideNav] = useState(false);
  const [activeSection, setActiveSection] = useState("chat");
  const [screensTab, setScreensTab] = useState(null);
  const [zenMode, setZenMode] = useState(false);
  const [showBioScan, setShowBioScan] = useState(false);
  const [deepSearchData, setDeepSearchData] = useState(null);
  const [searchModePromptData, setSearchModePromptData] = useState(null);
  const searchModePromptDataRef = useRef(null);
  searchModePromptDataRef.current = searchModePromptData;
  const [sessionStartedAt, setSessionStartedAt] = useState(null);
  const [sessionElapsed, setSessionElapsed] = useState(0);

  // ---- Seções 14 a 18 e Modo Sentinela ----
  const [appPrefs, setAppPrefs] = useState({});
  const [accessInfo, setAccessInfo] = useState(null); // {state, effective, enforced}
  const [hasPhoto, setHasPhoto] = useState(false);
  const [faceScan, setFaceScan] = useState({ status: "idle" }); // idle | scanning | verified | failed
  const [recheckOpen, setRecheckOpen] = useState(false);
  const [clapPulse, setClapPulse] = useState(0);
  const [hasPin, setHasPin] = useState(false);
  const [pinState, setPinState] = useState({ busy: false, message: "", lockedUntil: null });
  const [failCount, setFailCount] = useState(0);
  const [autoEntering, setAutoEntering] = useState(false);
  const [sentinelReply, setSentinelReply] = useState("");
  const [sentinelUnlock, setSentinelUnlock] = useState(false);
  // V4.2.2: na tela de bloqueio o microfone (escuta do Sentinela e palmas) começa SILENCIADO;
  // liga com clique no botão do microfone ou com a tecla P.
  const [sentinelMuted, setSentinelMuted] = useState(true);
  const [sentinelCooldown, setSentinelCooldown] = useState(false);
  const [pendingRequest, setPendingRequest] = useState(null);
  const [pendingToRun, setPendingToRun] = useState(null);
  // V4.5: "repetir o briefing ou pular?" na segunda entrada do dia ({ command } | null)
  const [briefingAsk, setBriefingAsk] = useState(null);
  const briefingAskRef = useRef(null);
  briefingAskRef.current = briefingAsk;
  const answerBriefingRef = useRef(() => {});
  answerBriefingRef.current = (repeat) => {
    const ask = briefingAskRef.current;
    setBriefingAsk(null);
    if (repeat && ask) setPendingToRun(ask.command);
    else api("/api/speak", { method: "POST", body: JSON.stringify({ text: "Certo, senhor. Em que posso ajudar?" }) }).catch(() => {});
  };
  useEffect(() => {
    if (!briefingAsk) return undefined;
    const onKey = (e) => {
      if (["INPUT", "TEXTAREA"].includes(e.target?.tagName)) return; // digitando um pedido: não atrapalha
      if (e.key === "Enter") { e.preventDefault(); answerBriefingRef.current(true); }
      if (e.key === "Escape") { e.preventDefault(); answerBriefingRef.current(false); }
    };
    window.addEventListener("keydown", onKey);
    const t = setTimeout(() => setBriefingAsk(null), 45_000); // some sozinha se ninguém responder
    return () => { window.removeEventListener("keydown", onKey); clearTimeout(t); };
  }, [briefingAsk]);
  const [guestReply, setGuestReply] = useState("");
  const [relockWarning, setRelockWarning] = useState(null); // segundos até bloquear
  const [summaryActive, setSummaryActive] = useState(false);
  const [godsEyeOpen, setGodsEyeOpen] = useState(false);
  const [notice, setNotice] = useState("");
  // V4.4: comemoração do Modo Torcedor (gol, gol sofrido, grito) e releitura do placar
  const [fanEvent, setFanEvent] = useState(null);
  const [fanRefresh, setFanRefresh] = useState(0);
  const clearFanEvent = useCallback(() => setFanEvent(null), []);
  const [fanBusy, setFanBusy] = useState(false);
  const [fanError, setFanError] = useState("");
  useEffect(() => {
    if (IS_JARVIS_APP) return undefined;
    return scheduleDailyUpdateCheck(api);
  }, []);
  useEffect(() => {
    if (!fanError) return undefined;
    const t = setTimeout(() => setFanError(""), 5000);
    return () => clearTimeout(t);
  }, [fanError]);
  const [notifItems, setNotifItems] = useState([]);
  // V5.5: aparelhos com a central aberta (evento "devices" do WebSocket)
  const [devices, setDevices] = useState([]);
  const [countdowns, setCountdowns] = useState([]); // V5.6
  const devicesRef = useRef(null);
  const [orbFlash, setOrbFlash] = useState(null); // Branding 4.2: "success" | "error" por um instante
  const orbFlashTimer = useRef(null);
  const flashOrb = (kind) => {
    clearTimeout(orbFlashTimer.current);
    setOrbFlash(kind);
    if (screenRef.current === "main") {
      if (kind === "error") soundManager.playError();
      else soundManager.playStateSuccess();
    }
    orbFlashTimer.current = setTimeout(() => setOrbFlash(null), kind === "error" ? 700 : 600);
  };
  const screenRef = useRef(screen);
  screenRef.current = screen;
  const lockPhaseRef = useRef(lockPhase);
  lockPhaseRef.current = lockPhase;
  const appPrefsRef = useRef(appPrefs);
  appPrefsRef.current = appPrefs;
  const responseCardsRef = useRef(responseCards);
  responseCardsRef.current = responseCards;
  const pendingRequestRef = useRef(pendingRequest);
  pendingRequestRef.current = pendingRequest;
  const wakeHandledRef = useRef(false);
  const lastVoiceRef = useRef(false); // o último pedido veio por voz? (conversa contínua)
  // Verificação rápida ao abrir: rosto reconhecido entra sozinho na central (sem clicar em ENTRAR)
  const quickEnterRef = useRef(false);
  const recheckTimerRef = useRef(null);
  const openWaterPanelRef = useRef(() => {});
  const { openSearchIndicator } = useSearchIndicator();
  const apiWithBase = useCallback((path, options) => api(path, options), []);
  apiWithBase.baseUrl = API_URL;

  const openSpotifyWindow = useCallback((monitor = 1) => {
    setShowMonitorPanel(false);
    setShowWidgetWorkspace(false);
    setFloatingWindows((current) => [
      ...current.filter((item) => item.type !== "spotify"),
      { id: `spotify-${Date.now()}`, type: "spotify", monitor, minimized: false, maximized: false, left: 32, top: 96, width: 384, height: 260 },
    ]);
  }, []);

  useEffect(() => {
    const handleGodsEyeShortcut = (event) => {
      const target = event.target;
      if (screenRef.current !== "main" || target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement) return;
      if (event.key.toLowerCase() !== "g") return;
      setGodsEyeOpen((current) => {
        const next = !current;
        if (next) soundManager.playSuccess();
        else soundManager.playIdle();
        return next;
      });
    };
    window.addEventListener("keydown", handleGodsEyeShortcut);
    return () => window.removeEventListener("keydown", handleGodsEyeShortcut);
  }, []);

  useEffect(() => {
    const handleOpenDeep = (e) => {
      if (e.detail) setDeepSearchData(e.detail);
    };
    window.addEventListener("jarvis_open_deep_search", handleOpenDeep);
    return () => window.removeEventListener("jarvis_open_deep_search", handleOpenDeep);
  }, []);

  const connectedRef = useRef(false);
  const busyRef = useRef(false);
  const bootedRef = useRef(false);
  const enterMainRef = useRef(() => {}); // boot() vem antes de enterMain no arquivo
  // V5.5: fora do PC (app do celular, outro aparelho) a imagem precisa da chave: o <img> não manda cabeçalho
  const photoToken = !BACKEND_ON_THIS_PC && getJarvisToken() ? `&token=${encodeURIComponent(getJarvisToken())}` : "";
  const photoUrl = `${API_URL}/api/profile/photo?v=${photoVersion}${photoToken}`;

  useEffect(() => {
    api("/api/network-access")
      .then((data) => setNetworkAccessUrl(data.url ?? ""))
      .catch(() => {});
  }, []);

  // ---- Carrega preferências ----
  // Com a central bloqueada o backend devolve só as chaves públicas (restricted=true):
  // widgets e layout só são aplicados depois do acesso liberado.
  const loadPrefs = useCallback(() => api("/api/prefs").then((data) => {
    setAiName(data.ai_name ? data.ai_name.toUpperCase() : "J.A.R.V.I.S.");
    if (!data.restricted) {
      setActiveWidgets(data.widgets ?? ["status", "about"]);
      setWidgetLayout(data.widget_layout ?? {});
    }
    applyTheme(data.theme_colors);
    applyBackground(data.background_style);
    applyAccessibility(data);
    const isFan = Boolean(data.fan_mode_enabled);
    const team = data.fan_team || "palmeiras";
    setFanModeEnabled(isFan);
    setFanTeam(team);
    applyFanMode(isFan, team);
    setAppPrefs(data);
    setPrefsStore(data);
    return data;
  }).catch(() => null), []);

  useEffect(() => {
    loadPrefs();
  }, [loadPrefs]);

  useEffect(() => {
    let active = true;
    let timer;
    const loadStatus = () => api("/api/health").then((data) => {
      if (active) setServices(data.services ?? {});
    }).catch(() => active && setServices((current) => ({ ...current, backend: false })));
    const start = () => {
      if (document.hidden) return;
      loadStatus();
      timer = setInterval(loadStatus, 30000);
    };
    const onVisibility = () => {
      clearInterval(timer);
      if (!document.hidden) start();
    };
    start();
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      active = false;
      clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  const handlePrefsChange = useCallback((data) => {
    setAppPrefs(data);
    setPrefsStore(data);
    setAiName(data.ai_name ? data.ai_name.toUpperCase() : "J.A.R.V.I.S.");
    setActiveWidgets(data.widgets ?? ["status", "about"]);
    applyTheme(data.theme_colors);
    if (data.background_style) applyBackground(data.background_style);
    if (data.a11y_text_scale !== undefined) applyAccessibility(data);
    if (data.fan_mode_enabled !== undefined) {
      const isFan = Boolean(data.fan_mode_enabled);
      const team = data.fan_team || fanTeam;
      setFanModeEnabled(isFan);
      setFanTeam(team);
      applyFanMode(isFan, team);
    }
    // Persiste os widgets no backend
    api("/api/prefs", {
      method: "PATCH",
      body: JSON.stringify({ widgets: data.widgets ?? activeWidgets }),
    }).catch(() => {});
  }, [activeWidgets, fanTeam]);

  const handleWidgetsChange = useCallback((widgets) => {
    setActiveWidgets(widgets);
    api("/api/prefs", {
      method: "PATCH",
      body: JSON.stringify({ widgets }),
    }).catch(() => {});
  }, []);

  const openSpotifyPanel = useCallback(() => {
    if (!activeWidgets.includes("spotify")) {
      handleWidgetsChange([...activeWidgets, "spotify"]);
    }
    setShowWidgetWorkspace(true);
  }, [activeWidgets, handleWidgetsChange]);

  // Ao ativar o Modo Torcedor, sobe o widget de notícias imediatamente e, se for dia de jogo, o widget de placar
  useEffect(() => {
    if (fanModeEnabled) {
      api("/api/fan/match")
        .then((res) => {
          const isMatchDay = Boolean(res?.match?.is_match_day);
          setFloatingWindows((current) => {
            let next = [...current];
            if (!next.some((item) => item.type === "fan_news")) {
              next.push({
                id: `fan_news-${Date.now()}`,
                type: "fan_news",
                monitor: 1,
                minimized: false,
                maximized: false,
                left: 28,
                top: 76,
                width: 360,
                height: 380,
              });
            }
            if (isMatchDay && !next.some((item) => item.type === "fan_score")) {
              next.push({
                id: `fan_score-${Date.now() + 1}`,
                type: "fan_score",
                monitor: 1,
                minimized: false,
                maximized: false,
                left: 410,
                top: 76,
                width: 380,
                height: 280,
              });
            }
            return next;
          });
        })
        .catch(() => {
          setFloatingWindows((current) => {
            if (current.some((item) => item.type === "fan_news")) return current;
            return [
              ...current,
              {
                id: `fan_news-${Date.now()}`,
                type: "fan_news",
                monitor: 1,
                minimized: false,
                maximized: false,
                left: 28,
                top: 76,
                width: 360,
                height: 380,
              },
            ];
          });
        });
    } else {
      setFloatingWindows((current) => current.filter((item) => item.type !== "fan_news" && item.type !== "fan_score"));
    }
  }, [fanModeEnabled]);

  const handleWidgetLayoutChange = useCallback((widget_layout) => {
    setWidgetLayout(widget_layout);
    api("/api/prefs", {
      method: "PATCH",
      body: JSON.stringify({ widget_layout }),
    }).catch(() => {});
  }, []);

  // Garante o token no PC local para sincronização uniforme
  useEffect(() => {
    if (!hasMemoryToken()) {
      api("/api/auth/token")
        .then((data) => {
          if (data?.token) setJarvisToken(data.token);
        })
        .catch(() => {});
    }
  }, []);

  // ---- WebSocket com reconexão automática (hooks/useJarvisSocket.js) ----
  const handleSocketMessage = (msg) => {
    switch (msg.type) {
      case "reset":
        setSteps({});
        setResponse("");
        setResponseCards([]);
        setError("");
        break;
      case "state":
        setJarvisState(msg.state);
        busyRef.current = msg.state !== "idle";
        // Cancelado no meio do briefing: os cards já falados ficam na fileira
        if (msg.state === "idle") {
          setBriefing((b) => (b && b.phase === "running"
            ? (b.cards.length ? { ...b, phase: "done" } : null)
            : b));
        }
        break;
      case "alarm":
        setAlarm(msg.state === "ringing" ? { id: msg.id, hora: msg.hora, rotulo: msg.rotulo, snooze_minutes: msg.snooze_minutes } : null);
        break;
      case "briefing_start":
        setBriefing({
          phase: "running",
          mode: msg.mode || "morning", // "evening" = fechamento do "boa noite"
          title: msg.title,
          tabs: msg.tabs || [],
          greeting: msg.greeting,
          opening: msg.opening,
          opening_sub: msg.opening_sub,
          speech: msg.text || "",
          index: -1,
          total: msg.total || 0,
          plan: msg.plan || [], // pauta inteira desde a saudação
          current: null,
          cards: [],
        });
        if (msg.text) setResponse(msg.text); // Canal Ativo ao vivo: cada parte entra como mensagem
        break;
      case "briefing_step":
        setBriefing((b) => (b ? {
          ...b,
          index: msg.index,
          total: msg.total,
          activeTab: msg.tab,
          progress: msg.progress,
          speech: msg.text || "",
          current: msg.card,
          cards: [...b.cards, msg.card],
        } : b));
        if (msg.text) setResponse(msg.text);
        break;
      case "briefing_end":
        setBriefing((b) => ({
          ...(b || {}),
          phase: "done",
          cards: msg.cards || [],
          readiness: msg.readiness,
          closing: msg.closing,
        }));
        break;
      case "speak_on_device":
        // V5.7: a resposta a um pedido DESTE aparelho: a voz toca aqui (o PC ficou em silêncio)
        if (msg.client_id && msg.client_id === clientId() && msg.text) enqueueHere(msg.text);
        break;
      case "countdowns":
        setCountdowns(Array.isArray(msg.items) ? msg.items : []); // V5.6: widget de contagem regressiva
        break;
      case "devices": {
        // V5.5: aparelhos conectados; avisa quando um celular acaba de entrar
        const items = Array.isArray(msg.items) ? msg.items : [];
        const before = new Set((devicesRef.current || []).map((dv) => `${dv.kind}|${dv.ip}|${dv.name}`));
        const fresh = items.filter((dv) => dv.kind !== "pc" && !before.has(`${dv.kind}|${dv.ip}|${dv.name}`));
        if (devicesRef.current !== null && fresh.length && !IS_JARVIS_APP) setNotice(`📱 Conectado: ${fresh[0].name}`);
        devicesRef.current = items;
        setDevices(items);
        break;
      }
      case "access_state":
        setAccessInfo(msg);
        break;
      case "face_scan_start":
        setFaceScan({ status: "scanning", phase: "searching", mode: msg.mode, frame: null });
        break;
      case "face_frame":
        setFaceScan((prev) => ({
          ...prev,
          status: prev.status === "idle" ? "scanning" : prev.status,
          frame: msg.jpeg,
          box: msg.box,
          score: msg.score,
          threshold: msg.threshold,
          phase: msg.phase,
          mode: msg.mode,
        }));
        break;
      case "face_scan_end":
        setFaceScan((prev) => ({
          ...prev,
          status: msg.verified ? "verified" : "failed",
          phase: msg.verified ? "verified" : "failed",
          error: msg.error ? "Câmera indisponível." : prev.error,
        }));
        break;
      case "sentinel_reply":
        setSentinelReply(msg.text || "");
        break;
      case "water_updated":
        // Mantém o texto da resposta igual ao cartão de água (seção 18)
        if (msg.data && responseCardsRef.current.some((c) => c.type === "water")) {
          setResponse(statusSentence(msg.data));
        }
        break;
      case "notice":
        window.dispatchEvent(new CustomEvent("jarvis_notice", { detail: msg.text || "" }));
        break;
      case "step":
        setSteps((prev) => ({ ...prev, [msg.step]: msg.status }));
        break;
      case "response":
        setResponse(msg.text);
        setResponseCards(msg.cards || []);
        if (msg.local) flashOrb("success"); // ação local concluída (timer, água, protocolo...)
        const deepCardWs = (msg.cards || []).find((c) => c.type === "deep_search");
        if (deepCardWs) {
          setDeepSearchData(deepCardWs.data);
        }
        if ((msg.cards || []).some((c) => c.type === "open_logs")) {
          setShowLogReport(true);
        }
        const promptCardWs = (msg.cards || []).find((c) => c.type === "search_mode_prompt");
        if (promptCardWs) {
          setSearchModePromptData(promptCardWs.data);
        }
        if ((msg.cards || []).some((c) => c.type === "water" && c.open_panel)) {
          openWaterPanelRef.current();
        }
        break;
      case "error":
        setError(msg.message);
        flashOrb("error");
        break;
      case "alert": // aviso de timer/lembrete
        setUserText("");
        setError("");
        setResponse(msg.text);
        break;
      case "prefs_updated":
        if (msg.fan_mode_enabled !== undefined) {
          const enabled = Boolean(msg.fan_mode_enabled);
          const team = msg.fan_team || fanTeam;
          setFanModeEnabled(enabled);
          setFanTeam(team);
          applyFanMode(enabled, team);
        }
        if (msg.notice) setNotice(msg.notice); // V4.4: "Hoje tem Palmeiras... Modo Torcedor ativado."
        break;
      case "fan_goal": // V4.4: placar ao vivo mudou
        setFanEvent({ kind: msg.kind, text: msg.text, match: msg.match });
        setFanRefresh((n) => n + 1);
        if (msg.kind === "goal") soundManager.playSuccess();
        break;
      case "fan_moment": // V4.4: intervalo e fim de jogo (uma vez cada)
        setFanEvent({ kind: msg.kind, text: msg.text, match: msg.match });
        setFanRefresh((n) => n + 1);
        break;
      case "notifications": // 4.2: central de notificações (experimental)
        setNotifItems(msg.items || []);
        break;
      case "fan_shout":
        setResponse(msg.text || "AVANTE PALESTRA!");
        setFanEvent({ kind: "shout", text: msg.text });
        break;
      default:
        break;
    }
  };
  useJarvisSocket({
    onMessage: handleSocketMessage,
    onConnectedChange: (isConnected) => {
      connectedRef.current = isConnected;
      setConnected(isConnected);
    },
  });

  // ---- Verificação facial ----
  // mode "login": tela de bloqueio. mode "recheck": reverificação por palma com a central aberta (seção 16).
  // trigger: "button" | "clap" | "wake" (só para o registro de tentativas).
  const verify = useCallback(async ({ mode = "login", trigger = "button" } = {}) => {
    const body = JSON.stringify({ mode, trigger });
    if (mode === "recheck") {
      clearTimeout(recheckTimerRef.current);
      setRecheckOpen(true);
      setFaceScan({ status: "scanning", phase: "searching", mode: "recheck", frame: null });
      try {
        const data = await api("/api/auth/verify", { method: "POST", body });
        setFaceScan((prev) => ({ ...prev, status: data.verified ? "verified" : "failed", phase: data.verified ? "verified" : "failed" }));
      } catch (err) {
        if (err.status === 409) { // ocupado: palmas são ignoradas sem erro na tela
          setRecheckOpen(false);
          setFaceScan({ status: "idle" });
          return;
        }
        setFaceScan((prev) => ({ ...prev, status: "failed", phase: "failed", error: err.message }));
      }
      recheckTimerRef.current = setTimeout(() => {
        setRecheckOpen(false);
        setFaceScan({ status: "idle" });
      }, 3000);
      return;
    }

    setScreen("lock");
    setLockPhase("scanning");
    setLockMessage("");
    setFaceScan({ status: "scanning", phase: "searching", mode: "login", frame: null });
    const apply = (data) => {
      setName(data.name ?? "");
      setLockMessage(data.message ?? "");
      setLockPhase(data.verified ? "verified" : "failed");
      setFailCount((n) => (data.verified ? 0 : n + 1));
    };
    try {
      apply(await api("/api/auth/verify", { method: "POST", body }));
    } catch (err) {
      if (err.message && err.message.includes("ocupado")) {
        try {
          await api("/api/cancel", { method: "POST" });
          await new Promise((r) => setTimeout(r, 600));
          apply(await api("/api/auth/verify", { method: "POST", body }));
          return;
        } catch (retryErr) {
          setLockMessage(retryErr.message);
          setLockPhase("failed");
          setFailCount((n) => n + 1);
          return;
        }
      }
      setLockMessage(err.message);
      setLockPhase("failed");
      setFailCount((n) => n + 1);
    }
  }, []);

  const loadPinStatus = useCallback(() => api("/api/auth/pin/status")
    .then((d) => {
      setHasPin(Boolean(d.has_pin));
      setPinState((cur) => ({ ...cur, lockedUntil: d.locked_until || null }));
    })
    .catch(() => {}), []);

  // ---- Ao abrir/atualizar a página (F5): carrega o perfil e verifica ----
  // ?wake=clap (Ouvinte de Palmas, seção 15): vai para a tela de bloqueio e inicia o escaneamento UMA vez.
  const boot = useCallback(async () => {
    setBootError("");
    const params = new URLSearchParams(window.location.search);
    const wake = params.get("wake") === "clap";
    if (wake) {
      params.delete("wake");
      const clean = params.toString() ? `?${params.toString()}` : "";
      window.history.replaceState({}, "", `${window.location.pathname}${clean}${window.location.hash}`);
    }
    try {
      const profile = await api("/api/profile", { timeout: 10_000 });
      setName(profile.name ?? "");
      setHasPhoto(Boolean(profile.has_photo));
      if (profile.access) setAccessInfo(profile.access);
      // V5.2: já entrou aqui há pouco e o JARVIS do PC continua liberado (F5, nova aba, site):
      // reabre direto na central, sem bloqueio nem verificação de novo. O backend é quem decide.
      if (profile.has_photo && !wake && canResumeSession(profile.access)) {
        wakeHandledRef.current = true;
        loadPinStatus();
        enterMainRef.current(undefined, { resume: true });
        return;
      }
      if (profile.has_photo) {
        // A tela de bloqueio visível significa central bloqueada também no backend.
        // Só no próprio PC: abrir o painel pelo celular (modo rede) não derruba a sessão do computador.
        if (BACKEND_ON_THIS_PC) {
          api("/api/access/lock", { method: "POST" }).then(setAccessInfo).catch(() => {});
        }
        loadPinStatus();
        setLockPhase("ready");
        setLockMessage("");
        setScreen("lock");
        // Verificação rápida: ao abrir (pelo site ou no PC), já lê o rosto uma vez.
        // É você: entra direto na sua central. Não é: a tela oferece criar um perfil novo.
        // No app do celular a câmera seria a do PC, então lá continua pelo PIN.
        if (!wakeHandledRef.current && !IS_JARVIS_APP) {
          wakeHandledRef.current = true;
          quickEnterRef.current = true;
          verify({ trigger: wake ? "wake" : "button" });
        }
      }
      else setScreen("enroll");
    } catch (err) {
      setBootError(err.message);
      setBootOffline(!err.status);
      setScreen("boot");
    }
  }, [verify, loadPinStatus]);

  useEffect(() => {
    if (bootedRef.current) return; // evita rodar duas vezes no modo de desenvolvimento
    bootedRef.current = true;
    boot();
  }, [boot]);

  // Backend do PC desligado: confere sozinho e, quando ele responder, continua (sem piscar a tela).
  // V5.2: a cada 2 s no começo e a cada 5 s depois de 2 min; confere NA HORA quando a aba volta ao foco,
  // quando a rede volta ou quando o celular/PC acorda (é quando o usuário acabou de ligar o JARVIS).
  useEffect(() => {
    if (screen !== "boot" || !bootError || !bootOffline) return undefined;
    let alive = true;
    let timer;
    let checking = false;
    const started = Date.now();
    const check = async () => {
      if (!alive || checking) return;
      checking = true;
      try {
        const ctrl = new AbortController();
        const abort = setTimeout(() => ctrl.abort(), 4000);
        const res = await fetch(`${API_URL}/api/health`, { cache: "no-store", signal: ctrl.signal });
        clearTimeout(abort);
        if (res.ok && alive) {
          alive = false;
          clearTimeout(timer);
          boot();
          return;
        }
      } catch {
        // ainda desligado
      } finally {
        checking = false;
      }
      if (alive) schedule();
    };
    const schedule = () => {
      clearTimeout(timer);
      timer = setTimeout(check, Date.now() - started > 120_000 ? 5000 : 2000);
    };
    const now = () => {
      if (document.visibilityState === "visible") check();
    };
    schedule();
    window.addEventListener("focus", now);
    window.addEventListener("online", now);
    document.addEventListener("visibilitychange", now);
    return () => {
      alive = false;
      clearTimeout(timer);
      window.removeEventListener("focus", now);
      window.removeEventListener("online", now);
      document.removeEventListener("visibilitychange", now);
    };
  }, [screen, bootError, bootOffline, boot]);

  // O navegador não avisa se o atalho jarvis:// existe. Truque: quando ele existe, abre a pergunta
  // "Abrir Iniciar JARVIS?" ou a janela do programa, e esta página perde o foco. Sem isso em ~2,5 s,
  // o atalho não está instalado neste PC e a tela explica como instalar (em vez de "não acontecer nada").
  // V5.2.1: o Chrome novo pergunta "Abrir …?" num quadro DENTRO da página, sem tirar o foco dela.
  // Então não dá para concluir "atalho não instalado" em 2,5 s (a pergunta ainda está esperando o clique).
  // Agora: logo depois do toque, a tela pede para clicar em "Abrir"; se a janela perder o foco, está ligando;
  // só depois de 30 s sem o JARVIS responder aparece a ajuda de instalar o atalho.
  const launchTimerRef = useRef(null);
  const launchJarvis = useCallback(() => {
    clearTimeout(launchTimerRef.current);
    setLaunchState("trying");
    let opened = false;
    const onBlur = () => {
      opened = true;
      markLauncherWorks(); // o atalho existe aqui
      setLaunchState("opening");
    };
    window.addEventListener("blur", onBlur, { once: true });
    window.location.href = "jarvis://iniciar";
    setTimeout(() => {
      if (!opened) setLaunchState(launcherWorks() ? "opening" : "asked");
    }, 1200);
    launchTimerRef.current = setTimeout(() => {
      window.removeEventListener("blur", onBlur);
      if (screenRef.current === "boot") setLaunchState("missing");
    }, 30_000);
  }, []);
  useEffect(() => () => clearTimeout(launchTimerRef.current), []);

  // Botão ATUALIZAR (tela de bloqueio): baixa a versão nova, o JARVIS avisa por voz e reinicia.
  // A tela espera o backend novo subir (boot_id diferente) e recarrega a página com a versão nova.
  // V6.1: barra 0–100% por etapa real: baixar (até 30) -> aviso por voz (até 50) -> reiniciando (até 85)
  // -> versão nova no ar (95) -> recarregando (100)
  const updateJarvis = useCallback(async () => {
    setUpdating({ message: "Baixando a versão mais nova…", stage: "Baixando", target: 30 });
    setScreen("boot");
    let res;
    try {
      res = await api("/api/system/update", { method: "POST", body: JSON.stringify({ confirm: true }) });
    } catch (err) {
      setUpdating(null);
      setLockMessage(err.message);
      setScreen("lock");
      return;
    }
    if (res.status !== "restarting") {
      setUpdating(null);
      setLockPhase("failed");
      setLockMessage(res.message || "Não consegui atualizar.");
      setScreen("lock");
      return;
    }
    const base = res.changed ? `Versão nova baixada (${res.after}).` : "Já estava na versão mais nova.";
    setUpdating({ message: `${base} Avisando e preparando o reinício…`, stage: "Preparando", target: 50 });
    const oldBoot = res.boot_id;
    const started = Date.now();
    let wentDown = false;
    const poll = setInterval(async () => {
      try {
        const r = await fetch(`${API_URL}/api/health`, { cache: "no-store" });
        const h = await r.json();
        if (h.boot_id && h.boot_id !== oldBoot) {
          clearInterval(poll);
          setUpdating({ message: "Versão nova no ar. Carregando a central…", stage: "Carregando", target: 100 });
          setTimeout(() => window.location.reload(), 900); // pega também a interface nova
          return;
        }
      } catch {
        // reiniciando: o backend some por alguns segundos
        if (!wentDown) {
          wentDown = true;
          setUpdating({ message: `${base} Reiniciando os sistemas…`, stage: "Reiniciando", target: 85 });
        }
      }
      if (Date.now() - started > 4 * 60 * 1000) {
        clearInterval(poll);
        setUpdating({ message: "Está demorando mais que o normal. Se não voltar, abra o Iniciar-JARVIS.bat no PC.", slow: true, stage: "Demorando", target: 90 });
      }
    }, 1500);
  }, []);
  const updatePct = useCreepingProgress(updating?.target ?? 0, updating?.target === 100); // no fim, salta para 100

  // V5.7.1: botão ATUALIZAR APP (bloqueio, só no app do celular). O app procura versão nova no PC
  // e responde (evento "jarvis-app-update"); app antigo sem esse recurso: recarrega pelo link
  // jarvis://open, que também confere a atualização.
  const [appUpdateNote, setAppUpdateNote] = useState("");
  const [appUpdatePct, setAppUpdatePct] = useState(null); // V6.1: 0–100 durante o download do APK
  useEffect(() => {
    if (!IS_JARVIS_APP) return undefined;
    const onResult = (e) => {
      const d = e.detail || {};
      setAppUpdateNote(d.message || "");
      setAppUpdatePct(typeof d.pct === "number" ? d.pct : d.status === "updating" ? 0 : null);
    };
    window.addEventListener("jarvis-app-update", onResult);
    return () => window.removeEventListener("jarvis-app-update", onResult);
  }, []);
  useEffect(() => {
    if (!appUpdateNote || appUpdateNote.endsWith("…")) return undefined;
    const t = setTimeout(() => setAppUpdateNote(""), 8000);
    return () => clearTimeout(t);
  }, [appUpdateNote]);
  const updateApp = useCallback(() => {
    setAppUpdateNote("Procurando atualização no PC…");
    try {
      if (window.JarvisApp?.checkUpdate) {
        window.JarvisApp.checkUpdate();
        return;
      }
    } catch {
      /* app antigo: cai no link abaixo */
    }
    window.location.href = "jarvis://open";
  }, []);

  // V5.1: alarme. Ao abrir (ou reconectar), confere se já tem um tocando; os botões chamam o backend.
  useEffect(() => {
    if (screen === "boot") return;
    api("/api/alarms/ringing")
      .then((r) => setAlarm((cur) => (r.ringing ? cur || { hora: r.hora, rotulo: "", snooze_minutes: r.snooze_minutes } : null)))
      .catch(() => {});
  }, [screen]);
  const stopAlarm = useCallback(() => {
    setAlarm(null);
    api("/api/alarms/stop", { method: "POST" }).catch(() => {});
  }, []);
  const snoozeAlarm = useCallback(() => {
    setAlarm(null);
    api("/api/alarms/snooze", { method: "POST" }).catch(() => {});
  }, []);
  const alarmOverlay = <AlarmOverlay alarm={alarm} onStop={stopAlarm} onSnooze={snoozeAlarm} />;

  // ---- Cadastro da foto de perfil ----
  const saveProfile = async (nameValue, photo) => {
    setSaving(true);
    setEnrollError("");
    try {
      await api("/api/profile", { method: "POST", body: JSON.stringify({ name: nameValue, photo }) });
      setName(nameValue);
      setHasPhoto(true);
      setPhotoVersion(Date.now());
      setSaving(false);
      setLockPhase("ready");
      setLockMessage("");
      setScreen("lock");
    } catch (err) {
      setEnrollError(err.message);
      setSaving(false);
    }
  };

  // ---- Entrar na tela principal ----
  // options.skipSummary: usado quando há um pedido pendente do Modo Sentinela (executa direto).
  // options.resume (V5.2): reabrindo uma sessão ainda liberada — sem "Em que posso ajudar?" nem resumo.
  const enterMain = useCallback(async (selectedMicrophoneId = microphoneId, options = {}) => {
    setMicrophoneId(selectedMicrophoneId);
    if (selectedMicrophoneId) localStorage.setItem("jarvis.microphone.id", selectedMicrophoneId);
    rememberLogin();
    // V5.4: em silêncio: a fala da entrada vem do briefing/saudação abaixo (antes saíam duas falas juntas)
    if (!options.resume) api("/api/enter", { method: "POST", body: JSON.stringify({ silent: true }) }).catch(() => {});
    setSteps({});
    setResponse("");
    setError("");
    setUserText("");
    setSessionStartedAt(Date.now());
    setSessionElapsed(0);
    setFloatingWindows([]); // motivação, clima, relógio e tarefas agora ficam dentro do HUD
    setAutoEntering(false);
    setFaceScan({ status: "idle" });
    setSentinelReply("");
    setScreen("main");
    loadPrefs(); // agora com acesso liberado: widgets, layout e demais preferências
    api("/api/countdowns").then((r) => setCountdowns(r.items || [])).catch(() => {}); // V5.6
    api("/api/network-access").then((data) => setNetworkAccessUrl(data.url ?? "")).catch(() => {});

    const prefsNow = appPrefsRef.current || {};
    const speak = (text) => api("/api/speak", {
      method: "POST",
      body: JSON.stringify({ text }),
    });
    const startIntroMusic = () => {
      if (!prefsNow.silent_mode) api("/api/lock/intro-music", { method: "POST" }).catch(() => {});
    };
    if (options.skipSummary || options.resume) return;

    const timeNow = new Date();
    const todayStr = new Intl.DateTimeFormat("pt-BR", {
      timeZone: "America/Sao_Paulo",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(timeNow);

    const lastAccessDate = localStorage.getItem("jarvis_last_access_date");
    const isFirstAccessOfDay = lastAccessDate !== todayStr;
    localStorage.setItem("jarvis_last_access_date", todayStr);

    // V5.4: quem decide é o PC (vale para site, PC e app juntos): 1ª entrada do dia = briefing;
    // 2ª = pergunta UMA vez se repete; depois, só uma saudação curta (sempre diferente). Antes cada
    // navegador tinha a própria memória e o briefing se repetia em cada aparelho.
    const summaryMode = prefsNow.lock_daily_summary || "first_login";
    if (summaryMode !== "off") {
      let decision = null;
      try {
        decision = await api("/api/briefing/entry", { method: "POST", timeout: 8000 });
      } catch {
        decision = null; // PC antigo ou sem resposta: segue sem falar nada
      }
      if (decision?.action === "briefing") {
        setPendingToRun(decision.command);
      } else if (decision?.action === "ask") {
        setBriefingAsk({ command: decision.command });
        if (!prefsNow.silent_mode) speak(decision.text).catch(() => {});
      } else if (decision?.action === "greet" && !prefsNow.silent_mode) {
        speak(decision.text).catch(() => {});
        startIntroMusic();
      }
      return;
    }

    // Resumo do dia (seção 17.3): "off" | "first_login" (padrão, como antes) | "always"
    if (!shouldSpeakSummary(prefsNow.lock_daily_summary || "first_login", isFirstAccessOfDay)) {
      const quickWelcomes = [
        "Sistemas restabelecidos, senhor. Ao seu dispor.",
        "Bem-vindo de volta, senhor. Todos os subsistemas operacionais e prontos.",
        "Reconectado com sucesso, senhor. Aguardando seus comandos.",
        "Painel tático ativo, senhor. Como posso ajudar agora?",
      ];
      const quickReply = quickWelcomes[Math.floor(Math.random() * quickWelcomes.length)];
      speak(quickReply).catch(() => {});
      startIntroMusic();
      return;
    }

    const time = new Intl.DateTimeFormat("pt-BR", {
      timeZone: "America/Sao_Paulo",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(timeNow);
    const [hour, minute] = time.split(":").map(Number);
    const motivation = getMotivationMessage(timeNow);
    const [weatherResult, tasksResult, extraResult] = await Promise.allSettled([
      api("/api/weather"),
      api("/api/tasks?include_completed=false"),
      api("/api/lock/summary-data"),
    ]);
    const weather = weatherResult.status === "fulfilled" ? weatherResult.value : null;
    const tasks = tasksResult.status === "fulfilled" ? (tasksResult.value.tasks ?? []) : [];
    const extra = extraResult.status === "fulfilled" ? extraResult.value : {};
    const summary = buildDailySummary({
      hour,
      minute,
      weather,
      tasks,
      fanMatch: prefsNow.fan_mode_enabled ? extra.fan_match : null,
      waterYesterday: extra.water_yesterday,
      motivation,
    });
    const welcome = "Seja muito bem-vindo ao J.A.R.V.I.S., senhor. "
      + "Todos os sistemas operacionais foram inicializados.";
    setResponse(summary.text);
    setSummaryActive(true);
    speak(welcome)
      .then(() => speak(summary.text))
      .then(startIntroMusic)
      .catch(() => {});
  }, [microphoneId, loadPrefs]);
  enterMainRef.current = enterMain;

  useEffect(() => {
    if (!sessionStartedAt) return undefined;
    const update = () => setSessionElapsed(Math.max(0, Date.now() - sessionStartedAt));
    update();
    return subscribeNow(update); // relógio central, parado com a aba oculta
  }, [sessionStartedAt]);

  const handleLockContinue = useCallback(() => {
    // V4.5: no app do celular o rosto usaria a webcam do PC, então a entrada é pelo PIN
    if (IS_JARVIS_APP && hasPin && (lockPhase === "ready" || lockPhase === "failed")) {
      loadPinStatus();
      setPinState((cur) => ({ ...cur, message: "", busy: false }));
      setLockPhase("pin");
      return;
    }
    if (lockPhase === "ready") verify();
    else if (lockPhase === "verified") {
      if (autoEntering) return;
      // V4.5: entra direto com o microfone padrão (ou o último escolhido); a troca fica em Configurações
      enterMain(microphoneId);
    }
    else if (lockPhase === "failed") verify();
  }, [lockPhase, verify, autoEntering, hasPin, loadPinStatus]);

  // Entrar sozinho (clap_auto_enter) ou com pedido pendente do Sentinela: ~1,5 s após o acesso autorizado
  useEffect(() => {
    if (screen !== "lock" || lockPhase !== "verified") return undefined;
    const pending = pendingRequestRef.current;
    if (!appPrefs.clap_auto_enter && !pending && !quickEnterRef.current) return undefined;
    if (pinResetRef.current) return undefined; // "Esqueci o PIN": espera o PIN novo antes de entrar
    setAutoEntering(true);
    const t = setTimeout(() => {
      setPendingRequest(null);
      if (pending) setPendingToRun(pending);
      enterMain(microphoneId, { skipSummary: Boolean(pending) });
    }, 1500);
    return () => clearTimeout(t);
  }, [screen, lockPhase, appPrefs.clap_auto_enter, enterMain, microphoneId]);

  // PIN de reserva (seção 17.1)
  const openPin = useCallback(() => {
    loadPinStatus();
    setPinState((cur) => ({ ...cur, message: "", busy: false }));
    setLockPhase("pin");
  }, [loadPinStatus]);

  // V5.1 "Esqueci o PIN" na tela de bloqueio: lê o rosto; se for a pessoa, pede o PIN novo duas vezes,
  // salva (rota /api/auth/pin/reset, que só aceita logo depois do rosto confirmado) e entra.
  // pinReset: null | { step: "scan" } | { step: "new" } | { step: "confirm", first }
  const [pinReset, setPinReset] = useState(null);
  const pinResetRef = useRef(null);
  pinResetRef.current = pinReset;
  const forgotPin = useCallback(() => {
    setPinReset({ step: "scan" });
    setPinState((cur) => ({ ...cur, message: "", busy: false }));
    setLockPhase("ready");
    verify();
  }, [verify]);
  useEffect(() => {
    if (pinReset?.step !== "scan") return;
    if (lockPhase === "verified") {
      setPinReset({ step: "new" });
      setPinState({ busy: false, message: "Rosto confirmado. Digite o PIN novo (4 a 8 números).", lockedUntil: null });
      setLockPhase("pin");
    } else if (lockPhase === "failed") {
      setPinReset(null);
    }
  }, [pinReset, lockPhase]);
  const submitNewPin = useCallback(async (pin) => {
    const flow = pinResetRef.current;
    if (!flow) return;
    if (!/^\d{4,8}$/.test(pin)) {
      setPinState((cur) => ({ ...cur, message: "O PIN tem de 4 a 8 números." }));
      return;
    }
    if (flow.step === "new") {
      setPinReset({ step: "confirm", first: pin });
      setPinState((cur) => ({ ...cur, message: "Digite o PIN novo mais uma vez para confirmar." }));
      return;
    }
    if (pin !== flow.first) {
      setPinReset({ step: "new" });
      setPinState((cur) => ({ ...cur, message: "Os dois não bateram. Digite o PIN novo de novo." }));
      return;
    }
    setPinState((cur) => ({ ...cur, busy: true }));
    try {
      const res = await api("/api/auth/pin/reset", { method: "POST", body: JSON.stringify({ new_pin: pin }) });
      setPinReset(null);
      setPinState({ busy: false, message: "", lockedUntil: null });
      setLockMessage(res.weak ? "PIN novo salvo. Dica: evite PINs fáceis como 1234." : "PIN novo salvo.");
      setLockPhase("verified");
    } catch (err) {
      setPinReset(null);
      setPinState({ busy: false, message: err.message, lockedUntil: null });
    }
  }, []);

  const pinEnteredRef = useRef(false);
  const submitPin = useCallback(async (pin) => {
    setPinState((cur) => ({ ...cur, busy: true, message: "" }));
    try {
      const data = await api("/api/auth/pin", { method: "POST", body: JSON.stringify({ pin }) });
      if (data.verified) {
        if (IS_JARVIS_APP) pinEnteredRef.current = true; // V6.0: oferece ativar a digital depois de entrar
        setPinState({ busy: false, message: "", lockedUntil: null });
        setName(data.name ?? "");
        setLockMessage(data.message ?? "");
        setFailCount(0);
        setLockPhase("verified");
      } else {
        setPinState({ busy: false, message: data.message, lockedUntil: data.locked_until || null });
      }
    } catch (err) {
      setPinState((cur) => ({ ...cur, busy: false, message: err.message }));
    }
  }, []);

  // Modo visitante (seção 17.6)
  const enterGuest = useCallback(async () => {
    try {
      const snap = await api("/api/guest/enter", { method: "POST" });
      setAccessInfo(snap);
      setGuestReply("Modo visitante ativo. Pergunte as horas, o clima ou controle a música.");
      setScreen("guest");
    } catch (err) {
      setLockMessage(err.message);
    }
  }, []);

  const exitGuest = useCallback(async () => {
    try {
      const snap = await api("/api/guest/exit", { method: "POST" });
      setAccessInfo(snap);
    } catch { /* volta ao bloqueio mesmo assim */ }
    setGuestReply("");
    setLockPhase("ready");
    setLockMessage("");
    setScreen("lock");
  }, []);

  const guestSend = useCallback(async (text) => {
    if (!text?.trim()) return;
    setGuestReply("...");
    try {
      const data = await api("/api/chat", { method: "POST", body: JSON.stringify({ message: text }) });
      setGuestReply(data.response || "");
    } catch (err) {
      setGuestReply(err.message);
    }
  }, []);

  const openFocusPomodoro = useCallback(() => {
    setFloatingWindows((current) => {
      const exists = current.find((item) => item.type === "focus" || item.type === "pomodoro");
      if (exists) {
        return current.map((item) => (item.id === exists.id ? { ...item, minimized: false } : item));
      }
      return [
        ...current,
        {
          id: `focus-${Date.now()}`,
          type: "focus",
          monitor: 1,
          minimized: false,
          maximized: false,
          left: Math.max(20, Math.floor(window.innerWidth / 2 - 220)),
          top: 90,
          width: 440,
          height: 420,
        },
      ];
    });
  }, []);

  // ---- Enviar mensagem (digitada ou falada) ----
  const send = useCallback(async (text, endpoint = "/api/chat") => {
    if (busyRef.current) return;
    const normalized = text
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
    // V4.5: resposta falada \u00e0 pergunta "repetir o briefing ou pular?"
    const ask = briefingAskRef.current;
    if (ask) {
      if (/\b(repet|repita|sim|quero|pode|manda|bora)/.test(normalized)) { answerBriefingRef.current(true); return; }
      if (/\b(pul|pula|nao|dispens|depois|agora nao|deixa)/.test(normalized)) { answerBriefingRef.current(false); return; }
      setBriefingAsk(null); // outro pedido: segue normalmente
    }
    const speakLocal = (message) => api("/api/speak", {
      method: "POST",
      body: JSON.stringify({ text: message }),
    }).catch(() => {});

    // Função auxiliar para manter o HUD limpo ao executar uma ação solicitada:
    // Fecha popups, modais, painéis e janelas auxiliares abertas anteriormente
    const keepHubClean = () => {
      setShowSideNav(false);
      setShowWidgetWorkspace(false);
      setShowLogReport(false);
      setShowSettings(false);
      setShowNetworkQr(false);
      setShowMonitorPanel(false);
      setShowAudioWidget(false);
      setShowBioScan(false);
      setDeepSearchData(null);
      setSearchModePromptData(null);
      setDeviceTest(null);
      setScreensTab(null);
    };
    if (/\b(abrir|abra|abre|ativar|ativa|mostrar|mostra|iniciar|inicia)\b.*\bolho\s+de\s+deus\b/.test(normalized)
      || /\bolho\s+de\s+deus\b.*\b(abrir|abra|abre|ativar|ativa|mostrar|mostra|iniciar|inicia)\b/.test(normalized)) {
      keepHubClean();
      setUserText(text);
      setGodsEyeOpen(true);
      soundManager.playSuccess();
      speakLocal("Olho de Deus ativado. Monitorando o planeta.");
      return;
    }
    if (/\b(fechar|feche|fecha|sair|saia|desativar|desativa)\b.*\bolho\s+de\s+deus\b/.test(normalized)
      || /\bolho\s+de\s+deus\b.*\b(fechar|feche|fecha|sair|saia|desativar|desativa)\b/.test(normalized)) {
      setUserText(text);
      setGodsEyeOpen(false);
      speakLocal("Olho de Deus fechado. O orbe permanece em espera.");
      return;
    }
    const isSpotifyOpen = /\b(?:abrir|abra|abre|iniciar|inicie|acessar|acesse|mostrar|mostre)\b.*\bspotify\b/.test(normalized)
      || /\bspotify\b.*\b(?:abrir|abra|abre|iniciar|inicie|acessar|acesse|mostrar|mostre)\b/.test(normalized);
    if (isSpotifyOpen) {
      openSearchIndicator("JARVIS · abrindo Spotify");
    }
    if (isSpotifyOpen) {
      setUserText(text);
      openSpotifyWindow();
      api("/api/chat", { method: "POST", body: JSON.stringify({ message: text }) })
        .then((data) => setResponse(data.response ?? "Spotify aberto no aplicativo do computador, senhor."))
        .catch((err) => setError(err.message));
      return;
    }
    const isDeviceTest = /\b(testar|teste|verificar|verifique|checar|checagem)\b/.test(normalized);
    const wantsMicrophoneTest = /\b(microfone|mic)\b/.test(normalized);
    const wantsCameraTest = /\b(câmera|camera|webcams?)\b/.test(normalized);
    if (isDeviceTest && wantsMicrophoneTest) {
      keepHubClean();
      setUserText(text);
      setDeviceTest("microphone");
      return;
    }
    if (isDeviceTest && wantsCameraTest) {
      keepHubClean();
      setUserText(text);
      setDeviceTest("camera");
      return;
    }
    if (/\b(abrir|abra|mostrar|mostre)\b.*\b(celular|telemóvel|telefone)\b|\b(celular|telemóvel|telefone)\b.*\b(abrir|acessar|mostrar)\b/.test(normalized)) {
      keepHubClean();
      setUserText(text);
      setShowNetworkQr(true);
      return;
    }
    if (/\b(abrir|abra|mostrar|mostre)\b.*\b(clima|tempo|previsão)\b/.test(normalized)) {
      keepHubClean();
      setUserText(text);
      setFloatingWindows((current) => current.some((item) => item.type === "weather")
        ? current
        : [...current, { id: `weather-${Date.now()}`, type: "weather", monitor: 1, minimized: false, maximized: false, left: 32, top: 96 }]);
      return;
    }
    if (/\b(abrir|abra|mostrar|mostre|detectar|listar)\b.*\b(monitores?|telas?)\b/.test(normalized)) {
      keepHubClean();
      setUserText(text);
      setShowMonitorPanel(true);
      api("/api/speak", {
        method: "POST",
        body: JSON.stringify({ text: "Vou verificar as telas disponíveis, senhor." }),
      }).catch(() => {});
      return;
    }
    if (/\b(abrir|abra|mostrar|mostre|exibir|acessar)\b.*\b(relogio|hora)\b/.test(normalized)
      || /\b(relogio|hora)\b.*\b(abrir|abra|mostrar|mostre|exibir|acessar)\b/.test(normalized)) {
      keepHubClean();
      setUserText(text);
      setFloatingWindows((current) => current.some((item) => item.type === "clock")
        ? current
        : [...current, { id: `clock-${Date.now()}`, type: "clock", monitor: 1, minimized: false, maximized: false, left: 32, top: 96 }]);
      const now = new Date();
      const time = new Intl.DateTimeFormat("pt-BR", {
        timeZone: "America/Sao_Paulo",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      }).format(now);
      const [hour, minute] = time.split(":").map(Number);
      const spokenTime = minute === 0
        ? `${hour === 0 ? "meia-noite" : hour === 12 ? "meio-dia" : `${hour} horas`} em ponto`
        : `${hour === 0 ? "meia-noite" : hour === 1 ? "uma hora" : `${hour} horas`} e ${minute} minuto${minute === 1 ? "" : "s"}`;
      const date = new Intl.DateTimeFormat("pt-BR", {
        timeZone: "America/Sao_Paulo",
        weekday: "long",
        day: "numeric",
        month: "long",
      }).format(now);
      speakLocal(`Relógio digital aberto, senhor. Agora são ${spokenTime}, no horário de Brasília. Hoje é ${date}. Um ótimo momento para manter o ritmo; estou à disposição.`);
      return;
    }
    if (/\b(fechar|feche|encerre|encerrar)\b.*\b(relogio|hora)\b/.test(normalized)) {
      setUserText(text);
      setFloatingWindows((current) => current.filter((item) => item.type !== "clock"));
      speakLocal("Relógio digital fechado, senhor. A central permanece limpa e pronta para o próximo comando.");
      return;
    }
    if (/\b(fechar|feche|encerre|encerrar)\b.*\b(clima|tempo|previsao)\b/.test(normalized)) {
      setUserText(text);
      setFloatingWindows((current) => current.filter((item) => item.type !== "weather"));
      speakLocal("Janela do clima fechada, senhor. Tudo organizado.");
      return;
    }
    if (/\b(ativar|abrir|ligar|iniciar)\b.*\b(monitor\s+secundario|segundo\s+monitor|tela\s+secundaria|segunda\s+tela)\b/.test(normalized)) {
      setUserText(text);
      window.open(
        `${window.location.origin}${import.meta.env.BASE_URL}?display=secondary`,
        "jarvis-secondary-display",
        "width=1280,height=720,left=1920,top=0"
      );
      localStorage.setItem("jarvis_display_secondary_tab", "command");
      window.dispatchEvent(new StorageEvent("storage", { key: "jarvis_display_secondary_tab", newValue: "command" }));
      speakLocal("Monitor secundário ativado com sucesso, senhor. Interface tática carregada.");
      return;
    }
    if (/\b(limpar)\b.*\b(monitor\s+secundario|segundo\s+monitor|tela\s+secundaria|segunda\s+tela)\b/.test(normalized)) {
      setUserText(text);
      localStorage.setItem("jarvis_display_secondary_tab", "blank");
      window.dispatchEvent(new StorageEvent("storage", { key: "jarvis_display_secondary_tab", newValue: "blank" }));
      speakLocal("Monitor secundário limpo, senhor. Apenas plano de fundo tático em espera.");
      return;
    }
    if (/\b(mover|enviar|jogar|passar)\b.*\b(monitor\s+secundario|segundo\s+monitor|tela\s+secundaria|segunda\s+tela)\b/.test(normalized)
      || /\b(monitor\s+secundario|segundo\s+monitor)\b.*\b(clima|noticia|tarefa|financeiro|cotacao)\b/.test(normalized)) {
      setUserText(text);
      let targetTab = "command";
      if (/noticia/.test(normalized)) targetTab = "news";
      else if (/financeiro|cotacao|dolar/.test(normalized)) targetTab = "finance";
      else if (/tarefa/.test(normalized)) targetTab = "tasks";
      else if (/filme|serie|cinema|streaming/.test(normalized)) targetTab = "media";

      localStorage.setItem("jarvis_display_secondary_tab", targetTab);
      window.dispatchEvent(new StorageEvent("storage", { key: "jarvis_display_secondary_tab", newValue: targetTab }));
      speakLocal(`Enviado para o monitor secundário na central de ${targetTab}.`);
      return;
    }
    if (/\b(bio[\s-]?scan|saude|saúde|sinais\s+vitais|biometria|batimentos)\b/.test(normalized)) {
      keepHubClean();
      setUserText(text);
      setShowBioScan(true);
      speakLocal("Iniciando bio-scan ao vivo com análise de sinais vitais, senhor.");
      return;
    }
    if (/\b(abrir|mostrar|exibir)\b.*\bbriefing\b|\bbriefing\b.*\b(abrir|mostrar)\b/.test(normalized)) {
      keepHubClean();
      setUserText(text);
      setScreensTab("briefing");
      speakLocal("Abrindo tela de briefing tático, senhor.");
      return;
    }
    if (/\b(abrir|mostrar|exibir)\b.*\bfinanceiro\b|\bfinanceiro\b.*\b(abrir|mostrar)\b/.test(normalized)) {
      keepHubClean();
      setUserText(text);
      setScreensTab("finance");
      speakLocal("Abrindo painel financeiro e mercado, senhor.");
      return;
    }
    if (/\b(abrir|mostrar|exibir)\b.*\bfontes\b|\bfontes\b.*\b(abrir|mostrar)\b/.test(normalized)) {
      keepHubClean();
      setUserText(text);
      setScreensTab("datasources");
      speakLocal("Abrindo catálogo de fontes de dados, senhor.");
      return;
    }
    if (/\b(abrir|mostrar|exibir)\b.*\bmonitoramento\b|\bmonitoramento\b.*\b(abrir|mostrar)\b/.test(normalized)) {
      keepHubClean();
      setUserText(text);
      setScreensTab("system");
      speakLocal("Abrindo monitoramento do núcleo do sistema, senhor.");
      return;
    }
    if (/\b(abrir|mostrar|exibir)\b.*\bmenu\b|\bmenu\b.*\b(abrir|mostrar)\b/.test(normalized)) {
      setUserText(text);
      setShowSideNav(true);
      speakLocal("Menu de navegação aberto, senhor.");
      return;
    }
    if (/\b(fechar|feche|esconder)\b.*\bmenu\b|\bmenu\b.*\b(fechar|feche|esconder)\b/.test(normalized)) {
      setUserText(text);
      setShowSideNav(false);
      speakLocal("Menu fechado.");
      return;
    }
    if (/\b(limpar|limpe|manter|mantenha|deixar|deixe|modo)\b.*\b(area|área|limpa)\b|\b(area|área)\s+limpa\b/.test(normalized)) {
      setUserText("");
      setResponse("");
      setResponseCards([]);
      setError("");
      setFloatingWindows([]);
      setShowLogReport(false);
      setShowWidgetWorkspace(false);
      setShowMonitorPanel(false);
      setShowAudioWidget(false);
      setScreensTab(null);
      setZenMode(true);
      speakLocal("Área limpa ativada, senhor. Cabeçalho e orbe mantidos ao seu comando.");
      return;
    }
    if (/\b(restaurar|restaure|mostrar|mostre|exibir|voltar)\b.*\b(area|área|paineis|painéis|widgets|central)\b|\b(sair\s+do\s+zen|desfazer\s+zen)\b/.test(normalized)) {
      setUserText(text);
      setZenMode(false);
      speakLocal("Painéis do HUD restaurados na central, senhor.");
      return;
    }
    if (/\b(fechar|feche|encerre|encerrar)\b.*\b(todas?|janelas?|telas?)\b/.test(normalized)
      || /\b(limpar|limpe)\b.*\b(janelas?|telas?|central|hub|area)\b/.test(normalized)) {
      setUserText(text);
      setFloatingWindows([]);
      setShowLogReport(false);
      setShowWidgetWorkspace(false);
      setShowMonitorPanel(false);
      setShowAudioWidget(false);
      speakLocal("Ok, hub principal limpa. O que deseja, senhor?");
      return;
    }
    if (/\b(abrir|abra|mostrar|mostre|exibir|acessar)\b.*\b(painel\s+de\s+)?widgets?\b/.test(normalized)
      || /\bwidgets?\b.*\b(abrir|abra|mostrar|mostre|exibir|acessar)\b/.test(normalized)) {
      keepHubClean();
      setUserText(text);
      setShowWidgetWorkspace(true);
      return;
    }
    if (
      /\b(logs?|log\s+de\s+erros?|relat[oó]rios?(\s+de)?\s+logs?|relat[oó]rios?(\s+de)?\s+erros?|hist[oó]rico\s+de\s+erros?)\b/i.test(normalized) ||
      (/\b(abrir|abra|ver|veja|mostrar|mostre|exibir|gerar|consultar)\b/i.test(normalized) && /\b(logs?|erros?|registro|relat[oó]rio)\b/i.test(normalized)) ||
      /\b(cade\s+o\s+log|onde\s+esta\s+o\s+log|cade\s+os\s+logs)\b/i.test(normalized)
    ) {
      keepHubClean();
      setUserText(text);
      setShowLogReport(true);
      speakLocal("Abrindo o painel de registros e relatório de logs do sistema, senhor.");
      return;
    }
    if (/\b(modo\s+foco|foco\s+total|modo\s+trabalho|pomodoro|abrir\s+pomodoro|iniciar\s+pomodoro)\b/.test(normalized)) {
      openFocusPomodoro();
    }

    // Se a pergunta de modo de pesquisa estiver ativa e o usuário responder por voz/texto
    if (searchModePromptDataRef.current) {
      if (/\b(api|gemini)\b/i.test(normalized)) {
        handleSelectSearchMode("api", /\b(lembr|sempre|salv)\b/i.test(normalized));
        return;
      }
      if (/\b(navegador|browser|local)\b/i.test(normalized)) {
        handleSelectSearchMode("browser", /\b(lembr|sempre|salv)\b/i.test(normalized));
        return;
      }
    }

    // Quando uma ação ou pergunta geral for enviada, limpa popups temporários
    keepHubClean();
    setSummaryActive(false);
    busyRef.current = true;
    setUserText(text);
    setError("");
    setResponse("");
    setResponseCards([]);
    setSteps({});
    setJarvisState("processing");

    try {
      const data = await api(endpoint, { method: "POST", body: JSON.stringify({ message: text }) });
      if (data.status === "canceled") return; // você cancelou: descarta a resposta
      setResponse(data.response);
      if (data.cards) {
        setResponseCards(data.cards);
        const deepCardHttp = (data.cards || []).find((c) => c.type === "deep_search");
        if (deepCardHttp) {
          setDeepSearchData(deepCardHttp.data);
        }
        if ((data.cards || []).some((c) => c.type === "open_logs")) {
          setShowLogReport(true);
        }
        const promptCardHttp = (data.cards || []).find((c) => c.type === "search_mode_prompt");
        if (promptCardHttp) {
          setSearchModePromptData(promptCardHttp.data);
        }
        if ((data.cards || []).some((c) => c.type === "water" && c.open_panel)) {
          openWaterPanelRef.current();
        }
      }
      if (!connectedRef.current) {
        setJarvisState("idle"); // sem WebSocket não chegam eventos de voz
        busyRef.current = false;
      }
    } catch (err) {
      setError(err.message);
      setJarvisState("idle");
      busyRef.current = false;
    }
  }, [openSearchIndicator, openSpotifyWindow]);

  const handleSelectSearchMode = useCallback(async (mode, remember) => {
    const prompt = searchModePromptDataRef.current;
    setSearchModePromptData(null);
    if (!prompt) return;

    setUserText(`Pesquisar por "${prompt.query}" (${mode === "browser" ? "Navegador local" : "API do Gemini"})...`);
    setJarvisState("processing");
    busyRef.current = true;
    setError("");

    try {
      const data = await api("/api/search/execute", {
        method: "POST",
        body: JSON.stringify({
          query: prompt.query,
          mode,
          remember: Boolean(remember),
        }),
      });
      if (data.status === "canceled") return;
      setResponse(data.response);
      if (data.cards) {
        setResponseCards(data.cards);
        const deepCard = (data.cards || []).find((c) => c.type === "deep_search");
        if (deepCard) {
          setDeepSearchData(deepCard.data);
        }
      }
      if (!connectedRef.current) {
        setJarvisState("idle");
        busyRef.current = false;
      }
    } catch (err) {
      setError(err.message);
      setJarvisState("idle");
      busyRef.current = false;
    }
  }, []);

  const openWeatherWindow = useCallback((monitor = 1) => {
    setShowMonitorPanel(false);
    setFloatingWindows((current) => [
      ...current.filter((item) => item.type !== "weather"),
      { id: `weather-${Date.now()}`, type: "weather", monitor, minimized: false, maximized: false, left: 32, top: 96 },
    ]);
  }, []);

  const openWaterPanel = useCallback(() => {
    setFloatingWindows((current) => {
      const existing = current.find((item) => item.type === "water");
      if (existing) {
        return current.map((item) => (item.id === existing.id ? { ...item, minimized: false, touchedAt: Date.now() } : item));
      }
      return [...current, {
        id: `water-${Date.now()}`, type: "water", monitor: 1, minimized: false, maximized: false,
        left: Math.max(16, window.innerWidth - 420), top: 96, width: 380, height: 420, pinned: false, touchedAt: Date.now(),
      }];
    });
  }, []);
  openWaterPanelRef.current = openWaterPanel;

  const closeFloatingWindow = useCallback((id) => {
    setFloatingWindows((current) => current.filter((item) => item.id !== id));
  }, []);

  const updateFloatingWindow = useCallback((id, changes) => {
    setFloatingWindows((current) => current.map((item) => (
      item.id === id ? { ...item, ...changes } : item
    )));
  }, []);

  const announceWeather = useCallback((weather) => {
    const rain = weather.rain_probability == null
      ? ""
      : ` A chance de chuva é de ${weather.rain_probability} por cento.`;
    const suggestion = weather.rain_probability >= 60
      ? " Melhor levar um guarda-chuva, senhor; o céu parece estar tramando alguma coisa."
      : weather.temperature >= 30
        ? " Um copo de água seria uma excelente ideia antes de sair."
        : " Clima razoável para seguir o dia sem grandes dramas meteorológicos.";
    const text = `Em ${weather.place}, agora faz ${weather.temperature} graus, com ${weather.description}. `
      + `A sensação térmica é de ${weather.apparent_temperature} graus. `
      + `A máxima de hoje é ${weather.maximum} e a mínima é ${weather.minimum} graus.${rain}${suggestion} `
      + "Se quiser, consulto outra cidade ou verifico a previsão de amanhã.";
    api("/api/speak", {
      method: "POST",
      body: JSON.stringify({ text }),
    }).catch(() => {});
  }, []);

  // ---- Microfone (barra de espaço liga/desliga) ----
  const { listening, interim, start, stop, cancel: cancelMic, supported } = useSpeechRecognition({
    onFinal: (text) => {
      lastVoiceRef.current = true; // pedido de voz: a conversa contínua vale para a resposta dele
      return screenRef.current === "guest" ? guestSend(text) : send(text);
    },
    onError: setError,
    deviceId: microphoneId,
  });

  // Mantém a transcrição disponível por um minuto após a última interação,
  // sem limpar uma resposta enquanto o JARVIS ainda estiver trabalhando.
  useEffect(() => {
    if (!userText && !response && !error) return undefined;
    const timer = setTimeout(() => {
      if (jarvisState === "idle" && !listening) {
        setUserText("");
        setResponse("");
        setError("");
        setSteps({});
      }
    }, 60_000);
    return () => clearTimeout(timer);
  }, [userText, response, error, jarvisState, listening]);

  const returnToWaiting = useCallback(async (notifyBackend = true) => {
    cancelMic();
    busyRef.current = false;
    setShowBioScan(false);
    setDeviceTest(null);
    setShowSettings(false);
    setRecheckOpen(false);
    setFaceScan({ status: "idle" });
    setRelockWarning(null);
    setSummaryActive(false);
    setAutoEntering(false);
    setPendingToRun(null);
    try {
      await api("/api/cancel", { method: "POST" });
    } catch {
      // A tela pode voltar ao estado de espera mesmo se o backend estiver indisponível.
    }
    if (notifyBackend) {
      api("/api/access/lock", { method: "POST" }).then(setAccessInfo).catch(() => {});
    }
    loadPinStatus();
    setJarvisState("idle");
    setSteps({});
    setResponse("");
    setError("");
    setUserText("");
    setLockPhase("ready");
    setLockMessage("");
    setSessionStartedAt(null);
    setSessionElapsed(0);
    setScreen("lock");
  }, [cancelMic, loadPinStatus]);

  const toggleMic = useCallback(() => {
    if (!supported) {
      setError("Seu navegador não suporta reconhecimento de voz. Use o Chrome ou o Edge.");
      return;
    }
    if (listening) {
      stop();
      return;
    }
    if (busyRef.current) return;
    setError("");
    start();
  }, [supported, listening, start, stop]);

  // ---- Cancelar: corta a voz, descarta a resposta e para de ouvir ----
  const handleCancel = useCallback(async () => {
    setSummaryActive(false);
    cancelMic();
    busyRef.current = false;
    setJarvisState("idle");
    setSteps({});
    setError("");
    setResponse("Ação cancelada.");
    try {
      await api("/api/cancel", { method: "POST" });
    } catch {
      /* backend fora do ar: nada a cancelar */
    }
  }, [cancelMic]);

  // ---- Atalhos: barra de espaço (falar) e Esc (cancelar) ----
  useEffect(() => {
    const onKey = (e) => {
      if (e.code === "Escape") {
        if (showSettings) { setShowSettings(false); return; }
        if (screen === "main") handleCancel();
        return;
      }
      // V4.2.2: P liga/desliga o microfone da tela de bloqueio (escuta e palmas)
      if (screen === "lock" && e.code === "KeyP" && !e.repeat && !e.ctrlKey && !e.altKey && !e.metaKey) {
        const typing = ["INPUT", "TEXTAREA"].includes(e.target?.tagName);
        if (!typing) {
          e.preventDefault();
          setSentinelMuted((v) => !v);
        }
        return;
      }
      if (alarmRef.current) return; // alarme tocando: ENTER/ESC/S ficam com o cartão do alarme
      if (e.code !== "Space" || e.repeat) return;
      const tag = e.target?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return; // deixa digitar espaços normalmente
      if (tag === "BUTTON") e.target.blur(); // evita o botão focado disparar um clique extra
      if (screen === "lock") {
        e.preventDefault();
        handleLockContinue();
      } else if ((screen === "main" || screen === "guest") && e.code === "Space") {
        e.preventDefault();
        toggleMic();
      }

    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [screen, handleLockContinue, toggleMic, handleCancel, showSettings]);

  // V4.2.2: sons por estado (volume, modo e silêncio vêm das preferências)
  useEffect(() => {
    soundManager.configure({ volume: appPrefs.sfx_volume, mode: appPrefs.sfx_mode, silent: appPrefs.silent_mode });
  }, [appPrefs.sfx_volume, appPrefs.sfx_mode, appPrefs.silent_mode]);
  const prevOrbRef = useRef({ state: "idle", listening: false });
  useEffect(() => {
    const prev = prevOrbRef.current;
    if (screen === "main") {
      if (listening && !prev.listening) soundManager.playListening();
      else if (!listening && jarvisState === "idle" && (prev.state === "speaking" || prev.state === "processing")) {
        soundManager.playIdle();
      }
    }
    prevOrbRef.current = { state: jarvisState, listening };
  }, [jarvisState, listening, screen]);

  // V4.2.2: estado do orbe no título da aba (ex.: "● Ouvindo · J.A.R.V.I.S.")
  useEffect(() => {
    document.title = tabTitle({ name: aiName, screen, state: jarvisState, listening, connected });
  }, [aiName, screen, jarvisState, listening, connected]);

  // V4.2.2: toda vez que a central volta para a tela de bloqueio, o microfone recomeça silenciado
  useEffect(() => {
    if (screen === "lock") setSentinelMuted(true);
  }, [screen]);

  // ================= Seção 14/16: palmas =================
  const handleDoubleClap = useCallback(() => {
    if (!appPrefsRef.current.silent_mode) soundManager.playChime();
    setClapPulse((n) => n + 1);
    if (screenRef.current === "lock") {
      if (lockPhaseRef.current === "ready" || lockPhaseRef.current === "failed") verify({ trigger: "clap" });
    } else if (screenRef.current === "main") {
      if (busyRef.current) return; // ocupado: ignora sem erro
      verify({ mode: "recheck", trigger: "clap" });
    }
  }, [verify]);

  const clapOn = Boolean(appPrefs.clap_wake_enabled);
  const lockClap = clapOn && screen === "lock" && (lockPhase === "ready" || lockPhase === "failed") && !showMicrophoneSelect
    && !sentinelMuted; // V4.2.2: palmas também esperam o microfone ser ligado (P)
  const mainClap = clapOn && appPrefs.clap_scope !== "lock" && screen === "main"
    && !showSettings && !showBioScan && !deviceTest; // BioScan/Teste usam a câmera pelo navegador
  const clapPaused = jarvisState !== "idle" || listening || faceScan.status === "scanning" || recheckOpen;
  const clap = useClapDetector({
    enabled: lockClap || mainClap,
    paused: clapPaused,
    deviceId: microphoneId,
    sensitivity: appPrefs.clap_sensitivity ?? 5,
    onDoubleClap: handleDoubleClap,
  });

  // ================= Modo Sentinela =================
  const wakeWords = useMemo(
    () => effectiveWakeWords(appPrefs.sentinel_wake_words, aiName),
    [appPrefs.sentinel_wake_words, aiName],
  );
  const sentinelOn = Boolean(appPrefs.sentinel_enabled) && screen === "lock";
  const unlockTimerRef = useRef(null);

  const askSentinel = useCallback(async (text) => {
    if (!text) return;
    setSentinelReply(text);
    try {
      const data = await api("/api/chat", { method: "POST", body: JSON.stringify({ message: text }) });
      setSentinelReply(data.response || "");
      if (data.action === "unlock_only") {
        // Pedido só de liberar (digitado ou sem o reconhecimento local): escaneia sem pedido pendente
        if (screenRef.current === "lock" && (lockPhaseRef.current === "ready" || lockPhaseRef.current === "failed")) {
          verify({ trigger: "wake" });
        }
      } else if (data.action === "unlock" || data.requires_unlock) {
        // Guarda o pedido e, quando a fala terminar, abre a câmera para o escaneamento
        setPendingRequest(text);
        setSentinelUnlock(true);
        const started = Date.now();
        clearInterval(unlockTimerRef.current);
        unlockTimerRef.current = setInterval(() => {
          const elapsed = Date.now() - started;
          if ((elapsed > 900 && !busyRef.current) || elapsed > 9000) {
            clearInterval(unlockTimerRef.current);
            setSentinelUnlock(false);
            if (screenRef.current === "lock" && (lockPhaseRef.current === "ready" || lockPhaseRef.current === "failed")) {
              verify({ trigger: "button" });
            }
          }
        }, 300);
      }
    } catch (err) {
      setSentinelReply(err.status === 409 ? "" : err.message);
    }
  }, [verify]);

  useEffect(() => () => clearInterval(unlockTimerRef.current), []);

  // V4.2.2: "abrir central" / "liberar" no Sentinela: vai direto para o escaneamento (sem IA e sem pedido pendente)
  const unlockByVoice = useCallback(() => {
    if (screenRef.current !== "lock") return;
    if (lockPhaseRef.current !== "ready" && lockPhaseRef.current !== "failed") return;
    setPendingRequest(null);
    setSentinelReply("Escaneando, senhor.");
    verify({ trigger: "wake" });
  }, [verify]);

  // Como a Alexa: com a central aberta, "Jarvis, ..." funciona sem tocar no microfone.
  // Pausa enquanto o JARVIS pensa ou fala (não escuta a própria voz) e enquanto o microfone manual está ligado.
  const central = useSentinelListener({
    enabled: !IS_JARVIS_APP && screen === "main" && appPrefs.hands_free_enabled !== false,
    paused: jarvisState !== "idle" || listening,
    wakeWords,
    onWake: () => soundManager.playListening(),
    onCommand: (_rest, original) => {
      const text = stripWake(original, wakeWords);
      if (!text) return;
      lastVoiceRef.current = true;
      send(text);
    },
  });

  // Conversa contínua: terminou de responder um pedido de voz -> fica 8 s ouvindo a próxima pergunta
  const prevStateRef = useRef(jarvisState);
  useEffect(() => {
    const was = prevStateRef.current;
    prevStateRef.current = jarvisState;
    if (jarvisState !== "idle" || was === "idle") return;
    if (!lastVoiceRef.current) return;
    lastVoiceRef.current = false;
    if (screen === "main" && appPrefs.follow_up_enabled !== false && appPrefs.hands_free_enabled !== false && !IS_JARVIS_APP) {
      central.keepAwake();
      soundManager.playListening();
    }
  }, [jarvisState, screen, appPrefs.follow_up_enabled, appPrefs.hands_free_enabled, central]);

  const sentinel = useSentinelListener({
    enabled: !IS_JARVIS_APP && sentinelOn && (lockPhase === "ready" || lockPhase === "failed") && !sentinelMuted && !sentinelCooldown,
    paused: jarvisState !== "idle" || faceScan.status === "scanning",
    wakeWords,
    onCommand: askSentinel,
    onWake: askSentinel,
    onUnlock: unlockByVoice,
  });

  // Rosto não reconhecido no Sentinela: nega, descarta o pedido e volta a dormir
  useEffect(() => {
    if (screen !== "lock" || lockPhase !== "failed") return undefined;
    if (pendingRequestRef.current) setPendingRequest(null);
    if (!appPrefs.sentinel_enabled) return undefined;
    const t = setTimeout(() => {
      if (lockPhaseRef.current === "failed") setLockPhase("ready");
    }, 4000);
    return () => clearTimeout(t);
  }, [screen, lockPhase, appPrefs.sentinel_enabled]);

  // Alerta de rosto desconhecido (Sentinela): 3 falhas seguidas pausam a escuta por 3 minutos
  useEffect(() => {
    if (!appPrefs.sentinel_enabled || failCount < 3 || failCount % 3 !== 0) return undefined;
    setSentinelCooldown(true);
    setSentinelReply("Escuta pausada por 3 minutos após 3 tentativas não reconhecidas.");
    const t = setTimeout(() => setSentinelCooldown(false), 3 * 60_000);
    return () => clearTimeout(t);
  }, [failCount, appPrefs.sentinel_enabled]);

  // Legenda da Sentinela some sozinha
  useEffect(() => {
    if (!sentinelReply) return undefined;
    const t = setTimeout(() => setSentinelReply(""), 8000);
    return () => clearTimeout(t);
  }, [sentinelReply]);

  // Pedido pendente do Sentinela: executa assim que a central abrir e o JARVIS ficar livre
  useEffect(() => {
    if (!pendingToRun || screen !== "main" || jarvisState !== "idle") return undefined;
    const t = setTimeout(() => {
      const text = pendingToRun;
      setPendingToRun(null);
      send(text);
    }, 700);
    return () => clearTimeout(t);
  }, [pendingToRun, screen, jarvisState, send]);

  // ================= Estado de acesso vindo do backend =================
  useEffect(() => {
    if (!accessInfo) return;
    if (accessInfo.effective === "locked" && screenRef.current === "main") {
      returnToWaiting(false); // ex.: "Jarvis, bloquear", reverificação falhou ou backend reiniciou
    }
  }, [accessInfo, returnToWaiting]);

  useEffect(() => {
    const onDenied = (e) => {
      if (e.detail?.code === "locked" && screenRef.current === "main") returnToWaiting(false);
    };
    window.addEventListener("jarvis_access_denied", onDenied);
    return () => window.removeEventListener("jarvis_access_denied", onDenied);
  }, [returnToWaiting]);

  // ================= Seção 17.5: bloqueio por ausência =================
  const lastActivityRef = useRef(Date.now());
  const relockCheckingRef = useRef(false);
  const relockStateRef = useRef({});
  relockStateRef.current = { jarvisState, listening, recheckOpen, scanning: faceScan.status === "scanning", relockWarning };
  useEffect(() => {
    const minutes = Number(appPrefs.lock_auto_relock_minutes) || 0;
    if (screen !== "main" || !minutes || !hasPhoto) {
      setRelockWarning(null);
      return undefined;
    }
    lastActivityRef.current = Date.now();
    const bump = () => {
      lastActivityRef.current = Date.now();
      if (relockStateRef.current.relockWarning != null) setRelockWarning(null);
    };
    const events = ["pointermove", "pointerdown", "keydown", "wheel", "touchstart"];
    events.forEach((ev) => window.addEventListener(ev, bump, { passive: true }));
    const timer = setInterval(async () => {
      const st = relockStateRef.current;
      if (st.jarvisState !== "idle" || st.listening || st.recheckOpen || st.scanning) {
        lastActivityRef.current = Date.now(); // falando, ouvindo ou verificando: não bloqueia
        return;
      }
      if (st.relockWarning != null || relockCheckingRef.current) return;
      if (Date.now() - lastActivityRef.current < minutes * 60_000) return;
      if (appPrefsRef.current.lock_presence_check) {
        relockCheckingRef.current = true;
        const seen = async () => {
          try { return Boolean((await api("/api/face/present")).face_seen); } catch { return false; }
        };
        const first = await seen();
        const second = first ? true : await new Promise((r) => setTimeout(async () => r(await seen()), 10_000));
        relockCheckingRef.current = false;
        if (first || second) {
          lastActivityRef.current = Date.now();
          return;
        }
      }
      setRelockWarning(30);
    }, 5000);
    return () => {
      clearInterval(timer);
      events.forEach((ev) => window.removeEventListener(ev, bump));
    };
  }, [screen, appPrefs.lock_auto_relock_minutes, hasPhoto]);

  useEffect(() => {
    if (relockWarning == null) return undefined;
    if (relockWarning <= 0) {
      setRelockWarning(null);
      returnToWaiting(true);
      return undefined;
    }
    const t = setTimeout(() => setRelockWarning((n) => (n == null ? null : n - 1)), 1000);
    return () => clearTimeout(t);
  }, [relockWarning, returnToWaiting]);

  // Aviso discreto (ex.: playlist de abertura indisponível)
  useEffect(() => {
    const onNotice = (e) => setNotice(e.detail || "");
    window.addEventListener("jarvis_notice", onNotice);
    return () => window.removeEventListener("jarvis_notice", onNotice);
  }, []);
  useEffect(() => {
    if (!notice) return undefined;
    const t = setTimeout(() => setNotice(""), 5000);
    return () => clearTimeout(t);
  }, [notice]);

  useEffect(() => {
    if (!summaryActive) return undefined;
    const t = setTimeout(() => setSummaryActive(false), 25_000);
    return () => clearTimeout(t);
  }, [summaryActive]);

  // Botão "Modo Sentinela" do menu de controles: liga o layout Sentinela e bloqueia a central
  const enterSentinelMode = useCallback(async () => {
    try {
      // Sempre grava: a cópia local das preferências pode estar desatualizada
      const updated = await api("/api/prefs", { method: "PATCH", body: JSON.stringify({ sentinel_enabled: true }) });
      handlePrefsChange(updated);
    } catch (err) {
      setError(err.message);
      return;
    }
    if (!hasPhoto) {
      setError("Cadastre uma foto de perfil para usar o Modo Sentinela.");
      return;
    }
    returnToWaiting(true);
  }, [handlePrefsChange, hasPhoto, returnToWaiting]);

  // ================= V6.0: app do celular — atalhos, compartilhar e digital =================
  const [shareItem, setShareItem] = useState(null); // { text, subject } vindo do "Compartilhar -> JARVIS"
  const [bioOffer, setBioOffer] = useState(false);
  const queuedAppCmd = useRef(null); // { listen } | { say } esperando entrar na central
  const sendRef = useRef(send);
  sendRef.current = send;
  const toggleMicRef = useRef(toggleMic);
  toggleMicRef.current = toggleMic;
  const listeningRef = useRef(listening);
  listeningRef.current = listening;

  const runAppCmd = useCallback((cmd) => {
    if (!cmd) return;
    if (cmd.listen && !listeningRef.current) toggleMicRef.current();
    if (cmd.say) sendRef.current(cmd.say);
  }, []);

  const unlockWithDevice = useCallback(async (secret) => {
    setPinState((cur) => ({ ...cur, busy: true, message: "" }));
    try {
      const data = await api("/api/auth/device/unlock", { method: "POST", body: JSON.stringify({ secret }) });
      if (data.verified) {
        setPinState({ busy: false, message: "", lockedUntil: null });
        setName(data.name ?? "");
        setLockMessage(data.message ?? "");
        setFailCount(0);
        setLockPhase("verified");
        setTimeout(() => enterMainRef.current(undefined), 400); // digital já é a confirmação: entra direto
      } else {
        try { window.JarvisApp?.forgetBiometric?.(); } catch { /* app antigo */ }
        setPinState((cur) => ({ ...cur, busy: false, message: data.message }));
      }
    } catch (err) {
      setPinState((cur) => ({ ...cur, busy: false, message: err.message }));
    }
  }, []);

  useEffect(() => {
    if (!IS_JARVIS_APP) return undefined;
    const onListen = () => {
      if (screenRef.current === "main") runAppCmd({ listen: true });
      else queuedAppCmd.current = { listen: true };
    };
    const onSay = (e) => {
      const text = String(e.detail?.text || "").trim();
      if (!text) return;
      if (screenRef.current === "main") runAppCmd({ say: text });
      else queuedAppCmd.current = { say: text };
    };
    const onShare = (e) => {
      const text = String(e.detail?.text || "").trim();
      if (text) setShareItem({ text: text.slice(0, 2000), subject: String(e.detail?.subject || "") });
    };
    const onBio = (e) => {
      const d = e.detail || {};
      if (d.action === "unlock" && d.secret) unlockWithDevice(d.secret);
      else if (d.action === "saved") setNotice(d.message || "Digital ativada.");
      else if (d.action === "error" && d.message) setPinState((cur) => ({ ...cur, message: d.message }));
    };
    window.addEventListener("jarvis-app-listen", onListen);
    window.addEventListener("jarvis-app-say", onSay);
    window.addEventListener("jarvis-app-share", onShare);
    window.addEventListener("jarvis-app-biometric", onBio);
    return () => {
      window.removeEventListener("jarvis-app-listen", onListen);
      window.removeEventListener("jarvis-app-say", onSay);
      window.removeEventListener("jarvis-app-share", onShare);
      window.removeEventListener("jarvis-app-biometric", onBio);
    };
  }, [runAppCmd, unlockWithDevice]);

  // Entrou na central: roda o atalho que estava esperando e, se entrou pelo PIN no app, oferece a digital
  useEffect(() => {
    if (screen !== "main") return undefined;
    const t = setTimeout(() => {
      const cmd = queuedAppCmd.current;
      queuedAppCmd.current = null;
      runAppCmd(cmd);
    }, 1200);
    if (IS_JARVIS_APP && pinEnteredRef.current) {
      pinEnteredRef.current = false;
      let asked = false;
      try { asked = localStorage.getItem("jarvis.bio.asked") === "1"; } catch { /* sem armazenamento */ }
      try {
        if (!asked && window.JarvisApp?.canUseBiometric?.() && !window.JarvisApp?.hasBiometric?.()) setBioOffer(true);
      } catch { /* app antigo, sem digital */ }
    }
    return () => clearTimeout(t);
  }, [screen, runAppCmd]);

  // Bloqueio no app com a digital ativada: já pede a digital ao abrir (cancelar = usar o PIN)
  useEffect(() => {
    if (!IS_JARVIS_APP || screen !== "lock") return undefined;
    let has = false;
    try { has = Boolean(window.JarvisApp?.hasBiometric?.()); } catch { has = false; }
    if (!has) return undefined;
    const t = setTimeout(() => { try { window.JarvisApp.biometricUnlock(); } catch { /* sem digital */ } }, 700);
    return () => clearTimeout(t);
  }, [screen]);

  const enableBiometric = useCallback(async () => {
    setBioOffer(false);
    try { localStorage.setItem("jarvis.bio.asked", "1"); } catch { /* sem armazenamento */ }
    try {
      const key = await api("/api/auth/device/enroll", { method: "POST", body: JSON.stringify({ name: "Celular" }) });
      window.JarvisApp?.saveDeviceSecret?.(key.secret);
    } catch (err) {
      setNotice(`Não consegui ativar a digital: ${err.message}`);
    }
  }, []);

  const shareActions = shareItem ? [
    { icon: "✦", label: "Resumir", say: `Resuma em poucas frases: ${shareItem.text}` },
    { icon: "✎", label: "Anotar", say: `anota: ${shareItem.text.slice(0, 280)}` },
    { icon: "⏰", label: "Lembrar amanhã", say: `me lembra amanhã às 9 de ver ${shareItem.subject || shareItem.text.slice(0, 120)}` },
    { icon: "🛒", label: "Lista de compras", say: `coloca ${shareItem.text.slice(0, 120)} na lista` },
  ] : [];

  // ================= Telas =================
  if (screen === "boot") {
    const returningUser = hasLoggedBefore();
    return (
      <div className="ls-container">
        <div className="ls-bracket ls-bracket-tl" aria-hidden="true" />
        <div className="ls-bracket ls-bracket-tr" aria-hidden="true" />
        <div className="ls-bracket ls-bracket-bl" aria-hidden="true" />
        <div className="ls-bracket ls-bracket-br" aria-hidden="true" />

        <div className="ls-header">
          <div className="ls-status-pill">
            <span className="ls-dot" />
            <span>SEQUÊNCIA DE INICIALIZAÇÃO NEURAL</span>
          </div>
        </div>

        {/* V4.2.2: boas-vindas com o logo Núcleo animado e o nome desenhado em traço */}
        <div className="ls-orb-wrapper" style={{ padding: "20px" }}>
          <WelcomeLogo name={aiName} />
        </div>
        <p className="ls-subbrand" style={{ textAlign: "center" }}>CENTRAL PESSOAL · v{APP_VERSION}</p>

        <div className="ls-status-box">
          {updating ? (
            <>
              <div className="ls-title is-amber">ATUALIZANDO O JARVIS</div>
              <ProgressBar pct={updatePct} label={updating.stage || "Atualizando"} />
              <p className="ls-hint" style={{ margin: "8px auto", maxWidth: "34rem" }}>{updating.message}</p>
              {!updating.slow && <p className="ls-hint ls-boot-wait" style={{ marginTop: "10px" }}>Volto em instantes e faço a verificação do seu rosto…</p>}
            </>
          ) : bootError && bootOffline && BACKEND_ON_THIS_PC && !IS_JARVIS_APP && returningUser ? (
            <>
              {/* V5.2: quem já usa o JARVIS aqui não vê o manual: só "reconectando", e entra sozinho */}
              <div className="ls-title">RECONECTANDO AO SEU JARVIS</div>
              <p className="ls-hint ls-boot-wait" style={{ margin: "6px auto 0" }}>
                {launchState === "opening" ? "Ligando o JARVIS do PC… pode levar 1 ou 2 minutos." : launchState === "asked" ? "O Chrome perguntou se pode abrir o programa? Clique em Abrir." : "Assim que o JARVIS do PC responder, eu entro sozinho."}
              </p>
              <div className="ls-boot-actions">
                <button type="button" onClick={launchJarvis} disabled={launchState === "trying"} className="ls-btn-main">
                  <span>{launchState === "trying" ? "ABRINDO…" : "LIGAR O JARVIS"}</span>
                </button>
                <button type="button" onClick={boot} className="ls-chip">TENTAR AGORA</button>
              </div>
              {launchState === "missing" && (
                <div className="ls-launch-missing" role="alert">
                  <b>O JARVIS ainda não respondeu.</b>
                  <span>Se o Chrome não perguntou nada ao tocar em LIGAR, dê duplo clique em <b>Instalar-Botao-Ligar.bat</b> (só uma vez). Ou ligue pelo <b>Iniciar-JARVIS.bat</b>: esta página entra sozinha.</span>
                </div>
              )}
              <details className="ls-boot-help">
                <summary>Não está entrando?</summary>
                <p>Com o JARVIS ligado, o Chrome pode barrar este site de falar com o PC: clique no ícone ao lado do endereço › <b>Acesso à rede local</b> › Permitir, e recarregue.</p>
                <p>O botão LIGAR precisa do <b>Instalar-Botao-Ligar.bat</b> rodado uma vez neste PC.</p>
              </details>
            </>
          ) : bootError && bootOffline && BACKEND_ON_THIS_PC && !IS_JARVIS_APP ? (
            <>
              {/* Primeira vez neste navegador: passo a passo curto para ligar o JARVIS do PC */}
              <div className="ls-title is-amber">VAMOS LIGAR O SEU JARVIS</div>
              <ol className="ls-boot-steps">
                <li><span><b>Toque em LIGAR O JARVIS</b> e permita abrir o programa.</span></li>
                <li><span><b>Deixe esta página aberta.</b> Quando ele responder, eu verifico seu rosto e abro a central.</span></li>
                <li><span><b>Da próxima vez</b> eu já reconheço este navegador e entro sozinho.</span></li>
              </ol>
              <div className="ls-boot-actions">
                <button type="button" onClick={launchJarvis} disabled={launchState === "trying"} className="ls-btn-main">
                  <span>{launchState === "trying" ? "ABRINDO…" : "LIGAR O JARVIS"}</span>
                </button>
                <button type="button" onClick={boot} className="ls-chip">TENTAR AGORA</button>
              </div>
              {launchState === "missing" ? (
                <div className="ls-launch-missing" role="alert">
                  <b>O JARVIS ainda não respondeu.</b>
                  <span>Se o Chrome não perguntou nada ao tocar em LIGAR, o botão não está ativado neste PC: na pasta do JARVIS, dê duplo clique em <b>Instalar-Botao-Ligar.bat</b> (só uma vez) e toque de novo. Ou ligue pelo <b>Iniciar-JARVIS.bat</b>: esta página entra sozinha.</span>
                </div>
              ) : (
                <p className="ls-hint ls-boot-wait" style={{ marginTop: "4px" }}>
                  {launchState === "opening" ? "Ligando o JARVIS… pode levar 1 ou 2 minutos." : launchState === "asked" ? "O Chrome perguntou se pode abrir o programa? Clique em Abrir (e marque para sempre permitir)." : "Aguardando o JARVIS responder…"}
                </p>
              )}
              <details className="ls-boot-help">
                <summary>Já está ligado e não entra?</summary>
                <p>O Chrome precisa permitir o <b>acesso à rede local</b> para este site: clique no ícone ao lado do endereço › Acesso à rede local › Permitir, e recarregue.</p>
              </details>
            </>
          ) : bootError ? (
            <>
              <div className="ls-title is-failed">FALHA NA CONEXÃO COM O BACKEND</div>
              <p className="max-w-md text-sm text-red-300" style={{ margin: "8px 0" }}>{bootError}</p>
              <button
                type="button"
                onClick={boot}
                className="ls-btn-main"
                style={{ marginTop: "12px" }}
              >
                <span>TENTAR NOVAMENTE</span>
              </button>
            </>
          ) : (
            <>
              <div className="ls-title">ESTABELECENDO ENLACE NEURAL...</div>
              <div className="ls-hint">Carregando módulos cognitivos e verificando serviços locais</div>
            </>
          )}
        </div>

        {showLogReport && <LogReportWidget api={api} onClose={() => setShowLogReport(false)} />}

        <footer className="ls-footer">
          <span>PORTA 8000 · WEBSOCKET LOCALHOST · MODO TÁTICO</span>
        </footer>
        <BlueprintStamp sheet="INICIALIZAÇÃO" />
      </div>
    );
  }

  if (screen === "newprofile") {
    return (
      <NewProfileScreen
        api={api}
        onCancel={() => { setLockPhase("ready"); setScreen("lock"); }}
        onCreated={(res) => {
          setName(res.name || "");
          setHasPhoto(true);
          setPhotoVersion(Date.now());
          if (res.access) setAccessInfo(res.access);
          setWelcomeName(res.name || "");
          enterMain(microphoneId, { skipSummary: true });
        }}
      />
    );
  }

  if (screen === "enroll") {
    return (
      <EnrollScreen
        initialName={name}
        onSave={saveProfile}
        onSkip={() => {
          if (hasPhoto) {
            setLockPhase("ready");
            setScreen("lock");
          } else {
            enterMain();
          }
        }}
        saving={saving}
        error={enrollError}
      />
    );
  }

  if (screen === "lock") {
    return (
      <>
        {alarmOverlay}
        <LockScreen
          photoUrl={lockPhase === "verified" || (accessInfo && accessInfo.effective === "unlocked" && lockPhase !== "ready" && lockPhase !== "pin") ? photoUrl : null}
          phase={lockPhase}
          name={name}
          message={lockMessage}
          jarvisState={jarvisState}
          onContinue={handleLockContinue}
          onChangePhoto={() => {
            setEnrollError("");
            setScreen("enroll");
          }}
          liveScan={faceScan.mode === "recheck" ? null : faceScan}
          mic={!IS_JARVIS_APP && (clapOn || appPrefs.sentinel_enabled) ? { muted: sentinelMuted, onToggle: () => setSentinelMuted((v) => !v) } : null}
          clap={clapOn ? { enabled: true, status: clap.status, level: clap.level, needsGesture: clap.needsGesture, pulse: clapPulse, autoEntering } : { enabled: false, autoEntering }}
          cards={{ list: appPrefs.lock_cards || [], api, fanModeEnabled, fanRefresh }}
          hasPin={hasPin}
          failCount={failCount}
          onUsePin={openPin}
          pin={pinReset ? {
            onSubmit: submitNewPin,
            onCancel: () => { setPinReset(null); setLockPhase("ready"); },
            busy: pinState.busy,
            message: pinState.message,
            lockedUntil: null,
          } : {
            onSubmit: submitPin,
            onCancel: () => setLockPhase("ready"),
            busy: pinState.busy,
            message: pinState.message,
            lockedUntil: pinState.lockedUntil,
            onForgot: BACKEND_ON_THIS_PC && !IS_JARVIS_APP ? forgotPin : null,
          }}
          guestEnabled={Boolean(appPrefs.lock_guest_enabled)}
          onGuest={enterGuest}
          onNewProfile={IS_JARVIS_APP ? null : () => setScreen("newprofile")}
          onUpdate={IS_JARVIS_APP ? updateApp : BACKEND_ON_THIS_PC ? updateJarvis : null}
          updateNote={appUpdateNote}
          updateProgress={appUpdatePct}
          phoneApp={IS_JARVIS_APP}
          onBiometric={IS_JARVIS_APP && (() => { try { return window.JarvisApp?.hasBiometric?.(); } catch { return false; } })()
            ? () => window.JarvisApp.biometricUnlock() : null}
          bgToggle={{
            value: appPrefs.background_style || "blueprint",
            onCycle: () => {
              // V5.9.1: troca na hora (e lembra no navegador); o PC salva para os outros aparelhos
              const order = ["blueprint", "space", "classic"];
              const cur = appPrefs.background_style || "blueprint";
              const next = order[(order.indexOf(cur) + 1) % order.length];
              applyBackground(next);
              setAppPrefs((p) => ({ ...p, background_style: next }));
              api("/api/background", { method: "POST", body: JSON.stringify({ style: next }) }).catch(() => {});
            },
          }}
          fanToggle={{
            enabled: fanModeEnabled,
            busy: fanBusy,
            error: fanError,
            onToggle: async () => {
              // V4.4: botão do bloqueio; rota pública só para o visual do clube
              setFanBusy(true);
              setFanError("");
              try {
                const res = await api("/api/fan/toggle", { method: "POST", body: JSON.stringify({ enabled: !fanModeEnabled }) });
                const team = res.fan_team || fanTeam;
                setFanModeEnabled(Boolean(res.fan_mode_enabled));
                setFanTeam(team);
                applyFanMode(Boolean(res.fan_mode_enabled), team);
                soundManager.playClick();
              } catch (err) {
                // 404/403 = backend de uma versão anterior ainda aberto (sem a rota do botão)
                setFanError(err?.status === 404 || err?.status === 403 ? "REINICIE O JARVIS" : "SEM RESPOSTA");
                soundManager.playAlert();
              } finally {
                setFanBusy(false);
              }
            },
          }}
          introSound={appPrefs.lock_intro_sound || "default"}
          silent={Boolean(appPrefs.silent_mode)}
          sentinel={appPrefs.sentinel_enabled ? {
            enabled: true,
            state: sentinelUnlock || (pendingRequest && lockPhase !== "verified") ? "unlock"
              : jarvisState === "speaking" ? "speaking"
                : sentinel.interim ? "listening"
                  : sentinel.phase === "awake" ? "awake" : "sleeping",
            caption: sentinelReply,
            interim: sentinel.interim,
            micStatus: sentinelMuted ? "off" : sentinel.status,
            muted: sentinelMuted,
            onToggleMute: () => setSentinelMuted((v) => !v),
            showClock: appPrefs.sentinel_show_clock !== false,
            nightDim: appPrefs.sentinel_night_dim !== false,
            wakeLabel: (aiName || "Jarvis").replace(/\./g, "").replace(/^\w/, (c) => c.toUpperCase()).replace(/\B\w+/, (w) => w.toLowerCase()),
            autoEntering,
          } : null}
        />
        {showMicrophoneSelect && (
          <MicrophoneSelectModal
            onConfirm={(selectedId) => {
              setShowMicrophoneSelect(false);
              enterMain(selectedId);
            }}
            onClose={() => setShowMicrophoneSelect(false)}
          />
        )}
        {fanModeEnabled && <FanGoalOverlay event={fanEvent} onDone={clearFanEvent} />}
      </>
    );
  }

  if (screen === "guest") {
    return (
      <GuestScreen
        api={api}
        jarvisState={jarvisState}
        listening={listening}
        interim={interim}
        onToggleMic={toggleMic}
        onExit={exitGuest}
        onAsk={guestSend}
        reply={guestReply}
      />
    );
  }

  const busy = jarvisState !== "idle";
  const heardAwake = central.phase === "awake" && jarvisState === "idle"; // "Jarvis" ouvido: esperando o pedido
  const stateLabel = listening || heardAwake ? "Ouvindo" : STATE_LABEL[jarvisState];
  const showConversation = listening || busy || Boolean(userText || response || error);
  const sessionSeconds = Math.floor(sessionElapsed / 1000);
  const sessionClock = [Math.floor(sessionSeconds / 3600), Math.floor((sessionSeconds % 3600) / 60), sessionSeconds % 60]
    .map((value) => String(value).padStart(2, "0"))
    .join(":");

  return (
    <>
      <OfflineBanner connected={connected} />
      {alarmOverlay}
      {showOnboarding && (
        <Onboarding
          aiName={aiName}
          api={api}
          onDone={() => {
            localStorage.setItem("jarvis.onboarding.done", "1");
            setShowOnboarding(false);
          }}
        />
      )}
      {showBioScan && (
        <BioScanModal
          api={api}
          operatorName={name || "Patrick"}
          onClose={() => setShowBioScan(false)}
        />
      )}
      {deepSearchData && (
        <DeepSearchModal
          data={deepSearchData}
          onClose={() => setDeepSearchData(null)}
          onDeepSearch={(query) => {
            setDeepSearchData(null);
            api("/api/search/execute", {
              method: "POST",
              body: JSON.stringify({ query, mode: "deep" }),
            })
              .then((data) => {
                if (data?.cards) {
                  setResponseCards(data.cards);
                  const deepCard = data.cards.find((c) => c.type === "deep_search");
                  if (deepCard) setDeepSearchData(deepCard.data);
                }
              })
              .catch((err) => {
                setError(err.message);
              });
          }}
        />
      )}
      {searchModePromptData && (
        <SearchModePromptModal
          data={searchModePromptData}
          onSelect={handleSelectSearchMode}
          onClose={() => setSearchModePromptData(null)}
        />
      )}
      {deviceTest && <DeviceTestModal device={deviceTest} onClose={() => setDeviceTest(null)} />}
      {recheckOpen && (
        <FaceRecheckPanel
          scan={faceScan}
          onClose={() => {
            clearTimeout(recheckTimerRef.current);
            setRecheckOpen(false);
          }}
        />
      )}
      {notice && <div className="notice-toast" role="status">{notice}</div>}
      {/* V6.0: "Compartilhar -> JARVIS" */}
      {shareItem && createPortal(
        <div className="ld-overlay" role="dialog" aria-modal="true" aria-label="Compartilhado com o JARVIS" onClick={(e) => { if (e.target === e.currentTarget) setShareItem(null); }}>
          <section className="ld-card app-share">
            <header className="ld-head">
              <span className="lc-label">COMPARTILHADO COM O JARVIS</span>
              <button type="button" className="ld-x" onClick={() => setShareItem(null)} aria-label="Fechar">✕</button>
            </header>
            <p className="app-share-text">{shareItem.subject ? <b>{shareItem.subject}<br /></b> : null}{shareItem.text.slice(0, 300)}{shareItem.text.length > 300 ? "…" : ""}</p>
            <div className="app-share-actions">
              {shareActions.map((a) => (
                <button key={a.label} type="button" className="hl-quick-btn" onClick={() => { setShareItem(null); send(a.say); }}>
                  <i aria-hidden="true">{a.icon}</i>{a.label}
                </button>
              ))}
            </div>
          </section>
        </div>,
        document.body,
      )}
      {/* V6.0: depois de entrar pelo PIN no app, oferece a digital */}
      {bioOffer && createPortal(
        <div className="ld-overlay" role="dialog" aria-modal="true" aria-label="Entrar com a digital">
          <section className="ld-card app-bio">
            <header className="ld-head"><span className="lc-label">ENTRAR COM A DIGITAL</span></header>
            <p className="ld-text" style={{ textTransform: "none" }}>Quer entrar no JARVIS só encostando o dedo, sem digitar o PIN? Dá para desligar quando quiser.</p>
            <div className="app-share-actions">
              <button type="button" className="hl-quick-btn" onClick={enableBiometric}><i aria-hidden="true">👆</i>Ativar a digital</button>
              <button type="button" className="hl-quick-btn" onClick={() => { setBioOffer(false); try { localStorage.setItem("jarvis.bio.asked", "1"); } catch { /* ok */ } }}>Agora não</button>
            </div>
          </section>
        </div>,
        document.body,
      )}
      {fanModeEnabled && <FanGoalOverlay event={fanEvent} onDone={clearFanEvent} />}
      {briefingAsk && (
        <div className="bask-root" role="dialog" aria-modal="false" aria-labelledby="bask-title">
          <span className="bask-eyebrow">BRIEFING DE HOJE</span>
          <strong id="bask-title">Quer que eu repita o briefing?</strong>
          <p>Você já viu o {briefingAsk.command === "boa noite" ? "fechamento" : "briefing"} de hoje. Diga “repetir” ou “pular”.</p>
          <div className="bask-actions">
            <button type="button" className="np-btn" onClick={() => answerBriefingRef.current(true)}>↻ REPETIR <small>ENTER</small></button>
            <button type="button" className="np-btn np-alt" onClick={() => answerBriefingRef.current(false)}>PULAR <small>ESC</small></button>
          </div>
        </div>
      )}
      {welcomeName !== null && (
        <ProfileWelcome
          api={api}
          name={welcomeName}
          onDone={(prefsNow) => {
            handlePrefsChange(prefsNow);
            const who = welcomeName;
            setWelcomeName(null);
            api("/api/speak", { method: "POST", body: JSON.stringify({ text: `Perfil pronto${who ? `, ${who}` : ""}. Em que posso ajudar?` }) }).catch(() => {});
          }}
        />
      )}
      {relockWarning != null && (
        <div className="relock-toast" role="alert" aria-live="assertive">
          <strong>Bloqueando em {relockWarning} s.</strong> Mexa o mouse para cancelar.
        </div>
      )}
      {summaryActive && jarvisState === "speaking" && (
        <button type="button" className="summary-skip" onClick={handleCancel}>
          Resumo do dia · clique ou Esc para pular
        </button>
      )}
      {showNetworkQr && (
        <NetworkQrModal
          api={api}
          initialUrl={networkAccessUrl}
          onClose={() => setShowNetworkQr(false)}
        />
      )}
      {showWidgetWorkspace && (
        <WidgetWorkspace
          activeWidgets={activeWidgets}
          layout={widgetLayout}
          onLayoutChange={handleWidgetLayoutChange}
          onClose={() => setShowWidgetWorkspace(false)}
          onSend={send}
          api={api}
          apiWithBase={apiWithBase}
          steps={steps}
          connected={connected}
          services={{ ...services, microphone: supported }}
        />
      )}
      {showMonitorPanel && (
        <MonitorPanel
          onClose={() => setShowMonitorPanel(false)}
          onOpenWindow={openWeatherWindow}
          onOpenSpotifyWindow={openSpotifyWindow}
        />
      )}
      {floatingWindows.map((item) => (
        <div
          key={item.id}
          id={item.id}
          className={`jarvis-floating-window fixed z-50 ${item.maximized ? "inset-4 w-auto" : ""}`}
          style={!item.maximized ? { left: `${item.left ?? 32}px`, top: `${item.top ?? 96}px`, width: `${item.width ?? 384}px`, minHeight: `${item.height ?? 220}px` } : undefined}
        >
          <div
            className="widget-workspace-toolbar hud-panel"
            onPointerDown={(event) => {
              if (event.button !== 0 || event.target.closest("button") || item.maximized) return;
              const element = document.getElementById(item.id);
              const rect = element?.getBoundingClientRect();
              if (!rect) return;
              const move = (moveEvent) => updateFloatingWindow(item.id, {
                left: Math.max(8, Math.min(window.innerWidth - rect.width - 8, rect.left + moveEvent.clientX - event.clientX)),
                top: Math.max(8, Math.min(window.innerHeight - rect.height - 8, rect.top + moveEvent.clientY - event.clientY)),
              });
              const up = () => {
                window.removeEventListener("pointermove", move);
                window.removeEventListener("pointerup", up);
                document.body.style.userSelect = "";
              };
              document.body.style.userSelect = "none";
              window.addEventListener("pointermove", move);
              window.addEventListener("pointerup", up);
            }}
          >
            <span>
              {item.type === "weather"
                ? `Clima · Monitor ${item.monitor}`
                : item.type === "clock"
                  ? "Relógio digital · Brasília"
                  : item.type === "motivation"
                    ? "Mensagem do dia"
                    : item.type === "tasks"
                      ? "Minhas tarefas"
                  : item.type === "spotify"
                    ? `Spotify · Monitor ${item.monitor}`
                  : item.type === "focus" || item.type === "pomodoro"
                    ? "Modo Foco · Pomodoro Tático"
                  : item.type === "fan_news"
                    ? "⚽ Notícias do Palmeiras · GE"
                  : item.type === "fan_score"
                    ? "🏆 Placar & Partida · Palmeiras"
                  : item.type === "water"
                    ? "💧 Índice de Hidratação Diária"
                  : "JARVIS"}
            </span>
            <div className="flex gap-1">
              {item.type === "water" && (
                <button
                  type="button"
                  onClick={() => updateFloatingWindow(item.id, { pinned: !item.pinned })}
                  aria-label={item.pinned ? "Desafixar painel" : "Fixar painel"}
                  title={item.pinned ? "Desafixar (fecha sozinho)" : "Fixar (não fecha sozinho)"}
                >
                  {item.pinned ? "📌" : "📍"}
                </button>
              )}
              <button type="button" onClick={() => setShowMonitorPanel(true)} aria-label="Mover janela para outro monitor" title="Mover para monitor">▦</button>
              <button
                type="button"
                onClick={() => updateFloatingWindow(item.id, { minimized: !item.minimized })}
                aria-label={item.minimized ? "Restaurar janela" : "Minimizar janela"}
                title={item.minimized ? "Restaurar" : "Minimizar"}
              >
                {item.minimized ? "▢" : "—"}
              </button>
              <button
                type="button"
                onClick={async () => {
                  const element = document.getElementById(item.id);
                  if (document.fullscreenElement) await document.exitFullscreen?.();
                  else await element?.requestFullscreen?.();
                  updateFloatingWindow(item.id, { maximized: !item.maximized });
                }}
                aria-label={item.maximized ? "Restaurar tamanho da janela" : "Colocar em tela cheia"}
                title={item.maximized ? "Restaurar" : "Tela cheia"}
              >
                {item.maximized ? "❐" : "□"}
              </button>
              <button type="button" onClick={() => closeFloatingWindow(item.id)} aria-label="Fechar janela" title="Fechar">×</button>
            </div>
          </div>
          {!item.minimized && item.type === "weather" && (
            <WeatherWidget api={api} onWeatherLoaded={item.startup ? undefined : announceWeather} />
          )}
          {!item.minimized && item.type === "clock" && <DigitalClockWidget />}
          {!item.minimized && item.type === "motivation" && <MotivationWidget />}
          {!item.minimized && item.type === "tasks" && <TodoWidget api={api} onSend={send} />}
          {!item.minimized && item.type === "spotify" && <SpotifyWidget api={apiWithBase} onSend={send} />}
          {!item.minimized && (item.type === "focus" || item.type === "pomodoro") && (
            <FocusWidget api={api} onSend={send} />
          )}
          {!item.minimized && item.type === "fan_news" && (
            <div className="p-3 bg-black/75 rounded-b-xl overflow-hidden h-[340px]">
              <FanNewsWidget api={api} onSend={send} />
            </div>
          )}
          {!item.minimized && item.type === "fan_score" && (
            <div className="p-3 bg-black/75 rounded-b-xl overflow-hidden">
              <FanScoreWidget api={api} onSend={send} />
            </div>
          )}
          {!item.minimized && item.type === "water" && (
            <WaterAutoClose
              key={item.touchedAt || item.id}
              pinned={item.pinned}
              onTimeout={() => closeFloatingWindow(item.id)}
            >
              {(touch) => (
                <div className="p-3 bg-black/75 rounded-b-xl overflow-hidden">
                  <WaterWidget api={api} onInteract={touch} />
                </div>
              )}
            </WaterAutoClose>
          )}
          {!item.maximized && (
            <div
              className="absolute bottom-0 right-0 h-4 w-4 cursor-se-resize"
              onPointerDown={(event) => {
                event.stopPropagation();
                const element = document.getElementById(item.id);
                const rect = element?.getBoundingClientRect();
                if (!rect) return;
                const move = (moveEvent) => updateFloatingWindow(item.id, {
                  width: Math.max(300, rect.width + moveEvent.clientX - event.clientX),
                  height: Math.max(180, rect.height + moveEvent.clientY - event.clientY),
                });
                const up = () => {
                  window.removeEventListener("pointermove", move);
                  window.removeEventListener("pointerup", up);
                };
                window.addEventListener("pointermove", move);
                window.addEventListener("pointerup", up);
              }}
              aria-label="Redimensionar janela"
            />
          )}
        </div>
      ))}
      {showAudioWidget && (
        <AudioWaveformWidget
          api={api}
          jarvisState={jarvisState}
          listening={listening}
          onClose={() => setShowAudioWidget(false)}
        />
      )}

      {/* Modal de configurações */}
      {showSettings && (
        <SettingsPanel
          api={api}
          onClose={() => setShowSettings(false)}
          onPrefsChange={handlePrefsChange}
          onOpenMicrophone={() => setShowMicrophoneSelect(true)}
        />
      )}

      {/* Modal de seleção de microfone (quando aberto pelo Perfil ou Configurações) */}
      {showMicrophoneSelect && (
        <MicrophoneSelectModal
          onConfirm={(selectedId) => {
            setShowMicrophoneSelect(false);
            setMicrophoneId(selectedId);
            localStorage.setItem("jarvis.microphone.id", selectedId);
          }}
          onClose={() => setShowMicrophoneSelect(false)}
        />
      )}

      {/* Menu Lateral de Navegação (SideNav) */}
      {showSideNav && (
        <SideNav
          activeSection={activeSection}
          onNavigate={(section) => {
            setActiveSection(section);
            const narrations = {
              chat: "Canal principal de comando ativado.",
              hud: "Projetando interface de widgets e telemetria.",
              water: "Acessando controle de hidratação.",
              briefing: "Carregando briefing diário e notícias.",
              fontes: "Abrindo fontes de dados e conexões.",
              financeiro: "Acessando painel do mercado financeiro.",
              monitoramento: "Telemetria de sensores e diagnóstico.",
              logs: "Abrindo registros de eventos e auditoria.",
              configuracoes: "Acessando configurações do sistema.",
              onboarding: "Iniciando apresentação do Stark OS.",
            };
            if (narrations[section]) {
              api("/api/speak", { method: "POST", body: JSON.stringify({ text: narrations[section] }) }).catch(() => {});
            }

            if (section === "chat") {
              setShowSideNav(false);
              setScreensTab(null);
            } else if (section === "hud") {
              setShowSideNav(false);
              setShowWidgetWorkspace(true);
            } else if (section === "water") {
              setShowSideNav(false);
              send("índice de água");
            } else if (section === "briefing") {
              setShowSideNav(false);
              setScreensTab("briefing");
            } else if (section === "fontes") {
              setShowSideNav(false);
              setScreensTab("datasources");
            } else if (section === "financeiro") {
              setShowSideNav(false);
              setScreensTab("finance");
            } else if (section === "monitoramento") {
              setShowSideNav(false);
              setScreensTab("system");
            } else if (section === "logs") {
              setShowSideNav(false);
              setShowLogReport(true);
            } else if (section === "configuracoes") {
              setShowSideNav(false);
              setShowSettings(true);
            } else if (section === "onboarding") {
              setShowSideNav(false);
              setShowOnboarding(true);
            }
          }}
          onClose={() => setShowSideNav(false)}
        />
      )}

      {fanModeEnabled && <FanModeBackground />}

      {appPrefs.notifications_enabled && (
        <NotificationTray
          items={notifItems}
          onDismiss={() => {
            setNotifItems([]);
            api("/api/notifications", { method: "DELETE" }).catch(() => {});
          }}
        />
      )}

      <HudLayout
        devices={devices}
        countdowns={countdowns}
        onRemoveCountdown={(id) => api(`/api/countdowns/${id}`, { method: "DELETE" }).then((r) => setCountdowns(r.items || [])).catch(() => {})}
        fanModeEnabled={fanModeEnabled}
        fanTeam={fanTeam}
        aiName={aiName}
        stateLabel={stateLabel}
        jarvisState={jarvisState}
        listening={listening}
        interim={interim}
        connected={connected}
        services={{ ...services, microphone: supported }}
        sessionClock={sessionClock}
        busy={busy}
        api={api}
        userText={userText}
        response={response}
        responseCards={responseCards}
        briefing={briefing}
        onCloseBriefing={() => setBriefing(null)}
        onSkipBriefing={() => api("/api/briefing/skip", { method: "POST" }).catch(() => {})}
        photoUrl={photoUrl}
        error={error}
        audioVisible={showAudioWidget}
        onToggleAudio={() => setShowAudioWidget((current) => !current)}
        onOpenSpotify={openSpotifyPanel}
        onOpenWidgets={() => setShowWidgetWorkspace(true)}
        onOpenMonitors={() => setShowMonitorPanel(true)}
        onOpenSideNav={() => setShowSideNav((current) => !current)}
        screensTab={screensTab}
        onOpenScreens={(tab) => setScreensTab(tab)}
        onCloseScreens={() => setScreensTab(null)}
        onExit={returnToWaiting}
        onCancel={handleCancel}
        onToggleMic={toggleMic}
        zenMode={zenMode}
        onToggleZen={() => setZenMode((prev) => !prev)}
        onOpenSettings={() => setShowSettings(true)}
        onOpenGodsEye={() => {
          setGodsEyeOpen(true);
          soundManager.playSuccess();
        }}
        onCommand={(cmd) => {
          if (cmd === "modo sentinela") {
            enterSentinelMode();
            return;
          }
          if (cmd === "modo trabalho" || cmd === "modo foco" || cmd === "pomodoro") {
            openFocusPomodoro();
          }
          send(cmd);
        }}
        showConversation={showConversation}
        profileSlot={(
          <ProfileMenu
            photoUrl={photoUrl}
            name={name}
            activeWidgets={activeWidgets}
            onWidgetsChange={handleWidgetsChange}
            onOpenSettings={() => setShowSettings(true)}
            onOpenQr={() => setShowNetworkQr(true)}
            onOpenWidgets={() => setShowWidgetWorkspace(true)}
            onOpenMonitors={() => setShowMonitorPanel(true)}
            onOpenMicrophone={() => setShowMicrophoneSelect(true)}
            api={api}
          />
        )}
        orbSlot={
          fanModeEnabled ? (
            <ArcReactorHUD
              state={listening || heardAwake ? "speaking" : jarvisState}
              fanMode={true}
              fanShieldUrl={publicUrl("/fan/palmeiras/palmeiras_shield.png")}
            />
          ) : (
            <WireOrb state={listening || heardAwake ? "listening" : jarvisState} flash={orbFlash} />
          )
        }
        commandSlot={<CommandBar onSend={(text) => send(text)} disabled={busy} listening={listening} onToggleMic={toggleMic} />}
        tasksSlot={<TodoWidget api={api} onSend={send} />}
      />
      {godsEyeOpen && <GodsEye onClose={() => setGodsEyeOpen(false)} />}
    </>
  );
}

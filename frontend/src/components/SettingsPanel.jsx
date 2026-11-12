import { useState, useEffect, useRef } from "react";
import ClapSettings from "./settings/ClapSettings.jsx";
import LockSettings from "./settings/LockSettings.jsx";
import WaterSettings from "./settings/WaterSettings.jsx";
import SoundSettings from "./settings/SoundSettings.jsx";
import VoiceSettings from "./settings/VoiceSettings.jsx";
import BrowserSettings from "./settings/BrowserSettings.jsx";
import BriefingNewsSettings from "./settings/BriefingNewsSettings.jsx";
import MaintenanceSettings from "./settings/MaintenanceSettings.jsx";
import AutomationSettings from "./settings/AutomationSettings.jsx";
import PeopleSettings from "./settings/PeopleSettings.jsx";
import AccessibilitySettings from "./settings/AccessibilitySettings.jsx";
import SitesSettings from "./settings/SitesSettings.jsx";

const THEME_NAMES = {
  blue: "Azul (Núcleo)",
  green: "Verde Tático",
  purple: "Roxo Quântico",
  orange: "Laranja Reator",
  red: "Vermelho Alerta",
};

const THEME_PREVIEWS = {
  blue: "bg-[#1fc2f5] shadow-[0_0_8px_#1fc2f5]",
  green: "bg-[#22c55e] shadow-[0_0_8px_#22c55e]",
  purple: "bg-[#a855f7] shadow-[0_0_8px_#a855f7]",
  orange: "bg-[#f97316] shadow-[0_0_8px_#f97316]",
  red: "bg-[#ef4444] shadow-[0_0_8px_#ef4444]",
};

export default function SettingsPanel({ api, onClose, onPrefsChange, onOpenMicrophone }) {
  const [prefs, setPrefs] = useState(null);
  const [aiName, setAiName] = useState("");
  const [theme, setTheme] = useState("blue");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [tab, setTab] = useState("geral"); // "geral" | "multimidia" | "camera" | "atalhos" | "sites"
  const [shortcuts, setShortcuts] = useState({});
  const [sites, setSites] = useState([]);
  const [newName, setNewName] = useState("");
  const [newApps, setNewApps] = useState("");
  const [newUrls, setNewUrls] = useState("");
  const [shortcutError, setShortcutError] = useState("");
  const [provider, setProvider] = useState("gemini");
  const [personality, setPersonality] = useState("direto");
  const [searchMode, setSearchMode] = useState("auto");
  const [deepSearchAllowed, setDeepSearchAllowed] = useState(false);
  const [deepSearchLimit, setDeepSearchLimit] = useState(5);

  // Modo Torcedor (Glassmorphism)
  const [fanModeEnabled, setFanModeEnabled] = useState(false);
  const [fanTeam, setFanTeam] = useState("palmeiras");
  const [fanAutoOnMatchDay, setFanAutoOnMatchDay] = useState(false);
  const [fanShoutEnabled, setFanShoutEnabled] = useState(true);

  // Preferências de Multimídia & Produtividade
  const [favoriteGenres, setFavoriteGenres] = useState(["Sci-Fi", "Cyberpunk", "Tech"]);
  const [pomodoroMinutes, setPomodoroMinutes] = useState(25);

  // Câmeras detectadas
  const [cameras, setCameras] = useState([]);
  const [selectedCamera, setSelectedCamera] = useState(0);
  const [loadingCameras, setLoadingCameras] = useState(false);

  useEffect(() => {
    api("/api/prefs")
      .then(applyPrefs)
      .catch(() => {});

    api("/api/shortcuts")
      .then((data) => setShortcuts(data.shortcuts ?? {}))
      .catch(() => {});

    api("/api/sites")
      .then((data) => setSites(data.sites ?? []))
      .catch(() => {});

    loadCameras();
  }, [api]); // eslint-disable-line react-hooks/exhaustive-deps

  // Preenche o formulário com as preferências (ao abrir e depois de importar um backup)
  function applyPrefs(data) {
    setPrefs(data);
    setAiName(data.ai_name ?? "JARVIS");
    setTheme(data.color_theme ?? "blue");
    setSelectedCamera(data.camera_index ?? 0);
    setProvider(data.llm_provider ?? "gemini");
    setPersonality(data.personality_mode ?? "direto");
    setSearchMode(data.search_mode ?? "auto");
    setDeepSearchAllowed(Boolean(data.deep_search_allowed));
    setDeepSearchLimit(Number(data.deep_search_daily_limit ?? 5));
    setFanModeEnabled(Boolean(data.fan_mode_enabled));
    setFanTeam(data.fan_team ?? "palmeiras");
    setFanAutoOnMatchDay(Boolean(data.fan_auto_on_match_day));
    setFanShoutEnabled(data.fan_shout_enabled !== false);
  }

  const loadCameras = async () => {
    setLoadingCameras(true);
    try {
      const data = await api("/api/cameras");
      setCameras(data.cameras ?? []);
      if (data.current !== undefined) setSelectedCamera(data.current);
    } catch {
      /* ignora */
    } finally {
      setLoadingCameras(false);
    }
  };

  const speakFeedback = (text) => {
    api("/api/speak", {
      method: "POST",
      body: JSON.stringify({ text }),
    }).catch(() => {});
  };

  const handleSelectTheme = (newTheme) => {
    setTheme(newTheme);
    const label = THEME_NAMES[newTheme] || newTheme;
    speakFeedback(`Tema ${label} selecionado. Salve as configurações para aplicar.`);
  };

  // Abas novas (Palmas, Bloqueio, Hidratação): cada mudança é salva na hora
  const [patchStatus, setPatchStatus] = useState("");
  const patchTimer = useRef(null);
  const patchPrefs = async (patch, { quiet = false } = {}) => {
    setPrefs((cur) => ({ ...(cur || {}), ...patch }));
    clearTimeout(patchTimer.current);
    const runPatch = async () => {
      try {
        const updated = await api("/api/prefs", { method: "PATCH", body: JSON.stringify(patch) });
        setPrefs(updated);
        onPrefsChange(updated);
        setPatchStatus("✓ Salvo");
      } catch (err) {
        setPatchStatus(`Erro: ${err.message}`);
      }
      setTimeout(() => setPatchStatus(""), 2000);
    };
    if (quiet) patchTimer.current = setTimeout(runPatch, 350); // ex.: arrastar o controle de sensibilidade
    else runPatch();
  };

  const save = async () => {
    setSaving(true);
    const finalName = aiName.trim() || "JARVIS";
    try {
      const updated = await api("/api/prefs", {
        method: "PATCH",
        body: JSON.stringify({
          ai_name: finalName,
          color_theme: theme,
          camera_index: selectedCamera,
          llm_provider: provider,
          personality_mode: personality,
          search_mode: searchMode,
          deep_search_allowed: deepSearchAllowed,
          deep_search_daily_limit: Number(deepSearchLimit) || 5,
          fan_mode_enabled: fanModeEnabled,
          fan_team: fanTeam,
          fan_auto_on_match_day: fanAutoOnMatchDay,
          fan_shout_enabled: fanShoutEnabled,
        }),
      });
      setPrefs(updated);
      onPrefsChange(updated);
      setSaved(true);
      speakFeedback(`Configurações salvas. Meu nome agora é ${finalName}.`);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      /* ignora */
    } finally {
      setSaving(false);
    }
  };

  const addShortcut = async () => {
    setShortcutError("");
    const name = newName.trim();
    if (!name) return setShortcutError("Dê um nome ao atalho.");
    if (!newApps.trim() && !newUrls.trim()) return setShortcutError("Adicione pelo menos um app ou URL.");

    const apps = newApps.split(",").map((s) => s.trim()).filter(Boolean);
    const urls = newUrls.split(",").map((s) => s.trim()).filter(Boolean);
    try {
      const data = await api("/api/shortcuts", {
        method: "POST",
        body: JSON.stringify({ name, apps, urls }),
      });
      setShortcuts(data.shortcuts ?? {});
      speakFeedback(`Atalho ${name} adicionado com sucesso.`);
      setNewName("");
      setNewApps("");
      setNewUrls("");
    } catch (err) {
      setShortcutError(err.message);
    }
  };

  const removeShortcut = async (name) => {
    try {
      const data = await api(`/api/shortcuts/${encodeURIComponent(name)}`, { method: "DELETE" });
      setShortcuts(data.shortcuts ?? {});
    } catch {
      /* ignora */
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
      <div className="relative w-full max-w-lg max-h-[92vh] overflow-y-auto rounded-lg border border-cyan-500/40 bg-gradient-to-b from-[#082037]/90 to-[#020813]/95 p-6 shadow-[0_0_35px_rgba(31,194,245,0.2)]">
        {/* Cantos Táticos */}
        <div className="absolute top-2 left-2 w-3 h-3 border-t-2 border-l-2 border-cyan-400" />
        <div className="absolute top-2 right-2 w-3 h-3 border-t-2 border-r-2 border-cyan-400" />
        <div className="absolute bottom-2 left-2 w-3 h-3 border-b-2 border-l-2 border-cyan-400" />
        <div className="absolute bottom-2 right-2 w-3 h-3 border-b-2 border-r-2 border-cyan-400" />

        {/* Topo */}
        <div className="mb-5 flex items-center justify-between border-b border-cyan-500/20 pb-3">
          <div>
            <h2 className="font-['Orbitron'] text-lg font-bold tracking-widest text-cyan-200">
              PAINEL DE CONTROLE
            </h2>
            <span className="text-[10px] text-cyan-400/60 font-['Orbitron']">CONFIGURAÇÕES DE SISTEMA</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-cyan-400/60 hover:text-white px-2 py-1 rounded hover:bg-cyan-500/20 text-sm font-['Orbitron']"
          >
            ✕ FECHAR
          </button>
        </div>

        {/* Abas da central */}
        <div className="mb-5 grid grid-cols-4 gap-1.5 p-1 bg-black/40 border border-cyan-500/20 rounded">
          {[
            ["geral", "Geral"],
            ["torcedor", "Torcedor"],
            ["multimidia", "Mídia & Foco"],
            ["camera", "Câmera"],
            ["atalhos", "Atalhos"],
            ["sites", "Meus Sites"],
            ["palmas", "Palmas"],
            ["bloqueio", "Bloqueio"],
            ["agua", "Hidratação"],
            ["automacao", "Automação"],
            ["pessoas", "Pessoas"],
            ["acessibilidade", "Acessível"],
          ].map(([key, label]) => (
            <button
              key={key}
              type="button"
              onClick={() => setTab(key)}
              className={`py-1.5 text-xs font-['Orbitron'] tracking-wider rounded transition ${
                tab === key
                  ? "bg-cyan-500/30 text-white border border-cyan-400/60 shadow-[0_0_10px_rgba(31,194,245,0.3)]"
                  : "text-cyan-300/60 hover:text-cyan-200"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {patchStatus && (
          <div className="mb-2 text-[11px] font-['Orbitron'] text-emerald-300" role="status">{patchStatus}</div>
        )}
        {tab === "palmas" && prefs && <ClapSettings prefs={prefs} onPatch={patchPrefs} />}
        {tab === "bloqueio" && prefs && <LockSettings api={api} prefs={prefs} onPatch={patchPrefs} />}
        {tab === "agua" && prefs && <WaterSettings api={api} prefs={prefs} onPatch={patchPrefs} />}
        {tab === "automacao" && prefs && <AutomationSettings api={api} prefs={prefs} onPatch={patchPrefs} />}
        {tab === "pessoas" && <PeopleSettings api={api} />}
        {tab === "acessibilidade" && prefs && <AccessibilitySettings prefs={prefs} onPatch={patchPrefs} />}

        {/* Aba Geral */}
        {tab === "geral" && (
          <div className="space-y-4">
            <div>
              <label className="mb-1 block font-['Orbitron'] text-xs tracking-wider text-cyan-300">
                IDENTIFICAÇÃO DA IA
              </label>
              <input
                value={aiName}
                onChange={(e) => setAiName(e.target.value)}
                maxLength={20}
                placeholder="JARVIS"
                className="w-full rounded border border-cyan-500/30 bg-black/50 px-3 py-2 text-sm text-cyan-100 focus:border-cyan-400 focus:outline-none"
              />
            </div>

            <div>
              <label className="mb-2 block font-['Orbitron'] text-xs tracking-wider text-cyan-300">
                TEMA HOLOGRÁFICO
              </label>
              <div className="grid grid-cols-3 gap-2">
                {Object.entries(THEME_NAMES).map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => handleSelectTheme(key)}
                    className={`flex items-center gap-2 rounded border px-2.5 py-1.5 text-xs transition ${
                      theme === key
                        ? "border-cyan-300 bg-cyan-500/25 text-white shadow-[0_0_10px_rgba(31,194,245,0.3)]"
                        : "border-cyan-500/20 bg-black/30 text-cyan-200/60 hover:border-cyan-400"
                    }`}
                  >
                    <span className={`h-2.5 w-2.5 rounded-full ${THEME_PREVIEWS[key]}`} />
                    <span className="truncate">{label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* V4.4: fundo da interface (salva e aplica na hora) */}
            <div>
              <label className="mb-2 block font-['Orbitron'] text-xs tracking-wider text-cyan-300">
                FUNDO
              </label>
              <div className="grid grid-cols-2 gap-2">
                {[
                  ["blueprint", "Blueprint (planta azul)"],
                  ["space", "Universo (estrelas)"],
                  ["classic", "Clássico escuro"],
                ].map(([key, label]) => {
                  const current = (prefs?.background_style || "blueprint") === key;
                  return (
                    <button
                      key={key}
                      type="button"
                      disabled={!prefs}
                      onClick={() => patchPrefs({ background_style: key })}
                      aria-pressed={current}
                      className={`rounded border px-2.5 py-1.5 text-xs transition ${
                        current
                          ? "border-cyan-300 bg-cyan-500/25 text-white shadow-[0_0_10px_rgba(31,194,245,0.3)]"
                          : "border-cyan-500/20 bg-black/30 text-cyan-200/60 hover:border-cyan-400"
                      }`}
                    >
                      {label}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-['Orbitron'] text-cyan-300/80 mb-1">PROVEDOR LLM</label>
                <select
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                  className="w-full rounded border border-cyan-500/30 bg-black/50 p-2 text-xs text-cyan-100"
                >
                  <option value="gemini">Google Gemini 2.5</option>
                  <option value="openai">OpenAI GPT-4o</option>
                  <option value="anthropic">Anthropic Claude</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-['Orbitron'] text-cyan-300/80 mb-1">PERSONALIDADE</label>
                <select
                  value={personality}
                  onChange={(e) => setPersonality(e.target.value)}
                  className="w-full rounded border border-cyan-500/30 bg-black/50 p-2 text-xs text-cyan-100"
                >
                  <option value="direto">Direto / Tático</option>
                  <option value="descontraido">Descontraído</option>
                  <option value="formal">Mordomo Britânico</option>
                </select>
              </div>
            </div>

            {/* Controle de Pesquisa e Cota de IA */}
            <div className="rounded border border-cyan-500/25 bg-black/40 p-3 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <label className="block text-xs font-['Orbitron'] text-cyan-300 font-semibold">MODO DE PESQUISA</label>
                  <span className="text-[10px] text-cyan-400/60 font-mono">Automático: responde na hora, pesquisando no Google pela IA. Navegador não consome cota de API.</span>
                </div>
                <select
                  value={searchMode}
                  onChange={(e) => setSearchMode(e.target.value)}
                  className="rounded border border-cyan-500/30 bg-black/60 p-1.5 text-xs text-cyan-100 font-mono"
                >
                  <option value="auto">Automático, como a Alexa (Padrão)</option>
                  <option value="browser">Navegador</option>
                  <option value="ask">Perguntar sempre</option>
                  <option value="api">API Direta</option>
                </select>
              </div>

              <div className="border-t border-cyan-500/15 pt-2 flex items-center justify-between">
                <div>
                  <label className="block text-xs font-['Orbitron'] text-cyan-300 font-semibold">PESQUISA PROFUNDA (IA + WEB)</label>
                  <span className="text-[10px] text-cyan-400/60 font-mono">Trava geral: quando desligada, exige autorização prévia.</span>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={deepSearchAllowed}
                    onChange={(e) => setDeepSearchAllowed(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-9 h-5 bg-black/60 border border-cyan-500/40 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-cyan-400 after:border-cyan-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-cyan-500/30"></div>
                </label>
              </div>

              <div className="border-t border-cyan-500/15 pt-2 flex items-center justify-between">
                <div>
                  <label className="block text-xs font-['Orbitron'] text-cyan-300 font-semibold">LIMITE DIÁRIO (PESQUISA IA)</label>
                  <span className="text-[10px] text-cyan-400/60 font-mono">Máximo de consultas com IA por dia.</span>
                </div>
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={deepSearchLimit}
                  onChange={(e) => setDeepSearchLimit(Number(e.target.value) || 1)}
                  className="w-16 rounded border border-cyan-500/30 bg-black/60 p-1.5 text-xs text-cyan-100 text-center font-mono"
                />
              </div>
            </div>

            <button
              type="button"
              onClick={save}
              disabled={saving}
              className="mt-3 w-full rounded border border-cyan-400/80 bg-cyan-500/20 py-2.5 font-['Orbitron'] text-xs font-bold tracking-widest text-white shadow-[0_0_15px_rgba(31,194,245,0.3)] hover:bg-cyan-500/30 transition disabled:opacity-50"
            >
              {saving ? "SALVANDO..." : saved ? "✓ CONFIGURAÇÕES SALVAS!" : "SALVAR CONFIGURAÇÕES"}
            </button>
            {/* V6.2: temas de notícias do "bom dia" (ex.: Marvel com as 3 principais) */}
            <BriefingNewsSettings api={api} />
            <MaintenanceSettings api={api} onImported={(data) => { applyPrefs(data); onPrefsChange(data); }} />
          </div>
        )}

        {/* Aba Modo Torcedor */}
        {tab === "torcedor" && (
          <div className="space-y-4">
            <div className="p-3 rounded border border-emerald-500/30 bg-emerald-950/20">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-['Orbitron'] text-xs tracking-wider text-emerald-300">
                    MODO TORCEDOR (GLASSMORPHISM)
                  </h3>
                  <p className="text-[11px] text-emerald-200/60 mt-0.5">
                    Interface temática, notícias em tempo real, placar e grito de torcida.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setFanModeEnabled(!fanModeEnabled)}
                  className={`px-3 py-1.5 rounded text-xs font-['Orbitron'] border transition ${
                    fanModeEnabled
                      ? "bg-emerald-500/30 border-emerald-400 text-emerald-100 shadow-[0_0_10px_rgba(16,185,129,0.3)]"
                      : "bg-black/40 border-emerald-500/20 text-emerald-400/50"
                  }`}
                >
                  {fanModeEnabled ? "ATIVADO" : "DESATIVADO"}
                </button>
              </div>
            </div>

            <div>
              <label className="mb-1 block font-['Orbitron'] text-xs tracking-wider text-cyan-300">
                CLUBE DO CORAÇÃO
              </label>
              <select
                value={fanTeam}
                onChange={(e) => setFanTeam(e.target.value)}
                className="w-full rounded border border-cyan-500/30 bg-black/60 px-3 py-2 text-sm text-cyan-100 focus:border-cyan-400 focus:outline-none"
              >
                <option value="palmeiras">Sociedade Esportiva Palmeiras (Alviverde Imponente)</option>
              </select>
            </div>

            <div className="space-y-2 pt-2">
              <label className="flex items-center gap-2 cursor-pointer text-xs text-cyan-200/90">
                <input
                  type="checkbox"
                  checked={fanAutoOnMatchDay}
                  onChange={(e) => setFanAutoOnMatchDay(e.target.checked)}
                  className="rounded border-cyan-500/40 bg-black text-emerald-500 focus:ring-0"
                />
                <span>Ativar Modo Torcedor automaticamente em dias de jogo</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer text-xs text-cyan-200/90">
                <input
                  type="checkbox"
                  checked={fanShoutEnabled}
                  onChange={(e) => setFanShoutEnabled(e.target.checked)}
                  className="rounded border-cyan-500/40 bg-black text-emerald-500 focus:ring-0"
                />
                <span>Grito de torcida com a bola rolando ("Avante Palestra!")</span>
              </label>
            </div>

            <button
              type="button"
              onClick={save}
              disabled={saving}
              className="w-full rounded border border-cyan-400/60 bg-cyan-500/20 py-2.5 font-['Orbitron'] text-xs tracking-widest text-cyan-100 hover:bg-cyan-500/30 transition shadow-[0_0_15px_rgba(31,194,245,0.2)] disabled:opacity-50"
            >
              {saving ? "SALVANDO..." : saved ? "✓ CONFIGURAÇÕES SALVAS!" : "SALVAR CONFIGURAÇÕES"}
            </button>
            <MaintenanceSettings api={api} onImported={(data) => { applyPrefs(data); onPrefsChange(data); }} />
          </div>
        )}

        {/* Aba Multimídia & Produtividade */}
        {tab === "multimidia" && (
          <div className="space-y-4">
            {onOpenMicrophone && (
              <button
                type="button"
                onClick={onOpenMicrophone}
                className="w-full rounded border border-cyan-500/30 bg-black/40 p-3 text-left hover:border-cyan-400"
              >
                <strong className="block text-xs font-['Orbitron'] tracking-wider text-cyan-200">🎙 MICROFONE</strong>
                <span className="text-[11px] text-cyan-300/70">O JARVIS usa o microfone padrão do Windows. Toque para escolher outro.</span>
              </button>
            )}
            {prefs && <VoiceSettings prefs={prefs} onPatch={patchPrefs} api={api} />}
            <BrowserSettings api={api} />
            {prefs && <SoundSettings prefs={prefs} onPatch={patchPrefs} />}
            <div>
              <label className="mb-1 block font-['Orbitron'] text-xs tracking-wider text-cyan-300">
                PREFERÊNCIAS DE FILMES & SÉRIES
              </label>
              <div className="flex flex-wrap gap-2 mb-2">
                {["Sci-Fi", "Cyberpunk", "Ação", "Tech", "Cinema Cult", "Séries"].map((g) => (
                  <button
                    key={g}
                    type="button"
                    onClick={() => {
                      setFavoriteGenres((prev) =>
                        prev.includes(g) ? prev.filter((item) => item !== g) : [...prev, g]
                      );
                    }}
                    className={`px-3 py-1 rounded text-xs border transition ${
                      favoriteGenres.includes(g)
                        ? "bg-cyan-500/30 border-cyan-400 text-white shadow-[0_0_8px_rgba(31,194,245,0.3)]"
                        : "bg-black/30 border-cyan-500/20 text-cyan-300/60"
                    }`}
                  >
                    {favoriteGenres.includes(g) ? "✓ " : "+ "} {g}
                  </button>
                ))}
              </div>
              <p className="text-[11px] text-cyan-300/50">O JARVIS usará esses gêneros nas recomendações do radar auxiliar.</p>
            </div>

            <div>
              <label className="mb-1 block font-['Orbitron'] text-xs tracking-wider text-cyan-300">
                TEMPO DO POMODORO (MINUTOS)
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min="15"
                  max="60"
                  step="5"
                  value={pomodoroMinutes}
                  onChange={(e) => setPomodoroMinutes(Number(e.target.value))}
                  className="flex-1 accent-cyan-400"
                />
                <span className="font-['Orbitron'] text-sm font-bold text-cyan-200 w-12 text-right">
                  {pomodoroMinutes}m
                </span>
              </div>
            </div>

            <div className="p-3 rounded bg-black/40 border border-cyan-500/20 text-xs text-cyan-200/80 leading-relaxed">
              💡 <strong>Dica:</strong> Você pode dizer diretamente ao JARVIS:  
              <br />
              <em>"Jarvis, recomende um filme de ficção científica"</em> ou  
              <br />
              <em>"Jarvis, inicie foco de {pomodoroMinutes} minutos"</em>.
            </div>
          </div>
        )}

        {/* Aba Webcam */}
        {tab === "camera" && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-['Orbitron'] text-xs text-cyan-300">DISPOSITIVOS DE VISÃO</span>
              <button onClick={loadCameras} className="text-xs text-cyan-400 underline">
                {loadingCameras ? "Atualizando..." : "Atualizar"}
              </button>
            </div>
            <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
              {cameras.map((cam) => (
                <label
                  key={cam.index}
                  className={`flex cursor-pointer items-center justify-between rounded border p-2.5 text-xs ${
                    selectedCamera === cam.index
                      ? "border-cyan-400 bg-cyan-500/20 text-white"
                      : "border-cyan-500/20 bg-black/30 text-cyan-300/60"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <input
                      type="radio"
                      name="camera"
                      value={cam.index}
                      checked={selectedCamera === cam.index}
                      onChange={() => setSelectedCamera(cam.index)}
                    />
                    <span>{cam.name}</span>
                  </div>
                  <span className="text-[10px] text-cyan-400 font-['Orbitron']">
                    {selectedCamera === cam.index ? "ATIVO" : "SELECIONAR"}
                  </span>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* Aba Atalhos */}
        {tab === "atalhos" && (
          <div className="space-y-3">
            <p className="text-xs text-cyan-200/70">
              Atalhos rápidos para abrir seus programas e sites de lazer ou trabalho:
            </p>
            <div className="space-y-2 border-t border-cyan-500/20 pt-3">
              <input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder='Nome (ex.: "cinema em casa", "estudos")'
                className="w-full rounded border border-cyan-500/30 bg-black/50 p-2 text-xs text-cyan-100"
              />
              <input
                value={newApps}
                onChange={(e) => setNewApps(e.target.value)}
                placeholder="Apps (ex.: spotify, code, chrome)"
                className="w-full rounded border border-cyan-500/30 bg-black/50 p-2 text-xs text-cyan-100"
              />
              <input
                value={newUrls}
                onChange={(e) => setNewUrls(e.target.value)}
                placeholder="Sites (ex.: netflix.com, youtube.com)"
                className="w-full rounded border border-cyan-500/30 bg-black/50 p-2 text-xs text-cyan-100"
              />
              {shortcutError && <p className="text-xs text-rose-400">{shortcutError}</p>}
              <button
                type="button"
                onClick={addShortcut}
                className="w-full rounded border border-cyan-500/50 bg-cyan-950/40 py-2 text-xs font-['Orbitron'] text-cyan-200 hover:bg-cyan-500/20"
              >
                + ADICIONAR NOVO ATALHO
              </button>
            </div>
          </div>
        )}

        {tab === "sites" && <SitesSettings api={api} sites={sites} setSites={setSites} />}
      </div>
    </div>
  );
}

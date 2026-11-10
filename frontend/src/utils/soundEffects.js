/**
 * soundEffects.js — Sons do J.A.R.V.I.S. sintetizados pela Web Audio (sem arquivos externos).
 *
 * V4.2.2 (Branding Book, capítulo de sons):
 * - sons por estado: repouso (playIdle), ouvindo (playListening), sucesso (playStateSuccess), erro (playError);
 * - volume geral (0 a 100) e modo: "all" (todos), "important" (só erro e alerta) ou "off";
 * - das 22h às 7h, o mesmo silêncio dos gatilhos: só os sons importantes tocam, com metade do volume;
 * - o modo silencioso do JARVIS cala tudo.
 * Todos os sons duram no máximo 400 ms.
 * A configuração vem das preferências (App.jsx chama soundManager.configure).
 */

let audioCtx = null;
let master = null;

function getAudioContext() {
  if (typeof window === "undefined") return null;
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (AudioContextClass) {
      audioCtx = new AudioContextClass();
      master = audioCtx.createGain();
      master.connect(audioCtx.destination);
    }
  }
  if (audioCtx && audioCtx.state === "suspended") {
    audioCtx.resume().catch(() => {});
  }
  return audioCtx;
}

// Sons que tocam mesmo no modo "só o que importa" e de madrugada
export const IMPORTANT = new Set(["error", "alert"]);
export const QUIET_START = 22;
export const QUIET_END = 7;

/**
 * Decide se um som toca e com qual volume (0 a 1). Função pura (testada em tests/sounds.test.js).
 * cfg: { enabled, volume (0-100), mode ("all" | "important" | "off"), silent }
 */
export function soundPolicy(kind, cfg, date = new Date()) {
  if (!cfg.enabled || cfg.silent || cfg.mode === "off") return 0;
  const important = IMPORTANT.has(kind);
  const hour = date.getHours();
  const quiet = hour >= QUIET_START || hour < QUIET_END;
  if ((cfg.mode === "important" || quiet) && !important) return 0;
  const volume = Math.max(0, Math.min(100, Number(cfg.volume ?? 60))) / 100;
  return quiet ? volume * 0.5 : volume;
}

function storedEnabled() {
  try {
    return localStorage.getItem("jarvis.sfx.enabled") !== "0";
  } catch {
    return true;
  }
}

// Toca uma sequência de notas curtas. notes: [{ f, f2?, t, d, g, type }] (t = início, d = duração em s)
function playNotes(kind, notes) {
  // Na prévia de Configurações o volume vem da barra (ignora modo e horário de silêncio)
  const level = soundManager.previewLevel ?? soundPolicy(kind, soundManager.config());
  if (!level) return;
  try {
    const ctx = getAudioContext();
    if (!ctx) return;
    master.gain.setValueAtTime(level, ctx.currentTime);
    const now = ctx.currentTime;
    notes.forEach(({ f, f2, t = 0, d = 0.12, g = 0.1, type = "sine" }) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(f, now + t);
      if (f2) osc.frequency.exponentialRampToValueAtTime(f2, now + t + d);
      gain.gain.setValueAtTime(0.0001, now + t);
      gain.gain.exponentialRampToValueAtTime(g, now + t + 0.012);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + t + d);
      osc.connect(gain);
      gain.connect(master);
      osc.start(now + t);
      osc.stop(now + t + d + 0.02);
    });
  } catch {
    /* sem áudio no navegador: segue em silêncio */
  }
}

export const soundManager = {
  enabled: typeof window !== "undefined" ? storedEnabled() : true,
  settings: { volume: 60, mode: "all", silent: false },

  configure({ volume, mode, silent } = {}) {
    if (volume !== undefined) this.settings.volume = volume;
    if (mode !== undefined) this.settings.mode = mode;
    if (silent !== undefined) this.settings.silent = Boolean(silent);
  },

  config() {
    return { enabled: this.enabled, ...this.settings };
  },

  toggle() {
    this.enabled = !this.enabled;
    try {
      localStorage.setItem("jarvis.sfx.enabled", this.enabled ? "1" : "0");
    } catch {
      /* sem armazenamento: vale só nesta sessão */
    }
    if (this.enabled) this.playClick();
    return this.enabled;
  },

  // Clique / toque na interface
  playClick() {
    playNotes("click", [{ f: 1400, f2: 800, d: 0.045, g: 0.08 }]);
  },

  // Chime de ativação (palmas reconhecidas)
  playChime() {
    playNotes("chime", [587.33, 880, 1174.66].map((f, i) => ({ f, t: i * 0.06, d: 0.2, g: 0.09 })));
  },

  // Sucesso longo (desbloqueio, fim do foco, pesquisa pronta)
  playSuccess() {
    playNotes("success", [523.25, 659.25, 783.99, 1046.5].map((f, i) => ({ f, t: i * 0.06, d: 0.2, g: 0.11, type: "triangle" })));
  },

  // Água entrando no recipiente: "bloop"
  playWater() {
    playNotes("water", [0, 0.09, 0.2].map((t, i) => ({ f: 520 - i * 70, f2: (520 - i * 70) * 1.9, t, d: 0.12, g: 0.07 })));
  },

  // Alerta tático
  playAlert() {
    playNotes("alert", [{ f: 440, t: 0, d: 0.1, g: 0.08, type: "sawtooth" }, { f: 330, t: 0.1, d: 0.14, g: 0.08, type: "sawtooth" }]);
  },

  // Aviso suave (ex.: pergunta de modo de pesquisa)
  playNotification() {
    playNotes("notification", [{ f: 880, t: 0, d: 0.1, g: 0.07 }, { f: 1318.5, t: 0.09, d: 0.16, g: 0.07 }]);
  },

  // ---- Sons por estado (V4.2.2) ----
  // Repouso: um "desligar" grave e curto quando o JARVIS volta a esperar
  playIdle() {
    playNotes("idle", [{ f: 392, f2: 261.6, d: 0.16, g: 0.05 }]);
  },
  // Ouvindo: bipe curto de abertura (duas notas subindo)
  playListening() {
    playNotes("listening", [{ f: 784, t: 0, d: 0.07, g: 0.08 }, { f: 1175, t: 0.07, d: 0.1, g: 0.08 }]);
  },
  // Sucesso: tom ascendente curto (ação concluída)
  playStateSuccess() {
    playNotes("success", [659.25, 880, 1318.5].map((f, i) => ({ f, t: i * 0.055, d: 0.14, g: 0.09, type: "triangle" })));
  },
  // Erro: tom descendente
  playError() {
    playNotes("error", [{ f: 466, t: 0, d: 0.13, g: 0.09, type: "triangle" }, { f: 311, t: 0.12, d: 0.2, g: 0.09, type: "triangle" }]);
  },

  previewLevel: null,

  // Toca um som de estado pelo nome (prévia em Configurações), no volume pedido (0 a 100)
  preview(name, volume = this.settings.volume) {
    const map = { idle: "playIdle", listening: "playListening", success: "playStateSuccess", error: "playError" };
    if (!map[name]) return;
    this.previewLevel = Math.max(0, Math.min(100, Number(volume))) / 100;
    try {
      this[map[name]]();
    } finally {
      this.previewLevel = null;
    }
  },
};

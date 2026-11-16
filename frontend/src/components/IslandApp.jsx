import { useCallback, useEffect, useRef, useState } from "react";
import RoboAvatar from "./RoboAvatar.jsx";
import { api } from "../utils/api.js";
import { hexToRgb } from "../utils/desk.js";
import IslandPanel from "./IslandPanel.jsx";
import { watchNewBuild } from "../utils/newBuild.js";
import { useLiteMode } from "../utils/lite.js";
import { useGroqVoice } from "../utils/voiceRecord.js";
import "../island.css";

// V8.0: a ILHA do app para Windows: pílula preta no topo da tela, sempre visível (como a "ilha" dos celulares).
// Em repouso: o avatar e a hora. Com música: a música tocando. Quando o JARVIS responde: a resposta, que some sozinha.
// V8.1.2: clicar ABRE a ilha (como a ilha dinâmica): avatar e estado, a música com ⏮ ⏯ ⏭ e a capa, a última
// resposta e os botões 🎙 FALAR e 🖥 ABRIR. Fecha ao clicar de novo, ao sair dela ou sozinha depois de alguns segundos.
// V8.1.3: a janela do JARVIS só aparece pela ilha (🖥 ABRIR JARVIS ou dois cliques na pílula). O app também avisa
// aqui quando o botão do mouse desce em cima da ilha (window.__jarvisIslandPress), para o clique funcionar mesmo
// se o WebView2 não receber o mouse; o clique repetido (o de verdade, logo depois) é ignorado.
// V8.3.0 (ideia 9): clicar ABRE OS MENUS NA PRÓPRIA ILHA (painel que cresce para baixo, ~440×560): Resumo do
// dia, Conversa, Tarefas, Lembretes, Música, Timers, Missões, Hábitos e Copiados. Fecha ao clicar fora, no ✕,
// com Esc ou depois de 1 minuto parada. Dois cliques na pílula (ou 🖥 ABRIR JARVIS) ainda abrem a janela toda.
// Esta página é aberta só pelo app (?ilha=1); as funções do Windows vêm do window.pywebview.api.
const IDLE_CLOSE_MS = 60000;
const DEDUPE_MS = 800;

/** Toque avisado pelo app: clica no que está naquele ponto; o clique real que vier logo depois é ignorado. */
export function installIslandPress(win = window, doc = document) {
  let last = 0;
  win.__jarvisIslandPress = (x, y) => {
    last = Date.now();
    const el = doc.elementFromPoint(x, y);
    if (el && /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName)) {
      el.focus?.(); // campo de texto: o toque só dá o foco (para digitar)
      return;
    }
    const target = el?.closest?.("button, [data-il-click]") || el;
    target?.click?.();
  };
  const swallow = (e) => {
    if (e.isTrusted && Date.now() - last < DEDUPE_MS) {
      e.stopPropagation();
      e.preventDefault();
    }
  };
  doc.addEventListener("click", swallow, true);
  return () => {
    delete win.__jarvisIslandPress;
    doc.removeEventListener("click", swallow, true);
  };
}

const pyApi = () => window.pywebview?.api || {};

export function islandMode(open, reply) {
  if (open) return "painel";
  return reply ? "resposta" : "mini";
}

let msgId = 0;

export default function IslandApp() {
  const [st, setSt] = useState(null);
  const [track, setTrack] = useState(null);
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState("resumo");
  const [chat, setChat] = useState([]);
  const [busy, setBusy] = useState(false);
  const [hint, setHint] = useState("");
  const [locked, setLocked] = useState(false);
  const modeRef = useRef("");
  const closeTimer = useRef(null);

  useEffect(() => installIslandPress(), []);
  useEffect(() => { // V8.3.2: JARVIS bloqueado: os menus avisam em vez de mostrar "Erro 403"
    let t;
    const onDenied = () => {
      setLocked(true);
      clearTimeout(t);
      t = setTimeout(() => setLocked(false), 30000);
    };
    window.addEventListener("jarvis_access_denied", onDenied);
    return () => {
      clearTimeout(t);
      window.removeEventListener("jarvis_access_denied", onDenied);
    };
  }, []);
  const openRef = useRef(false);
  useEffect(() => { openRef.current = open; }, [open]);
  useEffect(() => watchNewBuild(() => !openRef.current, 30000), []); // V8.3.1: interface nova -> recarrega fechada
  useEffect(() => {
    const report = (e) => pyApi().log?.(`${e.message || e.reason || e}`);
    window.addEventListener("error", report);
    window.addEventListener("unhandledrejection", report);
    return () => {
      window.removeEventListener("error", report);
      window.removeEventListener("unhandledrejection", report);
    };
  }, []);
  const lite = useLiteMode(st?.desempenho?.leve || "auto"); // V8.4.0: modo leve -> atualiza mais devagar
  useEffect(() => {
    document.documentElement.classList.add("is-island");
    let alive = true;
    const tick = () => api("/api/desk/island").then((d) => alive && setSt(d)).catch(() => alive && setSt((s) => s && { ...s, offline: true }));
    const music = () => api("/api/integrations/spotify/track").then((d) => alive && setTrack(d || null)).catch(() => {});
    tick();
    music();
    const a = setInterval(tick, lite ? 3500 : 1200);
    const b = setInterval(music, lite ? 12000 : 5000);
    return () => {
      alive = false;
      clearInterval(a);
      clearInterval(b);
    };
  }, [lite]);

  const reply = Boolean(st?.resposta);
  const mode = islandMode(open, reply);
  useEffect(() => { // a janela do Windows muda de tamanho junto (centralizada, recortada)
    if (mode === modeRef.current) return;
    modeRef.current = mode;
    const p = pyApi();
    if (p.island_mode) p.island_mode(mode);
    else p.island_expand?.(mode !== "mini");
  }, [mode]);

  const close = useCallback(() => {
    setOpen(false);
    setHint("");
  }, []);
  const armClose = useCallback(() => {
    clearTimeout(closeTimer.current);
    closeTimer.current = setTimeout(close, IDLE_CLOSE_MS);
  }, [close]);
  useEffect(() => {
    if (!open) return undefined;
    armClose();
    const onKey = (e) => {
      armClose();
      if (e.key === "Escape") close();
    };
    window.__jarvisIslandOutside = close; // o app avisa quando você clica fora da ilha
    window.addEventListener("blur", close);
    window.addEventListener("keydown", onKey);
    return () => {
      clearTimeout(closeTimer.current);
      delete window.__jarvisIslandOutside;
      window.removeEventListener("blur", close);
      window.removeEventListener("keydown", onKey);
    };
  }, [open, armClose, close]);

  const openPanel = (where = "resumo") => {
    if (where === "conversa" && st?.resposta) { // tocou na resposta: ela aparece na Conversa
      setChat((c) => (c.some((m) => m.text === st.resposta) ? c : [...c, { id: ++msgId, role: "jarvis", text: st.resposta }]));
    }
    setTab(where);
    setOpen(true);
  };

  const control = (action) => {
    armClose();
    api("/api/integrations/spotify/control", { method: "POST", body: JSON.stringify({ action }) })
      .then(() => setTrack((t) => (t && (action === "play" || action === "pause") ? { ...t, state: action === "play" ? "playing" : "paused" } : t)))
      .catch(() => {});
    setTimeout(() => api("/api/integrations/spotify/track").then((d) => setTrack(d || null)).catch(() => {}), 900);
  };

  const send = useCallback(async (text) => {
    const add = (role, t) => setChat((c) => [...c.slice(-30), { id: ++msgId, role, text: t }]);
    add("user", text);
    setBusy(true);
    armClose();
    try {
      const r = await api("/api/chat", { method: "POST", body: JSON.stringify({ message: text }) });
      if (r?.response) add("jarvis", r.response);
      return r;
    } catch (e) {
      add("error", e.message || "Não consegui falar com o JARVIS.");
      throw e;
    } finally {
      setBusy(false);
      armClose();
    }
  }, [armClose]);
  const sendQuiet = (text) => send(text).catch(() => {});

  // 🎙 FALAR na própria ilha. V8.4.0: grava e a Groq entende (o reconhecimento do navegador falha dentro do app).
  const voice = useGroqVoice({ onText: (t) => { setHint(""); sendQuiet(t); }, onError: setHint });
  const listening = voice.listening;
  const talk = () => {
    setTab("conversa");
    armClose();
    setHint("");
    voice.toggle();
  };
  const openMain = () => {
    close();
    pyApi().show_main?.();
  };

  const hasTrack = track && (track.state === "playing" || track.state === "paused") && track.title;
  const playing = hasTrack && track.state === "playing";
  const estado = st?.offline ? "offline" : st?.estado || "idle";
  const face = estado === "speaking" ? "speaking" : estado === "processing" ? "processing" : "idle";
  const stateLabel = { offline: "Desligado", speaking: "Falando…", processing: "Pensando…", listening: "Ouvindo…" }[estado] || "Pronto";
  const style = { "--il-accent": st?.cor || "#22d3ee", "--il-rgb": hexToRgb(st?.cor) };

  if (mode === "painel") {
    return (
      <div className={`il il-${estado} is-card is-panel`} style={style} onMouseMove={armClose} role="dialog" aria-label="Ilha do JARVIS">
        <div className="il-head">
          <RoboAvatar avatar={st?.avatar} tema={st?.tema} state={face} size={40} />
          <div className="il-head-txt"><b>JARVIS</b><small><i className="il-dot" />{stateLabel}</small></div>
          <span className="il-clock">{st?.hora || ""}</span>
          <button type="button" className="il-x" onClick={() => pyApi().quit?.()} aria-label="Sair do app" title="Sair do app (o JARVIS continua rodando no PC)">⏻</button>
          <button type="button" className="il-x" onClick={close} aria-label="Fechar a ilha" title="Fechar (Esc)">✕</button>
        </div>
        <IslandPanel tab={tab} setTab={(t) => { setTab(t); armClose(); }} st={st} track={hasTrack ? track : null} onControl={control}
          chat={chat} busy={busy || voice.busy} onSend={send} onTalk={talk} listening={listening} />
        {locked && <button type="button" className="ilp-locked" onClick={openMain}>🔒 O JARVIS está bloqueado. Toque aqui para desbloquear (rosto ou PIN).</button>}
        {hint && <p className="ilp-hint">{hint}</p>}
        <div className="il-actions">
          <button type="button" className="is-main" onClick={talk}>🎙 FALAR</button>
          <button type="button" onClick={openMain}>🖥 ABRIR JARVIS</button>
        </div>
      </div>
    );
  }

  return (
    <button type="button" className={`il il-${estado}${mode === "resposta" ? " is-open" : ""}`} style={style}
      onClick={() => openPanel(mode === "resposta" ? "conversa" : "resumo")} onDoubleClick={openMain} title="Clique: abre os menus · dois cliques: abre o JARVIS">
      <span className="il-row">
        <RoboAvatar avatar={st?.avatar} tema={st?.tema} state={face} size={mode === "resposta" ? 30 : 24} />
        <i className="il-dot" />
        {estado === "offline" ? <span className="il-txt">JARVIS desligado</span>
          : playing ? <span className="il-txt il-music"><b className="il-eq"><i /><i /><i /></b>{track.title}{track.artist ? ` · ${track.artist}` : ""}</span>
            : <span className="il-txt">{estado === "speaking" ? "Falando…" : estado === "processing" ? "Pensando…" : st?.hora || ""}</span>}
      </span>
      {mode === "resposta" && <span className="il-reply">{st.resposta}</span>}
    </button>
  );
}

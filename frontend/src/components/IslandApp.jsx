import { useCallback, useEffect, useRef, useState } from "react";
import RoboAvatar from "./RoboAvatar.jsx";
import DeskApp from "./DeskApp.jsx";
import { api } from "../utils/api.js";
import { hexToRgb } from "../utils/desk.js";
import { watchNewBuild } from "../utils/newBuild.js";
import { useLiteMode } from "../utils/lite.js";
import { startPacman, usePoke } from "../utils/poke.js";
import "../island.css";

// V8.0: a ILHA do app para Windows: pílula preta no topo da tela, sempre visível (como a "ilha" dos celulares).
// Em repouso: o avatar e a hora. Com música: a música tocando. Quando o JARVIS responde: a resposta, que some sozinha.
// V8.1.3: a janela grande do JARVIS só aparece pela ilha (dois cliques ou 🖥). O app também avisa aqui quando o botão
// do mouse desce/sobe em cima da ilha (window.__jarvisIslandDown/Press), para o clique funcionar mesmo se o WebView2
// não receber o mouse; o clique repetido (o de verdade) é ignorado.
// V8.4.1 (igual ao vídeo): clicar na pílula ABRE O APP INTEIRO DENTRO DA ILHA: um painel largo que desce do topo com
// a barra lateral do Modo Desk (Início, Conversa, Memória, Tarefas, ... e as Configurações: Personalizar, Cérebro,
// Ilha...). A barra de cima do painel (e a pílula fechada) arrasta a ilha para os lados; ela lembra onde ficou.
// Fecha no ✕, com Esc, clicando fora ou depois de 2 minutos parada.
// Esta página é aberta só pelo app (?ilha=1); as funções do Windows vêm do window.pywebview.api.
const IDLE_CLOSE_MS = 120000;
// V8.6.0: o avatar da pílula bem maior, em close no rosto (dava para ver a expressão)
const PILL_AVATAR = { pequena: 40, media: 46, grande: 54 }; // V8.6.2: dentro de um círculo escuro, sem encostar na borda
const DEDUPE_MS = 800;

/** Toque avisado pelo app. O app avisa quando o botão DESCE (aí o clique real que vier é ignorado) e, se não foi
 *  um arraste, quando SOBE (aí clica no que está naquele ponto). Arrastou: só ignora o clique real. */
export function installIslandPress(win = window, doc = document) {
  let last = 0;
  let pending = false;
  win.__jarvisIslandDown = () => {
    pending = true;
  };
  win.__jarvisIslandDragged = () => {
    pending = false;
    last = Date.now();
  };
  win.__jarvisIslandPress = (x, y) => {
    pending = false;
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
    if (e.isTrusted && (pending || Date.now() - last < DEDUPE_MS)) {
      e.stopPropagation();
      e.preventDefault();
    }
  };
  doc.addEventListener("click", swallow, true);
  return () => {
    delete win.__jarvisIslandPress;
    delete win.__jarvisIslandDown;
    delete win.__jarvisIslandDragged;
    doc.removeEventListener("click", swallow, true);
  };
}

const pyApi = () => window.pywebview?.api || {};

export function islandMode(open, reply) {
  if (open) return "painel";
  return reply ? "resposta" : "mini";
}

export default function IslandApp() {
  const [st, setSt] = useState(null);
  const [track, setTrack] = useState(null);
  const [open, setOpen] = useState(false);
  const [locked, setLocked] = useState(false);
  const [names, setNames] = useState({ ai: "JARVIS", user: "" });
  const [turn, setTurn] = useState({ userText: "", response: "", error: "" });
  const [busy, setBusy] = useState(false);
  const modeRef = useRef("");
  const openRef = useRef(false);
  const closeTimer = useRef(null);

  useEffect(() => installIslandPress(), []);
  useEffect(() => { openRef.current = open; }, [open]);
  useEffect(() => watchNewBuild(() => !openRef.current, 30000), []); // V8.3.1: interface nova -> recarrega fechada
  useEffect(() => { // V8.3.2: JARVIS bloqueado: avisa em vez de mostrar "Erro 403"
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
  useEffect(() => {
    const report = (e) => pyApi().log?.(`${e.message || e.reason || e}`);
    window.addEventListener("error", report);
    window.addEventListener("unhandledrejection", report);
    return () => {
      window.removeEventListener("error", report);
      window.removeEventListener("unhandledrejection", report);
    };
  }, []);
  useEffect(() => {
    api("/api/prefs").then((d) => setNames((n) => ({ ...n, ai: d?.ai_name ? d.ai_name.toUpperCase() : "JARVIS" }))).catch(() => {});
    api("/api/profile").then((d) => setNames((n) => ({ ...n, user: d?.name || "" }))).catch(() => {});
  }, []);

  const [pacHint, setPacHint] = useState("");
  const { mood, poke } = usePoke(() => { // V8.6.0: irritou -> corre atrás do mouse
    setOpen(false);
    if (!startPacman()) { // V8.6.2: o app do Windows aberto é de antes do Pac-Man
      setPacHint("😤 Para ele correr atrás do mouse, feche o app pelo ⏻ e abra de novo (versão nova).");
      setTimeout(() => setPacHint(""), 9000);
    }
  });
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

  // a resposta que o JARVIS deu por outro caminho (voz "Jarvis, …", celular) também entra na conversa do painel
  useEffect(() => {
    if (st?.resposta) setTurn((t) => (t.response === st.resposta ? t : { ...t, response: st.resposta, error: "" }));
  }, [st?.resposta]);

  // V8.5.0: tamanho do painel e posição escolhidos em Configurações › Ilha vão para a janela do Windows
  const panel = st?.ilha?.painel;
  useEffect(() => { if (panel) pyApi().island_layout?.(panel); }, [panel]);
  const autohide = st?.ilha?.ocultar; // V8.7.0: escondida no topo (desce quando o mouse chega lá)
  useEffect(() => { if (typeof autohide === "boolean") pyApi().island_autohide?.(autohide); }, [autohide]);
  const posRef = useRef(null);
  const pos = st?.ilha?.posicao;
  useEffect(() => {
    if (typeof pos !== "number") return;
    if (posRef.current !== null && posRef.current !== pos) pyApi().island_set_pos?.(pos);
    posRef.current = pos;
  }, [pos]);
  const [zoom, setZoom] = useState(null);
  const shownZoom = zoom ?? st?.ilha?.zoom ?? 0.9;
  const changeZoom = (delta) => {
    const z = Math.round(Math.min(1.4, Math.max(0.7, shownZoom + delta)) * 100) / 100;
    setZoom(z);
    api("/api/desk", { method: "PATCH", body: JSON.stringify({ ilha: { zoom: z } }) }).then(() => setZoom(null)).catch(() => {});
  };

  const reply = Boolean(st?.resposta) || Boolean(pacHint);
  const mode = islandMode(open, reply);
  useEffect(() => { // a janela do Windows muda de tamanho junto (recortada no formato da ilha)
    if (mode === modeRef.current) return;
    modeRef.current = mode;
    const p = pyApi();
    if (p.island_mode) p.island_mode(mode);
    else p.island_expand?.(mode !== "mini");
  }, [mode]);

  const close = useCallback(() => setOpen(false), []);
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
    window.addEventListener("keydown", onKey);
    window.addEventListener("mousemove", armClose, { passive: true });
    return () => {
      clearTimeout(closeTimer.current);
      delete window.__jarvisIslandOutside;
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("mousemove", armClose);
    };
  }, [open, armClose, close]);

  const send = useCallback(async (text) => {
    setTurn({ userText: text, response: "", error: "" });
    setBusy(true);
    try {
      const r = await api("/api/chat", { method: "POST", body: JSON.stringify({ message: text }) });
      setTurn((t) => ({ ...t, response: r?.response || t.response }));
    } catch (e) {
      setTurn((t) => ({ ...t, error: e.message || "Não consegui falar com o JARVIS." }));
    } finally {
      setBusy(false);
    }
  }, []);
  const openMain = () => {
    close();
    pyApi().show_main?.();
  };
  const lock = () => {
    api("/api/access/lock", { method: "POST" }).catch(() => {});
    openMain(); // o desbloqueio (rosto ou PIN) é na janela do JARVIS
  };
  const rename = (n) => api("/api/prefs", { method: "PATCH", body: JSON.stringify({ ai_name: n.trim() }) })
    .then((d) => setNames((x) => ({ ...x, ai: d?.ai_name ? d.ai_name.toUpperCase() : x.ai }))).catch(() => {});

  const hasTrack = track && (track.state === "playing" || track.state === "paused") && track.title;
  const playing = hasTrack && track.state === "playing";
  const estado = st?.offline ? "offline" : busy ? "processing" : st?.estado || "idle";
  const face = estado === "speaking" ? "speaking" : estado === "processing" ? "processing" : "idle";
  const stateLabel = { offline: "Desligado", speaking: "Falando…", processing: "Pensando…", listening: "Ouvindo…" }[estado] || "Pronto";
  const style = { "--il-accent": st?.cor || "#22d3ee", "--il-rgb": hexToRgb(st?.cor) };

  if (mode === "painel") {
    return (
      <div className={`il-app il-${estado}`} style={style} role="dialog" aria-label="JARVIS na ilha">
        <div className="il-bar" data-il-drag title="Arraste para mover a ilha · dois cliques: volta ao centro"
          onDoubleClick={(e) => { if (e.target === e.currentTarget) pyApi().island_center?.(); }}>
          <button type="button" className="il-poke" onClick={poke} title="Não cutuque o JARVIS… 😈" aria-label="Cutucar o JARVIS">
            <RoboAvatar avatar={mood ? { ...st?.avatar, expressao: mood } : st?.avatar} tema={st?.tema} state={mood ? "idle" : face} size={30} tight still={Boolean(mood)} />
          </button>
          <i className="il-dot" />
          <span className="il-bar-txt">{playing ? `♫ ${track.title}${track.artist ? ` · ${track.artist}` : ""}` : stateLabel}</span>
          {locked && <button type="button" className="il-locked" onClick={openMain}>🔒 Bloqueado: toque para desbloquear</button>}
          <span className="il-zoom" role="group" aria-label="Zoom do painel">
            <button type="button" onClick={() => changeZoom(-0.1)} aria-label="Diminuir o zoom" title="Diminuir">A−</button>
            <b>{Math.round(shownZoom * 100)}%</b>
            <button type="button" onClick={() => changeZoom(0.1)} aria-label="Aumentar o zoom" title="Aumentar">A+</button>
          </span>
          <span className="il-clock">{st?.hora || ""}</span>
          <button type="button" className="il-x" onClick={openMain} aria-label="Abrir a janela do JARVIS" title="Abrir a janela grande">🖥</button>
          <button type="button" className="il-x" onClick={() => pyApi().quit?.()} aria-label="Sair do app" title="Sair do app (o JARVIS continua rodando no PC)">⏻</button>
          <button type="button" className="il-x" onClick={close} aria-label="Fechar a ilha" title="Fechar (Esc)">✕</button>
        </div>
        <div className="il-desk" style={{ "--z": shownZoom }}>
          <DeskApp api={api} aiName={names.ai === "J.A.R.V.I.S." ? "JARVIS" : names.ai} userName={names.user} jarvisState={estado}
            listening={false} interim="" userText={turn.userText} response={turn.response} responseCards={[]} error={turn.error}
            send={send} onToggleMic={() => {}} onClassic={openMain} onLock={lock} onOpenSettings={openMain} onOpenQr={openMain}
            onRename={rename} embedded />
        </div>
      </div>
    );
  }

  const pillText = estado === "offline" ? "JARVIS desligado"
    : estado === "speaking" ? "Falando…" : estado === "processing" ? "Pensando" : estado === "listening" ? "Ouvindo…" : names.ai;
  return (
    <button type="button" className={`il il-${estado}${mode === "resposta" ? " is-open" : ""}`} style={style}
      onClick={() => setOpen(true)} title="Clique: abre o JARVIS aqui · arraste: move · dois cliques: janela grande">
      <span className="il-row">
        <span className={`il-face${mood ? " is-poked" : ""}`} data-il-click title="Não cutuque o JARVIS… 😈"
          onClick={(e) => { e.stopPropagation(); poke(); }}>
          <RoboAvatar avatar={mood ? { ...st?.avatar, expressao: mood } : st?.avatar} tema={st?.tema} state={mood ? "idle" : face}
            size={PILL_AVATAR[st?.ilha?.tamanho] || PILL_AVATAR.media} tight still={Boolean(mood)} />
        </span>
        {playing ? (
          <span className="il-txt il-music"><b className="il-eq"><i /><i /><i /><i /></b><span>{track.title}{track.artist ? ` · ${track.artist}` : ""}</span></span>
        ) : (
          <span className="il-txt">
            <i className="il-dot" />{pillText}
            {estado === "processing" && <b className="il-think" aria-hidden="true"><i /><i /><i /></b>}
            {estado === "speaking" && <b className="il-eq" aria-hidden="true"><i /><i /><i /><i /></b>}
          </span>
        )}
        <span className="il-time">{st?.hora || ""}</span>
      </span>
      {mode === "resposta" && st?.resposta && <span className="il-reply">{st.resposta}</span>}
      {pacHint && <span className="il-reply">{pacHint}</span>}
    </button>
  );
}

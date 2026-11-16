import { useCallback, useEffect, useRef, useState } from "react";
import RoboAvatar from "./RoboAvatar.jsx";
import { api } from "../utils/api.js";
import { hexToRgb } from "../utils/desk.js";
import "../island.css";

// V8.0: a ILHA do app para Windows: pílula preta no topo da tela, sempre visível (como a "ilha" dos celulares).
// Em repouso: o avatar e a hora. Com música: a música tocando. Quando o JARVIS responde: a resposta, que some sozinha.
// V8.1.2: clicar ABRE a ilha (como a ilha dinâmica): avatar e estado, a música com ⏮ ⏯ ⏭ e a capa, a última
// resposta e os botões 🎙 FALAR e 🖥 ABRIR. Fecha ao clicar de novo, ao sair dela ou sozinha depois de alguns segundos.
// Esta página é aberta só pelo app (?ilha=1); as funções do Windows vêm do window.pywebview.api.
const AUTO_CLOSE_MS = 9000;

const pyApi = () => window.pywebview?.api || {};

export function islandMode(card, reply) {
  if (card) return "cartao";
  return reply ? "resposta" : "mini";
}

export default function IslandApp() {
  const [st, setSt] = useState(null);
  const [track, setTrack] = useState(null);
  const [card, setCard] = useState(false);
  const [lastReply, setLastReply] = useState("");
  const modeRef = useRef("");
  const closeTimer = useRef(null);

  useEffect(() => {
    document.documentElement.classList.add("is-island");
    let alive = true;
    const tick = () => api("/api/desk/island").then((d) => alive && setSt(d)).catch(() => alive && setSt((s) => s && { ...s, offline: true }));
    const music = () => api("/api/integrations/spotify/track").then((d) => alive && setTrack(d || null)).catch(() => {});
    tick();
    music();
    const a = setInterval(tick, 1200);
    const b = setInterval(music, 5000);
    return () => {
      alive = false;
      clearInterval(a);
      clearInterval(b);
    };
  }, []);

  useEffect(() => {
    if (st?.resposta) setLastReply(st.resposta);
  }, [st?.resposta]);

  const reply = Boolean(st?.resposta);
  const mode = islandMode(card, reply);
  useEffect(() => { // a janela do Windows muda de tamanho junto (centralizada, recortada em pílula)
    if (mode === modeRef.current) return;
    modeRef.current = mode;
    const p = pyApi();
    if (p.island_mode) p.island_mode(mode);
    else p.island_expand?.(mode !== "mini");
  }, [mode]);

  const armClose = useCallback(() => {
    clearTimeout(closeTimer.current);
    closeTimer.current = setTimeout(() => setCard(false), AUTO_CLOSE_MS);
  }, []);
  useEffect(() => {
    if (!card) return undefined;
    armClose();
    const blur = () => setCard(false);
    window.addEventListener("blur", blur);
    return () => {
      clearTimeout(closeTimer.current);
      window.removeEventListener("blur", blur);
    };
  }, [card, armClose]);

  const control = (action) => {
    armClose();
    api("/api/integrations/spotify/control", { method: "POST", body: JSON.stringify({ action }) })
      .then(() => setTrack((t) => (t && (action === "play" || action === "pause") ? { ...t, state: action === "play" ? "playing" : "paused" } : t)))
      .catch(() => {});
    setTimeout(() => api("/api/integrations/spotify/track").then((d) => setTrack(d || null)).catch(() => {}), 900);
  };
  const talk = () => {
    setCard(false);
    pyApi().talk?.();
  };
  const openMain = () => {
    setCard(false);
    pyApi().show_main?.();
  };

  const hasTrack = track && (track.state === "playing" || track.state === "paused") && track.title;
  const playing = hasTrack && track.state === "playing";
  const estado = st?.offline ? "offline" : st?.estado || "idle";
  const face = estado === "speaking" ? "speaking" : estado === "processing" ? "processing" : "idle";
  const stateLabel = { offline: "Desligado", speaking: "Falando…", processing: "Pensando…", listening: "Ouvindo…" }[estado] || "Pronto";
  const style = { "--il-accent": st?.cor || "#22d3ee", "--il-rgb": hexToRgb(st?.cor) };

  if (mode === "cartao") {
    return (
      <div className={`il il-${estado} is-card`} style={style} onMouseMove={armClose} role="dialog" aria-label="Ilha do JARVIS">
        <div className="il-head">
          <RoboAvatar avatar={st?.avatar} tema={st?.tema} state={face} size={40} />
          <div className="il-head-txt"><b>JARVIS</b><small><i className="il-dot" />{stateLabel}</small></div>
          <span className="il-clock">{st?.hora || ""}</span>
          <button type="button" className="il-x" onClick={() => setCard(false)} aria-label="Fechar a ilha">✕</button>
        </div>
        {hasTrack ? (
          <div className="il-player">
            {track.image ? <img src={track.image} alt="" className="il-cover" /> : <span className="il-cover is-empty">♫</span>}
            <div className="il-track"><b>{track.title}</b><small>{track.artist}</small></div>
            <div className="il-ctrl">
              <button type="button" onClick={() => control("previous")} aria-label="Música anterior">⏮</button>
              <button type="button" className="is-main" onClick={() => control(playing ? "pause" : "play")} aria-label={playing ? "Pausar" : "Tocar"}>{playing ? "⏸" : "▶"}</button>
              <button type="button" onClick={() => control("next")} aria-label="Próxima música">⏭</button>
            </div>
          </div>
        ) : (
          <p className="il-last">{lastReply || "Toque em 🎙 FALAR ou use a tecla de atalho para falar comigo."}</p>
        )}
        {hasTrack && lastReply && <p className="il-last is-small">{lastReply}</p>}
        <div className="il-actions">
          <button type="button" className="is-main" onClick={talk}>🎙 FALAR</button>
          <button type="button" onClick={openMain}>🖥 ABRIR JARVIS</button>
        </div>
      </div>
    );
  }

  return (
    <button type="button" className={`il il-${estado}${mode === "resposta" ? " is-open" : ""}`} style={style}
      onClick={() => setCard(true)} title="Abrir a ilha do JARVIS">
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

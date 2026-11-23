import { useCallback, useEffect, useRef, useState } from "react";
import RoboAvatar from "./RoboAvatar.jsx";
import ProgressBar from "./ProgressBar.jsx";
import LockCards from "./LockCards.jsx";
import { FaceCircle } from "./LockOrbe.jsx";
import useNow from "../hooks/useNow.js";
import { hexToRgb } from "../utils/desk.js";
import { startPacman, usePoke } from "../utils/poke.js";
import { deskBubble, deskFace, haloTone } from "../utils/deskLockState.js";
import DeskLockBg, { BG_EVENT, LOCK_BGS, readBg, saveBg } from "./DeskLockBg.jsx";
import "../desk.css";

// V8.8.0 (ideia 11): BLOQUEIO DO MODO DESK, com o robô JARVIS no centro. O DESBLOQUEIO é o mesmo de sempre
// (rosto ou PIN): esta tela só recebe os botões prontos do LockScreen.
// V8.16: só o avatar do JARVIS — sem Tamagotchi, jogo das estrelas nem atividades automáticas (eram muitos timers e
// animações) — e com as MESMAS FUNÇÕES do bloqueio clássico (estilo Orbe): cartões (relógio, clima, música, jogo do
// time, água), microfone e Sentinela com a legenda do que ele ouviu, palmas, painel do Modo Torcedor e o ⚙ GERENCIAR
// com os atalhos de sempre. A expressão e o anel de luz seguem o estado de verdade (ouvindo, falando, pensando,
// liberado, falhou, dormindo à noite). Com a tela bloqueada, ela só lê /api/desk/lockface (aparência e CONTAGENS).

const PHRASES = [
  "Estou de olho em tudo por aqui, senhor. 👀",
  "Pode ir tranquilo: guardo o PC enquanto isso.",
  "Que tal uma pausa para um copo d'água? 💧",
  "Quando voltar, é só olhar para a câmera.",
  "Clique em mim… se tiver coragem. 😏",
];

/** As falas do balão, a partir do que a tela bloqueada pode mostrar (só contagens, nada pessoal). */
export function bubbleLines(face, weather, now = new Date()) {
  const lines = [];
  const hour = now.getHours();
  const hi = hour < 5 ? "Boa noite" : hour < 12 ? "Bom dia" : hour < 18 ? "Boa tarde" : "Boa noite";
  lines.push(`${hi}! Agora são ${String(hour).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}.`);
  if (weather && Number.isFinite(weather.temperature)) {
    lines.push(`Lá fora: ${weather.temperature}° e ${weather.description}${weather.rain_probability != null ? ` (chuva ${weather.rain_probability}%)` : ""}.`);
  }
  if (face) {
    if (face.proximo_lembrete) lines.push(`Você tem ${face.lembretes_hoje} ${face.lembretes_hoje === 1 ? "lembrete" : "lembretes"} hoje; o próximo é às ${face.proximo_lembrete}. ⏰`);
    if (face.tarefas > 0) lines.push(`${face.tarefas} ${face.tarefas === 1 ? "tarefa pendente" : "tarefas pendentes"} esperando você. ☰`);
    else lines.push("Nenhuma tarefa pendente. Missão cumprida! 🎉");
    if (face.ofensiva > 0) lines.push(`Ofensiva de ${face.ofensiva} ${face.ofensiva === 1 ? "dia" : "dias"}! Não deixe apagar. 🔥`);
  }
  return [...lines, ...PHRASES];
}

export default function DeskLock({ api, phase, name, message, photoUrl, scan, pinBlock, mainLabel, onMain, mainVisible = true,
  failedActions = null, phoneButtons = null, jarvisState = "idle", onClassic = null, hint = "", stateHint = "", phone = false,
  listening = false, caption = "", cards = null, cardsList = [], fanPanelNode = null, mic = null, clapNode = null, clapPulse = 0,
  stampNode = null, hubActions = null, styleToggle = null, onChangePhoto = null,
  onUpdate = null, updateCount = 0, updateNote = "", updateProgress = null }) {
  const now = useNow(true);
  const [face, setFace] = useState(null);
  const [line, setLine] = useState(0);
  const [reaction, setReaction] = useState(null);
  const [hub, setHub] = useState(false);
  const [bg, setBg] = useState(readBg);
  const reactTimer = useRef(0);
  const react = useCallback((expr, ms = 1600) => {
    clearTimeout(reactTimer.current);
    setReaction(expr);
    reactTimer.current = setTimeout(() => setReaction(null), ms);
  }, []);
  useEffect(() => () => clearTimeout(reactTimer.current), []);
  const { mood, poke } = usePoke(() => { if (!startPacman()) react("bravo", 2500); });
  const [hintShown, setHintShown] = useState(Boolean(hint)); // V8.8.1: no celular, a 1ª fala explica como entrar
  useEffect(() => {
    if (!hint) return undefined;
    setHintShown(true);
    const t = setTimeout(() => setHintShown(false), 9000);
    return () => clearTimeout(t);
  }, [hint]);

  // aparência do robô e as contagens do dia (a cada minuto; nada pessoal)
  useEffect(() => {
    if (!api) return undefined;
    let alive = true;
    const load = () => { if (!document.hidden) api("/api/desk/lockface").then((d) => alive && setFace(d)).catch(() => {}); };
    load();
    const t = setInterval(load, 60000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [api]);
  useEffect(() => {
    const on = (e) => setBg(e.detail || readBg());
    window.addEventListener(BG_EVENT, on);
    return () => window.removeEventListener(BG_EVENT, on);
  }, []);
  useEffect(() => {
    const t = setInterval(() => { if (!document.hidden) setLine((n) => n + 1); }, 7000);
    return () => clearInterval(t);
  }, []);
  useEffect(() => { // Esc fecha o GERENCIAR (antes do Esc da tela)
    if (!hub) return undefined;
    const onKey = (e) => { if (e.key === "Escape") { e.stopPropagation(); setHub(false); } };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [hub]);

  const hour = now.getHours();
  const scanning = phase === "scanning";
  const showFace = Boolean(scan) || scanning || (phase === "verified" && Boolean(photoUrl));
  const { expr, state } = deskFace({ phase, listening, jarvisState, hour, mood, reaction });
  const tone = haloTone({ phase, listening, jarvisState, hour });
  const lines = bubbleLines(face, null, now);
  const say = deskBubble({ phase, name, message, caption, listening, hint, hintShown, hour, mood }) || lines[line % lines.length];
  const showCards = !pinBlock && phase !== "scanning" && cardsList.length > 0;
  const accent = face?.cor || "#22d3ee";
  const clickRobot = (e) => {
    e.stopPropagation();
    poke();
    if (!mood) react(Math.random() < 0.5 ? "feliz" : "rindo");
  };

  return (
    <div className={`dkl dkl-v2${phone ? " is-phone" : ""}${bg !== "escuro" ? ` has-bg bg-${bg}` : ""} is-${tone}`} role="main"
      style={{ "--dk-accent": accent, "--dk-accent-rgb": hexToRgb(accent) }}>
      <DeskLockBg bg={bg} />
      <div className="dkl-glow" aria-hidden="true" />
      <header className="dkl-top">
        <div className="dkl-clock">{now.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</div>
        <div className="dkl-date">{now.toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" })}</div>
      </header>
      <button type="button" className={`dkl-hub-btn${hub ? " is-on" : ""}`} onClick={(e) => { e.stopPropagation(); setHub((v) => !v); }} aria-expanded={hub}>
        ⚙ GERENCIAR{updateCount > 0 && <span className="upd-badge" aria-label={`${updateCount} atualizações disponíveis`}>{updateCount}</span>}
      </button>

      {fanPanelNode}

      {pinBlock ? <div className="dkl-pin">{pinBlock}</div> : (
        <div className="dkl-stage">
          {showFace ? (
            <div className="dkl-face"><FaceCircle scan={scan} phase={phase} photoUrl={photoUrl} /></div>
          ) : (
            <div className={`dkl-avatar${clapPulse ? " is-clap" : ""}`} key={`clap-${clapPulse}`}>
              <i className="dkl-halo" aria-hidden="true" />
              <button type="button" className={`dkl-robot${mood ? " is-poked" : ""}`} onClick={clickRobot} aria-label={`${face?.nome || "JARVIS"}: clique para interagir`}>
                <RoboAvatar avatar={expr ? { ...(face?.avatar || {}), expressao: expr } : face?.avatar} tema={face?.tema}
                  state={expr ? "idle" : state} size={phone ? 200 : 250} still={Boolean(expr)} />
              </button>
            </div>
          )}
          <p className="dkl-bubble" key={say} aria-live="polite">{say}</p>
        </div>
      )}

      <footer className="dkl-actions">
        {showCards && <div className="dkl-cards"><LockCards api={cards?.api} cards={cardsList} fanModeEnabled={cards?.fanModeEnabled} layout="strip" /></div>}
        {mainVisible && !pinBlock && phase !== "scanning" && !phoneButtons && (
          <button type="button" className="dkl-main" onClick={(e) => { e.stopPropagation(); onMain(); }}>
            {phase === "verified" ? "➜" : phase === "failed" ? "⟳" : "🙂"} {mainLabel}
            {!phone && <span className="dkl-key">ESPAÇO</span>}
          </button>
        )}
        {phoneButtons}
        {failedActions}
        {stateHint && !pinBlock && <p className="dkl-hint">{stateHint}</p>}
        {updateProgress != null && <div className="dkl-update"><ProgressBar pct={updateProgress} label="Atualizando o app" /></div>}
        {updateNote && <p className="dkl-update-note" role="status">{updateNote}</p>}
      </footer>

      {(mic || clapNode) && (
        <div className="dkl-side">
          {mic && (
            <button type="button" className={`lo-mic ${mic.muted ? "" : "on"}`} onClick={(e) => { e.stopPropagation(); mic.onToggle(); }} aria-pressed={!mic.muted}
              title={mic.muted ? "Ligar o microfone (palmas e escuta)" : "Silenciar o microfone"}>
              <i /> {mic.muted ? "MIC SILENCIADO" : "MIC LIGADO"} <kbd>P</kbd>
            </button>
          )}
          {clapNode}
        </div>
      )}

      {hub && (
        <div className="dkl-hub" role="dialog" aria-label="Gerenciar" onClick={(e) => e.stopPropagation()}>
          <header>
            <strong>⚙ GERENCIAR</strong>
            <button type="button" onClick={() => setHub(false)} aria-label="Fechar">✕</button>
          </header>
          {hubActions}
          <div className="dkl-hub-row">
            {onClassic && <button type="button" className="ls-chip" onClick={onClassic}>◐ BLOQUEIO CLÁSSICO</button>}
            {styleToggle}
            {!phone && onChangePhoto && <button type="button" className="ls-chip" onClick={onChangePhoto}>⚙ ALTERAR FOTO DO ROSTO</button>}
            {!hubActions && onUpdate && <button type="button" className="ls-chip" onClick={onUpdate}>⟳ ATUALIZAR</button>}
          </div>
          <div className="dkl-bgpick" role="radiogroup" aria-label="Papel de parede do bloqueio">
            {LOCK_BGS.map((b) => (
              <button type="button" key={b.id} role="radio" aria-checked={bg === b.id} className={`dkl-swatch sw-${b.id}${bg === b.id ? " is-on" : ""}`}
                onClick={() => setBg(saveBg(b.id))}>
                <span aria-hidden="true">{b.emoji}</span>{b.label}
              </button>
            ))}
          </div>
          {stampNode}
        </div>
      )}
    </div>
  );
}

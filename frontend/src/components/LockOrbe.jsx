import { useEffect, useMemo, useState } from "react";
import TangleOrb from "./TangleOrb.jsx";
import LockCards from "./LockCards.jsx";
import { similarityPct } from "./FaceScanOverlay.jsx";
import { APP_VERSION } from "../utils/version.js";
import "../lock-orbe.css";
import { orbeLabel } from "../utils/lockOrbe.js";

// V7.12: tela de bloqueio estilo ORBE (igual ao vídeo do Patrick): grade azul, o orbe de linhas entrelaçadas no
// centro, o estado em cima (EM ESPERA, OUVINDO, FALANDO…), o rosto aparece DENTRO do orbe durante a identificação
// e os cartões passam numa faixa. Todas as funções do bloqueio continuam: ficam no ⚙ GERENCIAR HUB.

function FaceCircle({ scan, phase, photoUrl }) {
  const pct = scan ? similarityPct(scan.score, scan.threshold) : 0;
  const verified = phase === "verified";
  const img = scan?.frame ? `data:image/jpeg;base64,${scan.frame}` : verified ? photoUrl : null;
  if (!img && phase !== "scanning") return null;
  return (
    <div className={`lo-face${verified ? " is-ok" : ""}${phase === "failed" ? " is-fail" : ""}`}>
      <small className="lo-face-top">◉ IDENTIFICAÇÃO BIOMÉTRICA — LOCAL</small>
      <div className="lo-face-ring" style={{ "--pct": verified ? 100 : pct }}>
        <div className="lo-face-img">
          {img ? <img src={img} alt="Câmera da identificação facial" /> : <span className="lo-face-wait">◌</span>}
          {!verified && <i className="lo-face-mesh" aria-hidden="true" />}
          {!verified && <i className="lo-face-scan" aria-hidden="true" />}
          <b className="tl" /><b className="tr" /><b className="bl" /><b className="br" />
        </div>
      </div>
      <small className="lo-face-bottom" aria-live="polite">{verified ? "IDENTIDADE CONFIRMADA" : `ESCANEANDO · ${pct}%`}</small>
    </div>
  );
}

export default function LockOrbe({
  phase, name, photoUrl, message, jarvisState, hint, caption, listening, liveScan, pinBlock,
  mainLabel, onMain, mainVisible = true, phoneButtons = null, failedActions = null, hubActions, cards, cardsList, fanPanelNode = null,
  mic = null, clapNode = null, stampNode = null, phoneApp = false, onChangePhoto, styleToggle,
}) {
  const [hub, setHub] = useState(false);
  const lite = useMemo(() => {
    try {
      return window.matchMedia("(max-width: 760px)").matches;
    } catch {
      return false;
    }
  }, []);
  const label = orbeLabel({ phase, jarvisState, listening });
  const tone = phase === "verified" ? "ok" : phase === "failed" ? "fail" : "default";
  const orbState = phase === "scanning" || jarvisState === "processing" ? "processing" : jarvisState === "speaking" ? "speaking" : listening ? "listening" : "idle";

  useEffect(() => {
    if (!hub) return undefined;
    const onKey = (e) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        setHub(false);
      }
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [hub]);

  const showCards = phase !== "scanning" && phase !== "pin";

  return (
    <div role="main" tabIndex={0} className={`ls-container lo-root lo-${tone} lo-${orbState}`}>
      <nav className="lo-top" aria-label="Atalhos do bloqueio">
        <span>◉ PERSONALIZADO{name ? ` · ${name.toUpperCase()}` : ""}</span>
        <span>⟳ SINCRONIZADO · v{APP_VERSION}</span>
        <button type="button" onClick={(e) => { e.stopPropagation(); setHub((v) => !v); }} aria-expanded={hub}>⚙ GERENCIAR HUB</button>
      </nav>

      <div className="lo-state" aria-live="polite">
        <b>{label}</b>
        <i className="lo-state-dots" aria-hidden="true" />
        {caption && <p className="lo-caption">{caption}</p>}
      </div>

      {fanPanelNode}

      {pinBlock || (
        <div className="lo-orb">
          <TangleOrb state={orbState} tone={tone} lite={lite} />
          <FaceCircle scan={liveScan?.frame ? liveScan : null} phase={phase} photoUrl={photoUrl} />
        </div>
      )}

      <div className="lo-dock">
        {showCards && <LockCards api={cards?.api} cards={cardsList} fanModeEnabled={cards?.fanModeEnabled} layout="strip" />}
        <div className="lo-bottom">
          {phase === "failed" && message && <p className="lo-msg" role="alert" title={message}>{message}</p>}
          {failedActions}
          {phoneButtons}
          {mainVisible && phase !== "pin" && phase !== "scanning" && !phoneButtons && (
            <button type="button" className="lo-main" onClick={(e) => { e.stopPropagation(); onMain(); }} aria-label={mainLabel} title={mainLabel}>
              <span aria-hidden="true">{phase === "verified" ? "➜" : phase === "failed" ? "⟳" : "◉"}</span>
            </button>
          )}
          <p className="lo-hint">{hint}{!phoneApp && phase !== "pin" && <kbd>ESPAÇO</kbd>}</p>
        </div>
      </div>

      <div className="lo-side">
        {mic && (
          <button type="button" className={`lo-mic ${mic.muted ? "" : "on"}`} onClick={(e) => { e.stopPropagation(); mic.onToggle(); }} aria-pressed={!mic.muted}
            title={mic.muted ? "Ligar o microfone (palmas e escuta)" : "Silenciar o microfone"}>
            <i /> {mic.muted ? "MIC SILENCIADO" : "MIC LIGADO"} <kbd>P</kbd>
          </button>
        )}
        {clapNode}
      </div>

      {hub && (
        <div className="lo-hub" role="dialog" aria-label="Gerenciar hub" onClick={(e) => e.stopPropagation()}>
          <header>
            <strong>⚙ GERENCIAR HUB</strong>
            <button type="button" onClick={() => setHub(false)} aria-label="Fechar">✕</button>
          </header>
          {hubActions}
          <div className="lo-hub-row">
            {styleToggle}
            {!phoneApp && onChangePhoto && <button type="button" className="ls-chip" onClick={onChangePhoto}>⚙ ALTERAR FOTO DO ROSTO</button>}
          </div>
          {stampNode}
        </div>
      )}
    </div>
  );
}

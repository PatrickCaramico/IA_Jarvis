import { useEffect } from "react";
import ArcReactorHUD from "./ArcReactorHUD.jsx";
import { FaceScanStatus } from "./FaceScanOverlay.jsx";
import LockCards from "./LockCards.jsx";
import ProgressBar from "./ProgressBar.jsx";
import PinPad from "./PinPad.jsx";
import { soundManager } from "../utils/soundEffects.js";
import { CLAP_STATUS_TEXT } from "../hooks/useClapDetector.js";
import useNow from "../hooks/useNow.js";
import { APP_VERSION } from "../utils/version.js";
import FanLockPanel from "./FanLockPanel.jsx";
import MobileAppQr from "./MobileAppQr.jsx";

// Tela inicial biométrica do J.A.R.V.I.S.
// phase: "ready" | "scanning" | "verified" | "failed" | "pin"
// Dois layouts: clássico (padrão, igual ao anterior quando tudo está desligado) e Sentinela.

function ClapIndicator({ clap }) {
  if (!clap?.enabled || clap.status === "off") return null;
  const listening = clap.status === "listening";
  const bars = [0.15, 0.3, 0.5, 0.7, 0.9];
  const lvl = Math.min(1, (clap.level || 0) * 6);
  return (
    <div className={`ls-clap ${clap.pulse ? "is-pulse" : ""}`} key={clap.pulse} role="status" aria-live="polite">
      <span className="ls-clap-bars" aria-hidden="true">
        {bars.map((b) => <span key={b} className={listening && lvl >= b ? "on" : ""} />)}
      </span>
      <span>
        {clap.needsGesture ? "Clique uma vez na tela para ativar as palmas" : listening ? "OUVINDO PALMAS" : CLAP_STATUS_TEXT[clap.status] || ""}
      </span>
    </div>
  );
}

// V4.4: botão do Modo Torcedor no bloqueio (ao lado do carimbo). fan: { enabled, busy, onToggle }
function FanToggle({ fan }) {
  if (!fan?.onToggle) return null;
  const on = Boolean(fan.enabled);
  return (
    <button
      type="button"
      className={`bp-fan-btn ${on ? "is-on" : ""} ${fan.error ? "is-error" : ""}`}
      onClick={(e) => { e.stopPropagation(); e.currentTarget.blur(); fan.onToggle(); }}
      disabled={fan.busy}
      aria-pressed={on}
      title={on ? "Desligar o Modo Torcedor" : "Ligar o Modo Torcedor"}
    >
      <span className="bp-fan-ball" aria-hidden="true">⚽</span>
      <span className="bp-fan-txt">
        <b>MODO TORCEDOR</b>
        <small role={fan.error ? "alert" : undefined}>{fan.busy ? "..." : fan.error || (on ? "LIGADO" : "DESLIGADO")}</small>
      </span>
      <span className="bp-fan-dot" aria-hidden="true" />
    </button>
  );
}

// V5.9.1: botão de fundo no bloqueio. Cada toque passa para o próximo: Blueprint -> Universo -> Clássico.
const BG_LABEL = { blueprint: "BLUEPRINT", space: "UNIVERSO", classic: "CLÁSSICO" };
const BG_ICON = { blueprint: "▦", space: "✦", classic: "◐" };
function BgToggle({ bg }) {
  if (!bg?.onCycle) return null;
  const value = BG_LABEL[bg.value] ? bg.value : "blueprint";
  return (
    <button
      type="button"
      className={`bp-fan-btn bp-bg-btn is-${value}`}
      onClick={(e) => { e.stopPropagation(); e.currentTarget.blur(); bg.onCycle(); }}
      title="Trocar o fundo (Blueprint, Universo, Clássico)"
      aria-label={`Fundo: ${BG_LABEL[value]}. Tocar para trocar`}
    >
      <span className="bp-fan-ball bp-bg-icon" aria-hidden="true">{BG_ICON[value]}</span>
      <span className="bp-fan-txt">
        <b>FUNDO</b>
        <small>{BG_LABEL[value]}</small>
      </span>
    </button>
  );
}

// V6.5.8: botão ÁUDIO (microfone e saída de áudio), ao lado do FUNDO
function AudioToggle({ audio }) {
  if (!audio?.onOpen) return null;
  return (
    <button
      type="button"
      className="bp-fan-btn bp-audio-btn"
      onClick={(e) => { e.stopPropagation(); e.currentTarget.blur(); audio.onOpen(); }}
      title="Microfone e saída de áudio"
      aria-label="Áudio: microfone e saída de som"
    >
      <span className="bp-fan-ball bp-bg-icon" aria-hidden="true">🎧</span>
      <span className="bp-fan-txt">
        <b>ÁUDIO</b>
        <small>MIC · SAÍDA</small>
      </span>
    </button>
  );
}

// V4.4: carimbo de planta técnica (só aparece com o fundo blueprint; ver blueprint.css).
// O canto também leva o botão do Modo Torcedor e (V5.9.1) o do fundo, que aparecem em todos os fundos.
export function BlueprintStamp({ sheet = "BLOQUEIO", fan = null, bg = null, audio = null }) {
  return (
    <div className="bp-corner">
      <AudioToggle audio={audio} />
      <BgToggle bg={bg} />
      <FanToggle fan={fan} />
      <div className="bp-stamp" aria-hidden="true">
        <span className="bp-stamp-title">J.A.R.V.I.S.</span>
        <span>FOLHA · {sheet}</span>
        <span>REV. v{APP_VERSION}</span>
      </div>
    </div>
  );
}

function useClock(active) {
  return useNow(active); // relógio central (hooks/useNow.js)
}

export default function LockScreen({
  photoUrl,
  phase,
  name,
  message,
  jarvisState,
  onContinue,
  onChangePhoto,
  liveScan = null,
  clap = null,
  cards = null,
  hasPin = false,
  failCount = 0,
  onUsePin,
  pin = null,
  guestEnabled = false,
  onGuest,
  sentinel = null,
  mic = null, // V4.2.2: { muted, onToggle } — microfone da tela de bloqueio (escuta e palmas)
  introSound = "default",
  silent = false,
  fanToggle = null, // V4.4: { enabled, busy, onToggle } — botão do Modo Torcedor ao lado do carimbo
  bgToggle = null, // V5.9.1: { value, onCycle } — botão de fundo ao lado do Modo Torcedor
  audioToggle = null, // V6.5.8: { onOpen } — botão ÁUDIO (microfone e saída) ao lado do fundo
  onBiometric = null, // V6.0: no app com a digital ativada, "ENTRAR COM A DIGITAL"
  onNewProfile = null, // V4.5: "＋ NOVA PESSOA" (perfil próprio: rosto, PIN e preferências)
  onUpdate = null, // botão ATUALIZAR: no PC baixa a versão nova e reinicia; no app, atualiza o app (V5.7.1)
  updateCount = 0, // V6.7.2: versões novas esperando (bolinha com o número no botão)
  updateNote = "", // V5.7.1: resposta do ATUALIZAR APP ("O app já está na versão mais nova…")
  updateProgress = null, // V6.1: 0–100 enquanto o app baixa a versão nova
  phoneApp = false, // V4.5: dentro do app do celular (o rosto usaria a webcam do PC: entra pelo PIN)
}) {
  const scanning = phase === "scanning";
  const orbState = scanning ? "processing" : phase === "ready" || phase === "pin" ? "idle" : jarvisState;
  const tone = phase === "verified" ? "ok" : phase === "failed" ? "fail" : "default";
  const liveFrame = scanning && liveScan?.frame ? liveScan : null;
  const sentinelOn = Boolean(sentinel?.enabled);
  const now = useClock(sentinelOn && sentinel?.showClock);

  useEffect(() => {
    if (silent) return;
    if (phase === "verified") {
      if (introSound === "off") return;
      if (introSound === "custom") {
        // Som do usuário em frontend/public/sounds/intro.mp3 (cai no padrão se não existir)
        const audio = new Audio(`${import.meta.env.BASE_URL}sounds/intro.mp3`);
        audio.play().catch(() => soundManager.playSuccess());
      } else {
        soundManager.playSuccess();
      }
    } else if (phase === "failed") {
      soundManager.playAlert();
    }
  }, [phase, introSound, silent]);

  const handleBtnClick = () => {
    soundManager.playClick();
    onContinue();
  };

  const clapHint = clap?.enabled && clap.status === "listening";
  const showPinButton = hasPin && phase === "failed";
  // V4.4: no Modo Torcedor o painel do jogo ocupa a coluna da esquerda e substitui o cartão "próximo jogo"
  const fanPanel = Boolean(cards?.fanModeEnabled && cards?.api);
  const cardsList = (cards?.list || []).filter((c) => !(fanPanel && c === "fan_match"));

  // ---------------------------------------------------------------- PIN
  const pinBlock = phase === "pin" && pin ? (
    <PinPad onSubmit={pin.onSubmit} onCancel={pin.onCancel} busy={pin.busy} message={pin.message} lockedUntil={pin.lockedUntil}
      onForgot={pin.onForgot} title={pin.title} />
  ) : null;

  const phoneEntry = phoneApp && (phase === "ready" || phase === "failed");
  const phoneHint = hasPin
    ? (onBiometric ? "Encoste o dedo ou use o PIN" : "Toque em ENTRAR COM PIN")
    : "Para entrar pelo celular, crie um PIN no PC (Configurações › Bloqueio)";
  const phonePinButton = phoneEntry && hasPin ? (
    <>
      {/* V6.0: digital ativada no app: botão principal; o PIN continua como alternativa */}
      {onBiometric && (
        <button type="button" onClick={(e) => { e.stopPropagation(); onBiometric(); }} className="ls-chip is-strong ls-phone-pin">👆 ENTRAR COM A DIGITAL</button>
      )}
      <button type="button" onClick={handleBtnClick} className={`ls-chip ${onBiometric ? "" : "is-strong "}ls-phone-pin`}>🔑 ENTRAR COM PIN</button>
    </>
  ) : null;

  // Verificação rápida falhou: pode ser alguém novo. O convite para criar perfil fica em destaque.
  const unknownFace = Boolean(onNewProfile) && phase === "failed" && !phoneApp;
  const secondaryActions = (
    <>
    {unknownFace && (
      <p className="ls-hint ls-new-hint" role="status">
        Não reconheci você. Se é a sua primeira vez aqui, crie o seu perfil; se já tem perfil, tente de novo com o rosto de frente para a câmera ou use o PIN.
      </p>
    )}
    <div className="ls-secondary">
      {showPinButton && !phoneApp && (
        <button type="button" className={`ls-chip ${failCount >= 2 ? "is-strong" : ""}`} onClick={onUsePin}>
          ⌨ USAR PIN
        </button>
      )}
      {guestEnabled && phase !== "scanning" && phase !== "verified" && (
        <button type="button" className="ls-chip" onClick={onGuest}>👤 MODO VISITANTE</button>
      )}
      {onNewProfile && (phase === "ready" || phase === "failed") && (
        <button type="button" className={`ls-chip ${unknownFace ? "is-strong" : ""}`} onClick={(e) => { e.stopPropagation(); onNewProfile(); }}
          title="Criar o perfil de uma pessoa nova neste PC">
          {unknownFace ? "＋ SOU NOVO: CRIAR PERFIL" : "＋ NOVA PESSOA"}
        </button>
      )}
      {onUpdate && (phase === "ready" || phase === "failed") && (
        <button type="button" className="ls-chip" onClick={(e) => { e.stopPropagation(); onUpdate(); }}
          title={phoneApp ? "Procurar e instalar a versão nova do app" : "Baixar a versão mais nova do JARVIS e reiniciar"}>
          {phoneApp ? "⟳ ATUALIZAR APP" : "⟳ ATUALIZAR"}
          {!phoneApp && updateCount > 0 && (
            <span className="upd-badge" aria-label={`${updateCount} ${updateCount === 1 ? "atualização disponível" : "atualizações disponíveis"}`}>{updateCount}</span>
          )}
        </button>
      )}
      {(phase === "ready" || phase === "failed") && (
        <>
          <button type="button" className="ls-chip" onClick={(e) => { e.stopPropagation(); window.dispatchEvent(new CustomEvent("jarvis-open-branding")); }}
            title="Identidade visual do JARVIS">📘 BRANDING</button>
          <button type="button" className="ls-chip" onClick={(e) => { e.stopPropagation(); window.dispatchEvent(new CustomEvent("jarvis-open-optimizer")); }}
            title="Medir e deixar o JARVIS mais rápido neste aparelho">⚡ OTIMIZAR</button>
          <button type="button" className="ls-chip" onClick={(e) => { e.stopPropagation(); window.dispatchEvent(new CustomEvent("jarvis-open-notes")); }}
            title="O que mudou em cada versão">📝 NOTAS</button>
          <button type="button" className="ls-chip" onClick={(e) => { e.stopPropagation(); window.dispatchEvent(new CustomEvent("jarvis-open-diagnostic")); }}
            title="Testar IA, voz, internet, microfone e câmera">🩺 DIAGNÓSTICO</button>
        </>
      )}
      {updateProgress != null && (
        <div className="ls-update-progress"><ProgressBar pct={updateProgress} label="Atualizando o app" /></div>
      )}
      {updateNote && <p className="ls-update-note" role="status">{updateNote}</p>}
    </div>
    </>
  );

  // ---------------------------------------------------------------- Sentinela
  if (sentinelOn) {
    const st = sentinel.state || "sleeping";
    const hour = now.getHours();
    const night = sentinel.nightDim && (hour >= 22 || hour < 7);
    const title = phase === "scanning"
      ? "ESCANEANDO BIOMETRIA FACIAL"
      : phase === "verified"
        ? `ACESSO AUTORIZADO${name ? `, ${name.toUpperCase()}` : ""}`
        : phase === "failed"
          ? "ACESSO NEGADO"
          : phase === "pin"
            ? "LIBERAÇÃO POR PIN"
            : st === "unlock"
              ? "CENTRAL BLOQUEADA · ESCANEAMENTO NECESSÁRIO"
              : st === "awake" || st === "listening"
                ? "ESTOU OUVINDO"
                : "MODO BLOQUEIO";
    const wake = sentinel.wakeLabel || "Jarvis";
    const caption = sentinel.caption || "";
    const sub = phoneEntry
      ? (phase === "failed" && message ? message : phoneHint)
      : phase === "verified"
      ? (sentinel.autoEntering ? "Abrindo a central..." : phoneApp ? "Toque em ENTRAR" : "Pressione espaço para entrar")
      : phase === "failed"
        ? (message || "Rosto não reconhecido.")
        : sentinel.micStatus === "listening"
          ? `Diga "abrir central" ou "${wake}, …"`
          : sentinel.micStatus === "blocked"
            ? "Microfone bloqueado: libere no cadeado do navegador"
            : sentinel.micStatus === "insecure"
              ? "Escuta indisponível nesta conexão (use localhost)"
              : sentinel.muted
                ? "Escuta silenciada"
                : "Clique ou pressione espaço para armar a sentinela";
    const orbSentinelState = scanning ? "processing" : st === "awake" || st === "listening" || jarvisState === "speaking" ? "speaking" : orbState;

    return (
      <div role="main" tabIndex={0} className={`ls-container ls-sentinel snt-${st} ${night ? "is-night" : ""}`}>
        <div className="ls-bracket ls-bracket-tl" aria-hidden="true" />
        <div className="ls-bracket ls-bracket-tr" aria-hidden="true" />
        <div className="ls-bracket ls-bracket-bl" aria-hidden="true" />
        <div className="ls-bracket ls-bracket-br" aria-hidden="true" />

        {fanPanel && phase !== "scanning" && phase !== "pin" && (
          <FanLockPanel api={cards.api} refreshKey={cards.fanRefresh} />
        )}
        {sentinel.showClock && (
          <div className="snt-clock-wrap">
            <div className="snt-clock">{now.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</div>
            <div className="snt-date">{now.toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" })}</div>
          </div>
        )}

        {pinBlock || (
          <div className={`ls-orb-wrapper snt-orb ${clap?.pulse ? "is-clap-pulse" : ""}`} key={`orb-${clap?.pulse || 0}`}>
            <div className={`ls-hud-ring${scanning ? " is-scanning" : ""}`} />
            <ArcReactorHUD state={orbSentinelState} photoUrl={photoUrl} tone={tone} liveFrame={liveFrame} className="snt-hud" />
          </div>
        )}

        <div className="ls-status-box">
          <div className={`ls-title snt-title ${phase === "failed" ? "is-failed" : phase === "verified" ? "is-verified" : st === "unlock" ? "is-amber" : ""}`}>
            {title}
          </div>
          <div className="ls-hint">{sub}</div>
          {(caption || sentinel.interim) && phase !== "scanning" && (
            <div className="snt-caption" aria-live="polite">{sentinel.interim || caption}</div>
          )}
          {scanning && <FaceScanStatus scan={liveScan} />}
        </div>

        {phase === "verified" && !sentinel.autoEntering && (
          <button type="button" onClick={handleBtnClick} className="ls-chip is-strong">ENTRAR <span className="ls-key-badge">ESPAÇO</span></button>
        )}
        {phase === "failed" && !phoneApp && (
          <button type="button" onClick={handleBtnClick} className="ls-chip">TENTAR NOVAMENTE <span className="ls-key-badge">ESPAÇO</span></button>
        )}
        {phonePinButton}
        {phase !== "pin" && secondaryActions}

        {phase !== "scanning" && phase !== "pin" && (
          <LockCards api={cards?.api} cards={sentinel.showClock ? cardsList.filter((c) => c !== "clock") : cardsList}
            fanModeEnabled={cards?.fanModeEnabled} allRight={fanPanel} />
        )}

        {!phoneApp && (
          <div className="snt-footer">
            <button
              type="button"
              className={`snt-mic ${sentinel.micStatus === "listening" && !sentinel.muted ? "on" : ""}`}
              onClick={(e) => { e.stopPropagation(); sentinel.onToggleMute?.(); }}
              title={sentinel.muted ? "Reativar a escuta" : "Silenciar a escuta (privacidade)"}
            >
              <span className="dot" /> {sentinel.muted ? "MIC SILENCIADO" : sentinel.micStatus === "listening" ? "MIC ATIVO" : "MIC INATIVO"}
              <span className="ls-key-badge">P</span>
            </button>
            <ClapIndicator clap={clap} />
            <span className="snt-key">{phase === "ready" ? "ESPAÇO = LIBERAR" : ""}</span>
          </div>
        )}

        {phase !== "scanning" && phase !== "pin" && !phoneApp && (
          <button type="button" className="snt-photo-link" onClick={(e) => { e.stopPropagation(); onChangePhoto(); }}>
            alterar foto
          </button>
        )}
        {phase !== "scanning" && phase !== "pin" ? <BlueprintStamp sheet="SENTINELA" fan={fanToggle} bg={bgToggle} audio={audioToggle} /> : <BlueprintStamp sheet="SENTINELA" />}
        {/* V4.5: QR pequeno para baixar o app Android (só no modo rede) */}
        {cards?.api && phase !== "scanning" && phase !== "pin" && !phoneApp && <MobileAppQr api={cards.api} />}
      </div>
    );
  }

  // ---------------------------------------------------------------- Clássico
  const title =
    phase === "ready"
      ? "JARVIS EM ESPERA"
      : phase === "scanning"
      ? "ESCANEANDO BIOMETRIA FACIAL"
      : phase === "verified"
      ? `ACESSO AUTORIZADO${name ? `, ${name.toUpperCase()}` : ""}`
      : phase === "pin"
      ? "LIBERAÇÃO POR PIN"
      : message ? message.toUpperCase() : "ACESSO NÃO RECONHECIDO";

  const hint = phoneEntry
    ? (phase === "failed" && message ? message : phoneHint)
    : phase === "ready"
      ? clapHint ? "Pressione espaço, clique ou bata palmas 2x para ativar" : "Pressione a barra de espaço ou clique para ativar"
      : phase === "verified"
      ? (clap?.autoEntering ? "Entrando na central de comando..." : "Pressione espaço para entrar na central de comando")
      : phase === "failed"
      ? clapHint ? "Pressione espaço ou bata palmas 2x para tentar de novo" : "Pressione espaço para tentar novo escaneamento"
      : phase === "pin"
      ? "Digite o PIN no teclado ou na tela"
      : "Centralize seu rosto na câmera do sensor";

  return (
    <div
      role="main"
      tabIndex={0}
      className="ls-container"
    >
      {/* Cantos Táticos do HUD */}
      <div className="ls-bracket ls-bracket-tl" aria-hidden="true" />
      <div className="ls-bracket ls-bracket-tr" aria-hidden="true" />
      <div className="ls-bracket ls-bracket-bl" aria-hidden="true" />
      <div className="ls-bracket ls-bracket-br" aria-hidden="true" />

      {/* Marca / Header */}
      <header className="ls-header">
        <div className="ls-status-pill">
          <span className="ls-dot" />
          <span>SISTEMA DE SEGURANÇA · JARVIS v{APP_VERSION}</span>
        </div>
        <h1 className="ls-brand">J.A.R.V.I.S.</h1>
        <p className="ls-subbrand">NEURAL INTERFACE & TACTICAL WORKSPACE</p>
      </header>

      {fanPanel && phase !== "scanning" && phase !== "pin" && (
        <FanLockPanel api={cards.api} refreshKey={cards.fanRefresh} />
      )}

      {/* Orbe Arc Reactor Central com HUD de mira (ou o teclado do PIN) */}
      {pinBlock || (
        <div className={`ls-orb-wrapper ${clap?.pulse ? "is-clap-pulse" : ""}`} key={`orb-${clap?.pulse || 0}`}>
          <div className={`ls-hud-ring${scanning ? " is-scanning" : ""}`} />
          <ArcReactorHUD state={orbState} photoUrl={photoUrl} tone={tone} liveFrame={liveFrame} />
        </div>
      )}

      {/* Status & Legendas */}
      <div className="ls-status-box">
        <div className={`ls-title ${phase === "failed" ? "is-failed" : phase === "verified" ? "is-verified" : ""}`}>
          {title}
        </div>
        <div className="ls-hint">
          <span>{hint}</span>
        </div>
        {scanning && <FaceScanStatus scan={liveScan} />}
      </div>

      {/* Ações / Botão Principal */}
      {phase !== "scanning" && phase !== "pin" && !(phase === "verified" && clap?.autoEntering) && (
        <div className="ls-actions">
          <button
            type="button"
            onClick={handleBtnClick}
            className="ls-btn-main"
          >
            <span className="ls-btn-glow" />
            <span className="ls-btn-text">
              {phoneEntry ? (hasPin ? "🔑 ENTRAR COM PIN" : "CRIE UM PIN NO PC")
                : phase === "verified" ? "ENTRAR E FALAR" : phase === "failed" ? "TENTAR NOVAMENTE" : "ATIVAR VOZ E ENTRAR"}
            </span>
            {!phoneApp && <span className="ls-key-badge">ESPAÇO</span>}
          </button>

          {secondaryActions}

          {!phoneApp && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onChangePhoto();
              }}
              className="ls-link-photo"
            >
              ⚙ Alterar foto de identificação facial
            </button>
          )}
        </div>
      )}

      {phase !== "scanning" && phase !== "pin" && (
        <LockCards api={cards?.api} cards={cardsList} fanModeEnabled={cards?.fanModeEnabled} allRight={fanPanel} />
      )}

      {mic && (
        <button
          type="button"
          className={`ls-mic-toggle ${mic.muted ? "" : "on"}`}
          onClick={(e) => { e.stopPropagation(); mic.onToggle(); }}
          title={mic.muted ? "Ligar o microfone (palmas e escuta)" : "Silenciar o microfone"}
          aria-pressed={!mic.muted}
        >
          <span className="dot" /> {mic.muted ? "MIC SILENCIADO · aperte P para ligar" : "MIC LIGADO"}
          <span className="ls-key-badge">P</span>
        </button>
      )}

      <ClapIndicator clap={clap} />

      {/* Rodapé Tático */}
      <footer className="ls-footer">
        <span>JARVIS · NÚCLEO DE PROTOCOLOS AUTÔNOMOS · BRASÍLIA BR</span>
      </footer>
      {phase !== "scanning" && phase !== "pin" ? <BlueprintStamp fan={fanToggle} bg={bgToggle} audio={audioToggle} /> : <BlueprintStamp />}
    </div>
  );
}

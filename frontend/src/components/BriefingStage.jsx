import { useEffect, useState } from "react";
import BriefingCard, { ReadinessPanel } from "./BriefingCard.jsx";

/**
 * V4.3: palco do briefing "bom dia" / "boa noite" no centro da central.
 * - running: caixa de abertura, abas com barra de progresso própria, card do assunto falado,
 *   pilha dos cards já falados, legenda do que o JARVIS está dizendo e o botão PRÓXIMO ▸.
 * - done ("Em espera"): fileira de cards (clique amplia, ✕ esconde), "Gerenciar HUD" para
 *   reexibir os escondidos e a prontidão no canto esquerdo.
 * O estado vem dos eventos briefing_start / briefing_step / briefing_end (App.jsx).
 */

const HIDDEN_KEY = "jarvis_briefing_hidden";

// Frases curtas que abrem as telas (mesma lista de backend/modules/briefing_topics.py)
export const VOICE_HINTS = [
  { say: "bom dia", icon: "☀" },
  { say: "boa tarde", icon: "◐" }, // V6.5
  { say: "boa noite", icon: "☾" },
  { say: "notícias", icon: "◉" },
  { say: "notificações", icon: "◔" },
  { say: "e-mails", icon: "✉" },
  { say: "agenda", icon: "▦" },
  { say: "clima", icon: "☁" },
  { say: "tarefas", icon: "☑" },
  { say: "comandos", icon: "◎" },
];

// V6.5.5: no app do celular, dá para fixar um comando da faixa DIGA como ícone na tela inicial
function canPinShortcut() {
  try {
    return Boolean(window.JarvisApp?.canPinShortcut?.());
  } catch {
    return false;
  }
}

/** Faixa "DIGA:" com as frases. Clicar numa delas envia o comando como se você tivesse falado. */
export function VoiceHints({ onSay, exclude = [], compact = false }) {
  const hints = VOICE_HINTS.filter((h) => !exclude.includes(h.say));
  const [pinMode, setPinMode] = useState(false);
  const [pinNote, setPinNote] = useState("");
  const [canPin] = useState(canPinShortcut);
  useEffect(() => {
    if (!pinNote) return undefined;
    const t = setTimeout(() => setPinNote(""), 4000);
    return () => clearTimeout(t);
  }, [pinNote]);

  const pin = (h) => {
    setPinMode(false);
    const label = h.say.charAt(0).toUpperCase() + h.say.slice(1);
    let ok = false;
    try {
      ok = Boolean(window.JarvisApp?.pinShortcut?.(label, h.say));
    } catch {
      ok = false;
    }
    setPinNote(ok ? `Confirme no Android para pôr "${label}" na tela inicial.` : "Este celular não deixou criar o atalho.");
  };

  return (
    <div className={`bf-hints${compact ? " is-compact" : ""}${pinMode ? " is-pinning" : ""}`} aria-label="Comandos de voz">
      <span className="bf-hints-label">{pinMode ? "TOQUE NO COMANDO PARA FIXAR" : "DIGA"}</span>
      {hints.map((h) => (
        <button
          key={h.say}
          type="button"
          className="bf-hint"
          onClick={() => {
            if (pinMode) {
              pin(h);
              return;
            }
            // V6.5: tocar em "notícias" abre a janela de notícias (falar "notícias" continua lendo o resumo)
            if (h.say === "notícias") {
              window.dispatchEvent(new CustomEvent("jarvis-open-news"));
              return;
            }
            if (onSay) onSay(h.say);
          }}
          title={`Fale "${h.say}" ou clique`}
          disabled={!onSay}
        >
          <i aria-hidden="true">{h.icon}</i>"{h.say}"
        </button>
      ))}
      {canPin && (
        <button
          type="button"
          className={`bf-hint bf-pin${pinMode ? " is-on" : ""}`}
          onClick={() => setPinMode((v) => !v)}
          aria-pressed={pinMode}
          title="Pôr um comando como ícone na tela inicial do celular"
        >
          <i aria-hidden="true">📌</i>{pinMode ? "cancelar" : "fixar na tela inicial"}
        </button>
      )}
      {pinNote && <span className="bf-pin-note" role="status">{pinNote}</span>}
    </div>
  );
}

// Notícias se distinguem pelo tema; os outros cards, pelo rótulo (o título muda a cada dia)
const cardKey = (c) => (c.kind === "news" ? `news:${c.title}` : c.label);

function loadHidden() {
  try {
    return JSON.parse(localStorage.getItem(HIDDEN_KEY) || "[]");
  } catch {
    return [];
  }
}

function saveHidden(list) {
  try {
    localStorage.setItem(HIDDEN_KEY, JSON.stringify(list));
  } catch {
    /* sem armazenamento: vale só para esta sessão */
  }
}

// Duração aproximada da fala (~ritmo da voz pt-BR), usada para encher a barra da aba ativa
const speechMs = (text) => Math.max(1500, (text || "").length * 60);

function DoneRow({ briefing, onClose, onSay }) {
  const [hidden, setHidden] = useState(loadHidden);
  const [managing, setManaging] = useState(false);
  const [focus, setFocus] = useState(null);
  const cards = briefing.cards || [];
  const hiddenHere = cards.filter((c) => hidden.includes(cardKey(c)));
  const visible = managing ? cards : cards.filter((c) => !hidden.includes(cardKey(c)));

  const toggle = (c) => {
    const key = cardKey(c);
    const next = hidden.includes(key) ? hidden.filter((k) => k !== key) : [...hidden, key];
    setHidden(next);
    saveHidden(next);
  };

  useEffect(() => {
    if (!focus) return undefined;
    const onKey = (e) => e.key === "Escape" && setFocus(null);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [focus]);

  return (
    <div className="bf-stage is-done">
      {briefing.readiness && <ReadinessPanel data={briefing.readiness} />}
      <div className="bf-row-wrap">
        <div className="bf-row-head">
          <span className="bf-label">{briefing.title || "BRIEFING"} · {cards.length - hiddenHere.length} ASSUNTOS</span>
          {briefing.closing && <span className="bf-closing">{briefing.closing}</span>}
          <button
            type="button"
            className={`bf-pill${managing ? " is-on" : ""}`}
            onClick={() => setManaging((m) => !m)}
            title="Escolher quais cards ficam na fileira"
          >
            {managing ? "✓ CONCLUIR" : `GERENCIAR HUD${hiddenHere.length ? ` · ${hiddenHere.length} ESCONDIDOS` : ""}`}
          </button>
          <button type="button" className="bf-close" onClick={onClose} title="Fechar o briefing">✕</button>
        </div>
        {/* V6.6.4: no PC, colunas pela quantidade de assuntos para caber em 2 fileiras (8 -> 4x2, 10 -> 5x2) */}
        <div className="bf-row" style={{ "--bf-cols": Math.min(5, Math.max(2, Math.ceil(visible.length / 2))) }}>
          {visible.map((c, i) => {
            const isHidden = hidden.includes(cardKey(c));
            return (
              <div key={`${cardKey(c)}-${i}`} className={`bf-slot${isHidden ? " is-hidden" : ""}`}>
                {/* div, não button: o card de notícia tem o link "Abrir matéria" dentro */}
                <div
                  role="button"
                  tabIndex={0}
                  className="bf-slot-open"
                  onClick={(e) => {
                    if (e.target.closest("a")) return;
                    if (managing) toggle(c);
                    else setFocus(c);
                  }}
                  onKeyDown={(e) => {
                    if (e.key !== "Enter" && e.key !== " ") return;
                    e.preventDefault();
                    if (managing) toggle(c);
                    else setFocus(c);
                  }}
                  title={managing ? (isHidden ? "Mostrar este card" : "Esconder este card") : "Ampliar"}
                >
                  <BriefingCard card={c} mini />
                </div>
                {managing && (
                  <span className="bf-slot-badge">{isHidden ? "ESCONDIDO" : "VISÍVEL"}</span>
                )}
                {!managing && (
                  <button type="button" className="bf-slot-hide" onClick={() => toggle(c)} title="Esconder este card">
                    ✕
                  </button>
                )}
              </div>
            );
          })}
        </div>
        <VoiceHints onSay={onSay} compact />
      </div>
      {focus && (
        <div className="bf-focus" role="dialog" aria-label={focus.title} onClick={() => setFocus(null)}>
          <div className="bf-focus-card" onClick={(e) => e.stopPropagation()}>
            <BriefingCard card={focus} entering wide />
            <button type="button" className="bf-close" onClick={() => setFocus(null)}>✕ FECHAR</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function BriefingStage({ briefing, onClose, onSkip, onSay }) {
  if (!briefing) return null;
  if (briefing.phase === "done") return <DoneRow briefing={briefing} onClose={onClose} onSay={onSay} />;

  const { tabs = [], activeTab, index = -1, total = 0, progress, current, cards = [], speech, plan = [] } = briefing;
  const tabIdx = tabs.findIndex((t) => t.id === activeTab);
  // Pauta: com o plano (backend novo), todos os assuntos aparecem desde a saudação; os já falados
  // ficam acesos e os próximos, apagados, até a vez de cada um. Sem plano, como antes (só os falados).
  const trail = plan.length
    ? plan.map((c, i) => ({ card: c, state: i < index ? "is-done" : i === index ? null : "is-next" })).filter((t) => t.state)
    : cards.slice(0, -1).map((c) => ({ card: c, state: "is-done" }));
  return (
    <div className={`bf-stage is-running${index < 0 ? " is-opening" : ""}`} aria-live="polite">
      <div className="bf-head">
        <div className="bf-opening">
          <strong>{briefing.opening}</strong>
          <small>{index < 0 ? briefing.opening_sub : progress}</small>
        </div>
        <nav className="bf-tabs" aria-label="Etapas do briefing">
          {tabs.map((t, i) => {
            const state = i < tabIdx ? "is-done" : i === tabIdx ? "is-active" : "";
            return (
              <span key={t.id} className={`bf-tab ${state}`}>
                {t.label}
                <i className="bf-tab-bar">
                  <b key={i === tabIdx ? index : "x"} style={i === tabIdx ? { animationDuration: `${speechMs(speech)}ms` } : undefined} />
                </i>
              </span>
            );
          })}
        </nav>
      </div>

      {/* Como no vídeo: o card falado agora fica largo no centro do orbe e os já falados
          formam uma fileira logo abaixo dele */}
      <div className="bf-focus-area">
        {current && <BriefingCard key={index} card={current} entering wide />}
        {trail.length > 0 && (
          <div className="bf-trail" aria-label={plan.length ? "Pauta do briefing" : "Assuntos já falados"}>
            {trail.map((t, i) => (
              <div key={`${i}-${t.state}`} className={`bf-trail-item ${t.state}`}>
                <BriefingCard card={t.card} mini />
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="bf-bottom">
        <div className="bf-controls">
          {speech && <p className="bf-caption" key={index}>{speech}</p>}
          <div className="bf-controls-row">
            <span className="bf-count">{index < 0 ? "ABERTURA" : `${index + 1} / ${total}`}</span>
            {onSkip && total > 1 && (
              <button type="button" className="bf-skip" onClick={onSkip} title="Pular para o próximo assunto (→)">
                PRÓXIMO ▸
              </button>
            )}
            {onSkip && total > 1 && <span className="bf-count">ou aperte →</span>}
          </div>
        </div>
      </div>
    </div>
  );
}

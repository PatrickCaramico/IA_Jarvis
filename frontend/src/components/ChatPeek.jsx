import { useEffect, useRef, useState } from "react";
import { CLOSE_AFTER_MS, EXIT_MS, recentMessages, wantsPeek } from "../utils/chatPeek.js";

// V9.4.5: TRANSCRIÇÃO AO VIVO. Quando o JARVIS fala, a conversa abre numa janela de vidro maior (com animação de
// entrada e de saída) e fecha sozinha 7 s depois que ele termina. Passar o mouse segura aberta; ✕ fecha até a
// próxima fala. Só existe enquanto aparece (o vidro com desfoque não fica pesando na tela parada).

const WHO = { user: "VOCÊ", jarvis: "JARVIS", error: "AVISO" };

export default function ChatPeek({
  log = [],
  enabled = true,
  speaking = false,
  listening = false,
  interim = "",
  streamText = "",
  zen = false,
  briefing = false,
  TextComp = null, // o "digitando" do Canal Ativo (Typed), para a resposta aparecer igual
  onOpenChat = null,
}) {
  const want = wantsPeek({ enabled, speaking, streaming: Boolean(streamText), listening, zen, briefing });
  const [phase, setPhase] = useState("hidden"); // hidden | open | closing
  const [dismissed, setDismissed] = useState(false);
  const [hover, setHover] = useState(false);
  const bodyRef = useRef(null);

  // ✕ vale até ele parar de falar; a próxima fala abre de novo
  useEffect(() => {
    if (!want) setDismissed(false);
  }, [want]);

  useEffect(() => {
    if (want && !dismissed) {
      setPhase("open");
      return undefined;
    }
    if (phase !== "open") return undefined;
    if (hover && !dismissed) return undefined; // lendo com o mouse em cima: espera
    const t = setTimeout(() => setPhase("closing"), dismissed ? 0 : CLOSE_AFTER_MS);
    return () => clearTimeout(t);
  }, [want, dismissed, hover, phase]);

  useEffect(() => {
    if (phase !== "closing") return undefined;
    const t = setTimeout(() => setPhase("hidden"), EXIT_MS);
    return () => clearTimeout(t);
  }, [phase]);

  const msgs = recentMessages(log, 4);
  const last = msgs[msgs.length - 1];
  // a última linha acompanha o texto: rola para o fim quando muda
  useEffect(() => {
    const el = bodyRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [last?.id, streamText, interim, phase]);

  if (phase === "hidden") return null;
  const tag = listening ? "OUVINDO" : speaking ? "FALANDO" : streamText ? "ESCREVENDO" : "PRONTO";

  return (
    <section
      className={`cpk${phase === "closing" ? " cpk-out" : ""}${speaking || streamText ? " is-live" : ""}`}
      aria-label="Transcrição da conversa"
      data-testid="chat-peek"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <header className="cpk-head">
        <span className="cpk-dot" aria-hidden="true" />
        <b>JARVIS · TRANSCRIÇÃO</b>
        <span className="cpk-tag" role="status">{tag}</span>
        {speaking && (
          <span className="cpk-wave" aria-hidden="true"><i /><i /><i /><i /></span>
        )}
        {onOpenChat && (
          <button type="button" className="cpk-btn" onClick={() => { onOpenChat(); setDismissed(true); }} title="Abrir o Canal Ativo com a conversa toda">
            CHAT
          </button>
        )}
        <button type="button" className="cpk-btn cpk-x" onClick={() => setDismissed(true)} aria-label="Fechar a transcrição">✕</button>
      </header>
      <div className="cpk-body" ref={bodyRef} aria-live="polite">
        {msgs.map((m) => (
          <p key={m.id} className={`cpk-msg cpk-${m.role}`}>
            <b>{WHO[m.role]}</b>
            <span>{m.role === "jarvis" && m === last && TextComp && !streamText ? <TextComp text={m.text} /> : m.text}</span>
          </p>
        ))}
        {streamText && (
          <p className="cpk-msg cpk-jarvis"><b>JARVIS</b><span>{streamText}<span className="hl-caret" /></span></p>
        )}
        {listening && (
          <p className="cpk-msg cpk-user is-live"><b>VOCÊ</b><span>{interim || "Ouvindo…"}</span></p>
        )}
      </div>
    </section>
  );
}

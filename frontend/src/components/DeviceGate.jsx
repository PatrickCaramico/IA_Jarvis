import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { deviceInfo, pollDeviceKey, requestDeviceKey } from "../utils/deviceAccess.js";

// V7.6: aparelho (celular, tablet, TV, outro PC) pedindo a PRÓPRIA chave ao JARVIS.
// Nos primeiros dias da atualização sai aprovado na hora (migração); depois, espera PERMITIR na tela do PC.
const TEXT = {
  requesting: ["CONECTANDO", "Pedindo a chave deste aparelho ao JARVIS…"],
  pending: ["AGUARDANDO APROVAÇÃO", "Toque em PERMITIR na tela do PC para liberar este aparelho."],
  refused: ["ACESSO RECUSADO", "O pedido foi recusado no PC."],
  expired: ["TEMPO ESGOTADO", "Ninguém aprovou no PC a tempo."],
  revoked: ["APARELHO REMOVIDO", "Este aparelho foi removido do JARVIS. Peça acesso de novo."],
  error: ["NÃO CONSEGUI PEDIR", "O PC não respondeu. Confira se o JARVIS está ligado."],
};

export default function DeviceGate({ reason = "new", onDone }) {
  const info = useRef(deviceInfo()).current;
  const [phase, setPhase] = useState(reason === "revoked" ? "revoked" : "requesting");
  const [left, setLeft] = useState(0);
  const [detail, setDetail] = useState("");
  const [round, setRound] = useState(reason === "revoked" ? 0 : 1);

  useEffect(() => {
    if (!round) return undefined;
    const ctrl = new AbortController();
    (async () => {
      setPhase("requesting");
      setDetail("");
      try {
        const r = await requestDeviceKey(info);
        if (r.status === "approved" || r.status === "local") {
          onDone(r.status === "approved");
          return;
        }
        setPhase("pending");
        setLeft(r.expires_in || 120);
        const result = await pollDeviceKey(r.request_id, r.secret, { signal: ctrl.signal });
        if (result === "approved") onDone(true);
        else if (result !== "aborted") setPhase(result === "refused" ? "refused" : "expired");
      } catch (err) {
        setDetail(err.message || "");
        setPhase("error");
      }
    })();
    return () => ctrl.abort();
  }, [round]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (phase !== "pending") return undefined;
    const t = setInterval(() => setLeft((n) => Math.max(0, n - 1)), 1000);
    return () => clearInterval(t);
  }, [phase]);

  const [title, text] = TEXT[phase];
  const waiting = phase === "requesting" || phase === "pending";
  return createPortal(
    <div className="dgt-overlay" role="dialog" aria-modal="true" aria-label="Acesso deste aparelho">
      <div className={`dgt is-${phase}`}>
        <div className="dgt-shield" aria-hidden="true">
          {waiting && <i className="dgt-ring" />}
          <span>{phase === "refused" || phase === "revoked" ? "✕" : phase === "error" || phase === "expired" ? "!" : "🛡"}</span>
        </div>
        <small>SEGURANÇA DO JARVIS</small>
        <h2>{title}</h2>
        <p>{text}</p>
        <div className="dgt-device"><b>{info.name}</b><span>{info.kind}</span></div>
        {phase === "pending" && <p className="dgt-left">Expira em {left} s</p>}
        {detail && phase === "error" && <p className="dgt-detail">{detail}</p>}
        {!waiting && (
          <div className="dgt-actions">
            <button type="button" onClick={() => setRound((n) => n + 1)}>PEDIR ACESSO DE NOVO</button>
            {phase === "error" && <button type="button" className="is-ghost" onClick={() => onDone(false)}>CONTINUAR ASSIM</button>}
          </div>
        )}
      </div>
    </div>,
    document.body,
  );
}

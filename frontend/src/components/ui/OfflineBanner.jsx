import { useEffect, useRef, useState } from "react";

const GRACE_MS = 3000;     // quedas curtas (reinício do backend) não mostram o aviso
const BACK_MS = 2500;      // "Conexão restabelecida" fica na tela por um instante

// Faixa no topo quando o JARVIS perde a conexão com o backend (V4.2.2).
// O WebSocket já tenta reconectar sozinho a cada 2 s; aqui só avisamos com calma.
export default function OfflineBanner({ connected, active = true }) {
  const [phase, setPhase] = useState("hidden"); // hidden | offline | back
  const wasOffline = useRef(false);

  useEffect(() => {
    if (!active) return undefined;
    if (!connected) {
      const t = setTimeout(() => { wasOffline.current = true; setPhase("offline"); }, GRACE_MS);
      return () => clearTimeout(t);
    }
    if (wasOffline.current) {
      wasOffline.current = false;
      setPhase("back");
      const t = setTimeout(() => setPhase("hidden"), BACK_MS);
      return () => clearTimeout(t);
    }
    setPhase("hidden");
    return undefined;
  }, [connected, active]);

  if (!active || phase === "hidden") return null;
  const back = phase === "back";
  return (
    <div className={`j-offline ${back ? "is-back" : ""}`} role="status" aria-live="polite">
      <span className="j-offline-dot" aria-hidden="true" />
      {back ? (
        <span>Conexão restabelecida. Tudo certo, senhor.</span>
      ) : (
        <span>Perdi o contato com o servidor do JARVIS. Tentando reconectar sozinho…</span>
      )}
    </div>
  );
}

import FaceScanOverlay from "./FaceScanOverlay.jsx";

// Painel flutuante da reverificação por palma com a central já aberta (seção 16).
// Fecha sozinho ~3 s depois do resultado (controlado pelo App).
export default function FaceRecheckPanel({ scan, onClose }) {
  const phase = scan?.phase || "searching";
  const done = scan?.status === "verified" || scan?.status === "failed";
  return (
    <div className={`frp-panel ${done ? (scan.status === "verified" ? "is-ok" : "is-fail") : ""}`} role="dialog" aria-label="Reverificação facial">
      <div className="frp-head">
        <span>REVERIFICAÇÃO FACIAL</span>
        <button type="button" onClick={onClose} aria-label="Fechar">×</button>
      </div>
      {scan?.frame ? (
        <FaceScanOverlay scan={scan} variant="panel" recheck />
      ) : (
        <div className="frp-wait">{scan?.error ? scan.error : phase === "failed" ? "Câmera indisponível." : "Abrindo a câmera..."}</div>
      )}
      {done && !scan?.frame && (
        <div className={`frp-result ${scan.status === "verified" ? "ok" : "fail"}`}>
          {scan.status === "verified" ? "IDENTIDADE CONFIRMADA" : "ROSTO NÃO RECONHECIDO"}
        </div>
      )}
    </div>
  );
}

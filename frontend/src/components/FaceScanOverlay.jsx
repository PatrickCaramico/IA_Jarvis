// Camada da verificação facial ao vivo (seção 16): quadro da câmera transmitido pelo backend,
// cantos táticos em volta do rosto, linha de varredura, barra de similaridade e estado.
// A imagem é espelhada (como um espelho), e a caixa do rosto é espelhada junto.

export const PHASE_TEXT = {
  searching: "PROCURANDO ROSTO",
  comparing: "ROSTO DETECTADO, COMPARANDO",
  verified: "ACESSO AUTORIZADO",
  failed: "ROSTO NÃO RECONHECIDO",
};

export function similarityPct(score, threshold) {
  const thr = Number(threshold) > 0 ? Number(threshold) : 0.363;
  const s = Math.max(0, Number(score) || 0);
  return Math.max(0, Math.min(100, Math.round((s / thr) * 100)));
}

export default function FaceScanOverlay({ scan, variant = "panel", recheck = false }) {
  if (!scan || !scan.frame) return null;
  const phase = scan.phase || "searching";
  const pct = similarityPct(scan.score, scan.threshold);
  const box = Array.isArray(scan.box) && scan.box.length === 4 ? scan.box : null;
  const mirrored = box ? { left: 1 - box[0] - box[2], top: box[1], width: box[2], height: box[3] } : null;
  const finalText = recheck && phase === "verified" ? "IDENTIDADE CONFIRMADA" : PHASE_TEXT[phase];
  const live = phase === "searching" || phase === "comparing";

  return (
    <div className={`fs-root fs-${variant} fs-phase-${phase}`}>
      <div className="fs-video">
        <img src={`data:image/jpeg;base64,${scan.frame}`} alt="Câmera ao vivo do escaneamento facial" />
        {mirrored && (
          <div
            className="fs-box"
            style={{
              left: `${mirrored.left * 100}%`,
              top: `${mirrored.top * 100}%`,
              width: `${mirrored.width * 100}%`,
              height: `${mirrored.height * 100}%`,
            }}
            aria-hidden="true"
          >
            <span className="fs-corner tl" /><span className="fs-corner tr" />
            <span className="fs-corner bl" /><span className="fs-corner br" />
          </div>
        )}
        {live && <div className="fs-scanline" aria-hidden="true" />}
        {live && variant === "panel" && (
          <div className="fs-badge" role="status">
            <span className="fs-rec" /> CÂMERA ATIVA
          </div>
        )}
      </div>
      {variant === "panel" && (
        <div className="fs-info">
          <div className="fs-phase" aria-live="polite">{finalText}</div>
          <div className="fs-meter" aria-label={`Similaridade ${pct}% do necessário`}>
            <div className="fs-meter-fill" style={{ width: `${pct}%` }} />
            <div className="fs-meter-mark" />
          </div>
          <div className="fs-meter-label">SIMILARIDADE {pct}%</div>
        </div>
      )}
    </div>
  );
}

// Informações abaixo do orbe na tela de bloqueio (o vídeo fica dentro do orbe).
export function FaceScanStatus({ scan }) {
  if (!scan || !scan.frame) return null;
  const phase = scan.phase || "searching";
  const pct = similarityPct(scan.score, scan.threshold);
  const live = phase === "searching" || phase === "comparing";
  return (
    <div className={`fs-status fs-phase-${phase}`}>
      {live && <div className="fs-badge fs-badge-inline"><span className="fs-rec" /> CÂMERA ATIVA</div>}
      <div className="fs-meter" aria-label={`Similaridade ${pct}% do necessário`}>
        <div className="fs-meter-fill" style={{ width: `${pct}%` }} />
        <div className="fs-meter-mark" />
      </div>
      <div className="fs-meter-label" aria-live="polite">{PHASE_TEXT[phase]} · SIMILARIDADE {pct}%</div>
    </div>
  );
}

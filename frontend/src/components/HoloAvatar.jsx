import { useState } from "react";

// V9.4: AVATAR HOLOGRÁFICO no centro da tela de bloqueio, feito pelo PC a partir da foto do rosto cadastrada
// (backend/modules/holo_avatar.py: rosto recortado em ciano, com linhas de varredura). Aqui só o "palco":
// flutua devagar, um feixe de varredura passa, anéis giram; ouvindo/falando pulsa; verificando acelera;
// reconhecido fica verde e não reconhecido treme em vermelho. Animações só com transform/opacity (leve).
// Se a imagem não carregar (avatar desligado no PC), avisa o pai para voltar ao reator.
export default function HoloAvatar({ src, phase = "ready", state = "idle", onMissing = null }) {
  const [loaded, setLoaded] = useState(false);
  const mood = phase === "verified" ? "ok" : phase === "failed" ? "fail" : phase === "scanning" ? "scan" : state;
  return (
    <div className={`ha-root is-${mood}${loaded ? " is-loaded" : ""}`} aria-hidden="true">
      <span className="ha-floor" />
      <span className="ha-ring ha-ring-1" />
      <span className="ha-ring ha-ring-2" />
      <div className="ha-float">
        <div className="ha-face">
          <img src={src} alt="" draggable="false" onLoad={() => setLoaded(true)} onError={() => onMissing?.()} />
          <span className="ha-grid" />
          <span className="ha-beam" />
        </div>
      </div>
      <span className="ha-cone" />
    </div>
  );
}

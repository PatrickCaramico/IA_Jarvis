import { useState } from "react";

export default function FanModeBackground({ teamInfo }) {
  const [imgError, setImgError] = useState(false);
  const badgeUrl = teamInfo?.badge_url || "/fan/palmeiras/palmeiras_shield.png";

  return (
    <div
      className="fixed inset-0 pointer-events-none z-0 flex items-center justify-center overflow-hidden transition-opacity duration-700"
      aria-hidden="true"
    >
      {/* Escudo translúcido central com vinheta verde suave */}
      {!imgError && (
        <div className="relative flex items-center justify-center w-[580px] h-[580px] max-w-[85vw] max-h-[85vh] select-none">
          <img
            src={badgeUrl}
            alt="Escudo do Clube"
            onError={() => setImgError(true)}
            className="w-full h-full object-contain opacity-[0.09] blur-[0.6px] drop-shadow-[0_0_45px_rgba(4,101,56,0.6)]"
          />
        </div>
      )}

      {/* Camada sutil de vinheta tática verde escuro */}
      <div className="absolute inset-0 bg-radial-vignette opacity-50" />
    </div>
  );
}

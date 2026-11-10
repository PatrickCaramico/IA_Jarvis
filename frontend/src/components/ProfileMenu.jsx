import { useState } from "react";
import ProfileModal from "./ProfileModal.jsx";

export default function ProfileMenu({
  photoUrl,
  name,
  activeWidgets,
  onWidgetsChange,
  onOpenSettings,
  onOpenQr,
  onOpenWidgets,
  onOpenMonitors,
  onOpenMicrophone,
  api,
}) {
  const [modalOpen, setModalOpen] = useState(false);

  const handleClick = () => {
    if (api) {
      api("/api/speak", {
        method: "POST",
        body: JSON.stringify({ text: `Abrindo perfil do operador ${name || "Patrick"}.` }),
      }).catch(() => {});
    }
    setModalOpen(true);
  };

  return (
    <>
      {/* Botão do Avatar no Topo */}
      <button
        type="button"
        onClick={handleClick}
        title={name || "Perfil do Usuário"}
        className="flex-shrink-0 flex items-center justify-center overflow-hidden rounded-full border border-cyan-400/80 bg-black/60 shadow-[0_0_12px_rgba(31,194,245,0.4)] transition hover:scale-105 hover:border-cyan-200 focus:outline-none"
        style={{ width: "36px", height: "36px", minWidth: "36px", minHeight: "36px", padding: "1px", flexShrink: 0 }}
      >
        <img
          src={photoUrl}
          alt={name || "Perfil"}
          className="rounded-full object-cover aspect-square"
          style={{ width: "100%", height: "100%", objectFit: "cover", borderRadius: "9999px", display: "block" }}
          onError={(e) => {
            e.target.style.display = "none";
            if (e.target.nextSibling) e.target.nextSibling.style.display = "flex";
          }}
        />
        <span
          className="hidden h-full w-full items-center justify-center rounded-full bg-cyan-950 font-['Orbitron'] text-xs text-cyan-200"
          style={{ display: "none" }}
        >
          {(name || "P")[0].toUpperCase()}
        </span>
      </button>

      {/* Pop-up / Modal Central quando clica no avatar */}
      {modalOpen && (
        <ProfileModal
          photoUrl={photoUrl}
          name={name}
          activeWidgets={activeWidgets}
          onWidgetsChange={onWidgetsChange}
          onOpenSettings={onOpenSettings}
          onOpenQr={onOpenQr}
          onOpenWidgets={onOpenWidgets}
          onOpenMonitors={onOpenMonitors}
          onOpenMicrophone={onOpenMicrophone}
          onClose={() => setModalOpen(false)}
          api={api}
        />
      )}
    </>
  );
}

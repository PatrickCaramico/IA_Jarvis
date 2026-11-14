import { useEffect, useState } from "react";
import { BACKEND_ON_THIS_PC } from "../utils/api.js";
import { needsDeviceKey } from "../utils/deviceAccess.js";
import lazyComponent from "../utils/lazyComponent.jsx";

// V7.6: camada de SEGURANÇA, por cima de qualquer tela do JARVIS (boot, bloqueio, central, visitante…).
// - aparelho fora do PC: pede a própria chave (o QR code virou só a chave de pareamento);
// - tela do próprio PC: cartão PERMITIR / RECUSAR para cada aparelho novo.
// No modo nuvem (<html data-cloud="1">) não faz nada: lá quem protege é o PIN da nuvem.
const DeviceGate = lazyComponent(() => import("./DeviceGate.jsx"));
const DeviceApprovalCard = lazyComponent(() => import("./DeviceApprovalCard.jsx"));

const inCloud = () => typeof document !== "undefined" && document.documentElement.dataset.cloud === "1";

export default function SecurityLayer() {
  const [gate, setGate] = useState(null);

  useEffect(() => {
    if (BACKEND_ON_THIS_PC) return undefined;
    if (needsDeviceKey() && !inCloud()) setGate({ reason: "new" });
    const on = (e) => {
      if (!inCloud()) setGate({ reason: e.detail?.code === "device_revoked" ? "revoked" : "new" });
    };
    window.addEventListener("jarvis-device-access", on);
    return () => window.removeEventListener("jarvis-device-access", on);
  }, []);

  if (BACKEND_ON_THIS_PC) return <DeviceApprovalCard />;
  if (!gate || inCloud()) return null;
  return (
    <DeviceGate
      reason={gate.reason}
      onDone={(approvedNow) => {
        setGate(null);
        if (approvedNow) window.location.reload(); // recomeça tudo já com a chave nova (uma vez só)
      }}
    />
  );
}

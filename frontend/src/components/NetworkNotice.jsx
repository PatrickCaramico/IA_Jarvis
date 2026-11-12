import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { IS_JARVIS_APP } from "../utils/device.js";
import { enqueueHere } from "../utils/speakHere.js";
import { networkMessage } from "../utils/networkNotice.js";

// V6.4: no app do celular, avisa a rede ao abrir: "O senhor está conectado pelos dados móveis" e,
// quando muda, "Mudança de rede: agora o senhor está no Wi-Fi". O app Android diz qual é a rede
// (JarvisApp.networkNotice) e lembra a anterior, mesmo quando a página troca de endereço com a rede.
function readNetwork() {
  try {
    const raw = window.JarvisApp?.networkNotice?.();
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export default function NetworkNotice() {
  const [text, setText] = useState("");

  useEffect(() => {
    if (!IS_JARVIS_APP) return undefined;
    const check = (reason) => {
      const info = readNetwork();
      if (!info) return;
      const msg = networkMessage(info.type, info.prev, reason);
      if (!msg) return;
      setText(msg.text);
      enqueueHere(msg.speech); // fala no celular; sem o PC agora, fica só o aviso na tela
    };
    const t = setTimeout(() => check("open"), 1500); // dá tempo de a tela montar
    const onEvent = (e) => check(e.detail?.reason || "change");
    window.addEventListener("jarvis-app-network", onEvent);
    return () => {
      clearTimeout(t);
      window.removeEventListener("jarvis-app-network", onEvent);
    };
  }, []);

  useEffect(() => {
    if (!text) return undefined;
    const t = setTimeout(() => setText(""), 6000);
    return () => clearTimeout(t);
  }, [text]);

  if (!text) return null;
  return createPortal(
    <div className="notice-toast network-notice" role="status" onClick={() => setText("")}>
      {text}
    </div>,
    document.body,
  );
}

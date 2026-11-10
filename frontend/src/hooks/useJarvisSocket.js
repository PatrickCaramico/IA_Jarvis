import { useEffect, useRef } from "react";
import { WS_URL, getJarvisToken } from "../utils/api.js";

// WebSocket do backend com reconexão automática e ping (refatoração 4.2: saiu do App.jsx).
// onMessage recebe cada evento já decodificado; a versão mais recente do callback é sempre usada,
// então ele pode ler estado atual sem reabrir a conexão.
export default function useJarvisSocket({ onMessage, onConnectedChange }) {
  const onMessageRef = useRef(onMessage);
  const onConnectedRef = useRef(onConnectedChange);
  onMessageRef.current = onMessage;
  onConnectedRef.current = onConnectedChange;

  useEffect(() => {
    let ws;
    let retryTimer;
    let pingTimer;
    let closedByUs = false;

    const connect = () => {
      const token = getJarvisToken();
      const wsUrlWithToken = token ? `${WS_URL}?token=${encodeURIComponent(token)}` : WS_URL;
      ws = new WebSocket(wsUrlWithToken);

      ws.onopen = () => {
        onConnectedRef.current?.(true);
        pingTimer = setInterval(() => ws.readyState === 1 && ws.send("ping"), 20000);
      };

      ws.onmessage = (event) => {
        if (event.data === "pong") return;
        const msg = JSON.parse(event.data);
        window.dispatchEvent(new CustomEvent("jarvis_ws_event", { detail: msg }));
        onMessageRef.current?.(msg);
      };

      ws.onclose = () => {
        onConnectedRef.current?.(false);
        clearInterval(pingTimer);
        if (!closedByUs) retryTimer = setTimeout(connect, 2000);
      };
    };

    connect();
    return () => {
      closedByUs = true;
      clearTimeout(retryTimer);
      clearInterval(pingTimer);
      ws?.close();
    };
  }, []);
}

import { useEffect, useRef } from "react";
import { WS_URL, getJarvisToken } from "../utils/api.js";
import { reconnectDelay } from "../utils/reconnect.js";

// WebSocket do backend com reconexão automática e ping (refatoração 4.2: saiu do App.jsx).
// onMessage recebe cada evento já decodificado; a versão mais recente do callback é sempre usada,
// então ele pode ler estado atual sem reabrir a conexão.
//
// V5.2 (conexão mais firme, principalmente no celular):
// - espera crescente entre tentativas (1 s, 2 s, 4 s… até 10 s), com um pouco de sorteio;
// - reconecta NA HORA quando a rede volta, a aba volta ao foco ou o celular desbloqueia a tela;
// - percebe conexão "morta" (Wi-Fi trocou, celular dormiu): sem "pong" em 45 s, fecha e reabre;
// - window.dispatchEvent(new Event("jarvis_reconnect_now")) força uma tentativa (botão da faixa).
export const RECONNECT_EVENT = "jarvis_reconnect_now";
const PING_MS = 15_000;
const DEAD_MS = 45_000;

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
    let attempt = 0;
    let lastSeen = 0;

    const clearTimers = () => {
      clearTimeout(retryTimer);
      clearInterval(pingTimer);
    };

    const scheduleRetry = () => {
      clearTimeout(retryTimer);
      retryTimer = setTimeout(connect, reconnectDelay(attempt));
      attempt += 1;
    };

    function connect() {
      if (closedByUs) return;
      clearTimers();
      const token = getJarvisToken();
      const wsUrlWithToken = token ? `${WS_URL}?token=${encodeURIComponent(token)}` : WS_URL;
      let socket;
      try {
        socket = new WebSocket(wsUrlWithToken);
      } catch {
        scheduleRetry();
        return;
      }
      ws = socket;

      socket.onopen = () => {
        attempt = 0;
        lastSeen = Date.now();
        onConnectedRef.current?.(true);
        pingTimer = setInterval(() => {
          if (socket.readyState !== 1) return;
          if (Date.now() - lastSeen > DEAD_MS) {
            socket.close(); // conexão parada sem aviso: o onclose reconecta
            return;
          }
          socket.send("ping");
        }, PING_MS);
      };

      socket.onmessage = (event) => {
        lastSeen = Date.now();
        if (event.data === "pong") return;
        let msg;
        try {
          msg = JSON.parse(event.data);
        } catch {
          return; // mensagem quebrada não derruba a central
        }
        window.dispatchEvent(new CustomEvent("jarvis_ws_event", { detail: msg }));
        onMessageRef.current?.(msg);
      };

      socket.onclose = () => {
        if (ws !== socket) return; // já trocamos por uma conexão nova
        clearInterval(pingTimer);
        onConnectedRef.current?.(false);
        if (!closedByUs) scheduleRetry();
      };
    }

    // Tentar agora (rede voltou, aba visível, botão "reconectar"), sem esperar o próximo intervalo
    const reconnectNow = () => {
      if (closedByUs || document.visibilityState === "hidden") return;
      if (ws && (ws.readyState === 0 || ws.readyState === 1)) {
        // Aberta: confere se ainda responde (o celular pode ter dormido com ela "aberta")
        if (ws.readyState === 1 && Date.now() - lastSeen > PING_MS) {
          try {
            ws.send("ping");
          } catch {
            /* o onclose cuida */
          }
        }
        return;
      }
      attempt = 0;
      connect();
    };

    connect();
    window.addEventListener("online", reconnectNow);
    window.addEventListener("focus", reconnectNow);
    window.addEventListener(RECONNECT_EVENT, reconnectNow);
    document.addEventListener("visibilitychange", reconnectNow);
    return () => {
      closedByUs = true;
      clearTimers();
      window.removeEventListener("online", reconnectNow);
      window.removeEventListener("focus", reconnectNow);
      window.removeEventListener(RECONNECT_EVENT, reconnectNow);
      document.removeEventListener("visibilitychange", reconnectNow);
      ws?.close();
    };
  }, []);
}

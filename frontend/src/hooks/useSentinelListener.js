import { useCallback, useEffect, useRef, useState } from "react";
import { matchUnlock, matchWake } from "../utils/wakeWords.js";

// Modo Sentinela: escuta contínua (sem o limite de 15 s do hook de conversa), reiniciada
// automaticamente, que só reage quando a frase começa com a palavra de ativação.
const SR = typeof window !== "undefined" ? window.SpeechRecognition || window.webkitSpeechRecognition : null;
const AWAKE_WINDOW_MS = 8000;

/**
 * phase: "sleeping" (esperando a palavra) | "awake" (8 s atento para o pedido)
 * status: "off" | "listening" | "blocked" | "unsupported" | "insecure" | "error"
 */
export default function useSentinelListener({ enabled, paused = false, wakeWords, onCommand, onWake, onUnlock }) {
  const [status, setStatus] = useState("off");
  const [phase, setPhase] = useState("sleeping");
  const [interim, setInterim] = useState("");
  const recRef = useRef(null);
  const activeRef = useRef(false);
  const awakeUntilRef = useRef(0);
  const restartTimerRef = useRef(null);
  const backoffRef = useRef(400);
  const blockedRef = useRef(false);
  const cbRef = useRef({ onCommand, onWake, onUnlock });
  const wakeRef = useRef(wakeWords);
  cbRef.current = { onCommand, onWake, onUnlock };
  wakeRef.current = wakeWords;

  const goSleep = useCallback(() => {
    awakeUntilRef.current = 0;
    setPhase("sleeping");
  }, []);

  useEffect(() => {
    if (!enabled || paused) {
      activeRef.current = false;
      clearTimeout(restartTimerRef.current);
      try { recRef.current?.abort(); } catch { /* ignora */ }
      recRef.current = null;
      setInterim("");
      if (!enabled) {
        setStatus("off");
        goSleep();
        blockedRef.current = false;
      }
      return undefined;
    }
    if (!SR) {
      setStatus("unsupported");
      return undefined;
    }
    if (!window.isSecureContext) {
      setStatus("insecure");
      return undefined;
    }
    if (blockedRef.current) {
      setStatus("blocked");
      return undefined;
    }
    activeRef.current = true;

    // V6.5.17: o Chrome às vezes corta a frase numa pausa curta ("Jarvis abre o" + "YouTube").
    // Depois da palavra de ativação, os pedaços que chegam em seguida são juntados e só então enviados.
    const JOIN_MS = 1300;
    let pending = null; // { rest, text, timer }
    const flush = () => {
      if (!pending) return;
      const { rest, text } = pending;
      clearTimeout(pending.timer);
      pending = null;
      goSleep();
      cbRef.current.onCommand?.(rest, text);
    };
    const queue = (rest, text) => {
      if (pending) {
        clearTimeout(pending.timer);
        pending.rest = `${pending.rest} ${rest}`.trim();
        pending.text = `${pending.text} ${text}`.trim();
      } else {
        pending = { rest, text, timer: null };
      }
      pending.timer = setTimeout(flush, JOIN_MS);
    };
    const holdOn = () => {  // ainda falando (resultado parcial): espera mais um pouco
      if (pending) {
        clearTimeout(pending.timer);
        pending.timer = setTimeout(flush, JOIN_MS);
      }
    };

    const handleFinal = (text) => {
      const now = Date.now();
      if (pending) {  // continuação da mesma frase
        queue(text, text);
        return;
      }
      // V4.2.2: "abrir central", "liberar"... vão direto para o escaneamento (com ou sem "Jarvis")
      if (cbRef.current.onUnlock && matchUnlock(text, wakeRef.current || [])) {
        goSleep();
        cbRef.current.onUnlock(text);
        return;
      }
      const awake = now < awakeUntilRef.current;
      const { matched, rest } = matchWake(text, wakeRef.current || []);
      if (matched && !rest) {
        awakeUntilRef.current = now + AWAKE_WINDOW_MS;
        setPhase("awake");
        cbRef.current.onWake?.(text);
        return;
      }
      if (matched || awake) {
        queue(matched ? rest : text, text);
      }
    };

    const start = () => {
      if (!activeRef.current) return;
      const rec = new SR();
      rec.lang = "pt-BR";
      rec.interimResults = true;
      rec.continuous = true;
      rec.maxAlternatives = 1;
      rec.onresult = (event) => {
        let partial = "";
        for (let i = event.resultIndex; i < event.results.length; i += 1) {
          const result = event.results[i];
          if (result.isFinal) handleFinal(result[0].transcript);
          else partial += result[0].transcript;
        }
        setInterim(partial.trim());
        if (partial.trim()) holdOn();
        backoffRef.current = 400;
        if (awakeUntilRef.current && Date.now() > awakeUntilRef.current) goSleep();
      };
      rec.onerror = (event) => {
        if (event.error === "not-allowed" || event.error === "service-not-allowed") {
          blockedRef.current = true;
          activeRef.current = false;
          setStatus("blocked");
        } else if (event.error === "network") {
          backoffRef.current = Math.min(10000, backoffRef.current * 2);
        }
      };
      rec.onend = () => {
        recRef.current = null;
        setInterim("");
        if (activeRef.current) {
          // O Chrome encerra a escuta sozinho de tempos em tempos: reinicia
          restartTimerRef.current = setTimeout(start, backoffRef.current);
        }
      };
      try {
        rec.start();
        recRef.current = rec;
        setStatus("listening");
      } catch {
        restartTimerRef.current = setTimeout(start, 1500);
      }
    };
    start();

    const sleepTimer = setInterval(() => {
      if (awakeUntilRef.current && Date.now() > awakeUntilRef.current) goSleep();
    }, 1000);

    return () => {
      activeRef.current = false;
      clearInterval(sleepTimer);
      clearTimeout(restartTimerRef.current);
      try { recRef.current?.abort(); } catch { /* ignora */ }
      recRef.current = null;
    };
  }, [enabled, paused, goSleep]);

  // Conversa contínua: depois de responder, fica atento de novo (sem precisar da palavra de ativação)
  const keepAwake = useCallback((ms = AWAKE_WINDOW_MS) => {
    awakeUntilRef.current = Date.now() + ms;
    setPhase("awake");
  }, []);

  return { status, phase, interim, supported: Boolean(SR), goSleep, keepAwake };
}

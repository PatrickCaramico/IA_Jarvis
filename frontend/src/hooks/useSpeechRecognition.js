import { useCallback, useEffect, useRef, useState } from "react";

// Reconhecimento de voz nativo do navegador (Chrome/Edge).
const SR = typeof window !== "undefined" ? window.SpeechRecognition || window.webkitSpeechRecognition : null;

// V4.5: dentro do app Android do JARVIS, o WebView não tem o reconhecimento do Chrome; o app expõe o
// reconhecedor de voz do Android (JarvisApp.listen) e devolve o texto pelo evento "jarvis-native-speech".
function nativeSpeech() {
  try {
    return typeof window !== "undefined" && Boolean(window.JarvisApp?.hasNativeSpeech?.());
  } catch {
    return false;
  }
}

const ERROR_TEXT = {
  "not-allowed": "O navegador bloqueou o microfone. Clique no cadeado ao lado do endereço e permita o microfone.",
  "service-not-allowed": "O navegador bloqueou o reconhecimento de voz nesta página.",
  "audio-capture": "Não encontrei um microfone. Verifique se ele está conectado.",
  network: "Falha no reconhecimento de voz. Ele precisa de internet.",
};

const SILENCE_TIMEOUT_MS = 2200; // Tempo de silêncio após falar para enviar automaticamente
const MAX_WAIT_TIMEOUT_MS = 15000; // Tempo máximo de espera se você não disser nada

function microphoneError(error) {
  if (error?.name === "NotAllowedError" || error?.name === "SecurityError") {
    return ERROR_TEXT["not-allowed"];
  }
  if (error?.name === "NotFoundError" || error?.name === "DevicesNotFoundError") {
    return ERROR_TEXT["audio-capture"];
  }
  return "Não foi possível acessar o microfone. Verifique as permissões do navegador e tente novamente.";
}

export default function useSpeechRecognition({ onFinal, onError, deviceId }) {
  const recRef = useRef(null);
  const canceledRef = useRef(false);
  const onFinalRef = useRef(onFinal);
  const onErrorRef = useRef(onError);
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState("");

  const silenceTimerRef = useRef(null);
  const maxWaitTimerRef = useRef(null);
  const textBufferRef = useRef("");
  const startingRef = useRef(false);

  useEffect(() => {
    onFinalRef.current = onFinal;
    onErrorRef.current = onError;
  }, [onFinal, onError]);

  const clearTimers = () => {
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    if (maxWaitTimerRef.current) clearTimeout(maxWaitTimerRef.current);
    silenceTimerRef.current = null;
    maxWaitTimerRef.current = null;
  };

  const nativeRef = useRef(null); // { off() } enquanto o microfone do app Android está ouvindo

  const startNative = useCallback(() => {
    if (nativeRef.current) return;
    canceledRef.current = false;
    textBufferRef.current = "";
    const onEvent = (e) => {
      const { type, text } = e.detail || {};
      if (type === "partial") setInterim(text || "");
      else if (type === "final") { textBufferRef.current = (text || "").trim(); setInterim(textBufferRef.current); }
      else if (type === "error") onErrorRef.current?.(text);
      else if (type === "end") {
        window.removeEventListener("jarvis-native-speech", onEvent);
        nativeRef.current = null;
        setListening(false);
        setInterim("");
        const finalText = textBufferRef.current.trim();
        if (finalText && !canceledRef.current) onFinalRef.current?.(finalText);
      }
    };
    window.addEventListener("jarvis-native-speech", onEvent);
    nativeRef.current = { off: () => window.removeEventListener("jarvis-native-speech", onEvent) };
    setListening(true);
    window.JarvisApp.listen();
  }, []);

  const start = useCallback(async () => {
    if (nativeSpeech()) { startNative(); return; }
    if (!SR || recRef.current || startingRef.current) return;
    if (!window.isSecureContext) {
      onErrorRef.current?.("O microfone exige uma conexão segura. Use localhost ou HTTPS.");
      return;
    }
    startingRef.current = true;
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error("media-devices-unavailable");
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: deviceId ? { deviceId: { exact: deviceId } } : true,
      });
      stream?.getTracks().forEach((track) => track.stop());
    } catch (error) {
      startingRef.current = false;
      onErrorRef.current?.(microphoneError(error));
      return;
    }
    canceledRef.current = false;
    textBufferRef.current = "";
    clearTimers();

    const rec = new SR();
    rec.lang = "pt-BR";
    rec.interimResults = true;
    rec.continuous = true; // Permite ficar ouvindo por mais tempo sem desligar no primeiro silêncio
    rec.maxAlternatives = 1;

    // Timeout máximo se o usuário não falar nada
    maxWaitTimerRef.current = setTimeout(() => {
      if (recRef.current) {
        rec.stop();
      }
    }, MAX_WAIT_TIMEOUT_MS);

    rec.onresult = (event) => {
      let finalChunk = "";
      let partial = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        if (result.isFinal) finalChunk += result[0].transcript;
        else partial += result[0].transcript;
      }
      if (finalChunk) {
        textBufferRef.current = (textBufferRef.current + " " + finalChunk).trim();
      }
      const currentFull = (textBufferRef.current + " " + partial).trim();
      setInterim(currentFull);

      // Reinicia o timer de silêncio após fala
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      if (currentFull) {
        // Se começou a falar, cancela o timer de espera inicial
        if (maxWaitTimerRef.current) clearTimeout(maxWaitTimerRef.current);
        silenceTimerRef.current = setTimeout(() => {
          if (recRef.current) rec.stop();
        }, SILENCE_TIMEOUT_MS);
      }
    };

    rec.onerror = (event) => {
      if (event.error === "no-speech" || event.error === "aborted") return;
      onErrorRef.current?.(ERROR_TEXT[event.error] ?? `Erro no microfone: ${event.error}`);
    };

    rec.onend = () => {
      clearTimers();
      recRef.current = null;
      startingRef.current = false;
      setListening(false);
      setInterim("");
      const text = textBufferRef.current.trim();
      if (text && !canceledRef.current) {
        onFinalRef.current?.(text);
      }
    };

    try {
      rec.start();
      recRef.current = rec;
      setListening(true);
    } catch (error) {
      recRef.current = null;
      onErrorRef.current?.(microphoneError(error));
    } finally {
      startingRef.current = false;
    }
  }, [deviceId, startNative]);

  const stop = useCallback(() => {
    clearTimers();
    if (nativeRef.current) { window.JarvisApp?.stopListen?.(false); return; }
    recRef.current?.stop();
  }, []);

  const cancel = useCallback(() => {
    canceledRef.current = true;
    clearTimers();
    if (nativeRef.current) { window.JarvisApp?.stopListen?.(true); return; }
    recRef.current?.abort?.();
  }, []);

  useEffect(() => () => {
    clearTimers();
    recRef.current?.abort?.();
    nativeRef.current?.off();
  }, []);

  return { listening, interim, start, stop, cancel, supported: Boolean(SR) || nativeSpeech() };
}

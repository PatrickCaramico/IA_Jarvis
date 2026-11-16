import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api.js";

// V8.4.0 (ideia 10): VOZ ENTENDIDA PELA GROQ na ilha e no app do Windows. Dentro do app, o reconhecimento de voz
// do navegador não funciona bem; aqui o 🎙 grava o pedido (para sozinho quando você para de falar) e o PC manda
// para a Groq transcrever (/api/voice/transcribe). O áudio não é guardado.

// O que conta como fala se ajusta ao ruído do ambiente: 3x o ruído de fundo, com um mínimo (microfones de
// notebook com redução de ruído chegam baixinho, ~0,02).
const MIN_SPEECH_LEVEL = 0.012;

/** Volume que conta como fala, dado o ruído de fundo medido. */
export function speechThreshold(floor) {
  return Math.max(MIN_SPEECH_LEVEL, (Number(floor) || 0) * 3);
}
const MIC_ERRORS = {
  NotAllowedError: "O Windows não deixou o app usar o microfone. Em Configurações > Privacidade > Microfone, permita os apps da área de trabalho.",
  NotFoundError: "Não encontrei um microfone conectado.",
};

/** Volume (0..1) de um pedaço de áudio (bytes 0..255 centrados em 128). */
export function rmsLevel(bytes) {
  if (!bytes || !bytes.length) return 0;
  let sum = 0;
  for (let i = 0; i < bytes.length; i++) {
    const v = (bytes[i] - 128) / 128;
    sum += v * v;
  }
  return Math.sqrt(sum / bytes.length);
}

/** Decide o que fazer a cada instante: "seguir", "fim" (falou e calou) ou "nada" (não falou nada). */
export function recordStep({ now, start, lastLoud, spoke, maxMs = 15000, silenceMs = 1300, waitMs = 6000 }) {
  if (now - start >= maxMs) return spoke ? "fim" : "nada";
  if (spoke && now - lastLoud >= silenceMs) return "fim";
  if (!spoke && now - start >= waitMs) return "nada";
  return "seguir";
}

/** Grava UM pedido. Devolve { stop, done } — `done` resolve com o Blob do áudio, ou null se ninguém falou. */
export async function recordUtterance(opts = {}) {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
  const mime = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus"].find((m) => window.MediaRecorder?.isTypeSupported?.(m)) || "";
  const rec = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
  const chunks = [];
  rec.ondataavailable = (e) => e.data && e.data.size && chunks.push(e.data);
  const Ctx = window.AudioContext || window.webkitAudioContext;
  const ctx = Ctx ? new Ctx() : null;
  if (ctx?.state === "suspended") ctx.resume?.().catch?.(() => {});
  const analyser = ctx ? ctx.createAnalyser() : null;
  if (ctx && analyser) {
    analyser.fftSize = 1024;
    ctx.createMediaStreamSource(stream).connect(analyser);
  }
  const buf = new Uint8Array(analyser ? analyser.fftSize : 0);
  const start = Date.now();
  let lastLoud = start;
  let spoke = !analyser; // sem medidor de volume: confia que falou e para pelo tempo
  let floor = Infinity; // ruído de fundo: o menor volume visto
  let timer = 0;
  const done = new Promise((resolve) => {
    rec.onstop = () => {
      clearInterval(timer);
      stream.getTracks().forEach((t) => t.stop());
      ctx?.close?.().catch?.(() => {});
      resolve(spoke && chunks.length ? new Blob(chunks, { type: rec.mimeType || mime || "audio/webm" }) : null);
    };
  });
  const stop = () => rec.state !== "inactive" && rec.stop();
  timer = setInterval(() => {
    if (analyser) {
      analyser.getByteTimeDomainData(buf);
      const level = rmsLevel(buf);
      floor = Math.min(floor, level);
      if (level > speechThreshold(floor)) {
        spoke = true;
        lastLoud = Date.now();
      }
    }
    const step = recordStep({ now: Date.now(), start, lastLoud, spoke, ...opts });
    if (step !== "seguir") {
      if (step === "nada") spoke = false;
      stop();
    }
  }, 100);
  rec.start(250);
  return { stop, done };
}

/** 🎙 pela Groq: toggle() começa/para; ao terminar chama onText(texto). Estados: idle | ouvindo | entendendo. */
export function useGroqVoice({ onText, onError } = {}) {
  const [phase, setPhase] = useState("idle");
  const recRef = useRef(null);
  const cbs = useRef({ onText, onError });
  useEffect(() => { cbs.current = { onText, onError }; }, [onText, onError]);
  useEffect(() => () => recRef.current?.stop(), []);
  const toggle = useCallback(async () => {
    if (recRef.current) {
      recRef.current.stop();
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      cbs.current.onError?.("Este app não consegue gravar áudio. Escreva o pedido.");
      return;
    }
    try {
      const rec = await recordUtterance();
      recRef.current = rec;
      setPhase("ouvindo");
      const blob = await rec.done;
      recRef.current = null;
      if (!blob) {
        setPhase("idle");
        cbs.current.onError?.("Não ouvi nada. Toque em 🎙 e fale.");
        return;
      }
      setPhase("entendendo");
      const r = await api("/api/voice/transcribe", { method: "POST", body: blob, headers: { "Content-Type": blob.type || "audio/webm" }, timeout: 40000 });
      setPhase("idle");
      if (r?.texto) cbs.current.onText?.(r.texto);
      else cbs.current.onError?.("Não entendi. Tente de novo ou escreva.");
    } catch (e) {
      recRef.current = null;
      setPhase("idle");
      cbs.current.onError?.(MIC_ERRORS[e?.name] || e?.message || "Não consegui usar o microfone.");
    }
  }, []);
  return { phase, listening: phase === "ouvindo", busy: phase === "entendendo", toggle };
}

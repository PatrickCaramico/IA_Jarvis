import { useEffect, useRef, useState } from "react";
import { createClapDetector } from "../utils/clapDetector.js";

/**
 * useClapDetector — abre o microfone e detecta PALMA DUPLA (seção 14).
 *
 * - O áudio é processado só no navegador: calcula-se a energia de quadros de 10 ms depois de um
 *   passa-alta de 1 kHz. Nada é gravado nem enviado ao backend.
 * - AudioWorklet (carregado por Blob URL) roda na thread de áudio; se não existir, usa
 *   AnalyserNode lido por setInterval (só funciona bem com a aba visível).
 * - enabled=false fecha as trilhas do microfone e o AudioContext.
 * - paused=true mantém o microfone aberto, mas ignora o áudio (ex.: JARVIS falando).
 *
 * status: "off" | "starting" | "listening" | "blocked" | "unsupported" | "insecure" | "error"
 */
const WORKLET_CODE = `
class JarvisClapEnergy extends AudioWorkletProcessor {
  constructor() {
    super();
    this.size = Math.max(64, Math.round(sampleRate * 0.01));
    this.sum = 0;
    this.n = 0;
  }
  process(inputs) {
    const ch = inputs[0] && inputs[0][0];
    if (ch) {
      for (let i = 0; i < ch.length; i += 1) {
        const v = ch[i];
        this.sum += v * v;
        this.n += 1;
        if (this.n >= this.size) {
          const t = ((currentFrame + i) / sampleRate) * 1000;
          this.port.postMessage({ energy: Math.sqrt(this.sum / this.n), t });
          this.sum = 0;
          this.n = 0;
        }
      }
    }
    return true;
  }
}
registerProcessor("jarvis-clap-energy", JarvisClapEnergy);
`;

export default function useClapDetector({
  enabled,
  paused = false,
  deviceId = "",
  sensitivity = 5,
  cooldownMs = 3000,
  onDoubleClap,
  onFrame,
}) {
  const [status, setStatus] = useState("off");
  const [level, setLevel] = useState(0);
  const [needsGesture, setNeedsGesture] = useState(false);
  const cbRef = useRef(onDoubleClap);
  const frameRef = useRef(onFrame);
  const pausedRef = useRef(paused);
  const detRef = useRef(null);

  cbRef.current = onDoubleClap;
  frameRef.current = onFrame;

  useEffect(() => {
    pausedRef.current = paused;
    if (paused) detRef.current?.reset(); // ao retomar, começa do zero (exige silêncio antes)
  }, [paused]);

  useEffect(() => {
    detRef.current?.setSensitivity(sensitivity);
  }, [sensitivity]);

  useEffect(() => {
    if (!enabled) {
      setStatus("off");
      setLevel(0);
      setNeedsGesture(false);
      return undefined;
    }
    if (typeof window === "undefined" || !window.isSecureContext) {
      setStatus("insecure");
      return undefined;
    }
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!navigator.mediaDevices?.getUserMedia || !AC) {
      setStatus("unsupported");
      return undefined;
    }

    let cancelled = false;
    let stream = null;
    let ctx = null;
    let node = null;
    let mute = null;
    let interval = null;
    let workletUrl = null;
    let resumeHandler = null;
    let lastLevelAt = 0;
    const det = createClapDetector({ sensitivity, cooldownMs });
    detRef.current = det;
    setStatus("starting");

    const handleFrame = (energy, tMs) => {
      if (cancelled) return;
      const now = performance.now();
      if (now - lastLevelAt > 66) { // ~15 atualizações por segundo no medidor
        lastLevelAt = now;
        setLevel(pausedRef.current ? 0 : energy);
      }
      if (pausedRef.current) return;
      frameRef.current?.(energy, tMs);
      if (det.process(energy, tMs) === "double") cbRef.current?.();
    };

    (async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            ...(deviceId ? { deviceId: { exact: deviceId } } : {}),
            echoCancellation: false, // filtros do navegador suavizam ou removem o pico da palma
            noiseSuppression: false,
            autoGainControl: false,
          },
        });
      } catch (err) {
        if (!cancelled) {
          setStatus(err?.name === "NotAllowedError" || err?.name === "SecurityError" ? "blocked" : "error");
        }
        return;
      }
      if (cancelled) {
        stream.getTracks().forEach((t) => t.stop());
        return;
      }
      try {
        ctx = new AC();
        const src = ctx.createMediaStreamSource(stream);
        const filter = ctx.createBiquadFilter();
        filter.type = "highpass";
        filter.frequency.value = 1000;
        filter.Q.value = 0.7;
        src.connect(filter);
        mute = ctx.createGain();
        mute.gain.value = 0; // o grafo precisa chegar ao destino para processar, mas sem som
        mute.connect(ctx.destination);

        let usingWorklet = false;
        if (ctx.audioWorklet && typeof AudioWorkletNode !== "undefined") {
          try {
            workletUrl = URL.createObjectURL(new Blob([WORKLET_CODE], { type: "application/javascript" }));
            await ctx.audioWorklet.addModule(workletUrl);
            if (cancelled) return;
            node = new AudioWorkletNode(ctx, "jarvis-clap-energy", { numberOfInputs: 1, numberOfOutputs: 1, outputChannelCount: [1] });
            node.port.onmessage = (e) => handleFrame(e.data.energy, e.data.t);
            filter.connect(node);
            node.connect(mute);
            usingWorklet = true;
          } catch {
            usingWorklet = false;
          }
        }
        if (!usingWorklet) {
          const analyser = ctx.createAnalyser();
          analyser.fftSize = 512;
          filter.connect(analyser);
          analyser.connect(mute);
          node = analyser;
          const buf = new Float32Array(analyser.fftSize);
          const frameSamples = Math.min(buf.length, Math.round(ctx.sampleRate * 0.01));
          interval = setInterval(() => {
            analyser.getFloatTimeDomainData(buf);
            let sum = 0;
            for (let i = buf.length - frameSamples; i < buf.length; i += 1) sum += buf[i] * buf[i];
            handleFrame(Math.sqrt(sum / frameSamples), ctx.currentTime * 1000);
          }, 10);
        }

        if (ctx.state === "suspended") {
          // Política de reprodução automática: precisa de um clique/tecla na página
          setNeedsGesture(true);
          resumeHandler = () => {
            ctx?.resume().then(() => setNeedsGesture(false)).catch(() => {});
          };
          window.addEventListener("pointerdown", resumeHandler);
          window.addEventListener("keydown", resumeHandler);
          ctx.resume().then(() => { if (ctx?.state === "running") setNeedsGesture(false); }).catch(() => {});
        }
        ctx.onstatechange = () => {
          if (ctx?.state === "running") setNeedsGesture(false);
        };
        if (!cancelled) setStatus("listening");
      } catch {
        if (!cancelled) setStatus("error");
      }
    })();

    return () => {
      cancelled = true;
      if (interval) clearInterval(interval);
      if (resumeHandler) {
        window.removeEventListener("pointerdown", resumeHandler);
        window.removeEventListener("keydown", resumeHandler);
      }
      try { if (node?.port) node.port.onmessage = null; } catch { /* ignora */ }
      try { node?.disconnect(); } catch { /* ignora */ }
      try { mute?.disconnect(); } catch { /* ignora */ }
      stream?.getTracks().forEach((t) => t.stop()); // libera o microfone
      ctx?.close().catch(() => {});
      if (workletUrl) URL.revokeObjectURL(workletUrl);
      detRef.current = null;
      setLevel(0);
    };
    // sensitivity é aplicada sem reabrir o microfone (efeito acima)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, deviceId, cooldownMs]);

  return { status, level, needsGesture };
}

export const CLAP_STATUS_TEXT = {
  off: "Desligado",
  starting: "Abrindo microfone...",
  listening: "Ouvindo palmas",
  blocked: "Microfone bloqueado pelo navegador",
  unsupported: "Navegador sem suporte a áudio",
  insecure: "Palmas indisponíveis nesta conexão",
  error: "Não consegui abrir o microfone",
};

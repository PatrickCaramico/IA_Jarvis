import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

// V6.8.2: câmera do APARELHO, como na Alexa ("Jarvis, abre a câmera").
// - Ao vivo, só aqui: nenhuma imagem sai do aparelho enquanto você só olha.
// - FOTO: salva no aparelho (download). TROCAR: frontal/traseira.
// - O QUE É ISSO?: manda UMA foto à IA (PC ou nuvem) e a resposta aparece e é falada.
// autoShot: "tira uma foto" -> contagem 3, 2, 1 e foto.
export default function CameraWindow({ api, onClose, onAnswer, autoShot = false }) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [facing, setFacing] = useState("user");
  const [error, setError] = useState("");
  const [count, setCount] = useState(autoShot ? 3 : 0);
  const [flash, setFlash] = useState(false);
  const [asking, setAsking] = useState(false);
  const [answer, setAnswer] = useState("");
  const [question, setQuestion] = useState("");
  const [shots, setShots] = useState(0);

  useEffect(() => {
    let alive = true;
    (async () => {
      setError("");
      try {
        streamRef.current?.getTracks().forEach((t) => t.stop());
        const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: facing, width: { ideal: 1280 } }, audio: false });
        if (!alive) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) videoRef.current.srcObject = stream;
      } catch (err) {
        setError(err?.name === "NotAllowedError"
          ? "O acesso à câmera foi negado. Permita a câmera para o JARVIS (no navegador: cadeado ao lado do endereço)."
          : "Não encontrei uma câmera neste aparelho.");
      }
    })();
    return () => {
      alive = false;
    };
  }, [facing]);

  useEffect(() => () => streamRef.current?.getTracks().forEach((t) => t.stop()), []);

  const grab = useCallback((maxWidth = 1280) => {
    const v = videoRef.current;
    if (!v || !v.videoWidth) return null;
    const scale = Math.min(1, maxWidth / v.videoWidth);
    const c = document.createElement("canvas");
    c.width = Math.round(v.videoWidth * scale);
    c.height = Math.round(v.videoHeight * scale);
    const ctx = c.getContext("2d");
    if (facing === "user") {
      ctx.translate(c.width, 0);
      ctx.scale(-1, 1); // a frontal aparece espelhada na tela; a foto sai como no espelho também
    }
    ctx.drawImage(v, 0, 0, c.width, c.height);
    return c;
  }, [facing]);

  const takePhoto = useCallback(() => {
    const c = grab(1920);
    if (!c) return;
    setFlash(true);
    setTimeout(() => setFlash(false), 180);
    c.toBlob((blob) => {
      if (!blob) return;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      const now = new Date();
      a.href = url;
      a.download = `jarvis-foto-${now.toISOString().slice(0, 19).replace(/[:T]/g, "-")}.jpg`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
      setShots((n) => n + 1);
    }, "image/jpeg", 0.92);
  }, [grab]);

  // "tira uma foto": 3, 2, 1
  useEffect(() => {
    if (count <= 0) return undefined;
    const t = setTimeout(() => {
      if (count === 1) takePhoto();
      setCount((n) => n - 1);
    }, 900);
    return () => clearTimeout(t);
  }, [count, takePhoto]);

  const ask = async (spoken) => {
    const c = grab(1024);
    if (!c || asking) return;
    setAsking(true);
    setAnswer("");
    try {
      const image = c.toDataURL("image/jpeg", 0.8);
      const r = await api("/api/camera/ask", { method: "POST", body: JSON.stringify({ image, question: (typeof spoken === "string" ? spoken : question).trim() }), timeout: 45_000 });
      setAnswer(r.text || "");
      onAnswer?.(r.text || "");
    } catch (err) {
      setAnswer(err.message || "Não consegui analisar a foto agora.");
    } finally {
      setAsking(false);
    }
  };

  // "o que é isso?" falado com a câmera aberta
  const askRef = useRef(null);
  askRef.current = ask;
  useEffect(() => {
    const onAsk = (e) => {
      setQuestion(e.detail || "");
      setTimeout(() => askRef.current?.(e.detail || ""), 0);
    };
    window.addEventListener("jarvis-camera-ask", onAsk);
    return () => window.removeEventListener("jarvis-camera-ask", onAsk);
  }, []);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return createPortal(
    <div className="camw-overlay" role="dialog" aria-modal="true" aria-label="Câmera do JARVIS">
      <div className="camw">
        <header className="camw-head">
          <span>📷 CÂMERA</span>
          <small>{shots ? `${shots} ${shots === 1 ? "foto salva" : "fotos salvas"} neste aparelho` : "Ao vivo só aqui: nada sai do aparelho"}</small>
          <button type="button" className="camw-x" onClick={onClose} aria-label="Fechar a câmera">✕</button>
        </header>
        <div className="camw-view">
          {error ? <p className="camw-error" role="alert">{error}</p> : (
            <video ref={videoRef} autoPlay playsInline muted className={facing === "user" ? "is-mirror" : ""} />
          )}
          {count > 0 && <div className="camw-count" aria-live="assertive">{count}</div>}
          {flash && <div className="camw-flash" aria-hidden="true" />}
        </div>
        {answer && <p className="camw-answer" role="status">{answer}</p>}
        <div className="camw-ask">
          <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Pergunta (opcional): que planta é essa?" aria-label="Pergunta sobre a foto" />
          <button type="button" onClick={() => ask()} disabled={asking || Boolean(error)}>{asking ? "OLHANDO…" : "🔍 O QUE É ISSO?"}</button>
        </div>
        <div className="camw-actions">
          <button type="button" onClick={() => setFacing((f) => (f === "user" ? "environment" : "user"))} disabled={Boolean(error) && facing === "environment"}>↺ TROCAR</button>
          <button type="button" className="camw-shot" onClick={takePhoto} disabled={Boolean(error)} aria-label="Tirar foto">📸 FOTO</button>
          <button type="button" onClick={() => setCount(3)} disabled={Boolean(error) || count > 0}>⏱ 3 s</button>
        </div>
        <p className="camw-note">"O que é isso?" manda só aquela foto à IA, e ela não é guardada.</p>
      </div>
    </div>,
    document.body,
  );
}

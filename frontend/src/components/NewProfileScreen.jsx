import { useEffect, useRef, useState } from "react";
import { BlueprintStamp } from "./LockScreen.jsx";

// V4.5: cadastro de uma pessoa nova neste PC (perfil próprio: rosto, PIN e preferências).
// Etapas: autorização do dono (PIN, se ele tiver) -> nome + foto (webcam ou arquivo) -> PIN opcional.
// Tudo fica só neste computador.

function useWebcam(active) {
  const videoRef = useRef(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!active) return undefined;
    let stream;
    let cancelled = false;
    navigator.mediaDevices?.getUserMedia({ video: { width: 640, height: 480 }, audio: false })
      .then((s) => {
        if (cancelled) { s.getTracks().forEach((t) => t.stop()); return; }
        stream = s;
        if (videoRef.current) videoRef.current.srcObject = s;
      })
      .catch(() => setError("Não consegui abrir a câmera. Escolha uma foto do computador."));
    return () => {
      cancelled = true;
      stream?.getTracks().forEach((t) => t.stop()); // libera a câmera para o reconhecimento do JARVIS
    };
  }, [active]);
  return { videoRef, error };
}

function snapshot(video) {
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", 0.92);
}

function readFile(file) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(r.result);
    r.onerror = () => reject(new Error("Não consegui abrir essa imagem."));
    r.readAsDataURL(file);
  });
}

export default function NewProfileScreen({ api, onCreated, onCancel }) {
  const [info, setInfo] = useState(null);
  const [step, setStep] = useState("loading"); // loading | owner | person | pin
  const [ownerPin, setOwnerPin] = useState("");
  const [name, setName] = useState("");
  const [photo, setPhoto] = useState(null);
  const [pin, setPin] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const { videoRef, error: camError } = useWebcam(step === "person" && !photo);

  useEffect(() => {
    api("/api/profiles/lock-info")
      .then((d) => { setInfo(d); setStep(d.owner_pin_required ? "owner" : "person"); })
      .catch((e) => { setError(e.message); setStep("person"); });
  }, [api]);

  const submit = async () => {
    setBusy(true);
    setError("");
    try {
      const res = await api("/api/profiles", {
        method: "POST",
        body: JSON.stringify({ name: name.trim(), photo, pin: pin || null, owner_pin: ownerPin || null }),
      });
      onCreated(res);
    } catch (e) {
      setError(e.message);
      if (/PIN do perfil principal/.test(e.message)) { setStep("owner"); setOwnerPin(""); }
      else if (/rosto|foto|imagem/i.test(e.message)) { setStep("person"); setPhoto(null); }
    } finally {
      setBusy(false);
    }
  };

  const steps = info?.owner_pin_required ? ["owner", "person", "pin"] : ["person", "pin"];
  const idx = Math.max(0, steps.indexOf(step));

  return (
    <div role="main" className="ls-container np-root">
      <div className="ls-bracket ls-bracket-tl" aria-hidden="true" />
      <div className="ls-bracket ls-bracket-tr" aria-hidden="true" />
      <div className="ls-bracket ls-bracket-bl" aria-hidden="true" />
      <div className="ls-bracket ls-bracket-br" aria-hidden="true" />

      <section className="np-card" aria-labelledby="np-title">
        <header className="np-head">
          <span className="np-eyebrow">NOVA PESSOA · ETAPA {idx + 1} / {steps.length}</span>
          <h1 id="np-title">Perfil neste PC</h1>
          <div className="np-progress" aria-hidden="true"><i style={{ width: `${((idx + 1) / steps.length) * 100}%` }} /></div>
        </header>

        {step === "loading" && <p className="np-muted">Carregando…</p>}

        {step === "owner" && (
          <form className="np-body" onSubmit={(e) => { e.preventDefault(); if (ownerPin.length >= 4) setStep("person"); }}>
            <p>Para criar um perfil novo, o dono deste PC autoriza com o <b>PIN dele</b>.</p>
            <label className="np-label" htmlFor="np-owner">PIN DO PERFIL PRINCIPAL</label>
            <input id="np-owner" className="np-input np-pin" type="password" inputMode="numeric" autoComplete="off"
              maxLength={8} value={ownerPin} onChange={(e) => setOwnerPin(e.target.value.replace(/\D/g, ""))} autoFocus />
            <div className="np-actions">
              <button type="button" className="np-btn np-alt" onClick={onCancel}>Cancelar</button>
              <button type="submit" className="np-btn" disabled={ownerPin.length < 4}>Continuar</button>
            </div>
          </form>
        )}

        {step === "person" && (
          <div className="np-body">
            <label className="np-label" htmlFor="np-name">COMO O JARVIS DEVE TE CHAMAR?</label>
            <input id="np-name" className="np-input" value={name} maxLength={30} onChange={(e) => setName(e.target.value)}
              placeholder="Seu nome" autoFocus autoComplete="off" />

            <span className="np-label">SEU ROSTO (é a sua chave de entrada)</span>
            <div className="np-photo">
              {photo ? (
                <img src={photo} alt="Prévia da sua foto" />
              ) : camError ? (
                <span className="np-muted">{camError}</span>
              ) : (
                <video ref={videoRef} autoPlay playsInline muted aria-label="Câmera ao vivo" />
              )}
            </div>
            <div className="np-actions">
              {photo ? (
                <button type="button" className="np-btn np-alt" onClick={() => setPhoto(null)}>Tirar outra</button>
              ) : (
                !camError && <button type="button" className="np-btn np-alt" onClick={() => videoRef.current && setPhoto(snapshot(videoRef.current))}>📸 Tirar foto</button>
              )}
              <label className="np-btn np-alt np-file">
                Escolher arquivo
                <input type="file" accept="image/*" className="sr-only"
                  onChange={async (e) => { const f = e.target.files?.[0]; if (f) setPhoto(await readFile(f)); }} />
              </label>
            </div>
            <p className="np-muted">De frente, sozinho na foto e com boa luz.</p>
            <div className="np-actions">
              <button type="button" className="np-btn np-alt" onClick={onCancel}>Cancelar</button>
              <button type="button" className="np-btn" disabled={!name.trim() || !photo} onClick={() => setStep("pin")}>Continuar</button>
            </div>
          </div>
        )}

        {step === "pin" && (
          <form className="np-body" onSubmit={(e) => { e.preventDefault(); submit(); }}>
            <p>Crie um <b>PIN</b> para entrar quando a câmera não reconhecer (opcional, 4 a 8 dígitos).</p>
            <label className="np-label" htmlFor="np-pin">SEU PIN</label>
            <input id="np-pin" className="np-input np-pin" type="password" inputMode="numeric" autoComplete="off"
              maxLength={8} value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))} autoFocus />
            <div className="np-actions">
              <button type="button" className="np-btn np-alt" onClick={() => setStep("person")}>Voltar</button>
              <button type="submit" className="np-btn" disabled={busy || (pin.length > 0 && pin.length < 4)}>
                {busy ? "Criando…" : "Criar meu perfil"}
              </button>
            </div>
          </form>
        )}

        {error && <p className="np-error" role="alert">{error}</p>}
        <p className="np-foot">Seu perfil, suas preferências e seus dados ficam só neste computador. Ninguém mais vê.</p>
      </section>
      <BlueprintStamp sheet="NOVO PERFIL" />
    </div>
  );
}

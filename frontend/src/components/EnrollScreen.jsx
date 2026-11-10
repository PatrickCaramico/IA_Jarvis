import { useState } from "react";

// Reduz a foto no navegador (máx. 1024px) e devolve um data URL JPEG.
function resizeImage(file, maxSize = 1024) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      const scale = Math.min(1, maxSize / Math.max(img.width, img.height));
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(img.width * scale);
      canvas.height = Math.round(img.height * scale);
      canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      resolve(canvas.toDataURL("image/jpeg", 0.9));
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Não consegui abrir essa imagem. Use JPG ou PNG."));
    };
    img.src = url;
  });
}

export default function EnrollScreen({ initialName, onSave, onSkip, saving, error }) {
  const [name, setName] = useState(initialName ?? "");
  const [photo, setPhoto] = useState(null);
  const [localError, setLocalError] = useState("");

  const pickFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLocalError("");
    try {
      setPhoto(await resizeImage(file));
    } catch (err) {
      setLocalError(err.message);
    }
  };

  return (
    <div className="flex min-h-full flex-col items-center justify-center gap-6 px-5 py-10">
      <h1 className="font-display text-2xl font-bold tracking-[0.25em] text-arc-200">J.A.R.V.I.S.</h1>

      <section className="hud-panel flex w-full max-w-md flex-col items-center gap-5 p-6">
        <h2 className="font-display text-base text-arc-200">Cadastre seu perfil</h2>
        <p className="text-center text-lg text-arc-300/80">
          Escolha uma foto sua, de frente e bem iluminada. O JARVIS vai comparar com a webcam para confirmar que é você.
        </p>

        <div className="flex h-40 w-40 items-center justify-center overflow-hidden rounded-full border-2 border-arc-300 shadow-arc">
          {photo ? (
            <img src={photo} alt="Prévia da foto" className="h-full w-full object-cover" />
          ) : (
            <span className="text-arc-300/60">Sem foto</span>
          )}
        </div>

        <label className="cursor-pointer rounded border border-arc-400/60 px-5 py-2 text-lg text-arc-100 hover:bg-arc-500/20">
          {photo ? "Escolher outra foto" : "Escolher foto"}
          <input type="file" accept="image/*" onChange={pickFile} className="sr-only" />
        </label>

        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Como o JARVIS deve te chamar?"
          className="w-full rounded border border-arc-700 bg-void/60 px-4 py-2 text-lg text-arc-100 placeholder:text-arc-300/50 focus:border-arc-300 focus:outline-none"
        />

        {(localError || error) && <p className="text-center text-red-400">{localError || error}</p>}

        <button
          type="button"
          disabled={!photo || saving}
          onClick={() => onSave(name.trim(), photo)}
          className="w-full rounded border border-arc-300 bg-arc-500/15 px-6 py-3 font-display text-sm tracking-widest text-arc-100 shadow-arc transition hover:bg-arc-400/30 focus:outline-none focus-visible:ring-2 focus-visible:ring-arc-200 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {saving ? "Salvando…" : "Salvar e verificar"}
        </button>

        <button type="button" onClick={onSkip} className="text-base text-arc-300/70 underline underline-offset-4 hover:text-arc-100">
          Pular por enquanto
        </button>
      </section>
    </div>
  );
}

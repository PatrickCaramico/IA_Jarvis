import { useEffect, useState } from "react";

export default function MicrophoneSelectModal({ onConfirm, onClose }) {
  const [microphones, setMicrophones] = useState([]);
  const [selectedId, setSelectedId] = useState(() => localStorage.getItem("jarvis.microphone.id") || "");
  const [status, setStatus] = useState("Solicitando acesso aos microfones…");

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        if (!navigator.mediaDevices?.getUserMedia) throw new Error("unsupported");
        const permissionStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        permissionStream.getTracks().forEach((track) => track.stop());
        const devices = (await navigator.mediaDevices.enumerateDevices())
          .filter((item) => item.kind === "audioinput");
        if (!active) return;
        setMicrophones(devices);
        setSelectedId((current) => (
          devices.some((item) => item.deviceId === current)
            ? current
            : devices[0]?.deviceId || ""
        ));
        setStatus(devices.length ? "Selecione o microfone que o JARVIS deve usar." : "Nenhum microfone encontrado.");
      } catch (error) {
        if (active) setStatus(error.name === "NotAllowedError"
          ? "Permissão de microfone negada no navegador."
          : "Não foi possível acessar os microfones.");
      }
    };
    load();
    return () => { active = false; };
  }, []);

  const confirm = () => {
    if (!selectedId) return;
    localStorage.setItem("jarvis.microphone.id", selectedId);
    onConfirm(selectedId);
  };

  return (
    <div className="fixed inset-0 z-[75] flex items-center justify-center bg-void/85 p-4 backdrop-blur-sm">
      <section className="hud-panel w-full max-w-md p-6 shadow-arc" role="dialog" aria-modal="true" aria-label="Escolher microfone">
        <div className="mb-5 flex items-start justify-between">
          <div>
            <h2 className="font-display text-sm tracking-widest text-arc-100">ESCOLHA SEU MICROFONE</h2>
            <p className="mt-1 text-xs text-arc-300/70">O JARVIS usará esta opção para ouvir seus comandos.</p>
          </div>
          <button type="button" onClick={onClose} className="text-arc-300/70 hover:text-arc-100" aria-label="Fechar">✕</button>
        </div>

        <div className="space-y-2">
          {microphones.map((microphone, index) => (
            <label key={microphone.deviceId} className={`flex cursor-pointer items-center gap-3 rounded border p-3 text-sm transition ${
              selectedId === microphone.deviceId
                ? "border-arc-200 bg-arc-400/20 text-arc-100"
                : "border-arc-700 text-arc-300/80 hover:bg-arc-500/15"
            }`}>
              <input
                type="radio"
                name="jarvis-microphone"
                checked={selectedId === microphone.deviceId}
                onChange={() => setSelectedId(microphone.deviceId)}
                className="accent-arc-300"
              />
              {microphone.label || `Microfone ${index + 1}`}
            </label>
          ))}
        </div>

        <p className="mt-4 text-center text-xs text-arc-300/70">{status}</p>
        <div className="mt-5 flex gap-2">
          <button type="button" onClick={onClose} className="flex-1 rounded border border-arc-600 px-4 py-2 font-display text-xs tracking-widest text-arc-300 hover:bg-arc-500/15">Cancelar</button>
          <button type="button" onClick={confirm} disabled={!selectedId} className="flex-1 rounded border border-arc-300 bg-arc-500/15 px-4 py-2 font-display text-xs tracking-widest text-arc-100 hover:bg-arc-400/30 disabled:cursor-not-allowed disabled:opacity-40">Continuar</button>
        </div>
      </section>
    </div>
  );
}

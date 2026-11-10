import { useEffect, useRef, useState } from "react";

const REQUESTS = {
  microphone: { title: "Teste do microfone", description: "Fale normalmente. O indicador mostra quando o áudio está chegando." },
  camera: { title: "Teste da câmera", description: "Esta é uma prévia local. Nenhuma imagem é enviada ao JARVIS." },
};

export default function DeviceTestModal({ device, onClose }) {
  const videoRefs = useRef(new Map());
  const streamRef = useRef(null);
  const cameraStreamsRef = useRef(new Map());
  const audioContextRef = useRef(null);
  const [status, setStatus] = useState("Solicitando permissão…");
  const [level, setLevel] = useState(0);
  const [cameras, setCameras] = useState([]);
  const [selectedCameraIds, setSelectedCameraIds] = useState([]);
  const config = REQUESTS[device];

  useEffect(() => {
    let active = true;
    const start = async () => {
      try {
        if (!navigator.mediaDevices?.getUserMedia) {
          setStatus("Seu navegador não suporta acesso a dispositivos");
          return;
        }
        const stream = await navigator.mediaDevices.getUserMedia(
          device === "camera" ? { video: true, audio: false } : { audio: true },
        );
        if (!active) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }
        streamRef.current = stream;
        setStatus("Funcionando");
        if (device === "camera") {
          const devices = (await navigator.mediaDevices.enumerateDevices())
            .filter((item) => item.kind === "videoinput");
          setCameras(devices);
          setSelectedCameraIds(devices.map((item) => item.deviceId));
          stream.getTracks().forEach((track) => track.stop());
          return;
        }
        if (device === "microphone") {
          const AudioContextClass = window.AudioContext || window.webkitAudioContext;
          if (!AudioContextClass) {
            setStatus("Permissão concedida; medição não suportada neste navegador");
            return;
          }
          const context = new AudioContextClass();
          const analyser = context.createAnalyser();
          const source = context.createMediaStreamSource(stream);
          source.connect(analyser);
          audioContextRef.current = context;
          const data = new Uint8Array(analyser.frequencyBinCount);
          const update = () => {
            if (!active) return;
            analyser.getByteTimeDomainData(data);
            const average = data.reduce((sum, value) => sum + Math.abs(value - 128), 0) / data.length;
            setLevel(Math.min(100, Math.round(average * 3)));
            requestAnimationFrame(update);
          };
          update();
        }
      } catch (error) {
        setStatus(error.name === "NotAllowedError" ? "Permissão negada no navegador" : "Dispositivo indisponível");
      }
    };
    start();
    return () => {
      active = false;
      streamRef.current?.getTracks().forEach((track) => track.stop());
      cameraStreamsRef.current.forEach((cameraStream) => cameraStream.getTracks().forEach((track) => track.stop()));
      cameraStreamsRef.current.clear();
      audioContextRef.current?.close();
    };
  }, [device]);

  useEffect(() => {
    if (device !== "camera" || selectedCameraIds.length === 0) return undefined;
    let active = true;

    const startSelectedCameras = async () => {
      for (const deviceId of selectedCameraIds) {
        if (cameraStreamsRef.current.has(deviceId)) continue;
        try {
          const stream = await navigator.mediaDevices.getUserMedia({
            video: { deviceId: { exact: deviceId } },
            audio: false,
          });
          if (!active) {
            stream.getTracks().forEach((track) => track.stop());
            return;
          }
          cameraStreamsRef.current.set(deviceId, stream);
          const video = videoRefs.current.get(deviceId);
          if (video) video.srcObject = stream;
        } catch {
          setStatus("Não foi possível abrir uma das câmeras");
        }
      }
    };

    startSelectedCameras();
    return () => {
      active = false;
      cameraStreamsRef.current.forEach((stream, deviceId) => {
        if (!selectedCameraIds.includes(deviceId)) {
          stream.getTracks().forEach((track) => track.stop());
          cameraStreamsRef.current.delete(deviceId);
        }
      });
    };
  }, [device, selectedCameraIds]);

  const toggleCamera = (deviceId) => {
    setSelectedCameraIds((current) => (
      current.includes(deviceId)
        ? current.filter((id) => id !== deviceId)
        : [...current, deviceId]
    ));
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-void/80 p-4 backdrop-blur-sm">
      <section className={`hud-panel w-full ${device === "camera" ? "max-w-3xl" : "max-w-md"} p-5 shadow-arc`} role="dialog" aria-modal="true" aria-label={config.title}>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="font-display text-sm tracking-widest text-arc-100">{config.title}</h2>
            <p className="mt-1 text-xs text-arc-300/70">{config.description}</p>
          </div>
          <button type="button" onClick={onClose} className="text-arc-300/70 hover:text-arc-100" aria-label="Fechar">✕</button>
        </div>
        {device === "camera" ? (
          <>
            {cameras.length > 1 && (
              <div className="mb-4 flex flex-wrap gap-2">
                {cameras.map((camera, index) => (
                  <button
                    key={camera.deviceId}
                    type="button"
                    onClick={() => toggleCamera(camera.deviceId)}
                    className={`rounded border px-3 py-2 text-left text-xs transition ${
                      selectedCameraIds.includes(camera.deviceId)
                        ? "border-arc-200 bg-arc-400/20 text-arc-100"
                        : "border-arc-600 text-arc-300/70 hover:bg-arc-500/15"
                    }`}
                  >
                    {camera.label || `Webcam ${index + 1}`}
                  </button>
                ))}
              </div>
            )}
            <div className={`grid gap-3 ${selectedCameraIds.length > 1 ? "md:grid-cols-2" : "grid-cols-1"}`}>
              {selectedCameraIds.map((deviceId) => (
                <div key={deviceId} className="overflow-hidden rounded border border-arc-700 bg-black">
                  <video
                    ref={(element) => {
                      if (element) videoRefs.current.set(deviceId, element);
                      else videoRefs.current.delete(deviceId);
                    }}
                    autoPlay
                    muted
                    playsInline
                    className="aspect-video w-full object-cover"
                  />
                </div>
              ))}
            </div>
            {cameras.length === 0 && <p className="rounded border border-arc-700 p-6 text-center text-sm text-arc-300/70">Nenhuma webcam encontrada.</p>}
          </>
        ) : (
          <div className="rounded border border-arc-700 bg-void/60 p-6 text-center">
            <div className="mx-auto mb-4 h-3 w-full overflow-hidden rounded bg-arc-900">
              <div className="h-full rounded bg-arc-300 transition-all duration-100" style={{ width: `${Math.max(4, level)}%` }} />
            </div>
            <p className="font-display text-2xl text-arc-200">{level}%</p>
            <p className="mt-1 text-xs text-arc-300/60">Nível de áudio detectado</p>
          </div>
        )}
        <p className={`mt-4 text-center text-sm ${status === "Funcionando" ? "text-emerald-300" : "text-arc-200"}`}>● {status}</p>
        <button type="button" onClick={onClose} className="mt-4 w-full rounded border border-arc-400/60 px-4 py-2 font-display text-xs tracking-widest text-arc-200 hover:bg-arc-500/20">Fechar teste</button>
      </section>
    </div>
  );
}

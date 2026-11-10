import { useState, useEffect, useRef } from "react";

/**
 * BioScanModal (Stark OS - Panorama de Saúde)
 * Réplica fidedigna do layout e animações do vídeo do usuário:
 * - Câmera ao vivo em orbe com anéis de partículas giratórias e varredura
 * - Hologramas centrais alternáveis (Bateria Verde, Coração Rosa Neon, Cérebro Azul Neon, Estrela Amarela)
 * - Métricas laterais com linhas e pontos conectores (Estilo Stark OS)
 * - Panorama de Saúde com dados de sono (horas de sono, eficiência durante o sono, respiração noturna)
 */
export default function BioScanModal({ onClose, api, operatorName = "Patrick" }) {
  const [activeStage, setActiveStage] = useState("heart"); // "battery" | "heart" | "brain" | "star"
  const [telemetry, setTelemetry] = useState({
    device_name: "Smartwatch MActivePro",
    connected: true,
    last_sync: "20 DE OUTUBRO",
    battery: 85,
    bpm: 84,
    hrv: 44.1,
    spo2: 96.6,
    skin_temp: 33.6,
    sleep_hours: 7.8,
    sleep_efficiency: 95,
    sleep_performance: 82,
    respiration: 13.6,
    recovery: 88,
  });

  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [scanningBle, setScanningBle] = useState(false);
  const [bleDevices, setBleDevices] = useState([]);
  const [showBleModal, setShowBleModal] = useState(false);

  // Busca dados atualizados do backend
  useEffect(() => {
    fetch("http://localhost:8000/api/health/biometrics")
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) setTelemetry((prev) => ({ ...prev, ...data }));
      })
      .catch(() => {});

    // Ativa câmera do operador de forma estável (sem recriar stream)
    let mounted = true;
    navigator.mediaDevices?.getUserMedia({ video: { width: { ideal: 640 }, height: { ideal: 640 } }, audio: false })
      .then((stream) => {
        if (!mounted) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play().catch(() => {});
        }
        setCameraActive(true);
      })
      .catch((err) => {
        console.warn("Câmera indisponível no bio-scan:", err);
      });

    // Alternância suave dos hologramas com o tempo (como no vídeo)
    // 0s-4s: bateria/energia -> 4s-12s: coração -> 12s-20s: cérebro/sono -> 20s+: estrela
    const t1 = setTimeout(() => setActiveStage("heart"), 3500);
    const t2 = setTimeout(() => setActiveStage("brain"), 11000);
    const t3 = setTimeout(() => setActiveStage("star"), 19000);

    // Fala do Jarvis reportando saúde e sono
    if (api) {
      api("/api/speak", {
        method: "POST",
        body: JSON.stringify({
          text: `Panorama de saúde carregado, senhor ${operatorName}. Seus batimentos médios estão em 84 bpm, com variabilidade em 44 milissegundos. Durante o sono, registrou 7 horas e 48 minutos, performance de 82 por cento e eficiência de 95 por cento. Respiração estável em 13 ponto 6 por minuto.`
        }),
      }).catch(() => {});
    }

    return () => {
      mounted = false;
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      }
    };
  }, [operatorName]);

  const handleScanBle = async () => {
    setScanningBle(true);
    setShowBleModal(true);
    try {
      const res = await fetch("http://localhost:8000/api/health/ble-scan?timeout=5.0");
      if (res.ok) {
        const data = await res.json();
        setBleDevices(data.devices || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setScanningBle(false);
    }
  };

  const handleConnectBle = async (device) => {
    try {
      const res = await fetch(`http://localhost:8000/api/health/connect-ble?address=${encodeURIComponent(device.address)}&name=${encodeURIComponent(device.name || "Smartwatch")}`, {
        method: "POST"
      });
      if (res.ok) {
        const data = await res.json();
        setTelemetry(data.telemetry);
        setShowBleModal(false);
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/95 select-none animate-fadeIn overflow-hidden">
      {/* Background Cyber Grid Holográfico com curvatura sci-fi */}
      <div 
        className="absolute inset-0 pointer-events-none opacity-30"
        style={{
          backgroundImage: `
            linear-gradient(to right, rgba(0, 150, 255, 0.15) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(0, 150, 255, 0.15) 1px, transparent 1px)
          `,
          backgroundSize: "42px 42px",
        }}
      />
      {/* Vignette azul profunda */}
      <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_center,transparent_20%,rgba(0,10,30,0.85)_100%)]" />

      {/* Top Bar (Exata do vídeo) */}
      <header className="absolute top-5 left-10 right-10 flex justify-between items-center z-20">
        <div className="flex items-center gap-3">
          <span className="font-['Orbitron'] font-black text-sm tracking-[0.3em] text-white">
            JARVIS
          </span>
          <span className="text-[10px] font-['Orbitron'] tracking-[0.25em] text-cyan-400/60 uppercase">
            — PROTOCOLO DE IA
          </span>
        </div>

        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-cyan-400 shadow-[0_0_8px_#38bdf8] animate-pulse" />
            <span className="text-[11px] font-['Orbitron'] tracking-[0.2em] text-cyan-300">
              SISTEMA ONLINE
            </span>
          </div>
          <span className="text-[11px] font-['Orbitron'] tracking-[0.2em] text-cyan-400/80">
            VOICE LINK
          </span>
          <button
            onClick={onClose}
            className="text-xs font-['Orbitron'] text-cyan-400 hover:text-white px-3 py-1 rounded border border-cyan-500/30 hover:bg-cyan-500/20 transition-all ml-4"
          >
            ✕ FECHAR
          </button>
        </div>
      </header>

      {/* Cabeçalho de Status: FALANDO (com barras ondulantes) */}
      <div className="absolute top-16 left-1/2 -translate-x-1/2 text-center z-20">
        <span className="font-['Orbitron'] text-xs font-bold tracking-[0.35em] text-cyan-300 block mb-1">
          FALANDO
        </span>
        <div className="flex items-center justify-center gap-[3px] text-cyan-400/80 opacity-70">
          {Array.from({ length: 24 }).map((_, i) => (
            <span
              key={i}
              className="inline-block w-[1.5px] bg-cyan-400 animate-pulse"
              style={{
                height: `${4 + (Math.sin(i * 0.7) + 1) * 4}px`,
                animationDelay: `${i * 0.05}s`,
              }}
            />
          ))}
        </div>
      </div>

      {/* Título do Canto Esquerdo: "Panorama de Saúde" (Exato do vídeo) */}
      <div className="absolute top-28 left-12 z-20 max-w-sm">
        <span className="text-[10px] font-['Orbitron'] tracking-[0.25em] text-cyan-400/70 block mb-1">
          --- SISTEMA BIOMÉTRICO
        </span>
        <h1 className="text-2xl font-['Orbitron'] font-bold text-white tracking-wide leading-tight">
          Panorama de <br /> Saúde
        </h1>
        <p className="text-xs text-cyan-300/70 font-sans mt-2 leading-relaxed">
          Coletando os sinais mais recentes <br /> de suas fontes pessoais.
        </p>
        <div className="w-24 h-[2px] bg-gradient-to-r from-cyan-400 to-transparent mt-3" />
      </div>

      {/* Área Central: Câmera Circular Holográfica à esquerda + Holograma Dinâmico ao centro-direita */}
      <div className="relative w-full max-w-6xl h-[65vh] flex items-center justify-between px-12 z-10">
        {/* Orbe com a Webcam Ao Vivo (Estilo do vídeo: anéis elípticos de luz girando) */}
        <div className="relative flex items-center justify-center w-1/2 h-full">
          {/* Ondas e anéis orbitais com partículas brilhantes */}
          <div 
            className="absolute w-80 h-80 rounded-full border border-cyan-400/30 animate-spin"
            style={{ animationDuration: "14s" }}
          />
          <div 
            className="absolute w-96 h-96 rounded-full border border-dashed border-cyan-400/40 animate-spin"
            style={{ animationDuration: "22s", animationDirection: "reverse" }}
          />
          <div 
            className="absolute w-[26rem] h-[26rem] rounded-full border border-cyan-500/20 animate-pulse"
          />

          {/* Círculo com Feed de Câmera Real */}
          <div className="relative w-64 h-64 rounded-full overflow-hidden border-2 border-cyan-400 shadow-[0_0_40px_rgba(56,189,248,0.5)] bg-black/80 flex items-center justify-center">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className={`w-full h-full object-cover scale-x-[-1] transition-opacity duration-300 ${cameraActive ? "opacity-100" : "opacity-0"}`}
            />
            {!cameraActive && (
              <div className="absolute inset-0 flex flex-col items-center justify-center p-4">
                <span className="text-4xl block mb-2">👤</span>
                <span className="text-xs font-['Orbitron'] text-cyan-300">BIO SCAN AO VIVO</span>
              </div>
            )}

            {/* Linha de varredura holográfica */}
            <div className="absolute inset-0 bg-gradient-to-b from-transparent via-cyan-400/25 to-transparent h-16 w-full animate-bounce pointer-events-none" />

            {/* Mini Label no Círculo */}
            <span className="absolute top-4 text-[9px] font-['Orbitron'] tracking-[0.25em] text-cyan-300/80 bg-black/60 px-2.5 py-0.5 rounded-full">
              BIO SCAN · AO VIVO
            </span>

            {/* Controles de Foto/Câmera na base interna */}
            <div className="absolute bottom-3 flex items-center gap-2 bg-black/70 px-2 py-1 rounded-full border border-cyan-500/30">
              <span className="text-xs text-cyan-300">📸</span>
              <span className="text-[10px] font-mono text-cyan-200">1080P</span>
            </div>
          </div>
        </div>

        {/* Holograma Dinâmico Central + Métricas Laterais Conectadas */}
        <div className="relative w-1/2 h-full flex items-center justify-center">
          {/* Seletor manual rápido dos 4 hologramas para o usuário testar se quiser */}
          <div className="absolute top-2 right-4 flex gap-1.5 z-30">
            {[
              ["battery", "⚡ Energia", "border-emerald-400 text-emerald-300"],
              ["heart", "❤️ Coração", "border-rose-400 text-rose-300"],
              ["brain", "🧠 Sono", "border-cyan-400 text-cyan-300"],
              ["star", "✨ Status", "border-amber-400 text-amber-300"],
            ].map(([stage, label, color]) => (
              <button
                key={stage}
                onClick={() => setActiveStage(stage)}
                className={`text-[10px] font-['Orbitron'] px-2 py-0.5 rounded border transition-all ${
                  activeStage === stage ? `bg-white/10 ${color} font-bold shadow-lg` : "border-white/10 text-white/40 hover:text-white"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* O Holograma Central 3D em wireframe */}
          <div className="relative flex items-center justify-center w-72 h-72">
            {/* Base holográfica elíptica com anéis concêntricos */}
            <div className="absolute bottom-6 w-44 h-12 rounded-[100%] border border-cyan-500/40 shadow-[0_0_20px_rgba(56,189,248,0.3)] animate-pulse" />
            <div className="absolute bottom-8 w-32 h-8 rounded-[100%] border border-dashed border-cyan-400/50 animate-spin" style={{ animationDuration: "16s" }} />

            {/* 1. ESTÁGIO: BATERIA / ENERGIA (VERDE) */}
            {activeStage === "battery" && (
              <div className="relative flex flex-col items-center justify-center animate-fadeIn">
                <div className="h-32 w-32 rounded-full bg-emerald-500/15 blur-2xl absolute" />
                <div className="relative flex items-center justify-center h-28 w-28 rounded-2xl border-2 border-emerald-400/80 shadow-[0_0_30px_rgba(52,211,153,0.7)] bg-emerald-950/20">
                  <span className="text-5xl font-['Orbitron'] font-black text-emerald-300 animate-pulse">
                    ⚡
                  </span>
                </div>
              </div>
            )}

            {/* 2. ESTÁGIO: CORAÇÃO PULSANTE (ROSA / VERMELHO NEON) */}
            {activeStage === "heart" && (
              <div className="relative flex items-center justify-center animate-fadeIn">
                <div className="h-36 w-36 rounded-full bg-rose-500/20 blur-2xl absolute" />
                <div className="text-7xl animate-pulse filter drop-shadow-[0_0_25px_rgba(244,63,94,0.9)]">
                  ❤️
                </div>
              </div>
            )}

            {/* 3. ESTÁGIO: CÉREBRO / SONO (AZUL NEON HOLOGRÁFICO) */}
            {activeStage === "brain" && (
              <div className="relative flex items-center justify-center animate-fadeIn">
                <div className="h-36 w-36 rounded-full bg-cyan-500/20 blur-2xl absolute" />
                <div className="text-7xl animate-pulse filter drop-shadow-[0_0_30px_rgba(56,189,248,0.9)]">
                  🧠
                </div>
              </div>
            )}

            {/* 4. ESTÁGIO: ESTRELA / STATUS GERAL (AMARELO DOURADO) */}
            {activeStage === "star" && (
              <div className="relative flex items-center justify-center animate-fadeIn">
                <div className="h-36 w-36 rounded-full bg-amber-500/20 blur-2xl absolute" />
                <div className="text-7xl animate-pulse filter drop-shadow-[0_0_30px_rgba(251,191,36,0.9)]">
                  ✨
                </div>
              </div>
            )}
          </div>

          {/* Painel Lateral Direito com Linhas Conectoras e Métricas (Exatas do vídeo) */}
          <div className="w-64 pl-6 space-y-6">
            {/* Bloco 1: Quando no modo Bateria/Energia */}
            {activeStage === "battery" && (
              <>
                <div className="relative pl-6">
                  <div className="absolute left-0 top-3 w-4 h-[1px] bg-emerald-400" />
                  <div className="absolute left-4 top-2 h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]" />
                  <span className="text-[9px] font-['Orbitron'] tracking-[0.2em] text-emerald-400/80 uppercase block">
                    HRV NOTURNO
                  </span>
                  <div className="text-2xl font-['Orbitron'] font-bold text-white tracking-wider">
                    {telemetry.hrv} <small className="text-xs text-emerald-300">MS</small>
                  </div>
                </div>

                <div className="relative pl-6">
                  <div className="absolute left-0 top-3 w-4 h-[1px] bg-emerald-400" />
                  <div className="absolute left-4 top-2 h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]" />
                  <span className="text-[9px] font-['Orbitron'] tracking-[0.2em] text-emerald-400/80 uppercase block">
                    REPOUSO
                  </span>
                  <div className="text-2xl font-['Orbitron'] font-bold text-white tracking-wider">
                    64 <small className="text-xs text-emerald-300">BPM</small>
                  </div>
                </div>

                <div className="relative pl-6">
                  <div className="absolute left-0 top-3 w-4 h-[1px] bg-emerald-400" />
                  <div className="absolute left-4 top-2 h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]" />
                  <span className="text-[9px] font-['Orbitron'] tracking-[0.2em] text-emerald-400/80 uppercase block">
                    TEMP. EM PELE
                  </span>
                  <div className="text-2xl font-['Orbitron'] font-bold text-white tracking-wider">
                    {telemetry.skin_temp || 33.6} <small className="text-xs text-emerald-300">°C</small>
                  </div>
                  <span className="text-[9px] text-emerald-300/60 block mt-0.5">elevada no sono</span>
                </div>
              </>
            )}

            {/* Bloco 2: Quando no modo Coração (Exato do vídeo: MÉDIA 84 BPM, VARIABILIDADE 44,1 MS, SATURAÇÃO 96,6%) */}
            {activeStage === "heart" && (
              <>
                <div className="relative pl-6">
                  <div className="absolute left-0 top-3 w-4 h-[1px] bg-rose-400" />
                  <div className="absolute left-4 top-2 h-2 w-2 rounded-full bg-rose-400 shadow-[0_0_8px_#fb7185]" />
                  <span className="text-[9px] font-['Orbitron'] tracking-[0.2em] text-rose-400 uppercase block">
                    MÉDIA
                  </span>
                  <div className="text-2xl font-['Orbitron'] font-bold text-white tracking-wider">
                    {telemetry.bpm} <small className="text-xs text-rose-300">BPM</small>
                  </div>
                  <span className="text-[9px] text-rose-300/60 font-mono block mt-0.5">registro de 20 de outubro</span>
                </div>

                <div className="relative pl-6">
                  <div className="absolute left-0 top-3 w-4 h-[1px] bg-rose-400" />
                  <div className="absolute left-4 top-2 h-2 w-2 rounded-full bg-rose-400 shadow-[0_0_8px_#fb7185]" />
                  <span className="text-[9px] font-['Orbitron'] tracking-[0.2em] text-rose-400 uppercase block">
                    VARIABILIDADE
                  </span>
                  <div className="text-2xl font-['Orbitron'] font-bold text-white tracking-wider">
                    {telemetry.hrv} <small className="text-xs text-rose-300">MS</small>
                  </div>
                  <span className="text-[9px] text-rose-300/60 font-mono block mt-0.5">RMSSD noturno</span>
                </div>

                <div className="relative pl-6">
                  <div className="absolute left-0 top-3 w-4 h-[1px] bg-rose-400" />
                  <div className="absolute left-4 top-2 h-2 w-2 rounded-full bg-rose-400 shadow-[0_0_8px_#fb7185]" />
                  <span className="text-[9px] font-['Orbitron'] tracking-[0.2em] text-rose-400 uppercase block">
                    SATURAÇÃO
                  </span>
                  <div className="text-2xl font-['Orbitron'] font-bold text-white tracking-wider">
                    {telemetry.spo2}%
                  </div>
                  <span className="text-[9px] text-rose-300/60 font-mono block mt-0.5">média de 30 dias</span>
                </div>
              </>
            )}

            {/* Bloco 3: Quando no modo Cérebro / Sono (Exato do vídeo: TEMPO DE SONO, PERFORMANCE 82%, EFICIÊNCIA 95%, RESPIRAÇÃO 13,6/MIN) */}
            {activeStage === "brain" && (
              <>
                <div className="relative pl-6">
                  <div className="absolute left-0 top-3 w-4 h-[1px] bg-cyan-400" />
                  <div className="absolute left-4 top-2 h-2 w-2 rounded-full bg-cyan-400 shadow-[0_0_8px_#38bdf8]" />
                  <span className="text-[9px] font-['Orbitron'] tracking-[0.2em] text-cyan-400 uppercase block">
                    TEMPO DE SONO
                  </span>
                  <div className="text-2xl font-['Orbitron'] font-bold text-white tracking-wider">
                    {Math.floor(telemetry.sleep_hours || 7)}h {Math.round(((telemetry.sleep_hours || 7.8) % 1) * 60)}min
                  </div>
                  <span className="text-[9px] text-cyan-300/60 font-mono block mt-0.5">noite passada · sono reparador</span>
                </div>

                <div className="relative pl-6">
                  <div className="absolute left-0 top-3 w-4 h-[1px] bg-cyan-400" />
                  <div className="absolute left-4 top-2 h-2 w-2 rounded-full bg-cyan-400 shadow-[0_0_8px_#38bdf8]" />
                  <span className="text-[9px] font-['Orbitron'] tracking-[0.2em] text-cyan-400 uppercase block">
                    PERFORMANCE
                  </span>
                  <div className="text-2xl font-['Orbitron'] font-bold text-white tracking-wider">
                    {telemetry.sleep_performance || 82}%
                  </div>
                  <span className="text-[9px] text-cyan-300/60 font-mono block mt-0.5">hoje</span>
                </div>

                <div className="relative pl-6">
                  <div className="absolute left-0 top-3 w-4 h-[1px] bg-cyan-400" />
                  <div className="absolute left-4 top-2 h-2 w-2 rounded-full bg-cyan-400 shadow-[0_0_8px_#38bdf8]" />
                  <span className="text-[9px] font-['Orbitron'] tracking-[0.2em] text-cyan-400 uppercase block">
                    EFICIÊNCIA
                  </span>
                  <div className="text-2xl font-['Orbitron'] font-bold text-white tracking-wider">
                    {telemetry.sleep_efficiency || 95}%
                  </div>
                  <span className="text-[9px] text-cyan-300/60 font-mono block mt-0.5">durante o sono</span>
                </div>

                <div className="relative pl-6">
                  <div className="absolute left-0 top-3 w-4 h-[1px] bg-cyan-400" />
                  <div className="absolute left-4 top-2 h-2 w-2 rounded-full bg-cyan-400 shadow-[0_0_8px_#38bdf8]" />
                  <span className="text-[9px] font-['Orbitron'] tracking-[0.2em] text-cyan-400 uppercase block">
                    RESPIRAÇÃO
                  </span>
                  <div className="text-2xl font-['Orbitron'] font-bold text-white tracking-wider">
                    {telemetry.respiration || 13.6}/MIN
                  </div>
                  <span className="text-[9px] text-cyan-300/60 font-mono block mt-0.5">média durante o sono</span>
                </div>
              </>
            )}

            {/* Bloco 4: Quando no modo Estrela (PRIORIDADE ÚNICA / FONTES DE DADOS) */}
            {activeStage === "star" && (
              <>
                <div className="relative pl-6">
                  <div className="absolute left-0 top-3 w-4 h-[1px] bg-amber-400" />
                  <div className="absolute left-4 top-2 h-2 w-2 rounded-full bg-amber-400 shadow-[0_0_8px_#fbbf24]" />
                  <span className="text-[9px] font-['Orbitron'] tracking-[0.2em] text-amber-400 uppercase block">
                    ANÁLISE
                  </span>
                  <div className="text-lg font-['Orbitron'] font-bold text-white tracking-wider">
                    PRIORIDADE ÚNICA
                  </div>
                </div>

                <div className="relative pl-6">
                  <div className="absolute left-0 top-3 w-4 h-[1px] bg-amber-400" />
                  <div className="absolute left-4 top-2 h-2 w-2 rounded-full bg-amber-400 shadow-[0_0_8px_#fbbf24]" />
                  <span className="text-[9px] font-['Orbitron'] tracking-[0.2em] text-amber-400 uppercase block">
                    BASE CONECTADA
                  </span>
                  <div className="text-sm font-['Orbitron'] font-bold text-amber-200 tracking-wider">
                    MACTIVEPRO + <br />
                    STRAVA + <br />
                    FITNESSSYNCER
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Botão de Busca Bluetooth no canto inferior */}
      <footer className="absolute bottom-6 left-12 right-12 flex justify-between items-center z-20">
        <div className="flex items-center gap-3">
          <button
            onClick={handleScanBle}
            className="text-xs font-['Orbitron'] text-cyan-300 hover:text-white px-3.5 py-1.5 rounded border border-cyan-500/40 bg-cyan-950/40 hover:bg-cyan-500/20 flex items-center gap-2 transition-all shadow-[0_0_15px_rgba(6,182,212,0.25)]"
          >
            <span>📡</span> SCAN SMARTWATCH BLUETOOTH
          </button>
          <span className="text-[10px] font-['Orbitron'] text-cyan-400/60">
            DISPOSITIVO: {telemetry.device_name} ({telemetry.connected ? "SINCRONIZADO" : "STANDBY"})
          </span>
        </div>

        <div className="text-[10px] font-['Orbitron'] text-cyan-400/50">
          STARK MEDICAL ENGINE · PROTOCOLO BIOMÉTRICO v4.0
        </div>
      </footer>

      {/* Modal de Scan BLE */}
      {showBleModal && (
        <div className="fixed inset-0 z-60 flex items-center justify-center bg-black/85 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-cyan-400/50 bg-[#061528] p-5 shadow-[0_0_40px_rgba(31,194,245,0.4)]">
            <div className="flex justify-between items-center mb-3 border-b border-cyan-500/30 pb-2">
              <h3 className="font-['Orbitron'] text-xs font-bold text-cyan-300 tracking-wider">
                DISPOSITIVOS BLUETOOTH PRÓXIMOS
              </h3>
              <button onClick={() => setShowBleModal(false)} className="text-cyan-400 hover:text-white text-xs font-mono">
                ✕
              </button>
            </div>

            {scanningBle ? (
              <div className="py-8 text-center">
                <div className="h-8 w-8 mx-auto border-2 border-cyan-400 border-t-transparent rounded-full animate-spin mb-3" />
                <p className="text-xs font-['Orbitron'] text-cyan-300">Escaneando frequências BLE...</p>
              </div>
            ) : (
              <div className="max-h-60 overflow-y-auto space-y-2 pr-1">
                {bleDevices.length === 0 ? (
                  <div className="py-6 text-center text-xs text-cyan-400/70">
                    <p>Nenhum relógio encontrado neste momento.</p>
                  </div>
                ) : (
                  bleDevices.map((dev, i) => (
                    <div
                      key={i}
                      onClick={() => handleConnectBle(dev)}
                      className="p-2.5 rounded border border-cyan-500/30 bg-cyan-950/30 hover:bg-cyan-800/40 cursor-pointer flex justify-between items-center"
                    >
                      <div>
                        <strong className="text-xs font-['Orbitron'] text-white block">{dev.name}</strong>
                        <span className="text-[10px] text-cyan-400/60 font-mono">{dev.address}</span>
                      </div>
                      <button className="text-[10px] font-['Orbitron'] text-cyan-300 border border-cyan-400/40 px-2 py-1 rounded">
                        CONECTAR
                      </button>
                    </div>
                  ))
                )}
              </div>
            )}

            <div className="mt-4 flex gap-2">
              <button
                onClick={handleScanBle}
                disabled={scanningBle}
                className="flex-1 py-1.5 rounded bg-cyan-500/20 border border-cyan-400/40 text-xs font-['Orbitron'] text-cyan-300"
              >
                RE-ESCANEAR
              </button>
              <button
                onClick={() => setShowBleModal(false)}
                className="px-4 py-1.5 rounded border border-white/20 text-xs font-['Orbitron'] text-white/70"
              >
                FECHAR
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

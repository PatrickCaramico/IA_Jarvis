import { useCallback, useEffect, useState } from "react";

export default function MonitorPanel({ onClose, onOpenWindow, onOpenSpotifyWindow }) {
  const [screens, setScreens] = useState([]);
  const [extended, setExtended] = useState(false);
  const [message, setMessage] = useState("");

  const detect = useCallback(async () => {
    setMessage("");
    try {
      setExtended(Boolean(window.screen?.isExtended));
      if (window.getScreenDetails) {
        const details = await window.getScreenDetails();
        setScreens(details.screens.map((screen, index) => ({
          index: index + 1,
          width: screen.width,
          height: screen.height,
          left: screen.availLeft,
          top: screen.availTop,
          primary: screen.isPrimary,
        })));
        return;
      }
      setScreens([{
        index: 1,
        width: window.screen.width,
        height: window.screen.height,
        left: window.screen.availLeft,
        top: window.screen.availTop,
        primary: true,
      }]);
      setMessage("O navegador não liberou a lista completa de monitores. A tela atual foi detectada.");
    } catch {
      setMessage("Permissão de gerenciamento de janelas não concedida. Mostrando apenas a tela atual.");
      setScreens([{
        index: 1,
        width: window.screen.width,
        height: window.screen.height,
        left: window.screen.availLeft,
        top: window.screen.availTop,
        primary: true,
      }]);
    }
  }, []);

  useEffect(() => { detect(); }, [detect]);

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-void/75 p-5 backdrop-blur-sm">
      <section className="hud-panel w-full max-w-xl p-5">
        <header className="mb-4 flex items-center justify-between">
          <div>
            <p className="font-display text-xs tracking-[0.25em] text-arc-400">J.A.R.V.I.S. · MONITORES</p>
            <h2 className="font-display text-xl tracking-widest text-arc-100">Central de telas</h2>
          </div>
          <button type="button" onClick={onClose} className="text-sm text-arc-300 hover:text-white">Fechar</button>
        </header>
        <p className="mb-3 text-sm text-arc-300/80">
          {extended ? "Modo multi-monitor detectado." : "A janela atual está em uma única área de trabalho."}
        </p>
        <div className="space-y-2">
          {screens.map((screen) => (
            <div key={screen.index} className="flex items-center justify-between rounded border border-arc-700/70 p-3">
              <div>
                <p className="text-sm text-arc-100">Monitor {screen.index} {screen.primary && "· principal"}</p>
                <p className="text-xs text-arc-300/60">{screen.width} × {screen.height} · posição {screen.left}, {screen.top}</p>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    window.open(
                      `${window.location.origin}/?display=secondary&monitor=${screen.index}`,
                      `jarvis-display-${screen.index}`,
                      `width=${screen.width || 1280},height=${screen.height || 720},left=${screen.left || 100},top=${screen.top || 100}`
                    );
                  }}
                  className="rounded border border-cyan-400/80 bg-cyan-950/40 px-3 py-1.5 text-xs font-['Orbitron'] text-cyan-200 hover:bg-cyan-500/30"
                >
                  Abrir Central na Tela {screen.index}
                </button>
                <button type="button" onClick={() => onOpenWindow(screen.index)} className="rounded border border-arc-400/50 px-3 py-1.5 text-xs text-arc-200 hover:bg-arc-500/20">
                  Clima
                </button>
                <button type="button" onClick={() => onOpenSpotifyWindow(screen.index)} className="rounded border border-emerald-400/50 px-3 py-1.5 text-xs text-emerald-200 hover:bg-emerald-500/20">
                  Spotify
                </button>
              </div>
            </div>
          ))}
        </div>
        {message && <p className="mt-3 text-xs text-amber-200/80">{message}</p>}
        <button type="button" onClick={detect} className="mt-4 rounded border border-arc-600 px-3 py-2 text-xs text-arc-200 hover:bg-arc-500/20">
          Detectar novamente
        </button>
      </section>
    </div>
  );
}

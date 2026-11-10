import { useEffect, useRef, useState } from "react";
import { startPolling } from "../hooks/usePolling.js";

// V4.2.2: "Tocando agora" do Spotify. Usado na tela de bloqueio (sem botões) e na coluna direita
// da central (com voltar, tocar/pausar e avançar). Some quando o Spotify não está conectado ou
// não há nada tocando; pausado mostra "Spotify · pausado".
const POLL_MS = 15000;

function fmt(ms) {
  const s = Math.max(0, Math.floor(ms / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export function useNowPlaying(api, enabled = true) {
  const [track, setTrack] = useState(null);
  const [progress, setProgress] = useState(0);
  const fetchedAt = useRef(0);

  const load = useRef(null);
  load.current = () =>
    api("/api/integrations/spotify/track")
      .then((d) => {
        setTrack(d);
        setProgress(d?.progress_ms || 0);
        fetchedAt.current = Date.now();
      })
      .catch(() => setTrack(null));

  useEffect(() => {
    if (!enabled) return undefined;
    return startPolling(() => load.current(), POLL_MS);
  }, [enabled]);

  // Barra de progresso anda sozinha entre as consultas
  useEffect(() => {
    if (track?.state !== "playing") return undefined;
    const t = setInterval(() => {
      setProgress(Math.min(track.duration_ms || 0, (track.progress_ms || 0) + (Date.now() - fetchedAt.current)));
    }, 1000);
    return () => clearInterval(t);
  }, [track]);

  return { track, progress, refresh: () => load.current() };
}

export default function NowPlaying({ api, variant = "lock", controls = false }) {
  const { track, progress, refresh } = useNowPlaying(api);
  const [busy, setBusy] = useState(false);

  if (!track || (track.state !== "playing" && track.state !== "paused")) return null;
  const playing = track.state === "playing";
  const pct = track.duration_ms ? Math.min(100, (progress / track.duration_ms) * 100) : 0;

  const control = async (action) => {
    setBusy(true);
    try {
      await api("/api/integrations/spotify/control", { method: "POST", body: JSON.stringify({ action }) });
      setTimeout(refresh, 600);
    } catch {
      /* Spotify sem dispositivo ativo: o próximo ciclo atualiza */
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={`np np-${variant} ${playing ? "is-playing" : "is-paused"}`} aria-label="Tocando agora no Spotify">
      <div className="np-head">
        <span className="np-dot" aria-hidden="true" />
        <span>{playing ? "TOCANDO AGORA · SPOTIFY" : "SPOTIFY · PAUSADO"}</span>
        {playing && (
          <span className="np-eq" aria-hidden="true"><i /><i /><i /></span>
        )}
      </div>
      <div className="np-body">
        {track.image ? <img className="np-cover" src={track.image} alt="" /> : <span className="np-cover np-cover-empty">♪</span>}
        <div className="np-text">
          <strong title={track.title}>{track.title}</strong>
          <span title={track.artist}>{track.artist}</span>
        </div>
      </div>
      <div className="np-bar" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(pct)}>
        <span style={{ width: `${pct}%` }} />
      </div>
      <div className="np-times"><span>{fmt(progress)}</span><span>{fmt(track.duration_ms)}</span></div>
      {controls && (
        <div className="np-controls">
          <button type="button" onClick={() => control("previous")} disabled={busy} aria-label="Faixa anterior">⏮</button>
          <button type="button" onClick={() => control(playing ? "pause" : "play")} disabled={busy} aria-label={playing ? "Pausar" : "Tocar"}>
            {playing ? "⏸" : "▶"}
          </button>
          <button type="button" onClick={() => control("next")} disabled={busy} aria-label="Próxima faixa">⏭</button>
        </div>
      )}
    </div>
  );
}

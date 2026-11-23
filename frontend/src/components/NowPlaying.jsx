import { useEffect, useRef, useState } from "react";
import { startPolling } from "../hooks/usePolling.js";
import { hasTrack, standbyView } from "../utils/nowPlaying.js";

// V4.2.2: "Tocando agora" do Spotify. Usado na tela de bloqueio (sem botões) e na coluna direita
// da central (com voltar, tocar/pausar e avançar). No bloqueio, some quando o Spotify não está conectado ou
// não há nada tocando; na central (V8.12) fica sempre. Pausado mostra "Spotify · pausado".
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

// V8.12: `always` (central): sem faixa, o cartão não some; mostra o estado e o próximo passo (conectar, tocar,
// tentar de novo). `onOpen` abre o painel do Spotify (conectar e escolher o que tocar).
export default function NowPlaying({ api, variant = "lock", controls = false, always = false, onOpen = null }) {
  const { track, progress, refresh } = useNowPlaying(api);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");

  const control = async (action) => {
    setBusy(true);
    setNote("");
    try {
      await api("/api/integrations/spotify/control", { method: "POST", body: JSON.stringify({ action }) });
      setTimeout(refresh, 600);
    } catch {
      // Spotify sem aparelho ativo: diz o que fazer em vez de não acontecer nada
      if (!hasTrack(track)) setNote("Abra o Spotify no PC ou no celular e tente de novo.");
    } finally {
      setBusy(false);
    }
  };

  if (!hasTrack(track)) {
    if (!always) return null;
    const view = standbyView(track);
    return (
      <div className={`np np-${variant} is-standby`} aria-label="Spotify">
        <div className="np-head">
          <span className="np-dot" aria-hidden="true" />
          <span>{view.head}</span>
        </div>
        <div className="np-body">
          <span className="np-cover np-cover-empty" aria-hidden="true">♪</span>
          <div className="np-text">
            <strong>{view.title}</strong>
            <span title={note || view.sub}>{note || view.sub}</span>
          </div>
        </div>
        <div className="np-controls">
          {view.action === "connect" && onOpen && (
            <button type="button" className="np-wide" onClick={onOpen}>CONECTAR</button>
          )}
          {view.action === "play" && (
            <>
              <button type="button" onClick={() => control("play")} disabled={busy} aria-label="Tocar">▶</button>
              {onOpen && <button type="button" className="np-wide" onClick={onOpen}>ESCOLHER MÚSICA</button>}
            </>
          )}
          {view.action === "retry" && (
            <button type="button" className="np-wide" onClick={refresh}>TENTAR DE NOVO</button>
          )}
        </div>
      </div>
    );
  }
  const playing = track.state === "playing";
  const pct = track.duration_ms ? Math.min(100, (progress / track.duration_ms) * 100) : 0;

  return (
    <div
      className={`np np-${variant} ${playing ? "is-playing" : "is-paused"}${track.image ? " has-art" : ""}`}
      aria-label="Tocando agora no Spotify"
      style={track.image ? { "--np-art": `url("${track.image}")` } : undefined}
    >
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

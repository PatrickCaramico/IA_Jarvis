import { useCallback, useEffect, useRef, useState } from "react";
import { useNowPlaying } from "./NowPlaying.jsx";
import { hasTrack, standbyView } from "../utils/nowPlaying.js";
import { MOODS, clampVolume, fmtTime } from "../utils/spotifyMoods.js";

// V9.1: janela do Spotify em VIDRO (glassmorphism), mais calma e futurista. Antes era um formulário com bordas
// retas e o nome da faixa num texto só. Agora: a capa do álbum desfocada vira o fundo (com uma aurora que se mexe
// devagar), capa grande com halo, barra de progresso fina, controles redondos, volume e atalhos de clima
// (lo-fi, relaxar, jazz, chuva). Os dados vêm das mesmas rotas de antes (track, control, volume, play).
export default function SpotifyWidget({ api, onSend }) {
  const [status, setStatus] = useState(null); // null = ainda consultando
  const { track, progress, refresh } = useNowPlaying(api, Boolean(status?.connected));
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [query, setQuery] = useState("");
  const [playlist, setPlaylist] = useState(false);
  const [volume, setVolume] = useState(null);
  const volTimer = useRef(null);

  const loadStatus = useCallback(async () => {
    try {
      setStatus(await api("/api/integrations/spotify/status"));
    } catch {
      setStatus({ configured: false, connected: false });
    }
  }, [api]);

  useEffect(() => { loadStatus(); }, [loadStatus]);
  useEffect(() => {
    if (!status?.connected) return;
    api("/api/integrations/spotify/volume", { timeout: 12000 })
      .then((d) => setVolume(clampVolume(d.percent)))
      .catch(() => setVolume(60));
  }, [api, status?.connected]);
  useEffect(() => () => clearTimeout(volTimer.current), []);

  const control = async (action) => {
    setBusy(true);
    setMessage("");
    try {
      await api("/api/integrations/spotify/control", { method: "POST", body: JSON.stringify({ action }) });
      setTimeout(refresh, 600);
    } catch (error) {
      setMessage(error.message || "Abra o Spotify no PC ou no celular e tente de novo.");
    } finally {
      setBusy(false);
    }
  };

  const play = async (text, asPlaylist) => {
    if (!text.trim()) return;
    setBusy(true);
    setMessage("");
    try {
      const result = await api("/api/integrations/spotify/play", {
        method: "POST",
        body: JSON.stringify({ query: text.trim(), playlist: asPlaylist }),
      });
      setMessage(result.response);
      setTimeout(refresh, 1200);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  };

  const changeVolume = (value) => {
    const v = clampVolume(value);
    setVolume(v);
    clearTimeout(volTimer.current);
    volTimer.current = setTimeout(() => {
      api("/api/integrations/spotify/volume", { method: "POST", body: JSON.stringify({ percent: v }) })
        .catch((error) => setMessage(error.message));
    }, 350); // espera parar de arrastar
  };

  const connect = () => {
    window.open(`${api.baseUrl ?? "http://127.0.0.1:8000"}/api/integrations/spotify/authorize`, "_blank", "width=600,height=700");
  };

  const playing = track?.state === "playing";
  const withTrack = hasTrack(track);
  const pct = withTrack && track.duration_ms ? Math.min(100, (progress / track.duration_ms) * 100) : 0;
  const view = withTrack ? null : standbyView(track || { state: status?.connected ? "idle" : "off" });

  return (
    <section
      className={`sg${playing ? " is-playing" : ""}${track?.image ? " has-art" : ""}`}
      aria-label="Spotify"
      style={track?.image ? { "--sg-art": `url("${track.image}")` } : undefined}
    >
      <div className="sg-bg" aria-hidden="true"><i /><i /><i /></div>

      <header className="sg-head">
        <span className="sg-dot" aria-hidden="true" />
        <span>{withTrack ? (playing ? "TOCANDO AGORA" : "PAUSADO") : "SPOTIFY"}</span>
        {status && <span className={`sg-pill${status.connected ? " is-on" : ""}`}>{status.connected ? "conectado" : "desconectado"}</span>}
      </header>

      {!status ? (
        <p className="sg-note" role="status">Consultando o Spotify…</p>
      ) : !status.configured ? (
        <p className="sg-note is-warn">Configure o Client ID e o Client Secret do Spotify no arquivo .env.</p>
      ) : !status.connected ? (
        <div className="sg-empty">
          <span className="sg-cover is-empty" aria-hidden="true">♪</span>
          <p>Conecte sua conta para ver e controlar a música aqui.</p>
          <button type="button" className="sg-cta" onClick={connect}>CONECTAR SPOTIFY</button>
        </div>
      ) : (
        <>
          <div className="sg-now">
            {track?.image ? <img className="sg-cover" src={track.image} alt="" /> : <span className="sg-cover is-empty" aria-hidden="true">♪</span>}
            <div className="sg-meta">
              <strong title={withTrack ? track.title : view.title}>{withTrack ? track.title : view.title}</strong>
              <span title={withTrack ? track.artist : view.sub}>{withTrack ? track.artist : view.sub}</span>
            </div>
            {playing && <span className="sg-eq" aria-hidden="true"><i /><i /><i /><i /></span>}
          </div>

          {withTrack && (
            <div className="sg-progress">
              <div className="sg-bar" role="progressbar" aria-label="Andamento da faixa" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(pct)}>
                <span style={{ width: `${pct}%` }} />
              </div>
              <div className="sg-times"><span>{fmtTime(progress)}</span><span>{fmtTime(track.duration_ms)}</span></div>
            </div>
          )}

          <div className="sg-controls">
            <button type="button" onClick={() => control("previous")} disabled={busy} aria-label="Faixa anterior">⏮</button>
            <button type="button" className="sg-main" onClick={() => control(playing ? "pause" : "play")} disabled={busy} aria-label={playing ? "Pausar" : "Tocar"}>
              {playing ? "⏸" : "▶"}
            </button>
            <button type="button" onClick={() => control("next")} disabled={busy} aria-label="Próxima faixa">⏭</button>
          </div>

          {volume !== null && (
            <label className="sg-volume">
              <span aria-hidden="true">{volume === 0 ? "🔇" : volume < 50 ? "🔉" : "🔊"}</span>
              <input type="range" min={0} max={100} step={1} value={volume} onChange={(e) => changeVolume(e.target.value)} aria-label="Volume da música" style={{ "--sg-vol": `${volume}%` }} />
              <b>{volume}%</b>
            </label>
          )}

          <div className="sg-moods" role="group" aria-label="Atalhos de clima">
            {MOODS.map((m) => (
              <button key={m.id} type="button" disabled={busy} onClick={() => play(m.query, m.playlist)} title={`Tocar uma playlist: ${m.label}`}>
                <span aria-hidden="true">{m.icon}</span>{m.label}
              </button>
            ))}
          </div>

          <form className="sg-search" onSubmit={(e) => { e.preventDefault(); play(query, playlist).then(() => setQuery("")); }}>
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={playlist ? "Nome da playlist" : "Música ou artista"} aria-label="Buscar no Spotify" />
            <button type="button" className={`sg-toggle${playlist ? " is-on" : ""}`} onClick={() => setPlaylist((p) => !p)} aria-pressed={playlist} title="Buscar playlist">≡</button>
            <button type="submit" disabled={busy || !query.trim()} aria-label="Buscar e tocar">▶</button>
          </form>

          <button type="button" className="sg-link" onClick={() => onSend("abrir Spotify")}>Abrir o aplicativo ↗</button>
        </>
      )}
      {message && <p className="sg-note" role="status">{message}</p>}
    </section>
  );
}

import { useCallback, useEffect, useState } from "react";
import { startPolling } from "../hooks/usePolling.js";
import { EmptyState, Skeleton } from "./ui/Skeleton.jsx";

export default function SpotifyWidget({ api, onSend }) {
  const [status, setStatus] = useState(null); // null = ainda consultando
  const [track, setTrack] = useState(null);     // null = nada tocando
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [query, setQuery] = useState("");
  const [playlist, setPlaylist] = useState(false);

  const loadStatus = useCallback(async () => {
    try {
      const data = await api("/api/integrations/spotify/status");
      setStatus(data);
    } catch {
      setStatus({ configured: false, connected: false });
    }
  }, [api]);

  const loadTrack = useCallback(async () => {
    if (!status?.connected) return;
    try {
      const data = await api("/api/integrations/spotify/now-playing");
      setTrack(data.track ?? null);
    } catch (error) {
      setTrack(error.message);
    }
  }, [api, status?.connected]);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  useEffect(() => {
    if (!status?.connected) {
      loadTrack();
      return undefined;
    }
    return startPolling(loadTrack, 15000);
  }, [loadTrack, status?.connected]);

  const command = async (text, confirmation) => {
    setLoading(true);
    setMessage("");
    try {
      const result = await api("/api/chat", {
        method: "POST",
        body: JSON.stringify({ message: text }),
      });
      setMessage(result.response ?? confirmation);
      await loadTrack();
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  };

  const connect = () => {
    window.open(`${api.baseUrl ?? "http://127.0.0.1:8000"}/api/integrations/spotify/authorize`, "_blank", "width=600,height=700");
  };

  const searchAndPlay = async (event) => {
    event.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setMessage("");
    try {
      const result = await api("/api/integrations/spotify/play", {
        method: "POST",
        body: JSON.stringify({ query: query.trim(), playlist }),
      });
      setMessage(result.response);
      setQuery("");
      await loadTrack();
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="hud-panel p-4" aria-label="Controles do Spotify">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-display text-sm tracking-wide text-arc-200">Spotify</h2>
        {status && (
          <span className={`rounded border px-2 py-1 text-[10px] ${status.connected ? "border-emerald-400/50 text-emerald-300" : "border-amber-400/50 text-amber-300"}`}>
            {status.connected ? "Conectado" : "Não conectado"}
          </span>
        )}
      </div>

      {!status ? (
        <Skeleton lines={3} label="Consultando o Spotify" />
      ) : !status.configured ? (
        <p className="text-xs text-red-300">Configure o Client ID e o Client Secret no arquivo .env.</p>
      ) : !status.connected ? (
        <div className="space-y-3">
          <p className="text-xs text-arc-300/70">Autorize sua conta para controlar a reprodução.</p>
          <button type="button" onClick={connect} className="w-full rounded border border-arc-400/60 px-3 py-2 text-xs text-arc-200 hover:bg-arc-500/20">
            Conectar Spotify
          </button>
        </div>
      ) : (
        <>
          {track ? (
            <p className="min-h-10 rounded border border-arc-700/70 px-3 py-2 text-xs leading-relaxed text-arc-200">{track}</p>
          ) : (
            <EmptyState icon="♪" title="Nada tocando agora" hint="Peça uma música abaixo ou diga “tocar Spotify”." />
          )}
          <form onSubmit={searchAndPlay} className="mt-3 space-y-2">
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={playlist ? "Nome da playlist" : "Nome da música ou artista"} className="w-full rounded border border-arc-700 bg-void/60 px-3 py-2 text-xs text-arc-100 outline-none focus:border-arc-300" />
            <div className="flex items-center justify-between gap-2">
              <label className="flex items-center gap-2 text-xs text-arc-300/80">
                <input type="checkbox" checked={playlist} onChange={(event) => setPlaylist(event.target.checked)} className="accent-arc-300" />
                Playlist
              </label>
              <button type="submit" disabled={loading || !query.trim()} className="rounded border border-arc-400/60 px-3 py-1.5 text-xs text-arc-200 hover:bg-arc-500/20 disabled:opacity-40">
                Buscar e tocar
              </button>
            </div>
          </form>
          <div className="mt-3 grid grid-cols-4 gap-1.5">
            <button type="button" onClick={() => command("voltar música no Spotify", "Faixa anterior.")} disabled={loading} className="rounded border border-arc-700 px-2 py-2 text-lg text-arc-200 hover:bg-arc-500/20 disabled:opacity-40" aria-label="Faixa anterior">⏮</button>
            <button type="button" onClick={() => command("tocar Spotify", "Reprodução retomada.")} disabled={loading} className="rounded border border-arc-700 px-2 py-2 text-lg text-arc-200 hover:bg-arc-500/20 disabled:opacity-40" aria-label="Tocar Spotify">▶</button>
            <button type="button" onClick={() => command("pausar Spotify", "Spotify pausado.")} disabled={loading} className="rounded border border-arc-700 px-2 py-2 text-lg text-arc-200 hover:bg-arc-500/20 disabled:opacity-40" aria-label="Pausar Spotify">⏸</button>
            <button type="button" onClick={() => command("próxima música no Spotify", "Avançando a faixa.")} disabled={loading} className="rounded border border-arc-700 px-2 py-2 text-lg text-arc-200 hover:bg-arc-500/20 disabled:opacity-40" aria-label="Próxima música">⏭</button>
          </div>
          <button type="button" onClick={() => onSend("abrir Spotify")} className="mt-2 w-full rounded border border-arc-400/60 px-3 py-2 text-xs text-arc-200 hover:bg-arc-500/20">
            Abrir aplicativo
          </button>
        </>
      )}
      {message && <p className="mt-3 text-xs text-arc-300/80">{message}</p>}
    </section>
  );
}

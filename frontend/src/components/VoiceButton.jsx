import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { DEFAULT_INTRO_SONG, SILENT_MUSIC_TEXT, VOICE_SAMPLE, VOICE_STYLES, musicErrorText, shouldPlayOnOpen } from "../utils/voiceStyles.js";

// V8.13: botão VOZ no topo da central, ao lado do ÁUDIO. Abre um painel para trocar a voz do JARVIS (toca um
// exemplo com a voz nova) e, ao abrir, já solta a música de entrada: Back in Black, do AC/DC (a do Homem de Ferro).
// A música toca pelo Spotify do usuário (busca na conta dele; nada de música embutida no JARVIS).
let playedThisPage = false; // toca ao abrir só uma vez por página aberta (abrir de novo não reinicia a música)

export default function VoiceButton({ api }) {
  const [open, setOpen] = useState(false);
  const [prefs, setPrefs] = useState(null);
  const [busy, setBusy] = useState("");
  const [music, setMusic] = useState({ state: "idle", text: "" }); // idle | playing | paused | error
  // V8.15.1: volume da música (barra). Guardado no PC: o Back in Black e o fim do briefing usam esse volume.
  const [volume, setVolume] = useState(null);
  const [volNote, setVolNote] = useState("");
  const volTimer = useRef(0);
  const volumeRef = useRef(null);
  volumeRef.current = volume;
  const sendVolume = (v) => api("/api/integrations/spotify/volume", { method: "POST", body: JSON.stringify({ percent: v }) })
    .then(() => setVolNote(""))
    .catch((err) => setVolNote(err.message || "Não deu para mudar o volume agora."));
  const changeVolume = (v) => {
    setVolume(v);
    clearTimeout(volTimer.current); // arrastando: manda só quando parar um instante
    volTimer.current = setTimeout(() => sendVolume(v), 250);
  };
  useEffect(() => () => clearTimeout(volTimer.current), []);
  const wrapRef = useRef(null);
  const panelRef = useRef(null);
  const [pos, setPos] = useState({ top: 64, right: 16 });

  const song = prefs?.intro_song || DEFAULT_INTRO_SONG;

  const play = async (query) => {
    setMusic({ state: "loading", text: "Chamando o Spotify… (se estiver fechado, eu abro)" });
    try {
      // V8.13.2: o PC escolhe o aparelho e abre o Spotify se precisar (pode levar uns segundos)
      await api("/api/integrations/spotify/play", { method: "POST", body: JSON.stringify({ query, playlist: false }), timeout: 40_000 });
      playedThisPage = true; // só conta como "já tocou" quando tocou de verdade (antes uma falha travava as próximas)
      setMusic({ state: "playing", text: `🎸 Tocando ${query}` });
      if (volumeRef.current != null) sendVolume(volumeRef.current); // V8.15.1: no volume que você escolheu
    } catch (err) {
      // V8.13.2: o motivo vem do PC (sem aparelho, sem Premium, não conectado); antes tudo virava "reconecte"
      setMusic({ state: "error", text: musicErrorText(err.message) });
    }
  };

  const pause = async () => {
    try {
      await api("/api/integrations/spotify/control", { method: "POST", body: JSON.stringify({ action: "pause" }) });
      setMusic({ state: "paused", text: "Música pausada." });
    } catch {
      setMusic((m) => ({ ...m, text: "Não consegui pausar agora." }));
    }
  };

  useEffect(() => {
    if (!open) return undefined;
    let alive = true;
    api("/api/integrations/spotify/volume").then((v) => alive && setVolume(Number(v?.percent) || 0)).catch(() => {});
    api("/api/prefs").then((p) => {
      if (!alive) return;
      setPrefs(p);
      const q = p?.intro_song || DEFAULT_INTRO_SONG;
      if (shouldPlayOnOpen({ alreadyPlayed: playedThisPage, silent: p?.silent_mode, song: q })) {
        play(q);
      } else if (p?.silent_mode && !playedThisPage) {
        setMusic({ state: "idle", text: SILENT_MUSIC_TEXT }); // antes ficava quieto sem dizer por quê
      }
    }).catch(() => setPrefs({}));
    // o painel fica fora da barra do topo (portal): a barra corta o que sai dela (overflow hidden)
    const place = () => {
      const r = wrapRef.current?.getBoundingClientRect();
      if (r) setPos({ top: Math.round(r.bottom + 8), right: Math.max(16, Math.round(window.innerWidth - r.right)) });
    };
    place();
    window.addEventListener("resize", place);
    const onDown = (e) => {
      if (wrapRef.current?.contains(e.target) || panelRef.current?.contains(e.target)) return;
      setOpen(false);
    };
    const onKey = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("pointerdown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      alive = false;
      window.removeEventListener("resize", place);
      document.removeEventListener("pointerdown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  const choose = async (key) => {
    setBusy(key);
    try {
      await api("/api/prefs", { method: "PATCH", body: JSON.stringify({ voice_style: key }) });
      setPrefs((p) => ({ ...(p || {}), voice_style: key }));
      await api("/api/speak", { method: "POST", body: JSON.stringify({ text: VOICE_SAMPLE }) });
    } catch {
      /* sem o PC agora: fica como estava */
    } finally {
      setTimeout(() => setBusy(""), 1500);
    }
  };

  // liga/desliga uma preferência da música (entrar na central; V8.14.1: inicialização do dia)
  const togglePref = async (key, on) => {
    setPrefs((p) => ({ ...(p || {}), [key]: on }));
    try {
      await api("/api/prefs", { method: "PATCH", body: JSON.stringify({ [key]: on }) });
    } catch {
      setPrefs((p) => ({ ...(p || {}), [key]: !on }));
    }
  };

  const current = prefs?.voice_style || "natural";
  return (
    <span className="hl-act-wrap" ref={wrapRef}>
      <button type="button" className={`hl-act${open ? " is-active" : ""}`} onClick={() => setOpen((v) => !v)}
        aria-expanded={open} aria-haspopup="dialog" title="Trocar a voz do JARVIS (e soltar a música de entrada)">
        <i aria-hidden="true">◍</i>VOZ
      </button>
      {open && createPortal(
        <div className="hv-panel" role="dialog" aria-label="Voz do JARVIS" ref={panelRef} style={{ top: pos.top, right: pos.right }}>
          <div className="hv-head">VOZ DO JARVIS</div>
          <div className="hv-styles">
            {VOICE_STYLES.map(([key, label, desc]) => (
              <button key={key} type="button" className={`hv-style${current === key ? " is-on" : ""}`} onClick={() => choose(key)}
                aria-pressed={current === key} title={desc}>
                <b>{current === key ? "● " : ""}{label}</b>
                <small>{busy === key ? "falando…" : desc}</small>
              </button>
            ))}
          </div>
          <div className="hv-music">
            <div className={`hv-now is-${music.state}`}>
              <span className="hv-eq" aria-hidden="true"><i /><i /><i /></span>
              <span>{music.text || `🎸 Música de entrada: ${song}`}</span>
            </div>
            <label className="hv-volume">
              <span aria-hidden="true">{volume === 0 ? "🔇" : volume != null && volume < 40 ? "🔉" : "🔊"}</span>
              <input type="range" min="0" max="100" step="5" value={volume ?? 60} disabled={volume == null}
                onChange={(e) => changeVolume(Number(e.target.value))} aria-label="Volume da música" />
              <b>{volume == null ? "…" : `${volume}%`}</b>
            </label>
            {volNote && <small className="hv-volnote" role="status">{volNote}</small>}
            <div className="hv-actions">
              {music.state === "playing"
                ? <button type="button" className="hv-btn" onClick={pause}>⏸ PAUSAR</button>
                : <button type="button" className="hv-btn" onClick={() => play(song)} disabled={music.state === "loading"}>▶ TOCAR</button>}
              <label className="hv-check">
                <input type="checkbox" checked={prefs ? prefs.intro_song_morning !== false : true} disabled={!prefs}
                  onChange={(e) => togglePref("intro_song_morning", e.target.checked)} />
                Tocar na inicialização do dia (bom dia), baixinho durante o briefing
              </label>
              <label className="hv-check">
                <input type="checkbox" checked={prefs ? prefs.intro_song_on_entry !== false : true} disabled={!prefs}
                  onChange={(e) => togglePref("intro_song_on_entry", e.target.checked)} />
                Tocar quando eu entrar na central
              </label>
              <label className="hv-check">
                <input type="checkbox" checked={prefs ? prefs.briefing_pause_music !== false : true} disabled={!prefs}
                  onChange={(e) => togglePref("briefing_pause_music", e.target.checked)} />
                Pausar a minha música durante o briefing (e continuar no fim)
              </label>
            </div>
          </div>
        </div>,
        document.body,
      )}
    </span>
  );
}

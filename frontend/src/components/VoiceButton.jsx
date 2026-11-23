import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { DEFAULT_INTRO_SONG, VOICE_SAMPLE, VOICE_STYLES, shouldPlayOnOpen } from "../utils/voiceStyles.js";

// V8.13: botão VOZ no topo da central, ao lado do ÁUDIO. Abre um painel para trocar a voz do JARVIS (toca um
// exemplo com a voz nova) e, ao abrir, já solta a música de entrada: Back in Black, do AC/DC (a do Homem de Ferro).
// A música toca pelo Spotify do usuário (busca na conta dele; nada de música embutida no JARVIS).
let playedThisPage = false; // toca ao abrir só uma vez por página aberta (abrir de novo não reinicia a música)

export default function VoiceButton({ api }) {
  const [open, setOpen] = useState(false);
  const [prefs, setPrefs] = useState(null);
  const [busy, setBusy] = useState("");
  const [music, setMusic] = useState({ state: "idle", text: "" }); // idle | playing | paused | error
  const wrapRef = useRef(null);
  const panelRef = useRef(null);
  const [pos, setPos] = useState({ top: 64, right: 16 });

  const song = prefs?.intro_song || DEFAULT_INTRO_SONG;

  const play = async (query) => {
    setMusic({ state: "loading", text: "Chamando o Spotify…" });
    try {
      await api("/api/integrations/spotify/play", { method: "POST", body: JSON.stringify({ query, playlist: false }), timeout: 20_000 });
      setMusic({ state: "playing", text: `🎸 Tocando ${query}` });
    } catch (err) {
      const msg = /409|expirou|autoriz/i.test(err.message || "")
        ? "O Spotify precisa ser reconectado (Configurações › Integrações)."
        : /404|dispositivo|device|active/i.test(err.message || "")
          ? "Abra o Spotify em algum aparelho e toque em TOCAR."
          : "Não deu para tocar agora. Confira se o Spotify está conectado.";
      setMusic({ state: "error", text: msg });
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
    api("/api/prefs").then((p) => {
      if (!alive) return;
      setPrefs(p);
      const q = p?.intro_song || DEFAULT_INTRO_SONG;
      if (shouldPlayOnOpen({ alreadyPlayed: playedThisPage, silent: p?.silent_mode, song: q })) {
        playedThisPage = true;
        play(q);
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

  const toggleEntry = async (on) => {
    setPrefs((p) => ({ ...(p || {}), intro_song_on_entry: on }));
    try {
      await api("/api/prefs", { method: "PATCH", body: JSON.stringify({ intro_song_on_entry: on }) });
    } catch {
      setPrefs((p) => ({ ...(p || {}), intro_song_on_entry: !on }));
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
            <div className="hv-actions">
              {music.state === "playing"
                ? <button type="button" className="hv-btn" onClick={pause}>⏸ PAUSAR</button>
                : <button type="button" className="hv-btn" onClick={() => play(song)} disabled={music.state === "loading"}>▶ TOCAR</button>}
              <label className="hv-check">
                <input type="checkbox" checked={prefs ? prefs.intro_song_on_entry !== false : true} disabled={!prefs}
                  onChange={(e) => toggleEntry(e.target.checked)} />
                Tocar quando eu entrar na central
              </label>
            </div>
          </div>
        </div>,
        document.body,
      )}
    </span>
  );
}

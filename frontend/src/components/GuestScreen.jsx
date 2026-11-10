import { useCallback, useEffect, useState } from "react";
import ArcReactorHUD from "./ArcReactorHUD.jsx";
import WeatherWidget from "./WeatherWidget.jsx";
import { startPolling } from "../hooks/usePolling.js";
import useNow from "../hooks/useNow.js";

// Modo visitante (seção 17.6): só relógio, clima e controles de música.
// O backend bloqueia (403) todas as rotas pessoais enquanto este modo estiver ativo.
export default function GuestScreen({ api, jarvisState, listening, interim, onToggleMic, onExit, onAsk, reply }) {
  const now = useNow();
  const [track, setTrack] = useState("");
  const [musicError, setMusicError] = useState("");
  const [text, setText] = useState("");


  const loadTrack = useCallback(() => {
    api("/api/integrations/spotify/now-playing")
      .then((d) => { setTrack(d.track || ""); setMusicError(""); })
      .catch((err) => setMusicError(err.message));
  }, [api]);

  useEffect(() => {
    return startPolling(loadTrack, 15000);
  }, [loadTrack]);

  const control = async (action) => {
    try {
      await api("/api/integrations/spotify/control", { method: "POST", body: JSON.stringify({ action }) });
      setMusicError("");
      setTimeout(loadTrack, 800);
    } catch (err) {
      setMusicError(err.message);
    }
  };

  return (
    <div className="gs-root" role="main">
      <div className="ls-bracket ls-bracket-tl" aria-hidden="true" />
      <div className="ls-bracket ls-bracket-tr" aria-hidden="true" />
      <div className="ls-bracket ls-bracket-bl" aria-hidden="true" />
      <div className="ls-bracket ls-bracket-br" aria-hidden="true" />

      <header className="gs-head">
        <span className="gs-badge">👤 MODO VISITANTE</span>
        <button type="button" className="ls-chip" onClick={onExit}>SAIR DO MODO VISITANTE</button>
      </header>

      <div className="gs-grid">
        <section className="gs-card gs-clock">
          <div className="gs-time">{now.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</div>
          <div className="gs-date">{now.toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" })}</div>
        </section>

        <section className="gs-card gs-orb">
          <ArcReactorHUD state={listening ? "speaking" : jarvisState} />
          <div className="gs-reply" aria-live="polite">{listening ? (interim || "Ouvindo...") : reply}</div>
          <form
            className="gs-ask"
            onSubmit={(e) => {
              e.preventDefault();
              if (!text.trim()) return;
              onAsk(text.trim());
              setText("");
            }}
          >
            <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Pergunte as horas, o clima..." aria-label="Pergunta" />
            <button type="submit">ENVIAR</button>
            <button type="button" onClick={onToggleMic} className={listening ? "on" : ""} aria-label="Falar">🎙</button>
          </form>
        </section>

        <section className="gs-card gs-weather">
          <WeatherWidget api={api} />
        </section>

        <section className="gs-card gs-music">
          <div className="gs-label">MÚSICA</div>
          <div className="gs-track">{musicError || track || "Nenhuma música tocando."}</div>
          <div className="gs-controls">
            <button type="button" onClick={() => control("previous")} aria-label="Faixa anterior">⏮</button>
            <button type="button" onClick={() => control("pause")} aria-label="Pausar">⏸</button>
            <button type="button" onClick={() => control("play")} aria-label="Tocar">▶</button>
            <button type="button" onClick={() => control("next")} aria-label="Próxima faixa">⏭</button>
          </div>
        </section>
      </div>
      <footer className="ls-footer"><span>ACESSO RESTRITO · DADOS PESSOAIS PROTEGIDOS · ESPAÇO = FALAR</span></footer>
    </div>
  );
}

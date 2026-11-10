import { useState } from "react";
import useFanMatch, { matchLogoUrl, matchSides, matchTime } from "../hooks/useFanMatch.js";
import { API_URL, getJarvisToken } from "../utils/api.js";

function TeamShield({ src, alt }) {
  const [failedSrc, setFailedSrc] = useState(null);
  const errored = failedSrc === src; // volta a tentar quando o escudo (src) muda
  if (!src || errored) {
    return <span className="fmb-crest fmb-crest-empty" aria-hidden="true">{(alt || "?").slice(0, 1)}</span>;
  }
  return <img className="fmb-crest" src={src} alt={alt || "Escudo"} onError={() => setFailedSrc(src)} loading="lazy" referrerPolicy="no-referrer" />;
}

// Faixa do dia de jogo na central (Modo Torcedor). V4.4: placar real (ESPN), mandante certo,
// horário de Brasília e de onde veio a informação.
export default function FanMatchBanner({ api, onSend, refreshKey = 0 }) {
  const { match, team } = useFanMatch(api, true, refreshKey);
  const [dismissed, setDismissed] = useState(false);

  if (dismissed || !match || !match.is_match_day) return null;

  const isLive = match.status === "live";
  const isFinished = match.status === "finished";
  const s = matchSides(match, team?.name || "Palmeiras");
  const sources = (match.sources || []).map((x) => (x === "espn" ? "ESPN" : x === "google_news" ? "Google Notícias" : x)).join(" · ");

  return (
    <div className={`fmb-root ${isLive ? "is-live" : ""}`}>
      <div className="fmb-left">
        <TeamShield src={matchLogoUrl(match, s.homeLogoSide, { base: API_URL, token: getJarvisToken() })} alt={s.home} />
        <span className="fmb-ball" aria-hidden="true">⚽</span>
        <strong className="fmb-tag">{isLive ? "BOLA ROLANDO" : isFinished ? "FIM DE JOGO" : "HOJE É DIA DE JOGO"}</strong>
        <span className="fmb-match">
          {s.home}
          {isLive || isFinished ? <b className="fmb-score">{s.homeScore} x {s.awayScore}</b> : <em> x </em>}
          {s.away}
        </span>
        <TeamShield src={matchLogoUrl(match, s.awayLogoSide, { base: API_URL, token: getJarvisToken() })} alt={s.away} />
        <span className="fmb-meta">
          {match.competition}
          {match.venue ? ` · ${match.venue}` : ""}
          {isLive ? ` · ${match.minute || "ao vivo"}` : isFinished ? "" : ` · ${matchTime(match)} · ${match.countdown}`}
        </span>
        {sources && <span className="fmb-src" title="Fonte dos dados (sem IA)">{sources}</span>}
      </div>

      <div className="fmb-actions">
        {onSend && (
          <button type="button" className="fmb-btn" onClick={() => onSend("avante palestra")}>
            AVANTE PALESTRA!
          </button>
        )}
        <button type="button" className="fmb-close" onClick={() => setDismissed(true)} title="Fechar aviso do jogo" aria-label="Fechar">
          ✕
        </button>
      </div>
    </div>
  );
}

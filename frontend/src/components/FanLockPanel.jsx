import { useState } from "react";
import useNow from "../hooks/useNow.js";
import useFanMatch, { matchLogoUrl, matchSides, matchTime } from "../hooks/useFanMatch.js";
import { API_URL, getJarvisToken } from "../utils/api.js";

// V4.4: painel do jogo na tela de bloqueio (Modo Torcedor). Só dados públicos do jogo (ESPN e
// Google Notícias, sem IA), então pode aparecer com a central bloqueada.
// Antes do jogo: contagem e próximos jogos. Durante: placar, tempo, gols e estatísticas.
// Depois: resultado e o próximo jogo.

function minuteNumber(minute) {
  const m = String(minute || "").match(/^(\d+)(?:'?\s*\+\s*(\d+))?/);
  return m ? Number(m[1]) + Number(m[2] || 0) : null;
}

function Crest({ src, name }) {
  const [failedSrc, setFailedSrc] = useState(null);
  const errored = failedSrc === src; // volta a tentar quando o escudo (src) muda
  if (!src || errored) return <span className="flp-crest flp-crest-empty" aria-hidden="true">{(name || "?").slice(0, 1)}</span>;
  return <img className="flp-crest" src={src} alt="" loading="lazy" referrerPolicy="no-referrer" onError={() => setFailedSrc(src)} />;
}

function StatRow({ label, ours, theirs, weAreHome, pct = false }) {
  if (ours == null && theirs == null) return null;
  const h = weAreHome ? ours ?? 0 : theirs ?? 0;
  const a = weAreHome ? theirs ?? 0 : ours ?? 0;
  const total = h + a || 1;
  const homeShare = (h / total) * 100;
  const fmt = (v) => (pct ? `${Math.round(v)}%` : Math.round(v));
  return (
    <div className="flp-stat">
      <span className={`flp-stat-v ${weAreHome ? "is-ours" : ""}`}>{fmt(h)}</span>
      <div className="flp-stat-mid">
        <span className="flp-stat-l">{label}</span>
        <div className="flp-stat-bar" aria-hidden="true">
          <i className={weAreHome ? "is-ours" : ""} style={{ width: `${homeShare}%` }} />
          <i className={weAreHome ? "" : "is-ours"} style={{ width: `${100 - homeShare}%` }} />
        </div>
      </div>
      <span className={`flp-stat-v ${weAreHome ? "" : "is-ours"}`}>{fmt(a)}</span>
    </div>
  );
}

function eventLabel(e) {
  if (e.kind === "red_card") return "🟥";
  return "⚽";
}

export default function FanLockPanel({ api, refreshKey = 0 }) {
  const { match, team, upcoming } = useFanMatch(api, true, refreshKey);
  const now = useNow(true);
  if (!match || match.status === "unknown") return null;

  const teamName = team?.name || "Palmeiras";
  const s = matchSides(match, teamName);
  const live = match.status === "live";
  const half = live && match.minute === "Intervalo";
  const done = match.status === "finished";
  const today = match.is_match_day;
  const homeLogo = matchLogoUrl(match, s.homeLogoSide, { base: API_URL, token: getJarvisToken() });
  const awayLogo = matchLogoUrl(match, s.awayLogoSide, { base: API_URL, token: getJarvisToken() });
  const details = match.details || {};
  const stats = details.stats;
  const events = (details.events || []).filter((e) => e.kind !== "own_goal" || e.player);
  const minute = minuteNumber(match.minute);
  const progress = half ? 50 : minute != null ? Math.min(100, (minute / 90) * 100) : done ? 100 : 0;
  const standing = details.standing;

  let tag;
  if (half) tag = "INTERVALO";
  else if (live) tag = `AO VIVO · ${match.minute || ""}`;
  else if (done) tag = "FIM DE JOGO";
  else if (today) tag = `HOJE · ${matchTime(match)}`;
  else tag = "PRÓXIMO JOGO";

  const ours = s.weAreHome ? s.homeScore : s.awayScore;
  const theirs = s.weAreHome ? s.awayScore : s.homeScore;
  const result = done ? (ours > theirs ? "VITÓRIA" : ours === theirs ? "EMPATE" : "DERROTA") : null;
  const next = upcoming?.[0];
  const showScore = live || done;
  const kickoff = new Date(match.date);
  const minsToKick = Math.round((kickoff - now) / 60000);

  return (
    <aside className={`flp-root ${live ? "is-live" : ""} ${done ? "is-done" : ""}`} aria-label="Jogo do Palmeiras" role="status" aria-live="polite">
      <header className="flp-head">
        <span className="flp-tag">{tag}</span>
        <span className="flp-comp">{match.competition}</span>
      </header>

      <div className="flp-board">
        <div className={`flp-team ${s.weAreHome ? "is-ours" : ""}`}>
          <Crest src={homeLogo} name={s.home} />
          <span>{s.home}</span>
        </div>
        <div className="flp-score">
          {showScore ? (
            <strong>{s.homeScore}<em>x</em>{s.awayScore}</strong>
          ) : (
            <strong className="flp-vs">VS</strong>
          )}
          {result && <span className={`flp-result r-${result.toLowerCase()}`}>{result}</span>}
        </div>
        <div className={`flp-team ${s.weAreHome ? "" : "is-ours"}`}>
          <Crest src={awayLogo} name={s.away} />
          <span>{s.away}</span>
        </div>
      </div>

      {live && (
        <div className="flp-clock" aria-label={`Tempo de jogo: ${match.minute}`}>
          <div className="flp-clock-bar"><i style={{ width: `${progress}%` }} /><b aria-hidden="true" /></div>
          <div className="flp-clock-l"><span>0'</span><span>INT</span><span>90'</span></div>
        </div>
      )}

      {!showScore && (
        <div className="flp-count">
          {today && match.time_known && minsToKick > 0 ? (
            <>
              <strong>{minsToKick >= 60 ? `${Math.floor(minsToKick / 60)}h ${String(minsToKick % 60).padStart(2, "0")}` : `${minsToKick} min`}</strong>
              <span>para a bola rolar</span>
            </>
          ) : (
            <span>{match.countdown}</span>
          )}
        </div>
      )}

      {events.length > 0 && (
        <ul className="flp-events">
          {events.slice(-6).map((e, i) => (
            <li key={`${e.minute}-${i}`} className={e.side === "ours" ? "is-ours" : ""}>
              <span className="flp-ev-ico" aria-hidden="true">{eventLabel(e)}</span>
              <span className="flp-ev-min">{e.minute}</span>
              <span className="flp-ev-who">
                {e.player || "Gol"}
                {e.kind === "own_goal" ? " (contra)" : e.penalty ? " (pênalti)" : ""}
                {e.assist ? <em> · assist. {e.assist}</em> : null}
              </span>
            </li>
          ))}
        </ul>
      )}

      {stats && showScore && (
        <div className="flp-stats">
          <StatRow label="POSSE" ours={stats.ours.possession} theirs={stats.theirs.possession} weAreHome={s.weAreHome} pct />
          <StatRow label="FINALIZAÇÕES" ours={stats.ours.shots} theirs={stats.theirs.shots} weAreHome={s.weAreHome} />
          <StatRow label="NO GOL" ours={stats.ours.on_target} theirs={stats.theirs.on_target} weAreHome={s.weAreHome} />
          <StatRow label="ESCANTEIOS" ours={stats.ours.corners} theirs={stats.theirs.corners} weAreHome={s.weAreHome} />
        </div>
      )}

      <footer className="flp-foot">
        <span>📍 {match.venue || "Estádio a confirmar"}</span>
        {standing?.rank > 0 && (
          <span className="flp-standing">{standing.table} · {standing.rank}º · {standing.points} pts</span>
        )}
      </footer>

      {(done || !today) && next && (
        <div className="flp-next">
          <span className="flp-next-l">PRÓXIMO</span>
          <span>{next.home_away === "away" ? `${next.opponent} x ${teamName}` : `${teamName} x ${next.opponent}`}</span>
          <span className="flp-next-d">{next.date_human} · {next.competition}</span>
        </div>
      )}
      {today && !done && upcoming?.length > 0 && !live && (
        <div className="flp-next">
          <span className="flp-next-l">DEPOIS</span>
          <span>{upcoming[0].home_away === "away" ? `${upcoming[0].opponent} x ${teamName}` : `${teamName} x ${upcoming[0].opponent}`}</span>
          <span className="flp-next-d">{upcoming[0].date_human}</span>
        </div>
      )}

      <span className="flp-src">{(match.sources || []).map((x) => (x === "espn" ? "ESPN" : "Google Notícias")).join(" · ") || "cache"} · sem IA</span>
    </aside>
  );
}

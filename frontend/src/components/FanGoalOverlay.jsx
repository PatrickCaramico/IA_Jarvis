import { useEffect } from "react";
import { matchSides } from "../hooks/useFanMatch.js";

// V4.4: momentos do Modo Torcedor na tela.
// event.kind: "goal" | "conceded" | "shout" | "half" | "full" — some sozinho; tocar fecha.
const DURATION = { goal: 8000, full: 9000, conceded: 5000, half: 5000, shout: 4000 };

function lastGoal(match, side) {
  const goals = (match?.details?.events || []).filter((e) => (e.kind === "goal" || e.kind === "own_goal") && e.side === side);
  return goals[goals.length - 1] || null;
}

export default function FanGoalOverlay({ event, onDone, teamName = "Palmeiras" }) {
  const kind = event?.kind;
  useEffect(() => {
    if (!event) return undefined;
    const t = setTimeout(() => onDone?.(), DURATION[kind] || 5000);
    return () => clearTimeout(t);
  }, [event, kind, onDone]);

  if (!event) return null;
  const match = event.match;
  const s = matchSides(match, teamName);
  const ours = s.weAreHome ? s.homeScore : s.awayScore;
  const theirs = s.weAreHome ? s.awayScore : s.homeScore;
  const scorer = kind === "goal" ? lastGoal(match, "ours") : kind === "conceded" ? lastGoal(match, "theirs") : null;

  let title = "AVANTE PALESTRA!";
  let sub = null;
  if (kind === "goal") title = "GOOOOL!";
  if (kind === "conceded") { title = "GOL DO ADVERSÁRIO"; sub = theirs > ours ? "Vamos virar, Verdão!" : "Bora, Verdão!"; }
  if (kind === "half") title = "INTERVALO";
  if (kind === "full") {
    title = "FIM DE JOGO";
    sub = ours > theirs ? "VITÓRIA DO VERDÃO!" : ours === theirs ? "EMPATE" : "Não foi dessa vez. Bora pro próximo!";
  }
  const win = kind === "full" && ours > theirs;
  const burst = kind === "goal" || win;

  return (
    <div className={`fgo-root fgo-${kind} ${win ? "fgo-win" : ""}`} role="status" aria-live="assertive" onClick={() => onDone?.()}>
      {burst && (
        <div className="fgo-burst" aria-hidden="true">
          {Array.from({ length: 14 }, (_, i) => <span key={i} style={{ "--i": i }} />)}
        </div>
      )}
      <div className="fgo-card">
        <div className="fgo-title">{title}</div>
        {scorer?.player && (
          <div className="fgo-scorer">
            ⚽ {scorer.player} {scorer.minute && <span>{scorer.minute}</span>}
            {scorer.assist && <em>assist. {scorer.assist}</em>}
          </div>
        )}
        {match && kind !== "shout" && (
          <div className="fgo-score">
            <span>{s.home}</span>
            <strong>{s.homeScore} <em>x</em> {s.awayScore}</strong>
            <span>{s.away}</span>
          </div>
        )}
        {match?.minute && (kind === "goal" || kind === "conceded") && !scorer?.minute && <div className="fgo-minute">{match.minute}</div>}
        {sub && <div className="fgo-sub">{sub}</div>}
      </div>
    </div>
  );
}

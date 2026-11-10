import { wordmarkStrokes, isJarvisName, LETTER_H, STROKE } from "../utils/wordmark.js";

// Tela de boas-vindas (V4.2.2): o logo Núcleo entra levemente animado e o nome se desenha em traço.
// Os anéis entram girando, o núcleo acende e depois fica "respirando". Tudo para com "reduzir movimento".
export default function WelcomeLogo({ name = "JARVIS", size = 150 }) {
  const { strokes, width } = wordmarkStrokes();
  const drawName = isJarvisName(name);
  return (
    <div className="wl-root" aria-label={name} role="img">
      <svg className="wl-logo" width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
        <circle className="wl-core-halo" cx="32" cy="32" r="8" fill="none" stroke="currentColor" strokeOpacity="0.35" strokeWidth="6" />
        <circle className="wl-core" cx="32" cy="32" r="8" fill="currentColor" />
        <g className="wl-ring wl-ring1">
          <circle cx="32" cy="32" r="17" fill="none" stroke="currentColor" strokeWidth="3.5"
            strokeDasharray="22.6 13" strokeLinecap="round" transform="rotate(-90 32 32)" />
        </g>
        <g className="wl-ring wl-ring2">
          <circle cx="32" cy="32" r="26" fill="none" stroke="currentColor" strokeWidth="2.5" strokeOpacity="0.8"
            strokeDasharray="30.8 10" strokeLinecap="round" transform="rotate(-45 32 32)" />
        </g>
      </svg>
      {drawName ? (
        <svg className="wl-word" viewBox={`-6 -6 ${width + 12} ${LETTER_H + 12}`} height="44" aria-hidden="true">
          <g fill="none" stroke="currentColor" strokeWidth={STROKE} strokeLinecap="square" strokeLinejoin="miter">
            {strokes.map((s, i) => (
              <path key={i} d={s.d} transform={`translate(${s.x} 0)`} pathLength="1"
                className="wl-stroke" style={{ animationDelay: `${0.55 + s.letter * 0.12}s` }} />
            ))}
          </g>
        </svg>
      ) : (
        <h1 className="ls-brand wl-text">{name}</h1>
      )}
    </div>
  );
}

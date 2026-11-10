// Logo "Núcleo" do Branding Book 4.2: núcleo central com dois anéis segmentados.
// Desenho original (não reproduz o reator de nenhuma marca). Usa currentColor: herda a cor do texto.
// spin=true gira os anéis devagar (desligado com "reduzir movimento" no sistema).
export default function JarvisLogo({ size = 28, spin = false, title = "JARVIS", className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      role="img"
      aria-label={title}
      className={`jarvis-logo ${spin ? "jarvis-logo-spin" : ""} ${className}`}
    >
      <circle cx="32" cy="32" r="8" fill="currentColor" />
      <circle cx="32" cy="32" r="8" fill="none" stroke="currentColor" strokeOpacity="0.35" strokeWidth="6" />
      <g className="jarvis-logo-ring1">
        <circle cx="32" cy="32" r="17" fill="none" stroke="currentColor" strokeWidth="3.5"
          strokeDasharray="22.6 13" strokeLinecap="round" transform="rotate(-90 32 32)" />
      </g>
      <g className="jarvis-logo-ring2">
        <circle cx="32" cy="32" r="26" fill="none" stroke="currentColor" strokeWidth="2.5" strokeOpacity="0.8"
          strokeDasharray="30.8 10" strokeLinecap="round" transform="rotate(-45 32 32)" />
      </g>
    </svg>
  );
}

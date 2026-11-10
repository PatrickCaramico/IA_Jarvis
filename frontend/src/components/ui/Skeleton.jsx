// Esqueleto de carregamento e estado vazio (V4.2.2, Branding Book: "carregando" e "vazio").
// O brilho que passa pelas barras some com "reduzir movimento" do sistema (ver feedback.css).

const WIDTHS = ["92%", "74%", "86%", "60%", "80%"];

// lines: quantas barras de texto. block: um retângulo maior em cima (ícone/valor em destaque).
export function Skeleton({ lines = 3, block = false, label = "Carregando", className = "" }) {
  return (
    <div className={`j-skel ${className}`} role="status" aria-live="polite" aria-label={label}>
      {block && <div className="j-skel-bar j-skel-block" />}
      {Array.from({ length: lines }, (_, i) => (
        <div key={i} className="j-skel-bar" style={{ width: WIDTHS[i % WIDTHS.length] }} />
      ))}
      <span className="j-sr-only">{label}...</span>
    </div>
  );
}

// Estado vazio amigável: ícone, frase curta e, se fizer sentido, uma ação.
export function EmptyState({ icon = "◇", title, hint, action, onAction, tone = "cyan" }) {
  return (
    <div className={`j-empty j-empty-${tone}`} role="status">
      <span className="j-empty-icon" aria-hidden="true">{icon}</span>
      <p className="j-empty-title">{title}</p>
      {hint && <p className="j-empty-hint">{hint}</p>}
      {action && onAction && (
        <button type="button" className="j-empty-action" onClick={onAction}>{action}</button>
      )}
    </div>
  );
}

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

// V7.2: 📘 BRANDING BOOK dentro do JARVIS (botão na central, em CONTROLES e na tela de bloqueio).
// O livro ilustrado (docs/branding-book.html) vai junto com a central; sem ele, abre o do site.
const LOCAL = `${import.meta.env.BASE_URL || "/"}branding-book.html`;
const SITE = "https://projeto-jarvis-ia.netlify.app/branding";

export default function BrandingBook({ onClose }) {
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return createPortal(
    <div className="bb-overlay" role="dialog" aria-modal="true" aria-label="Branding Book do JARVIS">
      <div className="bb">
        <header className="bb-head">
          <span>📘 BRANDING BOOK</span>
          <small>Identidade visual, cores, tipografia e componentes do J.A.R.V.I.S.</small>
          <a href={SITE} target="_blank" rel="noreferrer" className="bb-link">ABRIR NO SITE ↗</a>
          <button type="button" className="bb-x" onClick={onClose} aria-label="Fechar o Branding Book">✕</button>
        </header>
        <div className="bb-frame">
          {!loaded && <div className="bb-loading" role="status">Carregando o Branding Book…</div>}
          <iframe src={LOCAL} title="Branding Book do JARVIS" onLoad={() => setLoaded(true)} />
        </div>
      </div>
    </div>,
    document.body,
  );
}

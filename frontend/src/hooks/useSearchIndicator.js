import { useCallback, useEffect, useRef } from "react";

// Janelinha "JARVIS · pesquisando" aberta durante buscas longas (refatoração 4.2: saiu do App.jsx).
// Fecha sozinha quando o usuário volta para a aba principal.
export default function useSearchIndicator() {
  const searchIndicatorRef = useRef(null);

  const closeSearchIndicator = useCallback(() => {
    const popup = searchIndicatorRef.current;
    if (popup && !popup.closed) popup.close();
    searchIndicatorRef.current = null;
  }, []);

  const openSearchIndicator = useCallback((label = "JARVIS · pesquisando") => {
    closeSearchIndicator();
    const popup = window.open(
      "",
      "jarvis-search-indicator",
      "popup=yes,width=320,height=320,left=40,top=40,resizable=yes",
    );
    if (!popup) return;
    searchIndicatorRef.current = popup;
    popup.document.title = "J.A.R.V.I.S. · Pesquisa";
    popup.document.body.innerHTML = `
      <style>
        :root { color-scheme: dark; }
        * { box-sizing: border-box; }
        body {
          margin: 0; min-height: 100vh; display: grid; place-items: center;
          overflow: hidden; background: radial-gradient(circle, #102638, #03070d 70%);
          color: #b9edff; font-family: Segoe UI, sans-serif; text-align: center;
        }
        .wrap { display: grid; gap: 18px; justify-items: center; }
        .reactor {
          width: 118px; height: 118px; border: 3px solid #63d9ff;
          border-radius: 50%; box-shadow: 0 0 18px #25b9ef, inset 0 0 20px #25b9ef;
          animation: pulse 1.4s ease-in-out infinite;
          position: relative;
        }
        .reactor::after {
          content: ""; position: absolute; inset: 23px; border: 2px dashed #b9edff;
          border-radius: 50%; animation: spin 3s linear infinite;
        }
        .label { font-size: 12px; letter-spacing: .14em; text-transform: uppercase; }
        .hint { opacity: .62; font-size: 11px; }
        @keyframes pulse { 50% { transform: scale(1.08); opacity: .72; } }
        @keyframes spin { to { transform: rotate(360deg); } }
      </style>
      <div class="wrap">
        <div class="reactor" aria-label="Reator do JARVIS"></div>
        <div class="label">${label}</div>
        <div class="hint">Volte à hub principal para fechar esta janela</div>
      </div>`;
    popup.focus();
  }, [closeSearchIndicator]);

  useEffect(() => {
    const handleVisibility = () => {
      if (!document.hidden) closeSearchIndicator();
    };
    document.addEventListener("visibilitychange", handleVisibility);
    window.addEventListener("focus", handleVisibility);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibility);
      window.removeEventListener("focus", handleVisibility);
      closeSearchIndicator();
    };
  }, [closeSearchIndicator]);

  return { openSearchIndicator, closeSearchIndicator };
}

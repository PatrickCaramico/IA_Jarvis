import { Component, Suspense, lazy } from "react";

// Carrega um componente só quando ele aparece pela primeira vez (otimização 4.2).
// Telas e janelas pouco usadas (Configurações, modais, monitores) saem do pacote inicial,
// então a central abre mais rápido. Cada uma tem o seu próprio Suspense: enquanto o código
// chega (milissegundos, é local), só aquele pedaço fica vazio, nunca a tela inteira.
//
// V6.7.6: se o pedaço não carrega (o site foi atualizado com a aba aberta: o arquivo antigo não existe
// mais), a página recarrega UMA vez e pega a versão nova. Se ainda assim falhar, só aquele pedaço
// mostra o aviso, e a central continua de pé (antes a tela inteira ficava preta).
const RELOAD_KEY = "jarvis.chunkReloadAt";

function loadWithReload(load) {
  return () => load().catch((err) => {
    let last = 0;
    try {
      last = Number(sessionStorage.getItem(RELOAD_KEY)) || 0;
    } catch {
      /* sem armazenamento */
    }
    if (Date.now() - last > 60_000) {
      try {
        sessionStorage.setItem(RELOAD_KEY, String(Date.now()));
      } catch {
        /* sem armazenamento */
      }
      window.location.reload();
      return new Promise(() => {}); // espera o recarregamento
    }
    throw err;
  });
}

export class PieceBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error) {
    console.error("JARVIS: parte da tela falhou", error);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    if (this.props.quiet) return null;
    if (this.props.fullscreen) {
      return (
        <div role="alert" style={{ position: "fixed", inset: 0, display: "grid", placeItems: "center", background: "#0d3170", color: "#e3f4ff", font: "500 16px system-ui, sans-serif", textAlign: "center", padding: 24 }}>
          <div>
            <p style={{ fontSize: 20, marginBottom: 8 }}>O JARVIS precisa recarregar a tela.</p>
            <p style={{ opacity: 0.8, marginBottom: 16 }}>Provavelmente ele acabou de ser atualizado. Nada foi perdido.</p>
            <button type="button" onClick={() => window.location.reload()} style={{ padding: "10px 22px", borderRadius: 10, border: "1px solid #67e8f9", background: "rgba(103,232,249,.15)", color: "#e0fbff", font: "600 15px system-ui, sans-serif", cursor: "pointer" }}>
              RECARREGAR
            </button>
          </div>
        </div>
      );
    }
    return (
      <div role="alert" style={{ padding: 16, margin: 12, borderRadius: 12, border: "1px solid rgba(251,191,36,.6)", background: "rgba(3,14,38,.92)", color: "#fde68a", font: "500 14px system-ui, sans-serif", textAlign: "center", position: "relative", zIndex: 90 }}>
        Esta parte não carregou (o JARVIS pode ter sido atualizado).{" "}
        <button type="button" onClick={() => window.location.reload()} style={{ marginLeft: 8, padding: "4px 12px", borderRadius: 8, border: "1px solid #fbbf24", background: "transparent", color: "#fde68a", cursor: "pointer" }}>
          RECARREGAR
        </button>
      </div>
    );
  }
}

export default function lazyComponent(load) {
  const Lazy = lazy(loadWithReload(load));
  function LazyComponent(props) {
    return (
      <PieceBoundary>
        <Suspense fallback={null}>
          <Lazy {...props} />
        </Suspense>
      </PieceBoundary>
    );
  }
  return LazyComponent;
}

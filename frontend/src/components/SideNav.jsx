import { useEffect } from "react";

/**
 * SideNav — Menu lateral de navegação principal do JARVIS.
 * Estrutura de navegação tática entre telas e módulos.
 */

const NAV_ITEMS = [
  { id: "chat",           icon: "◈", label: "Chat",           sub: "Interação e comandos" },
  { id: "hud",            icon: "⬡", label: "JARVIS / HUD",   sub: "Widgets & monitor inteligente" },
  { id: "water",          icon: "💧", label: "Hidratação",    sub: "Índice diário de água" },
  { id: "briefing",       icon: "◷", label: "Briefing",       sub: "Agenda, e-mail e notícias" },
  { id: "fontes",         icon: "⊞", label: "Fontes de Dados",sub: "Conexões e memória" },
  { id: "monitoramento",  icon: "◎", label: "Monitoramento",  sub: "Saúde e bem-estar" },
  { id: "financeiro",     icon: "◻", label: "Financeiro",     sub: "Saldos, gastos e mercado" },
  { id: "logs",           icon: "≡", label: "Logs",           sub: "Eventos e auditoria" },
  { id: "configuracoes",  icon: "⚙", label: "Configurações",  sub: "Voz, IA, áudio e perfil" },
  { id: "onboarding",     icon: "★", label: "Primeiros Passos",sub: "Apresentação e tour" },
];

export default function SideNav({ activeSection, onNavigate, onClose }) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <>
      {/* Backdrop transparente para clicar fora e fechar */}
      <div className="snav-backdrop" onClick={onClose} aria-hidden="true" />

      <aside className="snav-root" role="navigation" aria-label="Navegação principal">
        {/* Brand / Logo com botão fechar no topo */}
        <div className="snav-brand flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="snav-logo-ring" aria-hidden="true" />
            <div className="snav-brand-text">
              <strong>J.A.R.V.I.S.</strong>
              <span>CENTRO DE CONTROLE</span>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-cyan-400/60 hover:text-white p-1 rounded hover:bg-cyan-500/20 transition-colors text-sm font-mono cursor-pointer"
            title="Fechar menu (Esc)"
          >
            ✕
          </button>
        </div>

        {/* Lista de navegação */}
        <nav className="snav-list">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`snav-item cursor-pointer${activeSection === item.id ? " snav-active" : ""}`}
              onClick={() => onNavigate(item.id)}
              aria-current={activeSection === item.id ? "page" : undefined}
            >
              <span className="snav-icon">{item.icon}</span>
              <span className="snav-labels">
                <span className="snav-label">{item.label}</span>
                <span className="snav-sub">{item.sub}</span>
              </span>
              {activeSection === item.id && <span className="snav-active-bar" aria-hidden="true" />}
            </button>
          ))}
        </nav>

        {/* Rodapé do Menu */}
        <div className="snav-footer">
          <button type="button" className="snav-close" onClick={onClose} title="Fechar menu lateral">
            ◀ FECHAR
          </button>
          <span className="snav-version">v4.0 TÁTICO</span>
        </div>
      </aside>
    </>
  );
}

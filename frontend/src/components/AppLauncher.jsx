/**
 * Widget "Abrir Programas": grade de botões para abrir apps com um clique.
 * A lista de apps disponíveis é carregada do backend (atalhos.json).
 */
const FEATURED_APPS = [
  { key: "vs code", label: "VS Code", icon: "💻" },
  { key: "bloco de notas", label: "Bloco de Notas", icon: "📝" },
  { key: "explorador de arquivos", label: "Explorador", icon: "📁" },
  { key: "configurações", label: "Configurações", icon: "⚙️" },
  { key: "calculadora", label: "Calculadora", icon: "🧮" },
  { key: "chrome", label: "Chrome", icon: "🌐" },
  { key: "youtube", label: "YouTube", icon: "▶️" },
  { key: "github", label: "GitHub", icon: "🐙" },
  { key: "whatsapp", label: "WhatsApp", icon: "💬" },
  { key: "spotify", label: "Spotify", icon: "🎵" },
];

export default function AppLauncher({ onSend }) {
  return (
    <section className="hud-panel p-4" aria-label="Abrir programas">
      <h2 className="mb-3 font-display text-sm tracking-wide text-arc-200">Abrir Programas</h2>
      <div className="grid grid-cols-2 gap-2">
        {FEATURED_APPS.map(({ key, label, icon }) => (
          <button
            key={key}
            type="button"
            onClick={() => onSend(`abre ${key}`)}
            title={`Abrir ${label}`}
            className="flex items-center gap-2 rounded border border-arc-700 px-3 py-2 text-sm text-arc-200 transition hover:border-arc-400 hover:bg-arc-500/20 focus:outline-none focus-visible:ring-1 focus-visible:ring-arc-300"
          >
            <span className="text-base">{icon}</span>
            <span className="truncate">{label}</span>
          </button>
        ))}
      </div>
      <p className="mt-3 text-xs text-arc-300/50">
        Ou diga: <span className="text-arc-300">"abre o VS Code"</span>
      </p>
    </section>
  );
}

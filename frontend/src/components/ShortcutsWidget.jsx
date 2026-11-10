import { useState, useEffect } from "react";

/**
 * Widget "Atalhos Rápidos": mostra os atalhos personalizados do usuário como botões clicáveis.
 */
export default function ShortcutsWidget({ api, onSend }) {
  const [shortcuts, setShortcuts] = useState({});

  useEffect(() => {
    api("/api/shortcuts")
      .then((data) => setShortcuts(data.shortcuts ?? {}))
      .catch(() => {});
  }, [api]);

  const names = Object.keys(shortcuts);

  if (names.length === 0) {
    return (
      <section className="hud-panel p-4" aria-label="Atalhos rápidos">
        <h2 className="mb-2 font-display text-sm tracking-wide text-arc-200">Atalhos Rápidos</h2>
        <p className="text-xs text-arc-300/50">
          Nenhum atalho criado ainda. Use as Configurações para adicionar.
        </p>
      </section>
    );
  }

  return (
    <section className="hud-panel p-4" aria-label="Atalhos rápidos">
      <h2 className="mb-3 font-display text-sm tracking-wide text-arc-200">Atalhos Rápidos</h2>
      <div className="flex flex-col gap-2">
        {names.map((name) => (
          <button
            key={name}
            type="button"
            onClick={() => onSend(`abre ${name}`)}
            className="flex items-center gap-2 rounded border border-arc-600 px-3 py-2 text-left text-sm text-arc-200 transition hover:bg-arc-500/20"
          >
            <span className="text-arc-400">⚡</span>
            <span className="capitalize">{name}</span>
          </button>
        ))}
      </div>
    </section>
  );
}

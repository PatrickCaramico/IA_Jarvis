import { useEffect, useMemo, useRef, useState } from "react";
import { GODS_EYE_CATEGORIES } from "./layers.config.js";
import { soundManager } from "../utils/soundEffects.js";

function Globe() {
  const stars = useMemo(
    () => Array.from({ length: 42 }, (_, index) => ({
      id: index,
      left: `${(index * 47) % 100}%`,
      top: `${(index * 71) % 100}%`,
      "--size": `${1 + (index % 3)}px`,
      "--delay": `${(index % 8) * 0.4}s`,
    })),
    [],
  );

  return (
    <div className="ge-scene" aria-label="Globo holográfico do Olho de Deus" role="img">
      <div className="ge-stars" aria-hidden="true">
        {stars.map((star) => <i key={star.id} style={star} />)}
      </div>
      <div className="ge-globe">
        <div className="ge-globe-grid ge-globe-grid-latitude" />
        <div className="ge-globe-grid ge-globe-grid-longitude" />
        <div className="ge-continent ge-continent-a" />
        <div className="ge-continent ge-continent-b" />
        <div className="ge-continent ge-continent-c" />
        <span className="ge-event ge-event-a" />
        <span className="ge-event ge-event-b" />
        <span className="ge-event ge-event-c" />
      </div>
      <div className="ge-orbit ge-orbit-one" />
      <div className="ge-orbit ge-orbit-two" />
      <div className="ge-atmosphere" />
    </div>
  );
}

function SearchBar({ onClose }) {
  const inputRef = useRef(null);

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === "/") {
        event.preventDefault();
        inputRef.current?.focus();
      }
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div className="ge-search">
      <span aria-hidden="true">⌕</span>
      <input ref={inputRef} placeholder="Buscar cidade, lugar ou CEP" aria-label="Buscar cidade, lugar ou CEP" />
      <kbd>/</kbd>
      <button type="button" onClick={onClose} title="Sair do Olho de Deus (Esc)">ESC</button>
    </div>
  );
}

export default function GodsEye({ onClose }) {
  const [selectedCategory, setSelectedCategory] = useState("events");
  const [activeLayers, setActiveLayers] = useState({});
  const [muted, setMuted] = useState(() => soundManager.config().silent);
  const category = GODS_EYE_CATEGORIES.find((item) => item.id === selectedCategory) || GODS_EYE_CATEGORIES[0];
  const activeCount = Object.values(activeLayers).filter(Boolean).length;

  const toggleCategory = (id) => {
    soundManager.playClick();
    setSelectedCategory(id);
  };

  const toggleLayer = (id) => {
    soundManager.playClick();
    setActiveLayers((current) => ({ ...current, [id]: !current[id] }));
  };

  const close = () => {
    soundManager.playIdle();
    onClose();
  };

  return (
    <section className="ge-root" aria-label="Olho de Deus" onClick={(event) => event.stopPropagation()}>
      <SearchBar onClose={close} />
      <div className="ge-status">
        <span className="ge-live-dot" /> OLHO DE DEUS <small>FASE 1 · AGUARDANDO DADOS</small>
      </div>
      <Globe />

      <aside className="ge-layer-panel" aria-label={`Camadas de ${category.label}`}>
        <header>
          <div>
            <strong>{category.label}</strong>
            <small>{category.layers.filter((layer) => activeLayers[layer.id]).length} de {category.layers.length} no mapa</small>
          </div>
          <button type="button" onClick={close} aria-label="Fechar painel de camadas">✕</button>
        </header>
        <div className="ge-layer-list">
          {category.layers.map((layer) => (
            <label key={layer.id} className={`ge-layer-row${activeLayers[layer.id] ? " is-active" : ""}`}>
              <span className="ge-layer-icon" style={{ color: layer.color }}>◉</span>
              <span className="ge-layer-name">{layer.label}</span>
              <span className="ge-layer-value">{layer.value}</span>
              <input type="checkbox" checked={Boolean(activeLayers[layer.id])} onChange={() => toggleLayer(layer.id)} />
              <span className="ge-toggle" aria-hidden="true" />
            </label>
          ))}
        </div>
      </aside>

      <nav className="ge-dock" aria-label="Categorias de camadas">
        {GODS_EYE_CATEGORIES.map((item) => {
          const count = item.layers.filter((layer) => activeLayers[layer.id]).length;
          return (
            <button
              type="button"
              key={item.id}
              className={selectedCategory === item.id ? "is-selected" : ""}
              onClick={() => toggleCategory(item.id)}
              title={item.label}
              aria-label={item.label}
              aria-pressed={selectedCategory === item.id}
            >
              <span>{item.icon}</span>
              <small>{item.label}</small>
              {count > 0 && <b>{count}</b>}
            </button>
          );
        })}
      </nav>

      <footer className="ge-stats">
        <span><b>{activeCount}</b> camadas ativas</span>
        <span><b>—</b> eventos monitorados</span>
        <button
          type="button"
          onClick={() => setMuted((current) => {
            const next = !current;
            soundManager.configure({ silent: next });
            return next;
          })}
          aria-pressed={muted}
        >
          {muted ? "🔇 SOM MUDO" : "🔊 SOM ATIVO"}
        </button>
      </footer>
    </section>
  );
}

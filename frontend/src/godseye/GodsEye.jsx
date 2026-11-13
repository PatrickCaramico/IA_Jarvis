import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { GODS_EYE_CATEGORIES } from "./layers.config.js";
import { DEFAULT_CENTER, geocode, wazeEmbedUrl, wazeNavigateUrl } from "./traffic.js";
import { soundManager } from "../utils/soundEffects.js";
import useEscape from "../hooks/useEscape.js";

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

function SearchBar({ onClose, onSearch, busy }) {
  const inputRef = useRef(null);
  const [text, setText] = useState("");

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === "/") {
        event.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <form className="ge-search" onSubmit={(e) => { e.preventDefault(); if (text.trim()) onSearch(text.trim()); }}>
      <span aria-hidden="true">{busy ? "…" : "⌕"}</span>
      <input ref={inputRef} value={text} onChange={(e) => setText(e.target.value)} placeholder="Buscar cidade, endereço, bairro ou CEP" aria-label="Buscar cidade, endereço, bairro ou CEP" />
      <kbd>/</kbd>
      <button type="button" onClick={onClose} title="Sair do Olho de Deus (Esc)">ESC</button>
    </form>
  );
}

function TrafficMap({ center, zoom }) {
  return (
    <div className="ge-traffic" aria-label={`Trânsito ao vivo: ${center.label}`}>
      <iframe
        key={`${center.lat},${center.lon},${zoom}`}
        title="Trânsito ao vivo (Waze)"
        src={wazeEmbedUrl(center, zoom)}
        allow="geolocation"
        loading="eager"
        referrerPolicy="no-referrer-when-downgrade"
      />
    </div>
  );
}

function TrafficPanel({ center, home, places, zoom, setZoom, goTo, locateMe, message, onHide }) {
  return (
    <aside className="ge-layer-panel ge-traffic-panel" aria-label="Trânsito ao vivo">
      <header>
        <div>
          <strong>🚦 TRÂNSITO AO VIVO</strong>
          <small>{center.label} · dados do Waze</small>
        </div>
        <button type="button" onClick={onHide} aria-label="Esconder o painel">—</button>
      </header>
      <div className="ge-traffic-actions">
        {home && <button type="button" onClick={() => goTo(home)}>🏠 MINHA CIDADE</button>}
        <button type="button" onClick={locateMe}>📍 ONDE ESTOU</button>
        <button type="button" onClick={() => setZoom((z) => Math.min(17, z + 1))} aria-label="Aproximar">＋</button>
        <button type="button" onClick={() => setZoom((z) => Math.max(5, z - 1))} aria-label="Afastar">－</button>
      </div>
      {places.length > 0 && (
        <div className="ge-traffic-places">
          <small>LUGARES SALVOS</small>
          {places.map(([name, address]) => (
            <button type="button" key={name} onClick={() => goTo(address, name)} title={address}>▸ {name}</button>
          ))}
        </div>
      )}
      <a className="ge-traffic-go" href={wazeNavigateUrl(center)} target="_blank" rel="noreferrer">🧭 IR ATÉ AQUI NO WAZE</a>
      {message && <p className="ge-traffic-msg" role="status">{message}</p>}
      <p className="ge-traffic-note">Zoom {zoom}. Arraste o mapa para ver outras regiões; cores = lentidão, ícones = alertas dos motoristas.</p>
    </aside>
  );
}

export default function GodsEye({ onClose, api = null, initialCategory = "traffic" }) {
  const [selectedCategory, setSelectedCategory] = useState(initialCategory);
  const [center, setCenter] = useState(DEFAULT_CENTER);
  const [home, setHome] = useState(null);
  const [zoom, setZoom] = useState(13);
  const [places, setPlaces] = useState([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [panelOpen, setPanelOpen] = useState(true);
  const [activeLayers, setActiveLayers] = useState({});
  const [muted, setMuted] = useState(() => soundManager.config().silent);
  const category = GODS_EYE_CATEGORIES.find((item) => item.id === selectedCategory) || GODS_EYE_CATEGORIES[0];
  const activeCount = Object.values(activeLayers).filter(Boolean).length;

  const isTraffic = Boolean(category.live);

  // centro inicial: a cidade do clima (a mesma do JARVIS); lugares salvos do agente de rotas
  useEffect(() => {
    if (!api) return;
    api("/api/weather").then((w) => {
      if (w?.coords?.lat != null) {
        const c = { lat: w.coords.lat, lon: w.coords.lon, label: w.place || "Minha cidade" };
        setHome(c);
        setCenter(c);
      }
    }).catch(() => {});
    api("/api/agents").then((d) => setPlaces(Object.entries(d?.places || {}).slice(0, 8))).catch(() => {});
  }, [api]);

  const goTo = useCallback(async (target, name = "") => {
    if (typeof target === "object") {
      setCenter(target);
      setMessage("");
      return;
    }
    setBusy(true);
    setMessage("");
    const hit = await geocode(target);
    setBusy(false);
    if (!hit) {
      setMessage(`Não encontrei "${target}".`);
      return;
    }
    soundManager.playClick();
    setSelectedCategory("traffic");
    setCenter(name ? { ...hit, label: name } : hit);
    setZoom((z) => Math.max(z, 14));
  }, []);

  const locateMe = () => {
    if (!navigator.geolocation) {
      setMessage("Este aparelho não informa a localização.");
      return;
    }
    setMessage("Procurando onde você está…");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setCenter({ lat: pos.coords.latitude, lon: pos.coords.longitude, label: "Onde estou" });
        setZoom(15);
        setMessage("");
      },
      () => setMessage("Não consegui a localização (permita o acesso no navegador)."),
      { enableHighAccuracy: true, timeout: 10_000 },
    );
  };

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
  useEscape(close); // V7.4: Esc fecha mesmo com um botão focado

  return (
    <section className="ge-root" aria-label="Olho de Deus" onClick={(event) => event.stopPropagation()}>
      <SearchBar onClose={close} onSearch={(q) => goTo(q)} busy={busy} />
      <div className="ge-status">
        <span className="ge-live-dot" /> OLHO DE DEUS <small>{isTraffic ? `TRÂNSITO AO VIVO · ${center.label.toUpperCase()}` : "FASE 1 · AGUARDANDO DADOS"}</small>
      </div>
      {isTraffic ? <TrafficMap center={center} zoom={zoom} /> : <Globe />}

      {isTraffic && panelOpen && (
        <TrafficPanel center={center} home={home} places={places} zoom={zoom} setZoom={setZoom} goTo={goTo} locateMe={locateMe} message={message} onHide={() => setPanelOpen(false)} />
      )}
      {isTraffic && !panelOpen && (
        <button type="button" className="ge-traffic-show" onClick={() => setPanelOpen(true)}>🚦 PAINEL</button>
      )}
      {!isTraffic && <aside className="ge-layer-panel" aria-label={`Camadas de ${category.label}`}>
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
      </aside>}

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
        {isTraffic ? (
          <span><b>●</b> trânsito ao vivo</span>
        ) : (
          <>
            <span><b>{activeCount}</b> camadas ativas</span>
            <span><b>—</b> eventos monitorados</span>
          </>
        )}
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

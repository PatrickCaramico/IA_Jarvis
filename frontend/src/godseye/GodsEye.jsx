import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Globe3D from "./Globe3D.jsx";
import { ALERTS, LAYERS, fmtTime, layerUrl, layerValue, pickCard, summaryText } from "./world.js";
import { DEFAULT_CENTER, geocode, wazeEmbedUrl, wazeNavigateUrl } from "./traffic.js";
import { soundManager } from "../utils/soundEffects.js";
import useEscape from "../hooks/useEscape.js";

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

function isLite() {
  try {
    return window.matchMedia("(max-width: 760px)").matches || (navigator.deviceMemory || 8) <= 2;
  } catch {
    return false;
  }
}

function IssPasses({ data }) {
  const list = data?.passagens || [];
  if (!data) return null;
  return (
    <div className="ge-iss-passes">
      <small>PASSAGENS VISÍVEIS NO SEU CÉU</small>
      {list.length === 0 ? <p>Nenhuma nos próximos 3 dias.</p> : list.slice(0, 4).map((p) => (
        <p key={p.inicio}>
          <b>{p.dia} · {p.hora}</b> {p.de} → {p.para} · {p.minutos} min · {p.max_el}°
          {p.nuvens != null && <span className={p.nuvens < 50 ? "is-clear" : "is-cloudy"}> {p.nuvens < 50 ? "☀ céu limpo" : `☁ ${Math.round(p.nuvens)}% nuvens`}</span>}
        </p>
      ))}
    </div>
  );
}

function RainForecast({ data }) {
  const slots = (data?.previsao?.prox || []).slice(0, 12);
  if (!slots.length) return null;
  const max = Math.max(1.25, ...slots.map((s) => s.mm));
  return (
    <div className="ge-rain-bars" aria-label="Chuva nas próximas 3 horas">
      {slots.map((s) => (
        <span key={s.t} title={`${s.hora}: ${String(s.mm).replace(".", ",")} mm`}>
          <i style={{ height: `${Math.max(4, (s.mm / max) * 100)}%` }} className={s.mm >= 1.25 ? "is-strong" : s.mm >= 0.2 ? "is-rain" : ""} />
          <small>{s.hora.endsWith(":00") ? s.hora.slice(0, 2) + "h" : ""}</small>
        </span>
      ))}
    </div>
  );
}

export default function GodsEye({ onClose, api = null, initialCategory = "traffic", initialLayer = null }) {
  const lite = useMemo(isLite, []);
  const [mode, setMode] = useState(initialLayer ? "globe" : initialCategory === "globe" ? "globe" : "traffic");
  const [center, setCenter] = useState(DEFAULT_CENTER);
  const [home, setHome] = useState(null);
  const [focus, setFocus] = useState(null); // o lugar de onde vêm os voos e a chuva (casa ou o que você buscou)
  const [zoom, setZoom] = useState(13);
  const [places, setPlaces] = useState([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [panelOpen, setPanelOpen] = useState(!lite);
  const [layersOn, setLayersOn] = useState(() => Object.fromEntries(LAYERS.map((l) => [l.id, initialLayer ? l.id === initialLayer || l.id === "chuva" : true])));
  const [data, setData] = useState({});
  const [errors, setErrors] = useState({});
  const [base, setBase] = useState("dark");
  const [pick, setPick] = useState(null);
  const [fly, setFly] = useState(null);
  const [globeOk, setGlobeOk] = useState(true);
  const [alerts, setAlerts] = useState(null);
  const [alertMsg, setAlertMsg] = useState("");
  const [muted, setMuted] = useState(() => soundManager.config().silent);
  const [homeTried, setHomeTried] = useState(!api);
  const isTraffic = mode === "traffic";

  // centro inicial: a cidade do clima (a mesma do JARVIS); lugares salvos do agente de rotas
  useEffect(() => {
    if (!api) return;
    api("/api/weather").then((w) => {
      if (w?.coords?.lat != null) {
        const c = { lat: w.coords.lat, lon: w.coords.lon, label: w.place || "Minha cidade" };
        setHome(c);
        setCenter(c);
      }
    }).catch(() => {}).finally(() => setHomeTried(true));
    api("/api/agents").then((d) => setPlaces(Object.entries(d?.places || {}).slice(0, 8))).catch(() => {});
    api("/api/world/alerts").then((d) => setAlerts(d)).catch(() => {});
  }, [api]);

  const where = focus || home || DEFAULT_CENTER;

  // voa até a cidade quando o globo abre (e quando você busca outro lugar)
  useEffect(() => {
    if (mode === "globe" && homeTried) setFly({ lat: where.lat, lon: where.lon, zoom: initialLayer === "terremotos" || initialLayer === "iss" ? 2.4 : 5.2 });
  }, [mode, homeTried, where.lat, where.lon, initialLayer]);

  // camadas: cada uma no seu ritmo, só enquanto está ligada e o globo aberto
  const load = useCallback(async (id, opts = {}) => {
    if (!api) return;
    try {
      const d = await api(layerUrl(id, where, { lite, ...opts }), { timeout: 30_000 });
      setData((cur) => ({ ...cur, [id]: opts.light && cur[id] ? { ...cur[id], agora: d.agora, trilha: d.trilha } : d }));
      setErrors((cur) => ({ ...cur, [id]: "" }));
    } catch (err) {
      setErrors((cur) => ({ ...cur, [id]: err.message || "Fonte fora do ar." }));
    }
  }, [api, where, lite]);

  useEffect(() => {
    if (mode !== "globe" || !homeTried) return undefined;
    const timers = [];
    for (const l of LAYERS) {
      if (!layersOn[l.id]) continue;
      load(l.id);
      if (l.id === "iss") {
        timers.push(setInterval(() => load("iss", { light: true }), l.refresh));
        timers.push(setInterval(() => load("iss"), 600_000));
      } else {
        timers.push(setInterval(() => load(l.id), lite ? l.refresh * 2 : l.refresh));
      }
    }
    return () => timers.forEach(clearInterval);
  }, [mode, homeTried, layersOn, load, lite]);

  const goTo = useCallback(async (target, name = "") => {
    if (typeof target === "object") {
      setCenter(target);
      setFocus(target);
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
    const place = name ? { ...hit, label: name } : hit;
    setCenter(place);
    setFocus(place);
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
        const here = { lat: pos.coords.latitude, lon: pos.coords.longitude, label: "Onde estou" };
        setCenter(here);
        setFocus(here);
        setZoom(15);
        setMessage("");
      },
      () => setMessage("Não consegui a localização (permita o acesso no navegador)."),
      { enableHighAccuracy: true, timeout: 10_000 },
    );
  };

  const toggleLayer = (id) => {
    soundManager.playClick();
    setLayersOn((cur) => ({ ...cur, [id]: !cur[id] }));
  };

  const toggleAlert = async (id) => {
    const next = !alerts?.ligados?.[id];
    setAlertMsg("");
    try {
      const d = await api("/api/world/alerts", { method: "POST", body: JSON.stringify({ [id]: next }) });
      setAlerts((cur) => ({ ...cur, ligados: d.ligados }));
    } catch (err) {
      setAlertMsg(err.message);
    }
  };

  const close = () => {
    soundManager.playIdle();
    onClose();
  };
  useEscape(close); // V7.4: Esc fecha mesmo com um botão focado

  const summary = summaryText(data);
  const card = pickCard(pick);
  const events = (data.terremotos?.total || 0) + (data.queimadas?.total || 0) + (data.voos?.no_ar || 0);
  const activeCount = Object.values(layersOn).filter(Boolean).length;
  const onReady = useCallback((ok) => setGlobeOk(ok), []);

  return (
    <section className={`ge-root${isTraffic ? "" : " is-globe"}`} aria-label="Olho de Deus" onClick={(event) => event.stopPropagation()}>
      <SearchBar onClose={close} onSearch={(q) => goTo(q)} busy={busy} />
      <div className="ge-status">
        <span className="ge-live-dot" /> OLHO DE DEUS <small>{isTraffic ? `TRÂNSITO AO VIVO · ${center.label.toUpperCase()}` : `AO VIVO · ${(where.label || "MINHA CIDADE").toUpperCase()}`}</small>
      </div>
      {!isTraffic && summary && <p className="ge-summary" role="status" aria-live="polite">{summary}</p>}

      {isTraffic ? <TrafficMap center={center} zoom={zoom} /> : (
        <Globe3D home={home} layersOn={layersOn} data={data} base={base} lite={lite} flyTo={fly} onPick={setPick} onReady={onReady} />
      )}
      {!isTraffic && !globeOk && <p className="ge-globe-fail" role="alert">Este aparelho não conseguiu abrir o globo 3D (WebGL desligado). As camadas continuam no painel.</p>}

      {isTraffic && panelOpen && (
        <TrafficPanel center={center} home={home} places={places} zoom={zoom} setZoom={setZoom} goTo={goTo} locateMe={locateMe} message={message} onHide={() => setPanelOpen(false)} />
      )}
      {!isTraffic && panelOpen && (
        <aside className="ge-layer-panel ge-world-panel" aria-label="Camadas do globo">
          <header>
            <div>
              <strong>🌐 CAMADAS AO VIVO</strong>
              <small>{activeCount} de {LAYERS.length} no globo · dados públicos</small>
            </div>
            <button type="button" onClick={() => setPanelOpen(false)} aria-label="Esconder o painel">—</button>
          </header>
          <div className="ge-traffic-actions">
            {home && <button type="button" onClick={() => { setFocus(null); setFly({ lat: home.lat, lon: home.lon, zoom: 5.2 }); }}>🏠 MINHA CIDADE</button>}
            <button type="button" onClick={locateMe}>📍 ONDE ESTOU</button>
            <button type="button" onClick={() => setBase((b) => (b === "dark" ? "sat" : "dark"))} aria-pressed={base === "sat"}>{base === "sat" ? "🌑 ESCURO" : "🛰 SATÉLITE"}</button>
            <button type="button" onClick={() => setFly({ lat: where.lat, lon: where.lon, zoom: 1.4 })}>🌍 MUNDO</button>
          </div>
          <div className="ge-layer-list">
            {LAYERS.map((layer) => (
              <div key={layer.id}>
                <label className={`ge-layer-row${layersOn[layer.id] ? " is-active" : ""}`}>
                  <span className="ge-layer-icon" style={{ color: layer.color }}>{layer.icon}</span>
                  <span className="ge-layer-name">
                    {layer.label}
                    {layersOn[layer.id] && (errors[layer.id]
                      ? <em className="ge-layer-err">fonte fora do ar agora</em>
                      : data[layer.id]?.atualizado && <em>atualizado {fmtTime(data[layer.id].atualizado).slice(-5)} · {data[layer.id].fonte}</em>)}
                  </span>
                  <span className="ge-layer-value">{layersOn[layer.id] ? layerValue(layer.id, data[layer.id]) : ""}</span>
                  <input type="checkbox" checked={Boolean(layersOn[layer.id])} onChange={() => toggleLayer(layer.id)} aria-label={layer.label} />
                  <span className="ge-toggle" aria-hidden="true" />
                </label>
                {layer.id === "chuva" && layersOn.chuva && <RainForecast data={data.chuva} />}
                {layer.id === "iss" && layersOn.iss && <IssPasses data={data.iss} />}
              </div>
            ))}
          </div>
          {message && <p className="ge-traffic-msg" role="status">{message}</p>}
          {alerts && (
            <div className="ge-alerts">
              <small>AVISOS AUTOMÁTICOS {alerts.cloud ? "(saem do PC)" : "(voz no PC e no celular)"}</small>
              {ALERTS.map((a) => (
                <label key={a.id} className={`ge-layer-row${alerts.ligados?.[a.id] ? " is-active" : ""}`}>
                  <span className="ge-layer-name">{a.label}</span>
                  <input type="checkbox" checked={Boolean(alerts.ligados?.[a.id])} onChange={() => toggleAlert(a.id)} disabled={Boolean(alerts.cloud)} aria-label={`Aviso: ${a.label}`} />
                  <span className="ge-toggle" aria-hidden="true" />
                </label>
              ))}
              {alertMsg && <p className="ge-traffic-msg" role="alert">{alertMsg}</p>}
            </div>
          )}
        </aside>
      )}
      {!panelOpen && (
        <button type="button" className="ge-traffic-show" onClick={() => setPanelOpen(true)}>{isTraffic ? "🚦 PAINEL" : "🌐 CAMADAS"}</button>
      )}

      {!isTraffic && card && (
        <aside className="ge-pick" aria-label={card.title}>
          <header><span>{card.icon}</span><strong>{card.title}</strong><button type="button" onClick={() => setPick(null)} aria-label="Fechar cartão">✕</button></header>
          {card.lines.filter(Boolean).map((line) => <p key={line}>{line}</p>)}
        </aside>
      )}

      <nav className="ge-dock" aria-label="Modos do Olho de Deus">
        {[{ id: "traffic", icon: "🚦", label: "Trânsito" }, { id: "globe", icon: "🌐", label: "Globo" }].map((item) => (
          <button
            type="button"
            key={item.id}
            className={mode === item.id ? "is-selected" : ""}
            onClick={() => { soundManager.playClick(); setPick(null); setMode(item.id); }}
            title={item.label}
            aria-label={item.label}
            aria-pressed={mode === item.id}
          >
            <span>{item.icon}</span>
            <small>{item.label}</small>
          </button>
        ))}
      </nav>

      <footer className="ge-stats">
        {isTraffic ? (
          <span><b>●</b> trânsito ao vivo</span>
        ) : (
          <>
            <span><b>{activeCount}</b> camadas</span>
            <span><b>{events.toLocaleString("pt-BR")}</b> eventos no globo</span>
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

import { useState } from "react";
import { createPortal } from "react-dom";
import useEscape from "../hooks/useEscape.js";
import ReactorOrb from "./ReactorOrb.jsx";
import { COLORS, DEFAULTS, SHAPES, load, normalize, save } from "../utils/reactor.js";

// V9.4.2: 🎨 PERSONALIZAR O REATOR (botão embaixo do orbe da central). Forma, cor, contraste, brilho, velocidade e
// quantidade de fios, com a prévia ao vivo. Vale na hora para a central deste aparelho.
const STATES = [["idle", "Em espera"], ["listening", "Ouvindo"], ["processing", "Pensando"], ["speaking", "Falando"]];

function Slider({ label, value, min, max, step = 5, suffix = "%", hint, onChange }) {
  return (
    <label className="rxs-slider">
      <span>{label} <b>{value}{suffix}</b></span>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))} />
      {hint && <small>{hint}</small>}
    </label>
  );
}

export default function ReactorStudio({ onClose }) {
  const [cfg, setCfg] = useState(load);
  const [preview, setPreview] = useState("idle");
  useEscape(onClose);
  const set = (patch) => setCfg((c) => save({ ...c, ...patch })); // salva e a central já muda
  const shape = SHAPES.find((s) => s.id === cfg.shape);

  return createPortal(
    <div className="rxs-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <section className="rxs" role="dialog" aria-modal="true" aria-label="Personalizar o reator">
        <header className="rxs-head">
          <h2>🎨 PERSONALIZAR O REATOR</h2>
          <button type="button" className="sp-close" onClick={onClose} aria-label="Fechar">✕</button>
        </header>
        <div className="rxs-body">
          <div className="rxs-preview">
            <div className="rxs-stage"><ReactorOrb cfg={normalize(cfg)} state={preview} /></div>
            <div className="rxs-states" role="group" aria-label="Ver no estado">
              {STATES.map(([id, label]) => (
                <button key={id} type="button" className={preview === id ? "is-on" : ""} onClick={() => setPreview(id)}>{label}</button>
              ))}
            </div>
          </div>
          <div className="rxs-controls">
            <h3>FORMA</h3>
            <div className="rxs-shapes">
              {SHAPES.map((s) => (
                <button key={s.id} type="button" className={cfg.shape === s.id ? "is-on" : ""} onClick={() => set({ shape: s.id })} title={s.hint}>
                  <b>{s.label}</b>
                  <small className={`is-${s.weight}`}>{s.weight}</small>
                </button>
              ))}
            </div>
            {shape && <p className="rxs-note">{shape.hint}.</p>}
            <h3>COR</h3>
            <div className="rxs-colors">
              {COLORS.map(([hex, name]) => (
                <button key={hex} type="button" className={cfg.color === hex ? "is-on" : ""} style={{ "--c": hex }} onClick={() => set({ color: hex })}
                  title={name} aria-label={name} />
              ))}
              <label className="rxs-picker" title="Outra cor">
                <input type="color" value={cfg.color} onChange={(e) => set({ color: e.target.value })} aria-label="Escolher outra cor" />
                ＋
              </label>
            </div>
            <Slider label="Contraste" value={cfg.contrast} min={50} max={160} onChange={(v) => set({ contrast: v })} />
            <Slider label="Brilho" value={cfg.glow} min={0} max={200} onChange={(v) => set({ glow: v })}
              hint="Em 0, sem o brilho em volta: bem mais leve para o aparelho." />
            <Slider label="Velocidade do giro" value={cfg.speed} min={25} max={250} onChange={(v) => set({ speed: v })} />
            {cfg.shape === "fios" && (
              <Slider label="Fios" value={cfg.wires} min={6} max={30} step={1} suffix="" onChange={(v) => set({ wires: v })}
                hint="Menos fios = mais leve." />
            )}
            <div className="rxs-actions">
              <button type="button" onClick={() => setCfg(save(DEFAULTS))}>↺ VOLTAR AO PADRÃO</button>
              <button type="button" className="is-main" onClick={onClose}>✓ PRONTO</button>
            </div>
            <p className="rxs-note">Fica salvo neste aparelho. No celular dá para escolher uma forma mais leve.</p>
          </div>
        </div>
      </section>
    </div>,
    document.body,
  );
}

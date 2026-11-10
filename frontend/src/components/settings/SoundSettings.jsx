import { useEffect, useState } from "react";
import { soundManager, QUIET_START, QUIET_END } from "../../utils/soundEffects.js";
import { Note, Section, SelectRow } from "./SettingsControls.jsx";

const MODES = [["all", "Todos os sons"], ["important", "Só o que importa (erro e alerta)"], ["off", "Desligado"]];
const PREVIEWS = [["listening", "Ouvindo"], ["success", "Sucesso"], ["error", "Erro"], ["idle", "Repouso"]];

// Seção "Sons do JARVIS" (V4.2.2) na aba Mídia & Foco: volume, modo e prévia dos sons por estado.
export default function SoundSettings({ prefs, onPatch }) {
  const [volume, setVolume] = useState(prefs.sfx_volume ?? 60);
  const mode = prefs.sfx_mode || "all";

  useEffect(() => setVolume(prefs.sfx_volume ?? 60), [prefs.sfx_volume]);

  const preview = (name) => soundManager.preview(name, volume);

  return (
    <Section title="SONS DO JARVIS">
      <div className="flex items-center gap-3 py-1.5">
        <span className="text-xs font-['Orbitron'] text-cyan-200">VOLUME</span>
        <input
          type="range"
          min="0"
          max="100"
          step="5"
          value={volume}
          aria-label="Volume dos sons"
          onChange={(e) => setVolume(Number(e.target.value))}
          onPointerUp={() => onPatch({ sfx_volume: volume }, { quiet: true })}
          onKeyUp={() => onPatch({ sfx_volume: volume }, { quiet: true })}
          className="flex-1 accent-cyan-400"
        />
        <span className="w-10 text-right font-['Orbitron'] text-sm font-bold text-cyan-200">{volume}</span>
      </div>
      <SelectRow label="MODO" value={mode} onChange={(v) => onPatch({ sfx_mode: v })} options={MODES} />
      <div className="flex flex-wrap gap-2 pt-1">
        {PREVIEWS.map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => preview(key)}
            className="rounded border border-cyan-500/30 bg-black/30 px-3 py-1 text-xs text-cyan-200 hover:bg-cyan-500/20"
          >
            ▶ {label}
          </button>
        ))}
      </div>
      <Note>
        Das {QUIET_START}h às {QUIET_END}h só tocam os sons importantes, com metade do volume. O modo silencioso cala tudo.
      </Note>
    </Section>
  );
}

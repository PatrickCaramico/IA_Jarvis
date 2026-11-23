import { useState } from "react";
import { Note, Section, Toggle } from "./SettingsControls.jsx";
import { VOICE_SAMPLE, VOICE_STYLES as STYLES } from "../../utils/voiceStyles.js";

// V6.1: estilo da voz do JARVIS (aba Mídia & Foco). Tocar num estilo salva e já fala um exemplo.
// V8.13: a lista mora em utils/voiceStyles.js (o botão VOZ do topo usa a mesma).
export default function VoiceSettings({ prefs, onPatch, api }) {
  const current = prefs.voice_style || "natural";
  const [busy, setBusy] = useState("");

  const choose = async (key) => {
    setBusy(key);
    try {
      // salva primeiro (no PC) e só depois fala o exemplo, já com a voz nova
      await api("/api/prefs", { method: "PATCH", body: JSON.stringify({ voice_style: key }) });
      onPatch({ voice_style: key });
      await api("/api/speak", { method: "POST", body: JSON.stringify({ text: VOICE_SAMPLE }) });
    } catch {
      /* a mensagem de erro aparece no salvar */
    } finally {
      setTimeout(() => setBusy(""), 1500);
    }
  };

  return (
    <Section title="VOZ DO JARVIS">
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {STYLES.map(([key, label, desc]) => {
          const on = current === key;
          return (
            <button
              key={key}
              type="button"
              onClick={() => choose(key)}
              aria-pressed={on}
              className={`rounded border p-2.5 text-left transition ${
                on ? "border-cyan-300 bg-cyan-500/20 shadow-[0_0_10px_rgba(31,194,245,0.3)]" : "border-cyan-500/20 bg-black/30 hover:border-cyan-400"
              }`}
            >
              <strong className="block font-['Orbitron'] text-xs tracking-wider text-cyan-100">
                {on ? "● " : ""}{label}{busy === key ? " · falando…" : ""}
              </strong>
              <span className="text-[11px] text-cyan-200/70">{desc}</span>
            </button>
          );
        })}
      </div>
      <Note>Toque num estilo para ouvir e usar. As falas curtas agora saem inteiras, sem picotar.</Note>
      <Toggle
        checked={prefs.voice_listener_enabled !== false}
        onChange={async (on) => {
          onPatch({ voice_listener_enabled: on });
          try {
            await api("/api/prefs", { method: "PATCH", body: JSON.stringify({ voice_listener_enabled: on }) });
          } catch {
            /* a mensagem de erro aparece no salvar */
          }
        }}
        label="Ouvir “Jarvis” com o navegador fechado"
        hint="Ouvido offline no PC (nada sai do computador). Fica quieto quando a central está aberta numa aba do PC."
      />
    </Section>
  );
}

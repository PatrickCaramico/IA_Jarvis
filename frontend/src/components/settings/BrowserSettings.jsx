import { useEffect, useState } from "react";
import { Note, Section } from "./SettingsControls.jsx";

// V6.5.11: em qual navegador o JARVIS abre os sites ("abra o YouTube").
export default function BrowserSettings({ api }) {
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    api("/api/browser").then(setData).catch(() => setData({ browsers: [], mode: "ask" }));
  }, [api]);

  const choose = async (mode) => {
    setData((d) => ({ ...d, mode }));
    try {
      await api("/api/prefs", { method: "PATCH", body: JSON.stringify({ site_browser: mode }) });
      setStatus("✓ Salvo.");
    } catch (err) {
      setStatus(`Erro: ${err.message}`);
    }
    setTimeout(() => setStatus(""), 2500);
  };

  if (!data) return null;
  const options = [
    ["ask", "Perguntar sempre", "Mostra a lista e você escolhe (falando ou tocando)."],
    ["default", "Padrão do Windows", "Sem perguntar."],
    ...data.browsers.map((b) => [b.id, b.name, "Sempre este, sem perguntar."]),
  ];
  return (
    <Section title="NAVEGADOR DOS SITES">
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {options.map(([id, label, desc]) => {
          const on = data.mode === id;
          return (
            <button
              key={id}
              type="button"
              onClick={() => choose(id)}
              aria-pressed={on}
              className={`rounded border p-2.5 text-left transition ${
                on ? "border-cyan-300 bg-cyan-500/20 shadow-[0_0_10px_rgba(31,194,245,0.3)]" : "border-cyan-500/20 bg-black/30 hover:border-cyan-400"
              }`}
            >
              <strong className="block font-['Orbitron'] text-xs tracking-wider text-cyan-100">{on ? "● " : ""}{label}</strong>
              <span className="text-[11px] text-cyan-200/70">{desc}</span>
            </button>
          );
        })}
      </div>
      <Note>"Jarvis, abra o YouTube" abre numa janela média, no canto da tela. {status}</Note>
    </Section>
  );
}

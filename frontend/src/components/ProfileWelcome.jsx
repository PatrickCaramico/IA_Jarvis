import { useState } from "react";

// V4.5: primeiro painel de uma pessoa nova: escolhe como o JARVIS fica para ela.
// Salva nas preferências DO PERFIL dela (cada pessoa tem as suas).
const THEMES = [["blue", "Azul"], ["green", "Verde"], ["purple", "Roxo"], ["orange", "Laranja"], ["red", "Vermelho"]];

function Choice({ on, onClick, children }) {
  return (
    <button type="button" className={`pw-choice ${on ? "is-on" : ""}`} aria-pressed={on} onClick={onClick}>{children}</button>
  );
}

export default function ProfileWelcome({ api, name, onDone }) {
  const [fan, setFan] = useState(false);
  const [auto, setAuto] = useState(true);
  const [bg, setBg] = useState("blueprint");
  const [theme, setTheme] = useState("blue");
  const [silent, setSilent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const save = async () => {
    setBusy(true);
    setError("");
    try {
      const prefs = await api("/api/prefs", {
        method: "PATCH",
        body: JSON.stringify({
          fan_mode_enabled: fan,
          fan_auto_on_match_day: fan && auto,
          background_style: bg,
          color_theme: theme,
          silent_mode: silent,
        }),
      });
      onDone(prefs);
    } catch (e) {
      setError(e.message);
      setBusy(false);
    }
  };

  return (
    <div className="pw-root" role="dialog" aria-modal="true" aria-labelledby="pw-title">
      <section className="np-card">
        <header className="np-head">
          <span className="np-eyebrow">PRIMEIROS PASSOS</span>
          <h1 id="pw-title">Bem-vindo{name ? `, ${name}` : ""}!</h1>
          <p className="np-muted">Deixe o JARVIS do seu jeito. Dá para mudar tudo depois em Configurações.</p>
        </header>

        <div className="np-body">
          <span className="np-label">MODO TORCEDOR (PALMEIRAS)</span>
          <div className="pw-row">
            <Choice on={fan} onClick={() => setFan(true)}>⚽ Ligar</Choice>
            <Choice on={!fan} onClick={() => setFan(false)}>Não, obrigado</Choice>
          </div>
          {fan && (
            <label className="pw-check">
              <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} />
              Entrar sozinho no Modo Torcedor em dia de jogo
            </label>
          )}

          <span className="np-label">FUNDO</span>
          <div className="pw-row">
            <Choice on={bg === "blueprint"} onClick={() => setBg("blueprint")}>Planta azul</Choice>
            <Choice on={bg === "classic"} onClick={() => setBg("classic")}>Clássico escuro</Choice>
          </div>

          <span className="np-label">COR DOS DESTAQUES</span>
          <div className="pw-row pw-wrap">
            {THEMES.map(([key, label]) => (
              <Choice key={key} on={theme === key} onClick={() => setTheme(key)}>
                <i className={`pw-dot pw-${key}`} aria-hidden="true" /> {label}
              </Choice>
            ))}
          </div>

          <span className="np-label">VOZ</span>
          <div className="pw-row">
            <Choice on={!silent} onClick={() => setSilent(false)}>🔊 JARVIS fala</Choice>
            <Choice on={silent} onClick={() => setSilent(true)}>🔇 Só texto</Choice>
          </div>

          {error && <p className="np-error" role="alert">{error}</p>}
          <div className="np-actions">
            <button type="button" className="np-btn" onClick={save} disabled={busy}>{busy ? "Salvando…" : "Entrar na central"}</button>
          </div>
        </div>
      </section>
    </div>
  );
}

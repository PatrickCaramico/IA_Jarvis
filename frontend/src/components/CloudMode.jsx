import { useEffect, useState } from "react";
import PinPad from "./PinPad.jsx";
import { cloud, cloudToken, setCloudToken } from "../utils/cloudApi.js";
import { applyAccessibility, applyBackground, applyTheme } from "../utils/theme.js";

// V6.6.5: porta de entrada do MODO NUVEM. Pede o PIN da nuvem (uma vez a cada 60 dias neste aparelho)
// e entrega as configurações da central (onReady). Depois disso, a central de sempre abre por cima do
// adaptador da nuvem (utils/cloudShim.js): mesmo layout do app e do site.

function CloudLogin({ status, onLogged, onBack }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const submit = async (pin) => {
    setBusy(true);
    setMessage("");
    try {
      const { token } = await cloud("/login", { method: "POST", body: { pin } });
      setCloudToken(token);
      onLogged();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  };
  if (status && !status.configured) {
    return (
      <div className="cm-card cm-setup">
        <h2>O modo nuvem ainda não foi ligado</h2>
        <p>No painel do Netlify, em <b>Site configuration › Environment variables</b>, crie:</p>
        <ul>
          <li><code>JARVIS_NUVEM_PIN</code>: o PIN para entrar por aqui (4 a 8 números).</li>
          <li><code>JARVIS_NUVEM_CHAVE</code>: uma senha longa (a mesma vai no <code>.env</code> do PC, para sincronizar).</li>
          <li><code>GEMINI_API_KEY</code> (ou <code>OPENAI_API_KEY</code> / <code>ANTHROPIC_API_KEY</code>): a chave da IA.</li>
        </ul>
        <p>Depois, em Deploys, toque em <b>Trigger deploy</b>. O passo a passo está em <code>docs/MODO-NUVEM.md</code>.</p>
        {onBack && <button type="button" className="cm-chip" onClick={onBack}>VOLTAR</button>}
      </div>
    );
  }
  return (
    <div className="cm-login">
      <p className="cm-login-hint">O notebook não está respondendo. Entre com o PIN do modo nuvem para usar o JARVIS daqui.</p>
      <PinPad title="PIN DO MODO NUVEM" cancelLabel="" busy={busy} message={message} onSubmit={submit} onCancel={() => onBack?.()} />
      {onBack && <button type="button" className="cm-chip" onClick={onBack}>VOLTAR</button>}
    </div>
  );
}

export default function CloudMode({ onReady, onBack }) {
  const [status, setStatus] = useState(null);
  const [logged, setLogged] = useState(Boolean(cloudToken()));
  const [error, setError] = useState("");

  useEffect(() => {
    cloud("/status").then(setStatus).catch((err) => {
      setError(err.message);
      setStatus({ configured: true });
    });
  }, []);

  // as configurações da central já valem na tela do PIN (fundo, cor, acessibilidade)
  useEffect(() => {
    const p = status?.prefs;
    if (!p) return;
    if (p.background_style) applyBackground(p.background_style);
    applyAccessibility(p);
    if (p.theme_colors) applyTheme(p.theme_colors);
  }, [status]);

  useEffect(() => {
    if (!logged || !status?.configured) return;
    // confere a chave (pode ter vencido) antes de abrir a central
    cloud("/state")
      .then(() => onReady(status))
      .catch((err) => {
        if (err.status === 401) setLogged(false);
        else setError(err.message);
      });
  }, [logged, status, onReady]);

  return (
    <div className="cm-root">
      <header className="cm-header">
        <div>
          <div className="cm-brand">{(status?.prefs?.ai_name || status?.assistente || "JARVIS").toUpperCase()} <span>· MODO NUVEM</span></div>
          <div className="cm-sub">
            <span className="cm-dot" aria-hidden="true" />
            {status?.nome ? `${status.nome}, o` : "O"} notebook está desligado: usando a nuvem.
          </div>
        </div>
      </header>
      {!logged || !status?.configured ? (
        <CloudLogin status={status} onLogged={() => setLogged(true)} onBack={onBack} />
      ) : (
        <div className="cm-login"><p className="cm-login-hint">{error || "Abrindo a central pela nuvem…"}</p></div>
      )}
    </div>
  );
}

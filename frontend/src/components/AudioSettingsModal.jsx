import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { BACKEND_ON_THIS_PC, setVoiceHere, voiceHere } from "../utils/api.js";

// V6.5.8: botão ÁUDIO da tela de bloqueio (ao lado do FUNDO).
// - Onde o JARVIS fala (no celular/outro aparelho: aqui ou no PC)
// - Caixa de som do PC (onde a voz toca) com "testar"
// - Microfone do PC (o ouvido offline, que atende "Jarvis" com o navegador fechado)
// - Microfone desta tela (palmas e escuta pelo navegador)
function Option({ checked, onChange, children, name }) {
  return (
    <label className={`au-opt${checked ? " is-on" : ""}`}>
      <input type="radio" name={name} checked={checked} onChange={onChange} />
      <span>{children}</span>
    </label>
  );
}

export default function AudioSettingsModal({ api, onClose, onMicChange }) {
  const [pc, setPc] = useState(null); // {outputs, output, inputs, input}
  const [status, setStatus] = useState("");
  const [here, setHere] = useState(voiceHere());
  const [browserMics, setBrowserMics] = useState(null);
  const [browserMic, setBrowserMic] = useState(() => {
    try {
      return localStorage.getItem("jarvis.microphone.id") || "";
    } catch {
      return "";
    }
  });

  useEffect(() => {
    api("/api/audio").then(setPc).catch(() => setPc({ outputs: [], inputs: [], output: "", input: "", error: true }));
  }, [api]);

  useEffect(() => {
    if (!status) return undefined;
    const t = setTimeout(() => setStatus(""), 3500);
    return () => clearTimeout(t);
  }, [status]);

  const loadBrowserMics = async () => {
    try {
      const s = await navigator.mediaDevices.getUserMedia({ audio: true });
      s.getTracks().forEach((t) => t.stop());
      const list = (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === "audioinput");
      setBrowserMics(list);
    } catch {
      setBrowserMics([]);
      setStatus("O navegador não liberou o microfone.");
    }
  };

  const choosePc = async (patch, label) => {
    setPc((cur) => ({ ...cur, ...patch }));
    try {
      setPc(await api("/api/audio", { method: "POST", body: JSON.stringify(patch) }));
      setStatus(`✓ ${label}`);
    } catch (err) {
      setStatus(`Erro: ${err.message}`);
    }
  };

  const test = async () => {
    try {
      await api("/api/audio/test", { method: "POST" });
      setStatus("🔊 Falando na caixa do PC…");
    } catch (err) {
      setStatus(`Erro: ${err.message}`);
    }
  };

  return createPortal(
    <div
      className="ld-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Áudio"
      onClick={(e) => { e.stopPropagation(); if (e.target === e.currentTarget) onClose(); }}
      onKeyDown={(e) => { e.stopPropagation(); if (e.key === "Escape") onClose(); }}
    >
      <section className="ld-card au-card">
        <header className="ld-head">
          <span className="lc-label">🎧 ÁUDIO</span>
          <button type="button" className="ld-x" onClick={onClose} aria-label="Fechar" autoFocus>✕</button>
        </header>

        {!BACKEND_ON_THIS_PC && (
          <div className="au-sec">
            <h3>ONDE O JARVIS FALA</h3>
            <Option name="au-where" checked={here} onChange={() => { setVoiceHere(true); setHere(true); setStatus("✓ A voz sai neste aparelho."); }}>
              Neste aparelho
            </Option>
            <Option name="au-where" checked={!here} onChange={() => { setVoiceHere(false); setHere(false); setStatus("✓ A voz sai na caixa do PC."); }}>
              Na caixa de som do PC
            </Option>
          </div>
        )}

        <div className="au-sec">
          <h3>
            SAÍDA DE ÁUDIO DO PC
            <button type="button" className="au-test" onClick={test}>🔊 TESTAR</button>
          </h3>
          {pc === null && <p className="au-muted">Procurando as caixas de som…</p>}
          {pc && (
            <>
              <Option name="au-out" checked={!pc.output} onChange={() => choosePc({ output: "" }, "Saída: padrão do Windows")}>
                Padrão do Windows
              </Option>
              {pc.outputs.map((n) => (
                <Option key={n} name="au-out" checked={pc.output === n} onChange={() => choosePc({ output: n }, `Saída: ${n}`)}>{n}</Option>
              ))}
            </>
          )}
        </div>

        <div className="au-sec">
          <h3>MICROFONE DO PC <small>ouvido offline: "Jarvis" com o navegador fechado</small></h3>
          {pc && (
            <>
              <Option name="au-in" checked={!pc.input} onChange={() => choosePc({ input: "" }, "Microfone: padrão do Windows")}>
                Padrão do Windows
              </Option>
              {pc.inputs.map((n) => (
                <Option key={n} name="au-in" checked={pc.input === n} onChange={() => choosePc({ input: n }, `Microfone: ${n}`)}>{n}</Option>
              ))}
            </>
          )}
          {pc?.error && <p className="au-muted">Não consegui falar com o PC agora.</p>}
        </div>

        {typeof navigator !== "undefined" && navigator.mediaDevices?.enumerateDevices && (
          <div className="au-sec">
            <h3>MICROFONE DESTA TELA <small>palmas e escuta pelo navegador</small></h3>
            {browserMics === null ? (
              <button type="button" className="au-load" onClick={loadBrowserMics}>Mostrar os microfones</button>
            ) : browserMics.length === 0 ? (
              <p className="au-muted">Nenhum microfone liberado.</p>
            ) : (
              browserMics.map((m, i) => (
                <Option
                  key={m.deviceId}
                  name="au-browser"
                  checked={browserMic === m.deviceId}
                  onChange={() => {
                    setBrowserMic(m.deviceId);
                    try {
                      localStorage.setItem("jarvis.microphone.id", m.deviceId);
                    } catch {
                      /* sem armazenamento: vale só agora */
                    }
                    if (onMicChange) onMicChange(m.deviceId);
                    setStatus("✓ Microfone desta tela trocado.");
                  }}
                >
                  {m.label || `Microfone ${i + 1}`}
                </Option>
              ))
            )}
          </div>
        )}

        {status && <p className="au-status" role="status">{status}</p>}
      </section>
    </div>,
    document.body,
  );
}

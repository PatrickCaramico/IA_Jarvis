import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import useEscape from "../hooks/useEscape.js";
import RoboAvatar from "./RoboAvatar.jsx";
import { API_URL } from "../utils/api.js";
import "../desk.css";

// V8.0: ⬇ APP PARA WINDOWS: baixa o JARVIS.exe (gerado no PC pelo Gerar-App-Windows.bat) ou explica como gerar.
export default function DesktopDownload({ api, onClose }) {
  const [info, setInfo] = useState(null);
  const [err, setErr] = useState("");
  useEscape(onClose);
  useEffect(() => {
    api("/api/desktop/info").then(setInfo).catch((e) => setErr(e.message || "O PC não respondeu."));
  }, [api]);
  return createPortal(
    <div className="dd-overlay" role="dialog" aria-modal="true" aria-label="App JARVIS para Windows" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="dd">
        <button type="button" className="dd-x" onClick={onClose} aria-label="Fechar">✕</button>
        <RoboAvatar size={84} />
        <h2>JARVIS para Windows</h2>
        <p>O JARVIS numa janela própria, com a <b>ilha</b> no topo da tela (hora, música e respostas) e uma tecla para falar com ele de qualquer lugar.</p>
        {err && <p className="dd-err" role="alert">{err}</p>}
        {info && !info.local && <p className="dd-note">O app é baixado no próprio PC do JARVIS. Abra a central no computador e toque em ⬇ APP PARA WINDOWS.</p>}
        {info?.disponivel && (
          <>
            <a className="dd-btn" href={`${API_URL}/api/desktop/app`} download="JARVIS.exe">⬇ BAIXAR JARVIS.exe · {info.tamanho_mb} MB</a>
            <small>Gerado em {info.gerado_em}. Depois de baixar, dê dois cliques. Se o Windows avisar "aplicativo não reconhecido", toque em "Mais informações" › "Executar assim mesmo" (o app é gerado no seu próprio PC).</small>
          </>
        )}
        {info && info.local && !info.gerado && (
          <ol className="dd-steps">
            <li>Na pasta do JARVIS, dê dois cliques em <b>Gerar-App-Windows.bat</b> (só uma vez; leva alguns minutos).</li>
            <li>Volte aqui e toque em ⬇ APP PARA WINDOWS de novo para baixar.</li>
          </ol>
        )}
        {!info && !err && <p>Conferindo…</p>}
      </div>
    </div>,
    document.body,
  );
}

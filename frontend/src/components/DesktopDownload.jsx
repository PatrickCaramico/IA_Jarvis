import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import useEscape from "../hooks/useEscape.js";
import RoboAvatar from "./RoboAvatar.jsx";
import "../desk.css";

// V8.0: ⬇ APP PARA WINDOWS. V8.1.1: não tem mais JARVIS.exe para baixar (o McAfee acusava como vírus, falso
// positivo do PyInstaller). O Gerar-App-Windows.bat cria o atalho "JARVIS" (pythonw.exe oficial); daqui dá para abrir.
export default function DesktopDownload({ api, onClose }) {
  const [info, setInfo] = useState(null);
  const [err, setErr] = useState("");
  const [opened, setOpened] = useState(false);
  const open = () => api("/api/desktop/open", { method: "POST" }).then(() => setOpened(true)).catch((e) => setErr(e.message));
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
        {info && !info.local && <p className="dd-note">O app é instalado e aberto no próprio PC do JARVIS. Abra a central no computador e toque em ⬇ APP PARA WINDOWS.</p>}
        {info?.local && info.instalado && (
          <>
            <button type="button" className="dd-btn" onClick={open}>{opened ? "✓ ABRINDO O APP…" : "▶ ABRIR O APP DO JARVIS"}</button>
            <small>Instalado em {info.instalado_em} (versão {info.versao}). Também abre pelo atalho <b>JARVIS</b> na Área de Trabalho ou no Menu Iniciar.</small>
          </>
        )}
        {info?.local && !info.instalado && (
          <ol className="dd-steps">
            <li>Na pasta do JARVIS, dê dois cliques em <b>Gerar-App-Windows.bat</b> (só uma vez; leva alguns minutos).</li>
            <li>Pronto: aparece o atalho <b>JARVIS</b> na Área de Trabalho e no Menu Iniciar.</li>
          </ol>
        )}
        {info?.local && (
          <p className="dd-note">🛡 Sem .exe novo: o atalho abre o app com o Python oficial (assinado), então o antivírus (McAfee, Windows Defender) não tem o que bloquear.{info.exe_antigo ? " O JARVIS.exe antigo é apagado quando você rodar o Gerar-App-Windows.bat." : ""}</p>
        )}
        {!info && !err && <p>Conferindo…</p>}
      </div>
    </div>,
    document.body,
  );
}

import { useEffect, useState } from "react";
import { formatElapsed, knownAlwaysOn, knownStartup, nextCheckProgress, reconnectHint, startupText } from "../utils/bootStatus.js";

// V8.12.3: "RECONECTANDO AO SEU JARVIS" mostra o estado de verdade: a central (site) no ar, o JARVIS do PC sendo
// procurado (há quanto tempo, quantas tentativas e a barrinha até a próxima) e se o PC está no "sempre ligado".
// Antes era só um título e uma frase piscando: não dava para saber se a tela estava tentando ou travada.
export default function BootReconnect({ probe, launchState, onLaunch, onRetry, onCloud }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(t);
  }, []);

  const alwaysOn = knownAlwaysOn();
  const lastStartup = startupText(knownStartup()); // V9.4.1: onde a demora estava da última vez
  const elapsed = probe?.since ? now - probe.since : 0;
  const progress = probe?.checking ? 1 : nextCheckProgress(now, probe?.lastAt, probe?.nextAt);
  const launching = launchState === "opening" || launchState === "trying" || launchState === "asked";

  return (
    <div className="br-wrap">
      <div className="ls-title">RECONECTANDO AO SEU JARVIS</div>
      <p className="ls-hint br-hint" role="status" aria-live="polite">
        {reconnectHint({ launchState, alwaysOn, elapsedMs: elapsed })}
      </p>

      <ul className="br-panel" aria-label="Estado da conexão">
        <li className="br-row is-ok">
          <span className="br-led" aria-hidden="true" />
          <span className="br-label">CENTRAL</span>
          <span className="br-value">no ar</span>
        </li>
        <li className={`br-row ${launching ? "is-warn" : "is-search"}`}>
          <span className="br-led" aria-hidden="true" />
          <span className="br-label">JARVIS DO PC</span>
          <span className="br-value">
            {probe?.checking ? "conferindo…" : launching ? "ligando…" : "procurando"}
            {elapsed >= 1000 && <em> · há {formatElapsed(elapsed)}</em>}
            {probe?.attempts > 0 && <em> · {probe.attempts} {probe.attempts === 1 ? "tentativa" : "tentativas"}</em>}
          </span>
        </li>
        <li className={`br-row ${alwaysOn ? "is-ok" : "is-idle"}`}>
          <span className="br-led" aria-hidden="true" />
          <span className="br-label">SEMPRE LIGADO</span>
          <span className="br-value">
            {alwaysOn === true ? "ativo · liga com o Windows" : alwaysOn === false ? "desligado neste PC" : "confirmo quando o PC responder"}
          </span>
        </li>
        {lastStartup && (
          <li className="br-row is-idle">
            <span className="br-led" aria-hidden="true" />
            <span className="br-label">ÚLTIMA SUBIDA</span>
            <span className="br-value">{lastStartup}</span>
          </li>
        )}
        <li className="br-meter" aria-hidden="true">
          <span style={{ transform: `scaleX(${progress})` }} />
        </li>
      </ul>

      <div className="ls-boot-actions">
        <button type="button" onClick={onLaunch} disabled={launchState === "trying"} className="ls-btn-main br-main">
          <span className="br-power" aria-hidden="true">⏻</span>
          <span>{launchState === "trying" ? "ABRINDO…" : "LIGAR O JARVIS"}</span>
        </button>
        <button type="button" onClick={onRetry} className="ls-chip">TENTAR AGORA</button>
        {onCloud && <button type="button" onClick={onCloud} className="ls-chip">USAR PELA NUVEM</button>}
      </div>

      {launchState === "missing" && (
        <div className="ls-launch-missing" role="alert">
          <b>O JARVIS ainda não respondeu.</b>
          <span>Se o Chrome não perguntou nada ao tocar em LIGAR, dê duplo clique em <b>Instalar-Botao-Ligar.bat</b> (só uma vez). Ou ligue pelo <b>Iniciar-JARVIS.bat</b>: esta página entra sozinha.</span>
        </div>
      )}
      <details className="ls-boot-help">
        <summary>Não está entrando?</summary>
        <p>Com o JARVIS ligado, o Chrome pode barrar este site de falar com o PC: clique no ícone ao lado do endereço › <b>Acesso à rede local</b> › Permitir, e recarregue.</p>
        <p>O botão LIGAR precisa do <b>Instalar-Botao-Ligar.bat</b> rodado uma vez neste PC.</p>
        <p>Passou de 3 minutos? No PC, abra o <b>Ver-Logs.bat</b>: o motivo da última queda fica em <b>logs\backend-erro.log</b> e o que o PC tentou para religar, em <b>logs\ligar.log</b>.</p>
        <p>Para ele não desligar mais: em <b>Configurações › Diagnóstico &amp; Backup › Inicialização</b>, deixe o <b>Sempre ligado</b> marcado. Ele liga junto com o Windows, volta sozinho se cair e, na tomada, não deixa o PC dormir.</p>
      </details>
    </div>
  );
}

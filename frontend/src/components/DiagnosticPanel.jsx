import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import useEscape from "../hooks/useEscape.js";
import { measureFps } from "../utils/perfMode.js";
import { APP_VERSION } from "../utils/version.js";

// V7.4: 🩺 DIAGNÓSTICO. Junta os testes do PC (/api/system/health-check: IA, voz, internet, nuvem, disco,
// dados, erros) com os deste aparelho (conexão, tempo real, versão, microfone, câmera, fluidez).
// Cada item diz ok / atenção / falha e o que fazer. "COPIAR RELATÓRIO" leva tudo em texto (sem dados pessoais).

const ICON = { ok: "✓", warn: "!", fail: "✕", run: "◌" };
const item = (id, label, status, detail, fix = "") => ({ id, label, status, detail, fix: status === "ok" ? "" : fix });

async function deviceChecks(api, connected) {
  const out = [];
  const t = performance.now();
  let health = null;
  try {
    health = await api("/api/health", { timeout: 6000 });
  } catch {
    /* sem PC */
  }
  const ms = Math.round(performance.now() - t);
  out.push(health
    ? item("pc-link", "Conexão com o PC", ms < 600 ? "ok" : "warn", `Respondeu em ${ms} ms.`, "Conexão lenta: no celular, use o Wi-Fi de casa.")
    : item("pc-link", "Conexão com o PC", "fail", "O PC não respondeu.", "Confira se o JARVIS está ligado no PC (Iniciar-JARVIS.bat). Fora de casa, o celular usa a nuvem."));
  if (health?.version) {
    out.push(health.version === APP_VERSION
      ? item("version", "Versão (tela e PC)", "ok", `As duas na ${APP_VERSION}.`)
      : item("version", "Versão (tela e PC)", "warn", `Tela ${APP_VERSION}, PC ${health.version}.`, "Toque em ⟳ ATUALIZAR (ou recarregue a página) para as duas ficarem iguais."));
  }
  out.push(connected
    ? item("realtime", "Tempo real (respostas e voz)", "ok", "Conectado.")
    : item("realtime", "Tempo real (respostas e voz)", "warn", "Desconectado.", "Recarregue a página. Se continuar, reinicie o JARVIS no PC."));
  const Rec = window.SpeechRecognition || window.webkitSpeechRecognition;
  let mic = "prompt";
  try {
    mic = (await navigator.permissions?.query({ name: "microphone" }))?.state || "prompt";
  } catch {
    /* navegador sem consulta */
  }
  out.push(!Rec
    ? item("mic", "Microfone e reconhecimento de voz", "warn", "Este navegador não reconhece voz.", "Use o Google Chrome ou o Microsoft Edge (ou o app do JARVIS no celular).")
    : mic === "denied"
      ? item("mic", "Microfone e reconhecimento de voz", "fail", "Microfone bloqueado.", "Libere o microfone: cadeado ao lado do endereço > Microfone > Permitir.")
      : item("mic", "Microfone e reconhecimento de voz", "ok", mic === "granted" ? "Liberado." : "Pronto (vai pedir permissão no primeiro uso)."));
  try {
    const devices = (await navigator.mediaDevices?.enumerateDevices?.()) || [];
    const cams = devices.filter((d) => d.kind === "videoinput").length;
    out.push(cams
      ? item("camera", "Câmera deste aparelho", "ok", `${cams} câmera(s).`)
      : item("camera", "Câmera deste aparelho", "warn", "Nenhuma câmera encontrada.", "Sem câmera, o \"abre a câmera e analisa\" não funciona neste aparelho."));
  } catch {
    out.push(item("camera", "Câmera deste aparelho", "warn", "Não consegui verificar.", ""));
  }
  const fps = await measureFps(1200);
  out.push(item("fps", "Fluidez da tela", fps >= 45 ? "ok" : "warn", `${fps} quadros/s.`, "Tela pesada: ligue o Modo leve em ⚡ OTIMIZAR."));
  return out;
}

export default function DiagnosticPanel({ api, connected = true, onClose }) {
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(true);
  const [copied, setCopied] = useState(false);
  const [meta, setMeta] = useState("");
  useEscape(onClose);

  const run = useCallback(async () => {
    setBusy(true);
    setItems([]);
    setCopied(false);
    const [device, pc] = await Promise.all([
      deviceChecks(api, connected),
      api("/api/system/health-check", { timeout: 60_000 }).catch(() => null),
    ]);
    const pcItems = pc?.items || [item("pc", "Testes do PC", "warn", "Não rodaram (PC desligado ou modo nuvem).", "Ligue o JARVIS no PC e rode de novo para testar IA, voz e internet.")];
    setItems([...pcItems, ...device]);
    setMeta(pc ? `PC ${pc.version} · ${pc.at} · ${(pc.took_ms / 1000).toFixed(1)} s` : `Tela ${APP_VERSION}`);
    setBusy(false);
  }, [api, connected]);

  useEffect(() => {
    run();
  }, [run]);

  const counts = items.reduce((acc, i) => ({ ...acc, [i.status]: (acc[i.status] || 0) + 1 }), {});
  const verdict = busy ? "TESTANDO…" : counts.fail ? `${counts.fail} PROBLEMA${counts.fail > 1 ? "S" : ""}` : counts.warn ? "FUNCIONANDO, COM AVISOS" : "TUDO CERTO";
  const tone = busy ? "run" : counts.fail ? "fail" : counts.warn ? "warn" : "ok";

  const copy = async () => {
    const text = [`Diagnóstico JARVIS (tela ${APP_VERSION}) · ${meta}`, ...items.map((i) => `[${i.status.toUpperCase()}] ${i.label}: ${i.detail}${i.fix ? ` → ${i.fix}` : ""}`)].join("\n");
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  return createPortal(
    <div className="dg-overlay" role="dialog" aria-modal="true" aria-label="Diagnóstico do JARVIS" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="dg">
        <header className="dg-head">
          <span>🩺 DIAGNÓSTICO</span>
          <small>{meta}</small>
          <button type="button" className="dg-x" onClick={onClose} aria-label="Fechar">✕</button>
        </header>
        <div className={`dg-verdict is-${tone}`}>
          <i aria-hidden="true">{busy ? <span className="dg-spin" /> : ICON[tone]}</i>
          <div>
            <strong>{verdict}</strong>
            <small>{busy ? "Testando IA, voz, internet, nuvem, microfone e câmera…" : `${counts.ok || 0} ok · ${counts.warn || 0} atenção · ${counts.fail || 0} falha`}</small>
          </div>
        </div>
        <ul className="dg-list">
          {items.map((i, n) => (
            <li key={i.id} className={`is-${i.status}`} style={{ animationDelay: `${n * 0.05}s` }}>
              <i aria-hidden="true">{ICON[i.status]}</i>
              <div>
                <b>{i.label}</b>
                <span>{i.detail}</span>
                {i.fix && <em>➜ {i.fix}</em>}
              </div>
            </li>
          ))}
        </ul>
        <div className="dg-actions">
          <button type="button" onClick={run} disabled={busy}>↻ RODAR DE NOVO</button>
          <button type="button" onClick={copy} disabled={busy}>{copied ? "✓ COPIADO" : "⧉ COPIAR RELATÓRIO"}</button>
        </div>
      </div>
    </div>,
    document.body,
  );
}

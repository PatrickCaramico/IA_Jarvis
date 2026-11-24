// V9.3: RELATÓRIO DE SEGURANÇA. Quem tentou entrar ou apareceu na câmera sem ser reconhecido (com a foto), pendrives
// ligados, bloqueios automáticos e a otimização sugerida do dia. Abre sozinho ao entrar na central quando há
// novidade, pela voz ("relatório de segurança") e pela paleta. Tudo vem do PC; as fotos nunca saem dele.
import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import useEscape from "../hooks/useEscape.js";
import { openPcScan } from "../utils/pcScan.js";
import { KIND_ICON, whenText } from "../utils/security.js";

export default function SecurityReport({ api, initial = null, onClose }) {
  const [report, setReport] = useState(initial);
  const [zoom, setZoom] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => api("/api/security/report", { timeout: 10000 }).then(setReport).catch(() => {}), [api]);
  useEffect(() => { if (!initial) load(); }, [initial, load]);

  const close = useCallback(() => {
    api("/api/security/seen", { method: "POST" }).catch(() => {});
    onClose();
  }, [api, onClose]);
  useEscape(zoom ? () => setZoom(null) : close);

  const toggle = async (key, value) => {
    setBusy(true);
    try {
      await api("/api/prefs", { method: "PATCH", body: JSON.stringify({ [key]: value }) });
      await load();
    } catch {
      /* sem resposta: a chave volta ao estado do PC na próxima leitura */
    } finally {
      setBusy(false);
    }
  };

  const guard = report?.guard || {};
  const events = report?.events || [];
  return createPortal(
    <div className="sec-backdrop" onMouseDown={(e) => e.target === e.currentTarget && close()}>
      <div className="sec" role="dialog" aria-modal="true" aria-label="Relatório de segurança">
        <header className="sec-head">
          <div>
            <h2>🛡️ SEGURANÇA</h2>
            <span>{report ? (report.unseen ? `${report.unseen} ${report.unseen === 1 ? "novidade" : "novidades"} desde a última vez` : "Nenhuma novidade") : "Carregando…"}</span>
          </div>
          <button type="button" className="sp-close" onClick={close} aria-label="Fechar">✕</button>
        </header>

        <div className="sec-guards" role="group" aria-label="Vigias">
          <button type="button" disabled={busy || (!guard.camera && !guard.has_face)} className={`sec-chip${guard.camera ? " is-on" : ""}`}
            onClick={() => toggle("camera_guard_enabled", !guard.camera)}
            title={guard.has_face ? "Olha pela câmera (tudo no PC): avisa sobre pessoas não reconhecidas e bloqueia quando o senhor sai" : "Cadastre a foto do rosto em Configurações › Bloqueio"}>
            📷 Vigia da câmera {guard.camera ? "ligado" : "desligado"}
          </button>
          <button type="button" disabled={busy} className={`sec-chip${guard.usb ? " is-on" : ""}`} onClick={() => toggle("usb_alert_enabled", !guard.usb)}>
            🔌 Alerta de pendrive {guard.usb ? "ligado" : "desligado"}
          </button>
          <button type="button" disabled={busy} className={`sec-chip${guard.optimize ? " is-on" : ""}`} onClick={() => toggle("auto_optimize_enabled", !guard.optimize)}>
            🧹 Otimização do dia {guard.optimize ? "ligada" : "desligada"}
          </button>
        </div>

        <ul className="sec-list">
          {events.map((e) => (
            <li key={e.id} className={`sec-item is-${e.kind}${e.new ? " is-new" : ""}`}>
              {e.photo_b64 ? (
                <button type="button" className="sec-photo" onClick={() => setZoom(e)} aria-label="Ampliar a foto">
                  <img src={`data:image/jpeg;base64,${e.photo_b64}`} alt="Pessoa não reconhecida" />
                </button>
              ) : <span className="sec-ico" aria-hidden="true">{KIND_ICON[e.kind] || "•"}</span>}
              <div className="sec-text">
                <b>{e.label}{e.new && <em>NOVO</em>}</b>
                <span>{e.text}</span>
                <small>{whenText(e.at)}</small>
                {e.scan && (
                  <button type="button" className="sec-action" onClick={() => { openPcScan(e.scan); close(); }}>VER E LIMPAR</button>
                )}
              </div>
            </li>
          ))}
          {report && !events.length && <li className="sec-empty">Nada registrado ainda. Com o vigia ligado, tudo o que acontecer aparece aqui.</li>}
        </ul>

        <footer className="sec-foot">
          <span>As fotos ficam só no PC (no máximo 20, por 30 dias).</span>
          <button type="button" className="sec-ok" onClick={close}>OK, VISTO</button>
        </footer>
      </div>
      {zoom && (
        <div className="sec-zoom" onMouseDown={() => setZoom(null)}>
          <img src={`data:image/jpeg;base64,${zoom.photo_b64}`} alt="Pessoa não reconhecida (ampliada)" />
          <p>{zoom.text} · {whenText(zoom.at)}</p>
        </div>
      )}
    </div>,
    document.body,
  );
}

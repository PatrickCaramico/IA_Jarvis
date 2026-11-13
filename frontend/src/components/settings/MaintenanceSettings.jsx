import { useEffect, useRef, useState } from "react";
import { APP_VERSION } from "../../utils/version.js";
import { checkForUpdate, readUpdateResult, saveUpdateResult } from "../../utils/updateCheck.js";
import { Note, SaveStatus, Section } from "./SettingsControls.jsx";

const btn = "rounded border border-cyan-500/40 bg-black/30 px-3 py-1.5 text-xs text-cyan-100 hover:bg-cyan-500/20 disabled:opacity-40";

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false; // sem permissão de área de transferência: mostramos o texto para copiar à mão
  }
}

// V4.2.2: "Copiar diagnóstico" (sem segredos) e exportar/importar os ajustes.
export default function MaintenanceSettings({ api, onImported }) {
  const [status, setStatus] = useState(null);
  const [manualText, setManualText] = useState("");
  const [busy, setBusy] = useState(false);
  const [checkingUpdates, setCheckingUpdates] = useState(false);
  const [updateResult, setUpdateResult] = useState(() => readUpdateResult());
  const fileRef = useRef(null);

  useEffect(() => {
    const onUpdateCheck = (event) => setUpdateResult(event.detail);
    window.addEventListener("jarvis-update-check", onUpdateCheck);
    return () => window.removeEventListener("jarvis-update-check", onUpdateCheck);
  }, []);

  const checkUpdates = async () => {
    setCheckingUpdates(true);
    try {
      const result = await checkForUpdate(api);
      saveUpdateResult(result);
      setUpdateResult(result);
      window.dispatchEvent(new CustomEvent("jarvis-update-check", { detail: result })); // bolinha do ATUALIZAR na hora
    } catch {
      const result = { error: "Não consegui conferir agora (o JARVIS do PC precisa estar ligado e com internet). Tente de novo em instantes." };
      saveUpdateResult(result);
      setUpdateResult(result);
    } finally {
      setCheckingUpdates(false);
    }
  };

  const copyDiagnostics = async () => {
    setBusy(true);
    setManualText("");
    try {
      const { text } = await api("/api/diagnostics?format=text");
      if (await copyText(text)) setStatus({ ok: "Diagnóstico copiado. Pode colar onde quiser." });
      else {
        setManualText(text);
        setStatus({ ok: "Não consegui copiar sozinho: selecione o texto abaixo e copie." });
      }
    } catch (err) {
      setStatus({ error: err.message });
    } finally {
      setBusy(false);
    }
  };

  const exportPrefs = async () => {
    try {
      const data = await api("/api/prefs/export");
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `jarvis-ajustes-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setStatus({ ok: "Ajustes exportados." });
    } catch (err) {
      setStatus({ error: err.message });
    }
  };

  const importPrefs = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    try {
      const parsed = JSON.parse(await file.text());
      const body = JSON.stringify({ prefs: parsed.prefs ?? parsed });
      const result = await api("/api/prefs/import", { method: "POST", body });
      onImported(result.prefs);
      const skipped = result.ignored.length ? ` (${result.ignored.length} ignorados)` : "";
      setStatus({ ok: `${result.applied.length} ajustes importados${skipped}.` });
    } catch (err) {
      setStatus({ error: err instanceof SyntaxError ? "Esse arquivo não é um JSON válido." : err.message });
    }
  };

  return (
    <Section title="DIAGNÓSTICO & BACKUP">
      <div className="flex flex-wrap gap-2">
        <button type="button" className={btn} onClick={copyDiagnostics} disabled={busy}>⧉ Copiar diagnóstico</button>
        <button type="button" className={btn} onClick={exportPrefs}>⇩ Exportar ajustes</button>
        <button type="button" className={btn} onClick={() => fileRef.current?.click()}>⇧ Importar ajustes</button>
        <button type="button" className={btn} onClick={checkUpdates} disabled={checkingUpdates}>
          ↻ {checkingUpdates ? "Verificando..." : "Verificar atualizações"}
        </button>
        <input ref={fileRef} type="file" accept="application/json,.json" className="hidden" onChange={importPrefs} />
      </div>
      {updateResult && (
        <div className="mt-3 rounded border border-cyan-500/25 bg-black/25 p-3 text-xs text-cyan-100" role="status" aria-live="polite">
          {updateResult.error ? (
            <p>{updateResult.error}</p>
          ) : updateResult.updateAvailable ? (
            <>
              <p className="font-semibold">
                {updateResult.count > 1 ? `${updateResult.count} versões novas` : "Versão nova"} disponível: {updateResult.latestVersion} (este PC: {updateResult.currentVersion}).
              </p>
              <p className="mt-1">Toque em ⟳ ATUALIZAR no topo da central (ou na tela de bloqueio).</p>
              {updateResult.notes && <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap font-sans text-cyan-100/75">{updateResult.notes}</pre>}
            </>
          ) : (
            <p>Você está na versão mais nova (v{updateResult.currentVersion}).</p>
          )}
        </div>
      )}
      {manualText && (
        <textarea readOnly value={manualText} rows={6} onFocus={(e) => e.target.select()}
          className="mt-2 w-full rounded border border-cyan-500/30 bg-black/60 p-2 font-mono text-[10px] text-cyan-100" />
      )}
      <SaveStatus status={status} />
      <Note>
        O diagnóstico traz versão (v{APP_VERSION}), sistema e últimos eventos, sem chaves, PIN nem o texto dos seus pedidos.
        O backup leva só as preferências (não leva chaves, rosto, memórias nem o índice da câmera).
      </Note>
    </Section>
  );
}

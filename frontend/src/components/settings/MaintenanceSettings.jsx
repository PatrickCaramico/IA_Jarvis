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

// V8.11: INICIALIZAÇÃO — ligar junto com o Windows e atualizar sozinho ao abrir a central.
function StartupSettings({ api }) {
  const [auto, setAuto] = useState(null); // {available, enabled}
  const [onOpen, setOnOpen] = useState(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const [awake, setAwake] = useState(null); // V8.12.3: { keep_awake, on_ac } (não deixa o PC dormir na tomada)
  useEffect(() => {
    api("/api/system/autostart").then(setAuto).catch(() => setAuto({ available: false, enabled: false }));
    api("/api/system/always-on").then(setAwake).catch(() => setAwake(null));
    api("/api/desk").then((d) => setOnOpen(d?.atualizacao?.ao_abrir !== false)).catch(() => setOnOpen(null));
  }, [api]);

  const toggleAuto = async (enabled) => {
    setBusy(true);
    setMsg("");
    try {
      const r = await api("/api/system/autostart", { method: "POST", body: JSON.stringify({ enabled }), timeout: 30_000 });
      setAuto(r);
      setMsg(r.ok === false ? r.message || "Não deu certo." : enabled ? "Pronto: o JARVIS fica sempre ligado e liga sozinho quando você entrar no Windows." : "O JARVIS não liga mais sozinho com o Windows.");
      api("/api/system/always-on").then(setAwake).catch(() => {});
    } catch (err) {
      setMsg(err.message);
    } finally {
      setBusy(false);
    }
  };

  const toggleAwake = async (keepAwake) => {
    setMsg("");
    try {
      const r = await api("/api/system/always-on", { method: "POST", body: JSON.stringify({ keep_awake: keepAwake }) });
      setAwake(r);
      setMsg(keepAwake ? "Pronto: na tomada, o PC não dorme mais por inatividade (a tela ainda apaga)." : "O PC volta a dormir normalmente.");
    } catch (err) {
      setMsg(err.message);
    }
  };

  const toggleOnOpen = async (value) => {
    setOnOpen(value);
    try {
      const d = await api("/api/desk", { method: "PATCH", body: JSON.stringify({ atualizacao: { ao_abrir: value } }) });
      setOnOpen(d?.atualizacao?.ao_abrir !== false);
    } catch (err) {
      setOnOpen(!value);
      setMsg(err.message);
    }
  };

  const row = "flex items-start gap-2 cursor-pointer text-xs text-cyan-200/90";
  const box = "mt-0.5 rounded border-cyan-500/40 bg-black text-emerald-500 focus:ring-0";
  return (
    <Section title="INICIALIZAÇÃO">
      <div className="flex flex-col gap-2">
        <label className={`${row}${auto && !auto.available ? " opacity-50" : ""}`}>
          <input type="checkbox" className={box} checked={!!auto?.enabled} disabled={!auto?.available || busy}
            onChange={(e) => toggleAuto(e.target.checked)} />
          <span>
            <b>Sempre ligado.</b> Ao entrar no Windows, o JARVIS liga sozinho em segundo plano (sem janela e sem abrir
            aba). Se ele cair, o guardião liga de novo; se o guardião cair, o JARVIS liga outro.
            {auto && !auto.available && <em className="block text-cyan-200/60">Só no PC com Windows onde o JARVIS roda.</em>}
          </span>
        </label>
        <label className={`${row}${!awake || !auto?.enabled ? " opacity-50" : ""}`}>
          <input type="checkbox" className={box} checked={!!awake?.keep_awake && !!auto?.enabled}
            disabled={!awake || !auto?.enabled} onChange={(e) => toggleAwake(e.target.checked)} />
          <span>
            <b>Não deixar o PC dormir na tomada.</b> Com o carregador ligado, o PC não entra em suspensão por
            inatividade, então o JARVIS continua respondendo pelo site e pelo celular. A tela ainda apaga normalmente;
            na bateria nada muda.
            {awake && awake.keep_awake && auto?.enabled && !awake.on_ac && <em className="block text-cyan-200/60">Agora na bateria: o PC pode dormir até voltar para a tomada.</em>}
          </span>
        </label>
        <label className={`${row}${onOpen === null ? " opacity-50" : ""}`}>
          <input type="checkbox" className={box} checked={!!onOpen} disabled={onOpen === null}
            onChange={(e) => toggleOnOpen(e.target.checked)} />
          <span>
            <b>Atualizar ao abrir a central.</b> Se tiver versão nova quando você abrir a central no PC (pelo site ou
            aqui), o JARVIS atualiza na hora, com a barra de progresso, e já abre na versão nova.
          </span>
        </label>
      </div>
      {msg && <p className="mt-2 text-xs text-cyan-100" role="status">{msg}</p>}
    </Section>
  );
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
    <>
    <StartupSettings api={api} />
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
    </>
  );
}

import { useCallback, useEffect, useState } from "react";
import { IcsConnect } from "../DataSourcesScreen.jsx";
import { Note, Section } from "./SettingsControls.jsx";

// V6.8.1: Google Agenda nos Ajustes (antes só em Menu › Fontes de Dados, difícil de achar).
export default function CalendarSettings({ api }) {
  const [status, setStatus] = useState(null);
  const [msg, setMsg] = useState("");
  const load = useCallback(() => api("/api/calendar/status").then(setStatus).catch(() => setStatus({ connected: false })), [api]);
  useEffect(() => {
    load();
  }, [load]);

  const disconnect = async () => {
    if (!window.confirm("Desconectar a agenda do JARVIS?")) return;
    try {
      await api("/api/calendar/ics", { method: "POST", body: JSON.stringify({ url: "" }) });
      setMsg("Agenda desconectada.");
      load();
    } catch (err) {
      setMsg(err.message);
    }
  };

  return (
    <Section title="GOOGLE AGENDA">
      <p className="text-xs text-cyan-100" role="status">
        {status === null ? "Conferindo…" : status.connected ? `✓ Conectada (${status.source || "agenda"}).` : "Ainda não conectada."}
      </p>
      {status && !status.connected && (
        <ol className="mt-2 list-decimal space-y-1 pl-5 text-xs text-cyan-100/85">
          <li>No computador, abra <a className="underline" href="https://calendar.google.com/calendar/r/settings" target="_blank" rel="noreferrer">as configurações do Google Agenda</a>.</li>
          <li>Na esquerda, em <b>Configurações das minhas agendas</b>, clique na sua agenda.</li>
          <li>Role até <b>Integrar agenda</b> e copie o <b>Endereço secreto no formato iCal</b> (termina em <code>basic.ics</code>).</li>
          <li>Cole abaixo e toque em <b>USAR ESTA AGENDA</b>.</li>
        </ol>
      )}
      <div className="mt-2">
        <IcsConnect api={api} onDone={load} hideHelp />
      </div>
      {status?.ics && (
        <button type="button" className="mt-2 rounded border border-red-400/50 px-3 py-1 text-xs text-red-200 hover:bg-red-500/15" onClick={disconnect}>
          Desconectar agenda
        </button>
      )}
      {msg && <p className="mt-1 text-xs text-cyan-100/80">{msg}</p>}
      <Note>O endereço iCal é secreto: com ele, qualquer pessoa vê sua agenda. Não compartilhe; se vazar, use "Redefinir" no Google. O JARVIS só lê (não cria nem altera compromissos).</Note>
    </Section>
  );
}

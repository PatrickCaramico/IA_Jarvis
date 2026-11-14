import { useCallback, useEffect, useState } from "react";
import { Note, Section } from "./SettingsControls.jsx";

// V7.6: Configurações > Segurança. Aparelhos com chave própria (remover um ou todos), pedidos esperando
// aprovação e o que aconteceu nas últimas 24 h (tentativas suspeitas, aparelhos aprovados/removidos).
const ICON = { celular: "📱", tablet: "📲", tv: "📺", pc: "💻", outro: "🔌" };

function when(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function HttpsSection({ api, local }) {
  const [st, setSt] = useState(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  useEffect(() => {
    api("/api/security/https").then(setSt).catch(() => {});
  }, [api]);
  const toggle = async () => {
    const on = !st.enabled;
    const warn = on
      ? "Ligar a conexão criptografada (https)?\n\nDepois disso:\n• cada celular precisa instalar o certificado do JARVIS (passo a passo na página do certificado);\n• escaneie o QR code de novo;\n• o app Android precisa ser gerado de novo (Gerar-App-Android.bat).\n\nO JARVIS vai reiniciar."
      : "Desligar a conexão criptografada? A rede de casa volta para http e o JARVIS reinicia.";
    if (!window.confirm(warn)) return;
    setBusy(true);
    try {
      const r = await api("/api/security/https", { method: "POST", body: JSON.stringify({ on }) });
      setSt(r);
      setNote(r.restarting ? "Reiniciando o JARVIS… a página volta sozinha em instantes." : "Pronto. Reinicie o JARVIS (Iniciar-JARVIS.bat) para valer.");
    } catch (err) {
      setNote(err.message);
    }
    setBusy(false);
  };
  if (!st) return null;
  const ip = st.ips?.[0] || "IP-DO-PC";
  return (
    <Section title="CONEXÃO CRIPTOGRAFADA (HTTPS)">
      <p className={`text-xs ${st.enabled ? "text-emerald-300" : "text-amber-200"}`}>
        {st.enabled ? `● LIGADA: celulares e outros aparelhos entram por https://${ip}:${st.front_port}` : "○ DESLIGADA: a rede de casa usa http (alguém no mesmo Wi-Fi poderia espiar)."}
      </p>
      <Note>Este PC continua em http://127.0.0.1 (não sai do computador). Na rede, com https ligado, a chave de acesso nunca viaja sem criptografia.</Note>
      {local && (
        <button type="button" disabled={busy} onClick={toggle}
          className={`w-full text-[11px] font-['Orbitron'] py-2 rounded border ${st.enabled ? "border-red-400/50 text-red-200 hover:bg-red-500/10" : "border-emerald-400/60 text-emerald-100 hover:bg-emerald-500/10"}`}>
          {busy ? "AGUARDE…" : st.enabled ? "DESLIGAR HTTPS" : "LIGAR HTTPS (RECOMENDADO)"}
        </button>
      )}
      {st.has_certificate && (
        <p className="text-[11px] text-cyan-200/80">
          No celular, abra <b className="text-white">http://{ip}:8000/api/mobile/certificado</b> para instalar o certificado (uma vez só).
          <br /><span className="text-[10px] text-cyan-300/50 break-all">Impressão digital: {st.fingerprint}</span>
        </p>
      )}
      {note && <p className="text-xs text-cyan-200" role="status">{note}</p>}
    </Section>
  );
}

export default function SecuritySettings({ api }) {
  const [data, setData] = useState(null);
  const [msg, setMsg] = useState("");

  const load = useCallback(() => {
    api("/api/security/devices").then(setData).catch((err) => setMsg(err.message));
  }, [api]);
  useEffect(() => {
    load();
  }, [load]);

  const remove = async (d) => {
    if (!window.confirm(`Remover "${d.name}"? Ele vai precisar pedir acesso de novo (com aprovação no PC).`)) return;
    try {
      await api(`/api/security/devices/${d.id}`, { method: "DELETE" });
      setMsg(`${d.name} removido.`);
      load();
    } catch (err) {
      setMsg(err.message);
    }
  };
  const removeAll = async () => {
    if (!window.confirm("Desconectar TODOS os aparelhos e trocar o QR code? Cada um vai precisar pedir acesso de novo.")) return;
    try {
      const r = await api("/api/security/disconnect-all", { method: "POST" });
      setMsg(`${r.removed} aparelho(s) desconectado(s). O QR code foi trocado.`);
      load();
    } catch (err) {
      setMsg(err.message);
    }
  };
  const endMigration = async () => {
    try {
      await api("/api/security/end-migration", { method: "POST" });
      setMsg("Pronto: a partir de agora, aparelho novo só entra com a sua aprovação.");
      load();
    } catch (err) {
      setMsg(err.message);
    }
  };

  if (!data) return <p className="text-xs text-cyan-200/60">{msg || "Carregando…"}</p>;
  return (
    <div className="space-y-4">
      <Section title="APARELHOS CONECTADOS">
        {data.devices.length === 0 && <p className="text-xs text-cyan-200/60">Nenhum aparelho com chave própria ainda. Eles aparecem aqui quando abrirem o JARVIS.</p>}
        <ul className="space-y-1.5">
          {data.devices.map((d) => (
            <li key={d.id} className="flex items-center gap-2 rounded border border-cyan-500/20 bg-black/30 px-2.5 py-2">
              <span aria-hidden="true">{ICON[d.kind] || "🔌"}</span>
              <div className="min-w-0 flex-1">
                <div className="text-xs text-white truncate">{d.name}{d.this && <span className="ml-2 text-[10px] text-emerald-300">(ESTE APARELHO)</span>}</div>
                <div className="text-[10px] text-cyan-300/60">Último acesso {when(d.last_seen)} · {d.ip}</div>
              </div>
              <button type="button" onClick={() => remove(d)} className="text-[10px] font-['Orbitron'] px-2 py-1 rounded border border-red-400/50 text-red-200 hover:bg-red-500/10">REMOVER</button>
            </li>
          ))}
        </ul>
        {data.local && (
          <button type="button" onClick={removeAll} className="mt-2 w-full text-[11px] font-['Orbitron'] py-2 rounded border border-red-400/50 text-red-200 hover:bg-red-500/10">
            DESCONECTAR TODOS E TROCAR O QR CODE
          </button>
        )}
      </Section>

      <Section title="APARELHO NOVO">
        {data.migration ? (
          <>
            <Note>Migração automática ligada até {when(data.migration_until)}: os aparelhos que já usavam o JARVIS ganham a própria chave sozinhos, sem escanear o QR de novo. Depois disso, aparelho novo só entra com a sua aprovação.</Note>
            {data.local && (
              <button type="button" onClick={endMigration} className="w-full text-[11px] font-['Orbitron'] py-2 rounded border border-cyan-400/50 text-cyan-100 hover:bg-cyan-500/10">
                JÁ MIGREI TUDO: EXIGIR APROVAÇÃO AGORA
              </button>
            )}
          </>
        ) : (
          <Note>Aparelho novo escaneia o QR code e fica esperando: na tela do PC aparece PERMITIR / RECUSAR.</Note>
        )}
      </Section>

      <HttpsSection api={api} local={data.local} />

      <Section title="ÚLTIMAS 24 HORAS">
        {data.events.length === 0 ? (
          <p className="text-xs text-cyan-200/60">Nada de diferente.</p>
        ) : (
          <ul className="space-y-1">
            {data.events.map((e, i) => (
              <li key={i} className={`text-[11px] ${e.level === "alert" ? "text-red-200" : e.level === "warn" ? "text-amber-200" : "text-cyan-100/80"}`}>
                {e.level === "alert" ? "⚠ " : "• "}{when(e.at)} · {e.message}
              </li>
            ))}
          </ul>
        )}
      </Section>
      {msg && <p className="text-xs text-cyan-200" role="status">{msg}</p>}
    </div>
  );
}

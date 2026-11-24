import { useCallback, useEffect, useState } from "react";
import { Note, Section, Toggle } from "./SettingsControls.jsx";
import { isLockKeyCandidate, keyLabel } from "../../utils/lockExtras.js";

// V9.4: TECLA DE ACESSO e AVATAR do bloqueio (Configurações > Bloqueio).
// Tecla: a câmera só começa a verificar o rosto depois que ela é apertada no teclado do PC. Espaço, clique,
// palmas e "abrir central" deixam de abrir a câmera; o PIN continua como reserva. A tela bloqueada nunca mostra qual é.
export default function LockKeySection({ api, prefs, onPatch }) {
  const [status, setStatus] = useState(null); // { enabled, code, label }
  const [capturing, setCapturing] = useState(false);
  const [msg, setMsg] = useState(null);

  const load = useCallback(() => api("/api/auth/lock-key").then(setStatus).catch(() => {}), [api]);
  useEffect(() => { load(); }, [load]);

  const changed = () => window.dispatchEvent(new CustomEvent("jarvis-lock-key-changed"));

  useEffect(() => {
    if (!capturing) return undefined;
    const onKey = async (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (e.code === "Escape") { setCapturing(false); return; }
      if (!isLockKeyCandidate(e.code)) {
        setMsg({ error: "Essa não vale. Use uma letra (menos o P), um número ou uma tecla F." });
        return;
      }
      setCapturing(false);
      try {
        const st = await api("/api/auth/lock-key", { method: "POST", body: JSON.stringify({ code: e.code }) });
        setStatus(st);
        setMsg({ ok: `Pronto: a tecla de acesso é ${st.label}. Na tela bloqueada, aperte ${st.label} e olhe para a câmera.` });
        changed();
      } catch (err) {
        setMsg({ error: err.message });
      }
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [capturing, api]);

  const turnOff = async () => {
    try {
      setStatus(await api("/api/auth/lock-key", { method: "DELETE" }));
      setMsg({ ok: "Tecla de acesso desligada: espaço, clique e palmas voltam a começar a verificação." });
      changed();
    } catch (err) {
      setMsg({ error: err.message });
    }
  };

  const btn = "rounded border border-cyan-500/40 bg-black/40 px-3 py-1.5 text-[11px] font-['Orbitron'] text-cyan-200";
  return (
    <Section title="TECLA DE ACESSO E AVATAR">
      <p className="text-[12px] text-cyan-100/80">
        Com a tecla de acesso, o JARVIS só olha o seu rosto depois que a tecla escolhida é apertada no teclado do PC:
        é preciso saber a tecla <b>e</b> ter o rosto. Seis teclas erradas seguidas viram uma tentativa no relatório de
        segurança (com a foto) e a tecla fica 2 minutos sem valer. O PIN continua funcionando.
      </p>
      <div className="lks-capture">
        {status?.enabled ? <kbd aria-label={`Tecla atual: ${keyLabel(status.code)}`}>{keyLabel(status.code)}</kbd> : <span className="text-[12px] text-cyan-100/60">Desligada</span>}
        <button type="button" className={btn} onClick={() => { setMsg(null); setCapturing(true); }} disabled={capturing}>
          {capturing ? "APERTE A TECLA… (Esc cancela)" : status?.enabled ? "TROCAR A TECLA" : "ESCOLHER A TECLA"}
        </button>
        {status?.enabled && <button type="button" className={btn} onClick={turnOff}>DESLIGAR</button>}
      </div>
      {msg && <p className={`text-[12px] ${msg.error ? "text-rose-300" : "text-emerald-300"}`} role="status">{msg.error || msg.ok}</p>}
      <Toggle
        label="Avatar holográfico na tela de bloqueio"
        hint="O PC transforma a foto do seu rosto num holograma (fica salvo em data/avatar_holo.png e nunca sai do PC) e ele aparece no centro do bloqueio. Por voz: 'coloca meu avatar na tela de bloqueio'."
        checked={Boolean(prefs.lock_avatar_enabled)}
        onChange={(v) => onPatch({ lock_avatar_enabled: v })}
      />
      <Note>Quem estiver na frente do PC verá o holograma do seu rosto. Se preferir não mostrar, deixe o avatar desligado.</Note>
    </Section>
  );
}

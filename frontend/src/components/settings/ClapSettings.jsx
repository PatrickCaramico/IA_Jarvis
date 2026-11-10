import { useState } from "react";
import useClapDetector, { CLAP_STATUS_TEXT } from "../../hooks/useClapDetector.js";
import { Note, Section, SelectRow, Toggle } from "./SettingsControls.jsx";

// Aba "Palmas" (seções 14 e 16): ativação por 2 palmas, sensibilidade, escopo e modo de teste.
export default function ClapSettings({ prefs, onPatch }) {
  const [testing, setTesting] = useState(false);
  const [count, setCount] = useState(0);
  const [flash, setFlash] = useState(0);
  const sensitivity = prefs.clap_sensitivity ?? 5;
  const microphoneId = typeof window !== "undefined" ? localStorage.getItem("jarvis.microphone.id") || "" : "";

  const test = useClapDetector({
    enabled: testing,
    deviceId: microphoneId,
    sensitivity,
    cooldownMs: 1500,
    onDoubleClap: () => {
      setCount((n) => n + 1);
      setFlash((n) => n + 1);
    },
  });
  const meter = Math.min(100, Math.round(test.level * 600));
  const insecure = typeof window !== "undefined" && !window.isSecureContext;

  return (
    <div className="space-y-3">
      <Section title="ATIVAÇÃO POR PALMAS">
        <Toggle
          label="Bater 2 palmas para ativar"
          hint="Na tela de bloqueio, 2 palmas iniciam o escaneamento facial. A palma nunca libera o JARVIS sozinha."
          checked={prefs.clap_wake_enabled}
          onChange={(v) => onPatch({ clap_wake_enabled: v })}
        />
        <div className="py-1.5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-['Orbitron'] text-cyan-200">Sensibilidade</span>
            <span className="text-xs font-['Orbitron'] text-cyan-100">{sensitivity}</span>
          </div>
          <input
            type="range"
            min="1"
            max="10"
            value={sensitivity}
            onChange={(e) => onPatch({ clap_sensitivity: Number(e.target.value) }, { quiet: true })}
            className="w-full accent-cyan-400"
            aria-label="Sensibilidade das palmas"
          />
          <Note>1 = só palmas fortes · 10 = palmas fracas também (mais risco de disparos indevidos).</Note>
        </div>
        <Toggle
          label="Entrar sozinho após reconhecer o rosto"
          hint="Depois do acesso autorizado, entra na central em ~1,5 s com o microfone já escolhido."
          checked={prefs.clap_auto_enter}
          onChange={(v) => onPatch({ clap_auto_enter: v })}
        />
        <Toggle
          label="Verificar o rosto a cada palma (também depois de logado)"
          hint="Na central, 2 palmas abrem um painel com a câmera ao vivo e fazem a reverificação."
          checked={prefs.clap_scope !== "lock"}
          onChange={(v) => onPatch({ clap_scope: v ? "always" : "lock" })}
        />
        <Toggle
          label="Bloquear a tela se não reconhecer"
          hint="Vale para a reverificação por palma com a central aberta."
          checked={prefs.clap_relock_on_fail}
          disabled={prefs.clap_scope === "lock"}
          onChange={(v) => onPatch({ clap_relock_on_fail: v })}
        />
        <Note tone="warn">
          Com o recurso ligado, o navegador mostra o ícone de microfone em uso na tela de bloqueio (e na central,
          se a verificação a cada palma estiver ativa). A câmera acende a cada verificação. Nenhum áudio é gravado.
        </Note>
        {insecure && <Note tone="warn">Palmas indisponíveis nesta conexão: o microfone só funciona em localhost (127.0.0.1) ou HTTPS.</Note>}
      </Section>

      <Section title="MODO DE TESTE">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => { setTesting((v) => !v); setCount(0); }}
            className={`px-3 py-1.5 rounded text-xs font-['Orbitron'] border ${testing ? "border-emerald-400 bg-emerald-500/20 text-emerald-100" : "border-cyan-500/40 bg-black/40 text-cyan-200"}`}
          >
            {testing ? "PARAR TESTE" : "INICIAR TESTE"}
          </button>
          <span className="text-[11px] text-cyan-300/70">{testing ? (test.needsGesture ? "Clique uma vez para ativar o áudio" : CLAP_STATUS_TEXT[test.status]) : "Desligado"}</span>
        </div>
        <div className="mt-2 h-3 rounded-full bg-black/60 border border-cyan-500/30 overflow-hidden" aria-label={`Nível do microfone ${meter}%`}>
          <div className="h-full bg-gradient-to-r from-cyan-500 to-emerald-400 transition-[width] duration-75" style={{ width: `${meter}%` }} />
        </div>
        <div className="flex items-center justify-between mt-2">
          <span className="text-xs text-cyan-200">Palmas duplas detectadas</span>
          <span key={flash} className={`font-['Orbitron'] text-lg text-white ${flash ? "clap-test-flash" : ""}`}>{count}</span>
        </div>
        <Note>Bata 2 palmas, fale, digite e faça barulho para conferir: só a palma dupla deve contar. Ajuste a sensibilidade acima.</Note>
      </Section>

      <SelectRow
        label="Escopo"
        value={prefs.clap_scope || "always"}
        onChange={(v) => onPatch({ clap_scope: v })}
        options={[["always", "A cada palma (bloqueio e central)"], ["lock", "Só na tela de bloqueio"]]}
      />
    </div>
  );
}

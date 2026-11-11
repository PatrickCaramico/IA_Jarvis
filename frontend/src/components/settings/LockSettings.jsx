import { useCallback, useEffect, useState } from "react";
import { Note, SaveStatus, Section, SelectRow, Toggle } from "./SettingsControls.jsx";

const CARD_LABELS = [
  ["clock", "Relógio e data"],
  ["weather", "Clima"],
  ["spotify", "Tocando agora (Spotify)"],
  ["fan_match", "Próximo jogo (Modo Torcedor)"],
  ["water", "Água de hoje"],
];

const RESULT_TEXT = { ok: "liberado", fail: "falhou", locked_out: "PIN bloqueado", enter: "entrou", exit: "saiu", lock: "bloqueou", pin_reset: "PIN redefinido" };
const METHOD_TEXT = { face: "rosto", pin: "PIN", clap: "palmas", wake: "palmas (JARVIS fechado)", guest: "visitante", auto: "bloqueio", voice: "voz" };

// Aba "Bloqueio" (seção 17 e Modo Sentinela).
export default function LockSettings({ api, prefs, onPatch }) {
  const [pinStatus, setPinStatus] = useState(null);
  const [currentPin, setCurrentPin] = useState("");
  const [newPin, setNewPin] = useState("");
  const [confirmPin, setConfirmPin] = useState("");
  const [pinMsg, setPinMsg] = useState(null);
  // V5.1 "Esqueci o PIN": "" | "scanning" (lendo o rosto) | "ready" (rosto confirmado: PIN novo sem o atual)
  const [resetMode, setResetMode] = useState("");
  const [log, setLog] = useState([]);
  const [showLog, setShowLog] = useState(false);
  const [wakeText, setWakeText] = useState((prefs.sentinel_wake_words || []).join(", "));
  const [playlist, setPlaylist] = useState(prefs.lock_intro_playlist_uri || "");
  const [fanPlaylist, setFanPlaylist] = useState(prefs.fan_intro_playlist_uri || "");

  const loadPin = useCallback(() => api("/api/auth/pin/status").then(setPinStatus).catch(() => {}), [api]);
  const loadLog = useCallback(() => api("/api/lock/log?limit=60").then((d) => setLog(d.entries || [])).catch(() => {}), [api]);

  useEffect(() => { loadPin(); }, [loadPin]);
  useEffect(() => { if (showLog) loadLog(); }, [showLog, loadLog]);

  const forgotPin = async () => {
    setPinMsg({ ok: "Olhe para a câmera do PC…" });
    setResetMode("scanning");
    try {
      const res = await api("/api/auth/verify", { method: "POST", body: JSON.stringify({ mode: "recheck", trigger: "button" }) });
      if (res.verified) {
        setResetMode("ready");
        setCurrentPin("");
        setPinMsg({ ok: "Rosto confirmado. Crie o PIN novo nos próximos 3 minutos." });
      } else {
        setResetMode("");
        setPinMsg({ error: "Não reconheci o rosto. Tente de novo com luz de frente, ou rode o Redefinir-PIN.bat no PC." });
      }
    } catch (err) {
      setResetMode("");
      setPinMsg({ error: err.message });
    }
  };

  const savePin = async () => {
    setPinMsg(null);
    if (!/^\d{4,8}$/.test(newPin)) return setPinMsg({ error: "O PIN deve ter de 4 a 8 dígitos." });
    if (newPin !== confirmPin) return setPinMsg({ error: "A confirmação não confere." });
    try {
      const res = resetMode === "ready"
        ? await api("/api/auth/pin/reset", { method: "POST", body: JSON.stringify({ new_pin: newPin }) })
        : await api("/api/auth/pin/set", {
          method: "POST",
          body: JSON.stringify({ new_pin: newPin, current_pin: pinStatus?.has_pin ? currentPin : null }),
        });
      setResetMode("");
      setPinMsg({ ok: res.weak ? "PIN salvo. Atenção: PIN fraco (ex.: 1234) reduz a segurança." : "PIN salvo." });
      setCurrentPin(""); setNewPin(""); setConfirmPin("");
      loadPin();
    } catch (err) {
      setPinMsg({ error: err.message });
    }
  };

  const removePin = async () => {
    setPinMsg(null);
    try {
      await api("/api/auth/pin", { method: "DELETE", body: JSON.stringify({ current_pin: currentPin }) });
      setPinMsg({ ok: "PIN removido." });
      setCurrentPin("");
      loadPin();
    } catch (err) {
      setPinMsg({ error: err.message });
    }
  };

  const toggleCard = (key, on) => {
    const cur = prefs.lock_cards || [];
    onPatch({ lock_cards: on ? [...cur, key] : cur.filter((c) => c !== key) });
  };

  const inputCls = "w-full rounded border border-cyan-500/30 bg-black/50 px-2 py-1.5 text-xs text-cyan-100";

  return (
    <div className="space-y-3">
      <Section title="PROTEÇÃO">
        <Toggle
          label="Bloqueio real no backend"
          hint="Com a tela bloqueada, tarefas, memória, finanças, controle do PC e demais rotas pessoais respondem 403. Desligado, o bloqueio volta a ser só visual."
          checked={prefs.lock_backend_enforce !== false}
          onChange={(v) => onPatch({ lock_backend_enforce: v })}
        />
        <Note>Sem foto de perfil e sem PIN não há como liberar, então nada é bloqueado. Se o backend reiniciar, a central volta para a tela de bloqueio.</Note>
      </Section>

      <Section title="PIN DE RESERVA">
        <div className="text-[11px] text-cyan-200/80">
          {pinStatus?.has_pin ? "PIN cadastrado." : "Nenhum PIN cadastrado."}
          {pinStatus?.locked_until ? " Bloqueado temporariamente por excesso de tentativas." : ""}
        </div>
        {pinStatus?.has_pin && resetMode !== "ready" && (
          <div className="flex gap-2">
            <input type="password" inputMode="numeric" maxLength={8} value={currentPin} onChange={(e) => setCurrentPin(e.target.value.replace(/\D/g, ""))}
              placeholder="PIN atual" className={inputCls} aria-label="PIN atual" />
            <button type="button" onClick={forgotPin} disabled={resetMode === "scanning"}
              className="shrink-0 rounded border border-amber-400/60 bg-amber-500/10 px-2 py-1.5 text-[11px] font-['Orbitron'] text-amber-200 disabled:opacity-50"
              title="Confirme o rosto e crie um PIN novo sem o atual">
              {resetMode === "scanning" ? "LENDO O ROSTO…" : "ESQUECI O PIN"}
            </button>
          </div>
        )}
        <div className="grid grid-cols-2 gap-2">
          <input type="password" inputMode="numeric" maxLength={8} value={newPin} onChange={(e) => setNewPin(e.target.value.replace(/\D/g, ""))}
            placeholder="Novo PIN (4 a 8 dígitos)" className={inputCls} aria-label="Novo PIN" />
          <input type="password" inputMode="numeric" maxLength={8} value={confirmPin} onChange={(e) => setConfirmPin(e.target.value.replace(/\D/g, ""))}
            placeholder="Confirmar" className={inputCls} aria-label="Confirmar PIN" />
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={savePin} className="flex-1 rounded border border-cyan-400/60 bg-cyan-500/20 py-1.5 text-[11px] font-['Orbitron'] text-cyan-100">
            {resetMode === "ready" ? "CRIAR PIN NOVO" : pinStatus?.has_pin ? "TROCAR PIN" : "CRIAR PIN"}
          </button>
          {pinStatus?.has_pin && resetMode !== "ready" && (
            <button type="button" onClick={removePin} className="rounded border border-rose-500/50 bg-rose-950/30 px-3 py-1.5 text-[11px] font-['Orbitron'] text-rose-200">
              REMOVER
            </button>
          )}
        </div>
        <SaveStatus status={pinMsg} />
        <Note tone="warn">O PIN dá o mesmo acesso do rosto. Evite PINs fracos como 1234. 5 erros bloqueiam o PIN por 5 min (dobra a cada novo bloqueio, até 30 min).</Note>
        <Note>Esqueceu? “Esqueci o PIN” confirma o seu rosto pela câmera do PC e libera um PIN novo sem o atual. Sem câmera, rode o Redefinir-PIN.bat na pasta do JARVIS.</Note>
      </Section>

      <Section title="AO ENTRAR">
        <SelectRow
          label="Resumo do dia"
          value={prefs.lock_daily_summary || "first_login"}
          onChange={(v) => onPatch({ lock_daily_summary: v })}
          options={[["first_login", "Só no 1º acesso do dia"], ["always", "Sempre"], ["off", "Desligado"]]}
        />
        <SelectRow
          label="Som de abertura"
          value={prefs.lock_intro_sound || "default"}
          onChange={(v) => onPatch({ lock_intro_sound: v })}
          options={[["default", "Padrão"], ["custom", "Meu arquivo (sounds/intro.mp3)"], ["off", "Desligado"]]}
        />
        <label className="block text-xs font-['Orbitron'] text-cyan-200 pt-1">Playlist do Spotify após a saudação</label>
        <input value={playlist} onChange={(e) => setPlaylist(e.target.value)} onBlur={() => onPatch({ lock_intro_playlist_uri: playlist.trim() })}
          placeholder="https://open.spotify.com/playlist/..." className={inputCls} aria-label="Playlist de abertura" />
        <label className="block text-xs font-['Orbitron'] text-cyan-200 pt-1">Playlist do Modo Torcedor</label>
        <input value={fanPlaylist} onChange={(e) => setFanPlaylist(e.target.value)} onBlur={() => onPatch({ fan_intro_playlist_uri: fanPlaylist.trim() })}
          placeholder="(opcional)" className={inputCls} aria-label="Playlist do Modo Torcedor" />
        <Note>A playlist exige Spotify conectado, conta Premium e um dispositivo ativo; se não der para tocar, o JARVIS ignora e mostra um aviso discreto. Nada toca no modo silencioso.</Note>
      </Section>

      <Section title="CARTÕES DA TELA DE BLOQUEIO">
        {CARD_LABELS.map(([key, label]) => (
          <Toggle key={key} label={label} checked={(prefs.lock_cards || []).includes(key)} onChange={(v) => toggleCard(key, v)} />
        ))}
        <Note>Nenhum cartão mostra agenda, tarefas, e-mails ou outros dados pessoais.</Note>
      </Section>

      <Section title="BLOQUEIO POR AUSÊNCIA">
        <SelectRow
          label="Bloquear após inatividade"
          value={String(prefs.lock_auto_relock_minutes ?? 0)}
          onChange={(v) => onPatch({ lock_auto_relock_minutes: Number(v) })}
          options={[["0", "Desligado"], ["5", "5 minutos"], ["10", "10 minutos"], ["15", "15 minutos"], ["30", "30 minutos"]]}
        />
        <Toggle
          label="Checar presença pela câmera antes de bloquear"
          hint="Checagem rápida (~1 s) só de detecção de rosto, sem comparar e sem salvar imagem. Bloqueia após 2 checagens sem rosto."
          checked={prefs.lock_presence_check}
          disabled={!prefs.lock_auto_relock_minutes}
          onChange={(v) => onPatch({ lock_presence_check: v })}
        />
      </Section>

      <Section title="MODO VISITANTE">
        <Toggle
          label='Mostrar o botão "Modo visitante"'
          hint="Visitantes veem só relógio, clima e música. Comandos pessoais são recusados e sair exige rosto ou PIN."
          checked={prefs.lock_guest_enabled}
          onChange={(v) => onPatch({ lock_guest_enabled: v })}
        />
      </Section>

      <Section title="MODO SENTINELA">
        <Toggle
          label="Tela de bloqueio em modo Sentinela"
          hint="Só o orbe e um aviso. O JARVIS escuta a palavra de ativação e responde hora, data, clima e afins; para mostrar algo, pede o escaneamento facial."
          checked={prefs.sentinel_enabled}
          onChange={(v) => onPatch({ sentinel_enabled: v })}
        />
        <Toggle
          label="Ouvir “Jarvis” com a central aberta"
          hint="Como a Alexa: diga “Jarvis, que horas são?” sem tocar no microfone. O microfone do navegador fica ligado enquanto a central está aberta e pausa enquanto o JARVIS fala."
          checked={prefs.hands_free_enabled !== false}
          onChange={(v) => onPatch({ hands_free_enabled: v })}
        />
        <Toggle
          label="Conversa contínua"
          hint="Depois de responder a um pedido de voz, o JARVIS fica 8 segundos ouvindo a próxima pergunta, sem precisar dizer “Jarvis” de novo."
          checked={prefs.follow_up_enabled !== false}
          onChange={(v) => onPatch({ follow_up_enabled: v })}
        />
        <label className="block text-xs font-['Orbitron'] text-cyan-200 pt-1">Palavras de ativação (separadas por vírgula)</label>
        <input value={wakeText} onChange={(e) => setWakeText(e.target.value)}
          onBlur={() => {
            const list = wakeText.split(",").map((w) => w.trim()).filter(Boolean);
            if (list.length) onPatch({ sentinel_wake_words: list });
          }}
          className={inputCls} aria-label="Palavras de ativação" />
        <Toggle label="Mostrar relógio e data" checked={prefs.sentinel_show_clock !== false} onChange={(v) => onPatch({ sentinel_show_clock: v })} />
        <Toggle label="Modo noturno (22h às 7h)" hint="Orbe mais escuro e voz mais baixa com a central bloqueada." checked={prefs.sentinel_night_dim !== false}
          onChange={(v) => onPatch({ sentinel_night_dim: v })} />
        <Note>O nome da IA também vale como palavra de ativação. A escuta usa o reconhecimento de voz do Chrome/Edge (precisa de internet) e só funciona com a página aberta em localhost.</Note>
      </Section>

      <Section title="HISTÓRICO DE ACESSOS">
        <Toggle
          label="Salvar miniatura de rosto não reconhecido"
          hint="Desligado por padrão. Guarda no máximo 20 miniaturas em data/intruders e apaga as com mais de 30 dias."
          checked={prefs.lock_save_failed_photo}
          onChange={(v) => onPatch({ lock_save_failed_photo: v })}
        />
        <div className="flex gap-2 pt-1">
          <button type="button" onClick={() => setShowLog((v) => !v)} className="flex-1 rounded border border-cyan-500/40 bg-black/40 py-1.5 text-[11px] font-['Orbitron'] text-cyan-200">
            {showLog ? "OCULTAR HISTÓRICO" : "VER HISTÓRICO"}
          </button>
          <button
            type="button"
            onClick={async () => {
              if (!window.confirm("Limpar o histórico de acessos (e as miniaturas salvas)?")) return;
              await api("/api/lock/log", { method: "DELETE" }).catch(() => {});
              setLog([]);
            }}
            className="rounded border border-rose-500/50 bg-rose-950/30 px-3 py-1.5 text-[11px] font-['Orbitron'] text-rose-200"
          >
            LIMPAR
          </button>
        </div>
        {showLog && (
          <ul className="max-h-48 overflow-y-auto text-[11px] text-cyan-100/90 divide-y divide-cyan-500/10">
            {log.length === 0 && <li className="py-1 text-cyan-400/60">Sem registros.</li>}
            {log.map((e, i) => (
              <li key={`${e.at}-${i}`} className="py-1 flex justify-between gap-2">
                <span>{new Date(e.at).toLocaleString("pt-BR")}</span>
                <span className={e.result === "ok" ? "text-emerald-300" : e.result === "fail" || e.result === "locked_out" ? "text-rose-300" : "text-cyan-300"}>
                  {METHOD_TEXT[e.method] || e.method} · {RESULT_TEXT[e.result] || e.result}
                  {e.score != null ? ` · ${(e.score * 100).toFixed(0)}%` : ""}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  );
}

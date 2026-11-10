import { useEffect, useState } from "react";
import { Note, SaveStatus, Section, Toggle } from "./SettingsControls.jsx";

// Aba "Automação" (4.2): gatilhos condicionais e protocolos.
const ACTION_LABELS = {
  open: "Abrir programa ou site",
  focus: "Modo foco (minutos)",
  focus_stop: "Parar o modo foco",
  silent: "Modo silencioso",
  volume: "Volume (0 a 100)",
  playlist: "Playlist do Spotify",
  say: "Falar no final",
};
const NUMBER_ACTIONS = new Set(["focus", "volume"]);

function NumberField({ label, value, min, max, onChange, suffix }) {
  return (
    <label className="flex items-center justify-between gap-3 py-1 text-xs font-['Orbitron'] text-cyan-200">
      <span>{label}</span>
      <span className="flex items-center gap-1">
        <input
          type="number"
          min={min}
          max={max}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="w-20 rounded border border-cyan-500/30 bg-black/60 px-2 py-1 text-right text-cyan-100"
          aria-label={label}
        />
        {suffix && <span className="text-[10px] text-cyan-400/70">{suffix}</span>}
      </span>
    </label>
  );
}

function TriggersSection({ api, onPatch }) {
  const [cfg, setCfg] = useState(null);
  useEffect(() => {
    api("/api/triggers").then((d) => setCfg(d.triggers)).catch(() => setCfg(null));
  }, [api]);
  if (!cfg) return <Section title="GATILHOS"><Note>Carregando…</Note></Section>;

  const change = (key, field, value) => {
    const next = { ...cfg, [key]: { ...cfg[key], [field]: value } };
    setCfg(next);
    onPatch({ triggers: next }, { quiet: field !== "enabled" }); // envia tudo: um ajuste não apaga outro
  };

  return (
    <Section title="GATILHOS (AVISOS AUTOMÁTICOS)">
      <Toggle label="Chuva amanhã" hint="Um aviso por dia, à noite, se a chance de chuva for alta."
        checked={cfg.rain_tomorrow.enabled} onChange={(v) => change("rain_tomorrow", "enabled", v)} />
      {cfg.rain_tomorrow.enabled && (
        <>
          <NumberField label="Avisar a partir das" value={cfg.rain_tomorrow.hour} min={6} max={23} suffix="h"
            onChange={(v) => change("rain_tomorrow", "hour", v)} />
          <NumberField label="Chance mínima de chuva" value={cfg.rain_tomorrow.min_probability} min={10} max={100} suffix="%"
            onChange={(v) => change("rain_tomorrow", "min_probability", v)} />
        </>
      )}
      <Toggle label="Jogo começando" hint="Só com o Modo Torcedor ligado."
        checked={cfg.match_soon.enabled} onChange={(v) => change("match_soon", "enabled", v)} />
      {cfg.match_soon.enabled && (
        <NumberField label="Minutos antes" value={cfg.match_soon.minutes} min={5} max={180} suffix="min"
          onChange={(v) => change("match_soon", "minutes", v)} />
      )}
      <Toggle label="Processador alto" hint="Avisa se ficar acima do limite por alguns minutos (no máximo 1 aviso a cada 30 min)."
        checked={cfg.cpu_high.enabled} onChange={(v) => change("cpu_high", "enabled", v)} />
      {cfg.cpu_high.enabled && (
        <>
          <NumberField label="Limite" value={cfg.cpu_high.threshold} min={50} max={100} suffix="%"
            onChange={(v) => change("cpu_high", "threshold", v)} />
          <NumberField label="Por quanto tempo" value={cfg.cpu_high.minutes} min={1} max={30} suffix="min"
            onChange={(v) => change("cpu_high", "minutes", v)} />
        </>
      )}
      <Toggle label="Água atrasada" hint="Compara com o ritmo esperado do dia (o lembrete fixo continua na aba Hidratação)."
        checked={cfg.water_behind.enabled} onChange={(v) => change("water_behind", "enabled", v)} />
      {cfg.water_behind.enabled && (
        <>
          <NumberField label="Diferença mínima" value={cfg.water_behind.deficit_ml} min={100} max={3000} suffix="ml"
            onChange={(v) => change("water_behind", "deficit_ml", v)} />
          <NumberField label="Só depois das" value={cfg.water_behind.after_hour} min={8} max={21} suffix="h"
            onChange={(v) => change("water_behind", "after_hour", v)} />
        </>
      )}
      <Note>Entre 22h e 7h os avisos só aparecem na tela, sem voz. Com a central bloqueada, o aviso é genérico.</Note>
    </Section>
  );
}

function StepRow({ step, actions, onChange, onRemove }) {
  const needsValue = step.action !== "focus_stop";
  return (
    <div className="flex flex-wrap items-center gap-1.5 rounded border border-cyan-500/15 bg-black/30 p-1.5">
      <select
        value={step.action}
        onChange={(e) => {
          const action = e.target.value;
          const value = action === "silent" ? true : NUMBER_ACTIONS.has(action) ? 30 : action === "focus_stop" ? null : "";
          onChange({ action, value });
        }}
        className="rounded border border-cyan-500/30 bg-black/60 p-1 text-[11px] text-cyan-100"
        aria-label="Ação"
      >
        {actions.map((a) => <option key={a} value={a}>{ACTION_LABELS[a] || a}</option>)}
      </select>
      {needsValue && step.action === "silent" && (
        <select value={step.value ? "on" : "off"} onChange={(e) => onChange({ ...step, value: e.target.value === "on" })}
          className="rounded border border-cyan-500/30 bg-black/60 p-1 text-[11px] text-cyan-100" aria-label="Silencioso">
          <option value="on">ligar</option>
          <option value="off">desligar</option>
        </select>
      )}
      {needsValue && NUMBER_ACTIONS.has(step.action) && (
        <input type="number" value={step.value ?? ""} min={0} max={step.action === "volume" ? 100 : 180}
          onChange={(e) => onChange({ ...step, value: Number(e.target.value) })}
          className="w-20 rounded border border-cyan-500/30 bg-black/60 px-2 py-1 text-[11px] text-cyan-100" aria-label="Valor" />
      )}
      {needsValue && ["open", "playlist", "say"].includes(step.action) && (
        <input value={step.value ?? ""} onChange={(e) => onChange({ ...step, value: e.target.value })}
          placeholder={step.action === "open" ? "ex.: obs, youtube" : step.action === "playlist" ? "link da playlist" : "frase"}
          className="min-w-0 flex-1 rounded border border-cyan-500/30 bg-black/60 px-2 py-1 text-[11px] text-cyan-100" aria-label="Valor" />
      )}
      <button type="button" onClick={onRemove} className="ml-auto text-[11px] text-rose-300 hover:text-rose-200" aria-label="Remover passo">✕</button>
    </div>
  );
}

function ProtocolsSection({ api, onPatch }) {
  const [data, setData] = useState(null);
  const [draft, setDraft] = useState({});
  const [status, setStatus] = useState(null);
  const [newName, setNewName] = useState("");

  const load = () => api("/api/protocols").then((d) => { setData(d); setDraft(d.protocols); }).catch((err) => setStatus({ error: err.message }));
  useEffect(() => { load(); }, [api]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!data) return <Section title="PROTOCOLOS"><Note>Carregando…</Note><SaveStatus status={status} /></Section>;

  const setSteps = (key, steps) => setDraft((cur) => ({ ...cur, [key]: { ...cur[key], steps } }));
  const save = async (next = draft) => {
    try {
      await onPatch({ protocols: next });
      setStatus({ ok: "Protocolos salvos." });
    } catch (err) {
      setStatus({ error: err.message });
    }
  };
  const run = async (key) => {
    try {
      const res = await api("/api/protocols/run", { method: "POST", body: JSON.stringify({ name: key }) });
      setStatus(res.ok ? { ok: res.reply } : { error: res.reply });
    } catch (err) {
      setStatus({ error: err.message });
    }
  };
  const add = () => {
    const label = newName.trim();
    if (!label) return;
    const key = label.toLowerCase();
    setDraft((cur) => ({ ...cur, [key]: { label, steps: [{ action: "say", value: `Protocolo ${label} ativo.` }] } }));
    setNewName("");
  };
  const remove = (key) => {
    const next = { ...draft };
    delete next[key];
    setDraft(next);
  };

  return (
    <Section title="PROTOCOLOS">
      <Note>Diga "protocolo" e o nome (ex.: "Jarvis, protocolo trabalho"). Os passos rodam em ordem; "Falar no final" é dito ao terminar.</Note>
      {data.using_defaults && <Note>Estes são exemplos. Ao salvar, viram os seus protocolos.</Note>}
      <div className="space-y-3 pt-1">
        {Object.entries(draft).map(([key, proto]) => (
          <div key={key} className="space-y-1.5 rounded border border-cyan-500/20 p-2">
            <div className="flex items-center justify-between gap-2">
              <strong className="text-xs font-['Orbitron'] text-cyan-100">{proto.label || key}</strong>
              <span className="flex gap-2 text-[11px]">
                <button type="button" onClick={() => run(key)} className="text-cyan-300 hover:text-white">▶ testar</button>
                <button type="button" onClick={() => remove(key)} className="text-rose-300 hover:text-rose-200">apagar</button>
              </span>
            </div>
            {proto.steps.map((step, i) => (
              <StepRow key={i} step={step} actions={data.actions}
                onChange={(s) => setSteps(key, proto.steps.map((old, j) => (j === i ? s : old)))}
                onRemove={() => setSteps(key, proto.steps.filter((_, j) => j !== i))} />
            ))}
            {proto.steps.length < 10 && (
              <button type="button" onClick={() => setSteps(key, [...proto.steps, { action: "open", value: "" }])}
                className="text-[11px] text-cyan-300 underline">+ passo</button>
            )}
          </div>
        ))}
      </div>
      <div className="flex gap-2 pt-2">
        <input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="nome do novo protocolo"
          className="flex-1 rounded border border-cyan-500/30 bg-black/50 px-2 py-1.5 text-xs text-cyan-100" aria-label="Nome do novo protocolo" />
        <button type="button" onClick={add} className="rounded border border-cyan-400/60 bg-cyan-500/10 px-3 text-[11px] font-['Orbitron'] text-cyan-100">CRIAR</button>
        <button type="button" onClick={() => save()} className="rounded border border-cyan-400/60 bg-cyan-500/20 px-3 text-[11px] font-['Orbitron'] text-cyan-100">SALVAR</button>
      </div>
      <SaveStatus status={status} />
    </Section>
  );
}

function RoutineSection({ api, prefs, onPatch }) {
  const [data, setData] = useState(null);
  const load = () => api("/api/routine").then(setData).catch(() => setData(null));
  useEffect(() => { load(); }, [api]); // eslint-disable-line react-hooks/exhaustive-deps
  const unmute = async () => {
    await api("/api/routine/unmute", { method: "POST" }).catch(() => {});
    load();
  };
  return (
    <Section title="SUGESTÕES PELA ROTINA">
      <Toggle label="Oferecer o que costumo fazer"
        hint="Se você repete uma ação (protocolo ou 'abre o...') no mesmo horário em 3 dias, o JARVIS pergunta se quer que ele faça. Nunca faz sem um 'sim'."
        checked={prefs?.routine_suggestions_enabled !== false} onChange={(v) => onPatch({ routine_suggestions_enabled: v })} />
      {data && data.habits.length > 0 && (
        <ul className="space-y-1 pt-1 text-[11px] text-cyan-200/80">
          {data.habits.map((h) => (
            <li key={h.key}>{h.muted ? "🔕 " : "• "}{h.text.replace(/^Senhor, o senhor /, "Você ")}</li>
          ))}
        </ul>
      )}
      {data && data.habits.length === 0 && <Note>Ainda não há hábitos suficientes ({data.events} ações anotadas).</Note>}
      {data && data.muted.length > 0 && (
        <button type="button" onClick={unmute} className="text-[11px] text-cyan-300 underline">reativar sugestões silenciadas</button>
      )}
    </Section>
  );
}

function NotificationsSection({ api, prefs, onPatch }) {
  const [info, setInfo] = useState(null);
  const enabled = Boolean(prefs?.notifications_enabled);
  useEffect(() => {
    if (!enabled) return undefined;
    const load = () => api("/api/notifications").then((d) => setInfo(d.status)).catch(() => {});
    load();
    const t = setTimeout(load, 25000); // o primeiro teste de leitura acontece em até 20 s
    return () => clearTimeout(t);
  }, [api, enabled]);
  return (
    <Section title="CENTRAL DE NOTIFICAÇÕES (EXPERIMENTAL)" tone="amber">
      <Toggle label="Mostrar notificações do Windows na HUD"
        hint="Precisa instalar backend/requirements-notificacoes.txt e liberar em Configurações do Windows > Privacidade > Notificações."
        checked={enabled} onChange={(v) => onPatch({ notifications_enabled: v })} />
      <Toggle label="Falar o título" hint="Por padrão o JARVIS diz só o aplicativo (ex.: 'Nova notificação do WhatsApp')."
        checked={prefs?.notifications_read_content} disabled={!enabled}
        onChange={(v) => onPatch({ notifications_read_content: v })} />
      {enabled && info && (
        <Note tone={info.available === false ? "warn" : "info"}>
          Status: {info.available === true ? "funcionando" : info.available === false ? info.reason : "verificando…"}
        </Note>
      )}
      <Note>No modo foco, entre 22h e 7h e com a central bloqueada, o JARVIS não fala notificações. O &quot;Não perturbe&quot; do próprio Windows não pode ser ligado por programa.</Note>
    </Section>
  );
}

export default function AutomationSettings({ api, prefs, onPatch, children }) {
  return (
    <div className="space-y-3">
      <TriggersSection api={api} onPatch={onPatch} />
      <ProtocolsSection api={api} onPatch={onPatch} />
      <RoutineSection api={api} prefs={prefs} onPatch={onPatch} />
      <NotificationsSection api={api} prefs={prefs} onPatch={onPatch} />
      <Section title="LEITURA DE TELA">
        <Toggle label='"O que é isso na tela?"'
          hint="Captura a tela só quando você pede e manda a imagem para a IA configurada. Nada é salvo; não funciona com a central bloqueada."
          checked={prefs?.screen_assist_enabled !== false} onChange={(v) => onPatch({ screen_assist_enabled: v })} />
      </Section>
      {children}
    </div>
  );
}

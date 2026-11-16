import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import RoboAvatar, { DEFAULT_AVATAR, EXPRESSIONS, WARDROBE } from "./RoboAvatar.jsx";
import NowPlaying, { useNowPlaying } from "./NowPlaying.jsx";
import { useConversationLog } from "./HudLayout.jsx";
import { DESK_COLORS, FUNCTIONS, greeting, hexToRgb, isLight, stateText } from "../utils/desk.js";
import { IS_DESKTOP_APP } from "../utils/device.js";
import { checkForUpdate, saveUpdateResult } from "../utils/updateCheck.js";
import { APP_VERSION } from "../utils/version.js";
import { watchNewBuild } from "../utils/newBuild.js";
import { useLiteMode } from "../utils/lite.js";
import { useGroqVoice } from "../utils/voiceRecord.js";
import { startPacman, usePoke } from "../utils/poke.js";
import "../desk.css";

// V8.0: MODO DESK (ideia 6): o JARVIS como app de assistente pessoal. Barra lateral com o avatar robô, Início,
// Conversa, Memória, Tarefas, Lembretes, Hábitos, Timers, Música, Copiados, Rotinas, Meu PC e Configurações.
// Usa o JARVIS de sempre por trás (mesmas rotas); o botão 🖥 MODO DESK troca de volta para a central clássica.

const MemoryMap = lazy(() => import("./DeskMemoryMap.jsx"));

const NAV = [
  ["inicio", "⌂", "Início"], ["conversa", "💬", "Conversa"], ["memoria", "✳", "Memória"], ["tarefas", "☰", "Tarefas"],
  ["lembretes", "🔔", "Lembretes"], ["missoes", "🎯", "Missões"], ["habitos", "◆", "Hábitos"], ["timers", "⏱", "Timers"], ["musica", "♫", "Música"],
  ["copiados", "⧉", "Copiados"], ["rotinas", "⚡", "Rotinas"], ["meupc", "🖥", "Meu PC"],
];
const SETTINGS = [
  ["Assistente", [["personalizar", "🎨", "Personalizar"], ["cerebro", "🧠", "Cérebro (IA)"], ["funcoes", "🧩", "Funções"], ["voz", "🎙", "Voz"], ["ilha", "▭", "Ilha"], ["atualizar", "⬆", "Atualizações"]]],
  ["Conexões", [["celular", "📱", "Celular e agendas"], ["rosto", "🙂", "Proteção com rosto"], ["atalhos", "⌘", "Atalhos"]]],
];

function useLoad(api, path, deps = []) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const load = useCallback(() => {
    api(path).then((d) => { setData(d); setErr(""); }).catch((e) => setErr(e.message || "Não consegui carregar."));
  }, [api, path]);
  useEffect(() => { load(); }, [load, ...deps]); // eslint-disable-line react-hooks/exhaustive-deps
  return [data, load, setData, err];
}

function Card({ title, icon, right, children, className = "" }) {
  return (
    <section className={`dk-card ${className}`}>
      {(title || right) && <header>{icon && <span className="dk-card-ico">{icon}</span>}<h3>{title}</h3>{right}</header>}
      {children}
    </section>
  );
}

function ChatBox({ log, send, busy, onMic, listening, interim, compact = false }) {
  const [text, setText] = useState("");
  const endRef = useRef(null);
  const msgs = log.filter((m) => m.role === "user" || m.role === "jarvis" || m.role === "error").slice(compact ? -6 : -60);
  useEffect(() => { endRef.current?.scrollIntoView({ block: "end" }); }, [msgs.length]);
  const submit = (e) => {
    e.preventDefault();
    const t = text.trim();
    if (!t) return;
    send(t);
    setText("");
  };
  return (
    <div className={`dk-chat${compact ? " is-compact" : ""}`}>
      <div className="dk-msgs" aria-live="polite">
        {msgs.length === 0 && <p className="dk-muted">Nenhuma conversa ainda. Escreva abaixo ou toque no microfone.</p>}
        {msgs.map((m) => (
          <p key={m.id} className={`dk-msg is-${m.role}`}>{m.text}</p>
        ))}
        {listening && <p className="dk-msg is-user is-live">{interim || "Ouvindo…"}</p>}
        <div ref={endRef} />
      </div>
      {IS_DESKTOP_APP && <p className="dk-muted dk-hint">🎙 Toque no microfone e fale (a Groq entende), diga "Jarvis, …" ou escreva aqui.</p>}
      <form className="dk-input" onSubmit={submit}>
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Escreva ou fale com o JARVIS…" aria-label="Mensagem para o JARVIS" disabled={busy && false} />
        <button type="submit" className="dk-icon-btn" disabled={!text.trim()} aria-label="Enviar">➤</button>
        <button type="button" className={`dk-mic${listening ? " is-on" : ""}`} onClick={onMic} aria-label={listening ? "Parar de ouvir" : "Falar"}>🎙</button>
      </form>
    </div>
  );
}

// ------------------------------------------------------------------ seções
function Home({ api, ctx, avatar, tema, setSection }) {
  const [tasks] = useLoad(api, "/api/tasks");
  const [rems] = useLoad(api, "/api/reminders?only_pending=true");
  const [habits] = useLoad(api, "/api/desk/habits");
  const pend = (tasks?.tasks || []).filter((t) => !t.concluida).length;
  return (
    <div className="dk-home">
      {ctx.updateInfo && (
        <button type="button" className="dk-update-banner" onClick={() => setSection("atualizar")}>
          ⬆ Tem versão nova do {ctx.aiName}{ctx.updateInfo.latest ? ` (${ctx.updateInfo.latest})` : ""}. Toque para atualizar.
        </button>
      )}
      <Card className="dk-hero">
        <RoboAvatar avatar={avatar} tema={tema} state={ctx.orbState} size={96} />
        <div>
          {tema && <span className="dk-pill dk-theme-pill">🎉 Tema: {tema.nome}</span>}
          <h2>{greeting(new Date())}, {ctx.userName || "senhor"}!</h2>
          <p>Escreva, fale, ou diga "{ctx.aiName}, …"</p>
          <div className="dk-row">
            <button type="button" className="dk-btn is-main" onClick={ctx.onToggleMic}>🎙 Falar com o {ctx.aiName}</button>
            <button type="button" className="dk-btn" onClick={() => setSection("conversa")}>💬 Conversar</button>
          </div>
        </div>
        <LevelBox level={ctx.level} />
      </Card>
      <div className="dk-home-grid">
        <Card title="Conversa" icon="💬" className="dk-span2">
          <ChatBox log={ctx.log} send={ctx.send} onMic={ctx.onToggleMic} listening={ctx.listening} interim={ctx.interim} compact />
        </Card>
        <Card title="Missões de hoje" icon="🎯" right={ctx.missions && <span className="dk-pill">🔥 {ctx.missions.ofensiva.atual}</span>} className="dk-span2">
          <MissionList api={api} data={ctx.missions} onChange={ctx.setMissions} compact />
          <button type="button" className="dk-link" onClick={() => setSection("missoes")}>Ver missões e desafio da semana →</button>
        </Card>
        <Card title="Música" icon="♫"><MusicNow api={api} send={ctx.send} /></Card>
        <button type="button" className="dk-stat" onClick={() => setSection("lembretes")}><b>{(rems?.reminders || []).length}</b><span>lembretes</span></button>
        <button type="button" className="dk-stat" onClick={() => setSection("tarefas")}><b>{pend}</b><span>tarefas</span></button>
        <button type="button" className="dk-stat" onClick={() => setSection("habitos")}><b>{habits ? `${habits.feitos_hoje}/${habits.total}` : "—"}</b><span>hábitos hoje</span></button>
      </div>
    </div>
  );
}

function LevelBox({ level }) {
  if (!level) return null;
  return (
    <div className="dk-level" title={`${level.xp} XP no total`}>
      <small>NÍVEL {level.nivel}</small>
      <div className="dk-bar"><b style={{ width: `${level.pct}%` }} /></div>
      <span>{level.no_nivel}/{level.para_subir} XP</span>
    </div>
  );
}

// V8.1 (ideia 7): missões do dia, desafio da semana e ofensiva
const MISSION_KIND = { uso: ["⚡", "Usar o JARVIS"], sobre: ["💭", "Sobre você"], bem: ["🌿", "Bem-estar"], semana: ["🏆", "Desafio da semana"] };

function MissionRow({ api, m, onChange, cloud }) {
  const [text, setText] = useState("");
  const [msg, setMsg] = useState("");
  const [ico, kind] = MISSION_KIND[m.tipo] || ["🎯", ""];
  const run = async (path, body) => {
    try {
      const r = await api(path, { method: "POST", body: body ? JSON.stringify(body) : undefined });
      onChange?.(r.missoes || r);
      setMsg("");
    } catch (err) {
      setMsg(err.message);
    }
  };
  const pct = Math.min(100, Math.round(((m.progresso || 0) / (m.meta || 1)) * 100));
  return (
    <div className={`dk-mission is-${m.tipo}${m.feita ? " is-done" : ""}`}>
      <span className="dk-mission-ico" aria-hidden="true">{m.feita ? "✓" : ico}</span>
      <div className="dk-mission-body">
        <small>{kind} · +{m.xp} XP</small>
        <b>{m.texto}</b>
        {!m.feita && (m.tipo === "uso" || m.tipo === "semana") && m.meta > 1 && (
          <div className="dk-bar is-thin" aria-label={`${m.progresso} de ${m.meta}`}><b style={{ width: `${pct}%` }} /><span>{m.progresso}/{m.meta}</span></div>
        )}
        {!m.feita && m.tipo === "sobre" && !cloud && (
          <form className="dk-add" onSubmit={(e) => { e.preventDefault(); if (text.trim()) run("/api/desk/missions/answer", { id: m.id, resposta: text.trim() }); }}>
            <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Sua resposta (vai para a memória)" aria-label={m.texto} maxLength={300} />
            <button type="submit" className="dk-btn is-main" disabled={!text.trim()}>➤</button>
          </form>
        )}
        {!m.feita && m.tipo === "sobre" && cloud && <small className="dk-muted">Responda no PC (vai para a memória).</small>}
        {!m.feita && m.tipo === "uso" && m.meta === 1 && <small className="dk-muted">Completa sozinha quando você fizer.</small>}
        {msg && <p className="dk-err" role="alert">{msg}</p>}
      </div>
      {!m.feita && m.tipo === "bem" && <button type="button" className="dk-btn" onClick={() => run(`/api/desk/missions/${m.id}/done`)}>FEITO</button>}
    </div>
  );
}

function MissionList({ api, data, onChange, compact = false }) {
  if (!data) return <p className="dk-muted">Carregando missões…</p>;
  return (
    <div className="dk-missions">
      {data.itens.map((m) => <MissionRow key={m.id} api={api} m={m} onChange={onChange} cloud={data.cloud} />)}
      {!compact && data.semana && <MissionRow api={api} m={data.semana} onChange={onChange} cloud={data.cloud} />}
    </div>
  );
}

function Streak({ of }) {
  if (!of) return null;
  return (
    <div className="dk-streak">
      <span className={`dk-flame${of.feita_hoje ? " is-lit" : ""}`} aria-hidden="true">🔥</span>
      <div>
        <b>{of.atual} {of.atual === 1 ? "dia" : "dias"} de ofensiva</b>
        <small>Recorde: {of.recorde} · {of.feita_hoje ? "hoje já conta ✓" : "faça 1 missão hoje para manter"}</small>
      </div>
      <div className="dk-shields" title="Protetores: seguram a ofensiva se você perder um dia (ganha 1 por semana, guarda até 2)">
        {Array.from({ length: of.max_protetores || 2 }, (_, i) => <i key={i} className={i < of.protetores ? "is-on" : ""}>🛡</i>)}
      </div>
    </div>
  );
}

function Missions({ api, data, onChange }) {
  return (
    <div className="dk-stack">
      <Card title="Ofensiva" icon="🔥"><Streak of={data?.ofensiva} /></Card>
      <Card title="Missões de hoje" icon="🎯" right={data && <span className="dk-pill">{data.feitas}/{data.total} hoje</span>}>
        <p className="dk-muted">Todo dia aparecem 3 missões novas. Cada uma dá XP; o desafio da semana vale bem mais. Itens novos do guarda-roupa liberam por nível e por ofensiva.</p>
        <MissionList api={api} data={data} onChange={onChange} />
      </Card>
    </div>
  );
}

function Tasks({ api }) {
  const [data, load] = useLoad(api, "/api/tasks?include_completed=true");
  const [text, setText] = useState("");
  const add = async (e) => {
    e.preventDefault();
    if (!text.trim()) return;
    await api("/api/tasks", { method: "POST", body: JSON.stringify({ texto: text.trim() }) }).catch(() => {});
    setText("");
    load();
  };
  const list = data?.tasks || [];
  const open = list.filter((t) => !t.concluida);
  const done = list.filter((t) => t.concluida).slice(-8);
  return (
    <Card title="Tarefas" icon="☰" right={<small className="dk-muted">Toque no círculo para concluir</small>}>
      <form className="dk-add" onSubmit={add}><input value={text} onChange={(e) => setText(e.target.value)} placeholder="Nova tarefa e Enter" aria-label="Nova tarefa" /></form>
      <ul className="dk-list">
        {open.map((t) => (
          <li key={t.id}>
            <button type="button" className="dk-check" aria-label={`Concluir ${t.texto}`} onClick={() => api(`/api/tasks/${t.id}/complete`, { method: "PATCH" }).then(load).catch(() => {})} />
            <span>{t.texto}</span>
            <button type="button" className="dk-del" aria-label={`Apagar ${t.texto}`} onClick={() => api(`/api/tasks/${t.id}`, { method: "DELETE" }).then(load).catch(() => {})}>✕</button>
          </li>
        ))}
        {open.length === 0 && <li className="dk-muted">Nada pendente. 🎉</li>}
      </ul>
      {done.length > 0 && <><small className="dk-label">FEITAS</small><ul className="dk-list is-done">{done.map((t) => <li key={t.id}><span className="dk-check is-on" aria-hidden="true">✓</span><span>{t.texto}</span></li>)}</ul></>}
    </Card>
  );
}

function Reminders({ api }) {
  const [data, load] = useLoad(api, "/api/reminders?only_pending=true");
  const [text, setText] = useState("");
  const [when, setWhen] = useState("");
  const add = async (e) => {
    e.preventDefault();
    if (!text.trim() || !when) return;
    await api("/api/reminders", { method: "POST", body: JSON.stringify({ texto: text.trim(), data_hora: when.replace("T", " ") }) }).catch(() => {});
    setText("");
    setWhen("");
    load();
  };
  return (
    <Card title="Lembretes" icon="🔔">
      <form className="dk-add is-two" onSubmit={add}>
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Lembrar de…" aria-label="Texto do lembrete" />
        <input type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} aria-label="Quando" />
        <button type="submit" className="dk-btn is-main">＋</button>
      </form>
      <ul className="dk-list">
        {(data?.reminders || []).map((r) => (
          <li key={r.id}><span className="dk-pill">{String(r.data_hora || "").slice(5, 16).replace("-", "/")}</span><span>{r.texto}</span>
            <button type="button" className="dk-del" aria-label={`Apagar ${r.texto}`} onClick={() => api(`/api/reminders/${r.id}`, { method: "DELETE" }).then(load).catch(() => {})}>✕</button></li>
        ))}
        {(data?.reminders || []).length === 0 && <li className="dk-muted">Nenhum lembrete. Diga "me lembra de ligar pro cliente às 15h".</li>}
      </ul>
    </Card>
  );
}

function Habits({ api, onChange }) {
  const [data, , setData] = useLoad(api, "/api/desk/habits");
  const [form, setForm] = useState({ nome: "", icone: "", lembrete: "" });
  const [msg, setMsg] = useState("");
  const add = async (e) => {
    e.preventDefault();
    if (!form.nome.trim()) return;
    try {
      setData(await api("/api/desk/habits", { method: "POST", body: JSON.stringify(form) }));
      setForm({ nome: "", icone: "", lembrete: "" });
      setMsg("");
    } catch (err) {
      setMsg(err.message);
    }
  };
  const toggle = async (h) => {
    try {
      setData(await api(`/api/desk/habits/${h.id}/toggle`, { method: "POST", body: JSON.stringify({ feito: !h.hoje }) }));
      onChange?.();
    } catch (err) {
      setMsg(err.message);
    }
  };
  const remove = async (h) => {
    if (!window.confirm(`Apagar o hábito "${h.nome}"?`)) return;
    setData(await api(`/api/desk/habits/${h.id}`, { method: "DELETE" }).catch(() => data));
  };
  const days = ["D", "S", "T", "Q", "Q", "S", "S"];
  const today = new Date().getDay();
  return (
    <Card title="Hábitos" icon="◆" right={data && <span className="dk-pill">{data.feitos_hoje}/{data.total} hoje</span>}>
      <div className="dk-habits">
        {(data?.itens || []).map((h) => (
          <div key={h.id} className={`dk-habit${h.hoje ? " is-done" : ""}`}>
            <button type="button" className="dk-habit-main" onClick={() => toggle(h)} aria-pressed={h.hoje}>
              <span className="dk-habit-ico">{h.icone || "✓"}</span>
              <span className="dk-habit-txt"><b>{h.nome}</b><small>🔥 {h.sequencia} {h.sequencia === 1 ? "dia" : "dias"}{h.lembrete ? ` · ⏰ ${h.lembrete}` : ""}</small></span>
              <span className="dk-habit-box">{h.hoje ? "✓" : ""}</span>
            </button>
            <div className="dk-week" aria-label="Últimos 7 dias">
              {h.semana.map((v, i) => <i key={i} className={v ? "is-on" : ""} title={days[(today - 6 + i + 7) % 7]}>{days[(today - 6 + i + 7) % 7]}</i>)}
            </div>
            <button type="button" className="dk-del" onClick={() => remove(h)} aria-label={`Apagar ${h.nome}`}>✕</button>
          </div>
        ))}
        {data && data.itens.length === 0 && <p className="dk-muted">Crie seu primeiro hábito: beber água, ler, treinar… Depois é só dizer "marquei o treino de hoje".</p>}
      </div>
      {!data?.cloud && (
        <form className="dk-add is-three" onSubmit={add}>
          <input value={form.icone} onChange={(e) => setForm({ ...form, icone: e.target.value })} placeholder="📚" aria-label="Ícone" maxLength={4} />
          <input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} placeholder="Novo hábito (ex.: Ler 10 páginas)" aria-label="Nome do hábito" />
          <input type="time" value={form.lembrete} onChange={(e) => setForm({ ...form, lembrete: e.target.value })} aria-label="Lembrete (opcional)" />
          <button type="submit" className="dk-btn is-main">＋</button>
        </form>
      )}
      {msg && <p className="dk-err" role="alert">{msg}</p>}
    </Card>
  );
}

function fmtSecs(s) {
  const m = Math.floor(s / 60);
  return m >= 60 ? `${Math.floor(m / 60)}h${String(m % 60).padStart(2, "0")}` : `${m}:${String(s % 60).padStart(2, "0")}`;
}

function Timers({ api, send }) {
  const [data, load] = useLoad(api, "/api/timers");
  useEffect(() => {
    const t = setInterval(load, 1000);
    return () => clearInterval(t);
  }, [load]);
  return (
    <Card title="Timers" icon="⏱">
      <div className="dk-row is-wrap">
        {[1, 5, 10, 25, 45].map((m) => <button type="button" key={m} className="dk-btn" onClick={() => send(`timer de ${m} ${m === 1 ? "minuto" : "minutos"}`)}>＋ {m} min</button>)}
      </div>
      <div className="dk-timers">
        {(data?.timers || []).map((t) => {
          const pct = t.total_seconds ? (t.seconds_left / t.total_seconds) * 100 : 0;
          return (
            <div key={t.id} className="dk-timer" style={{ "--p": pct }}>
              <b>{fmtSecs(t.seconds_left)}</b><small>{t.label || "timer"}</small>
            </div>
          );
        })}
        {(data?.timers || []).length === 0 && <p className="dk-muted">Nenhum timer rodando. Diga "timer de 10 minutos para a pizza".</p>}
      </div>
    </Card>
  );
}

// o cartão do Spotify quando algo toca; senão, um convite para tocar
function MusicNow({ api, send }) {
  const { track } = useNowPlaying(api);
  if (track && (track.state === "playing" || track.state === "paused")) return <NowPlaying api={api} variant="lock" controls />;
  return (
    <div className="dk-music-empty">
      <span>Nada tocando agora.</span>
      <button type="button" className="dk-btn is-main" onClick={() => send("toca minha playlist")}>▶ TOCAR MINHA PLAYLIST</button>
    </div>
  );
}

function Music({ api, send }) {
  return (
    <Card title="Música" icon="♫">
      <MusicNow api={api} send={send} />
      <div className="dk-row is-wrap">
        {["toca minha playlist", "próxima música", "pausa a música", "aumenta o volume", "abaixa o volume"].map((c) => (
          <button type="button" key={c} className="dk-btn" onClick={() => send(c)}>"{c}"</button>
        ))}
      </div>
    </Card>
  );
}

function Clips({ api }) {
  const [data, load, setData] = useLoad(api, "/api/desk/clips");
  const [copied, setCopied] = useState("");
  useEffect(() => {
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [load]);
  const copy = async (c) => {
    try {
      await navigator.clipboard.writeText(c.texto);
      setCopied(c.id);
      setTimeout(() => setCopied(""), 1500);
    } catch {
      setCopied("");
    }
  };
  if (data?.cloud) return <Card title="Copiados" icon="⧉"><p className="dk-muted">Os Copiados ficam só no PC (por privacidade). Abra o Modo Desk no computador.</p></Card>;
  return (
    <Card title="Copiados" icon="⧉" right={(
      <div className="dk-row">
        <button type="button" className="dk-btn" onClick={async () => setData(await api("/api/desk/clips/pause", { method: "POST", body: JSON.stringify({ pausado: !data?.pausado }) }))}>{data?.pausado ? "▶ RETOMAR" : "❚❚ PAUSAR"}</button>
        <button type="button" className="dk-btn is-danger" onClick={async () => { if (window.confirm("Apagar todo o histórico de copiados?")) setData(await api("/api/desk/clips", { method: "DELETE" })); }}>🗑 LIMPAR</button>
      </div>
    )}>
      <p className="dk-muted">O que você copia no PC (Ctrl+C) aparece aqui. Fica só neste PC; o que parece senha, cartão ou código não é guardado.</p>
      <ul className="dk-clips">
        {(data?.itens || []).map((c) => (
          <li key={c.id}>
            <button type="button" className="dk-clip" onClick={() => copy(c)} title="Copiar de novo">
              <span>{c.texto.length > 220 ? `${c.texto.slice(0, 220)}…` : c.texto}</span>
              <small>{copied === c.id ? "✓ copiado" : c.em}</small>
            </button>
            <button type="button" className="dk-del" onClick={async () => setData(await api(`/api/desk/clips/${c.id}`, { method: "DELETE" }))} aria-label="Apagar">✕</button>
          </li>
        ))}
        {data && data.itens.length === 0 && <li className="dk-muted">{data.pausado ? "Pausado." : "Nada copiado ainda (os Copiados funcionam com o JARVIS rodando no Windows)."}</li>}
      </ul>
    </Card>
  );
}

function Routines({ api }) {
  const [data] = useLoad(api, "/api/protocols");
  const [msg, setMsg] = useState("");
  const list = Object.entries(data?.protocols || {});
  const run = async (key, label) => {
    setMsg(`Rodando ${label}…`);
    try {
      const r = await api("/api/protocols/run", { method: "POST", body: JSON.stringify({ name: key }) });
      setMsg(r.reply || `${label}: pronto.`);
    } catch (err) {
      setMsg(err.message);
    }
  };
  return (
    <Card title="Rotinas" icon="⚡">
      <div className="dk-grid3">
        {list.map(([key, p]) => (
          <button type="button" key={key} className="dk-tile" onClick={() => run(key, p.label || key)}>
            <b>{p.label || key}</b><small>{(p.steps || []).length} passos</small>
          </button>
        ))}
      </div>
      {msg && <p className="dk-muted" role="status">{msg}</p>}
      <p className="dk-muted">Diga "modo trabalho", "modo dormir"… As rotinas são editadas em Configurações › Protocolos.</p>
    </Card>
  );
}

function MyPc({ avatar }) {
  return (
    <Card title="Meu PC" icon="🖥">
      <div className="dk-pc">
        <div className="dk-pc-ring"><RoboAvatar avatar={avatar} state="processing" size={96} /></div>
        <div>
          <h3>Verificar o PC</h3>
          <p className="dk-muted">Memória, processador, programas que abrem com o PC, arquivos temporários, disco e lixeira. Mostra o que dá para melhorar e só limpa o que você aprovar.</p>
          <button type="button" className="dk-btn is-main" onClick={() => window.dispatchEvent(new CustomEvent("jarvis-open-optimizer"))}>▶ VERIFICAR AGORA</button>
          <button type="button" className="dk-btn" onClick={() => window.dispatchEvent(new CustomEvent("jarvis-open-diagnostic"))}>🩺 DIAGNÓSTICO DO JARVIS</button>
        </div>
      </div>
    </Card>
  );
}

// ------------------------------------------------------------------ configurações
// V8.1.5: ATUALIZAR no Modo Desk (antes só existia na central clássica e no bloqueio)
function Updates({ api, info, onUpdate, cfg, setCfg }) {
  const [state, setState] = useState(info ? { updateAvailable: true, count: info.count, latestVersion: info.latest, notes: (info.notes || []).join("\n") } : null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  useEffect(() => {
    if (info) setState({ updateAvailable: true, count: info.count, latestVersion: info.latest, notes: (info.notes || []).join("\n") });
  }, [info]);
  const check = async () => {
    setBusy(true);
    setMsg("");
    try {
      const r = await checkForUpdate(api);
      saveUpdateResult(r);
      setState(r);
      window.dispatchEvent(new CustomEvent("jarvis-update-check", { detail: r }));
    } catch (err) {
      setMsg(err.message || "Não consegui conferir.");
    } finally {
      setBusy(false);
    }
  };
  const notes = (state?.notes || "").split("\n").filter(Boolean).slice(0, 8);
  return (
    <Card title="Atualizações" icon="⬆" right={<span className="dk-pill">versão {APP_VERSION}</span>}>
      {state?.updateAvailable ? (
        <div className="dk-update is-new">
          <b>⬆ Versão nova disponível{state.latestVersion ? `: ${state.latestVersion}` : ""}{state.count ? ` (${state.count} ${state.count === 1 ? "mudança" : "mudanças"})` : ""}</b>
          {notes.length > 0 && <ul>{notes.map((n) => <li key={n}>{n}</li>)}</ul>}
          {onUpdate ? <button type="button" className="dk-btn is-main" onClick={onUpdate}>⬆ ATUALIZAR AGORA</button>
            : <p className="dk-muted">A atualização é feita no próprio PC do JARVIS.</p>}
          <small className="dk-muted">O JARVIS baixa a versão nova, avisa por voz e reinicia sozinho (leva uns segundos). O app para Windows e a ilha se atualizam sozinhos logo depois.</small>
        </div>
      ) : state ? <p className="dk-muted">✓ Você está na versão mais nova.</p> : <p className="dk-muted">Toque em VERIFICAR para conferir se tem versão nova.</p>}
      <div className="dk-row"><button type="button" className="dk-btn" onClick={check} disabled={busy}>{busy ? "Conferindo…" : "🔄 VERIFICAR AGORA"}</button></div>
      {cfg && (
        <label className="dk-toggle-row">
          <input type="checkbox" checked={cfg.atualizacao?.automatica !== false}
            onChange={async (e) => setCfg(await api("/api/desk", { method: "PATCH", body: JSON.stringify({ atualizacao: { automatica: e.target.checked } }) }).catch(() => cfg))} />
          <span>Atualizar sozinho: quando sair versão nova, o JARVIS atualiza num momento em que estiver parado (sem pasta nem CMD) e avisa na ilha.</span>
        </label>
      )}
      {msg && <p className="dk-err" role="alert">{msg}</p>}
    </Card>
  );
}

function Personalize({ api, cfg, setCfg, aiName, onRename }) {
  const [msg, setMsg] = useState("");
  const [name, setName] = useState(aiName);
  const av = { ...DEFAULT_AVATAR, ...(cfg?.avatar || {}) };
  const [tab, setTab] = useState(WARDROBE[0][0]);
  const status = cfg?.guarda_roupa || {};
  const save = async (patch) => {
    const optimistic = { ...cfg, ...patch, avatar: { ...av, ...(patch.avatar || {}) } };
    setCfg(optimistic);
    try {
      setCfg(await api("/api/desk", { method: "PATCH", body: JSON.stringify(patch) }));
      setMsg("");
    } catch (err) {
      setMsg(err.message);
    }
  };
  const Swatches = ({ value, onPick, colors }) => (
    <div className="dk-swatches">
      {colors.map((c) => <button type="button" key={c} style={{ background: c }} className={value === c ? "is-on" : ""} onClick={() => onPick(c)} aria-label={`Cor ${c}`} />)}
      <label className="dk-swatch-custom" title="Outra cor"><input type="color" value={value} onChange={(e) => onPick(e.target.value)} />🎨</label>
    </div>
  );
  return (
    <Card title={`Personalizar o ${aiName}`} icon="🎨">
      <div className="dk-perso">
        <div className="dk-perso-preview">
          <RoboAvatar avatar={av} tema={cfg?.tema} size={240} />
          {cfg?.tema && <p className="dk-muted dk-center">🎉 Tema de {cfg.tema.nome} por cima do seu visual (volta sozinho depois da data).</p>}
          <div className="dk-row is-wrap is-center">
            {EXPRESSIONS.map(([k, label]) => <button type="button" key={k} className={`dk-chip${av.expressao === k ? " is-on" : ""}`} onClick={() => save({ avatar: { expressao: k } })}>{label}</button>)}
          </div>
        </div>
        <div className="dk-perso-form">
          <label className="dk-field"><span>Nome</span>
            <span className="dk-row"><input value={name} onChange={(e) => setName(e.target.value)} maxLength={20} aria-label="Nome do assistente" />
              <button type="button" className="dk-btn" onClick={() => onRename(name)} disabled={!name.trim() || name === aiName}>SALVAR</button></span>
          </label>
          <div className="dk-field"><span>Corpo</span><Swatches value={av.corpo} colors={["#e8f4ff", "#ffffff", "#cbd5e1", "#fde68a", "#fecaca", "#bbf7d0", "#ddd6fe", "#1f2937"]} onPick={(c) => save({ avatar: { corpo: c } })} /></div>
          <div className="dk-field"><span>Visor</span><Swatches value={av.visor} colors={["#0b1220", "#111827", "#1e1b4b", "#052e16", "#3b0764", "#450a0a"]} onPick={(c) => save({ avatar: { visor: c } })} /></div>
          <div className="dk-field"><span>Olhos</span><Swatches value={av.olhos} colors={DESK_COLORS} onPick={(c) => save({ avatar: { olhos: c } })} /></div>
          <div className="dk-field"><span>Guarda-roupa</span>
            <div className="dk-tabs" role="tablist">
              {WARDROBE.map(([slot, label]) => <button type="button" role="tab" key={slot} aria-selected={tab === slot} className={tab === slot ? "is-on" : ""} onClick={() => setTab(slot)}>{label}</button>)}
            </div>
            <div className="dk-wardrobe" role="tabpanel">
              {(WARDROBE.find(([slot]) => slot === tab)?.[2] || []).map(([k, label]) => {
                const st = (status[tab] || []).find((i) => i.id === k);
                const locked = st && !st.liberado;
                return (
                  <button type="button" key={k} className={`dk-ward${av[tab] === k ? " is-on" : ""}${locked ? " is-locked" : ""}`} disabled={locked}
                    onClick={() => save({ avatar: { [tab]: k } })} title={locked ? `Libera com ${st.precisa}` : label}>
                    <RoboAvatar avatar={{ ...av, [tab]: k, ...(tab === "olhos_forma" ? { expressao: "feliz" } : {}) }} size={54} still />
                    <span>{label}</span>
                    {locked && <small>🔒 {st.precisa}</small>}
                  </button>
                );
              })}
            </div>
          </div>
          <label className="dk-field dk-toggle-row"><input type="checkbox" checked={av.temas !== false} onChange={(e) => save({ avatar: { temas: e.target.checked } })} />
            <span>Temas das datas (Natal, Halloween, Carnaval e dia de jogo do Palmeiras)</span></label>
          <label className="dk-field dk-toggle-row"><input type="checkbox" checked={av.antena !== false} onChange={(e) => save({ avatar: { antena: e.target.checked } })} />
            <span>Antena</span></label>
          <div className="dk-field dk-jeito"><span>Jeito de ser</span>
            <label className="dk-toggle-row"><input type="checkbox" checked={av.olhos_seguem !== false} onChange={(e) => save({ avatar: { olhos_seguem: e.target.checked } })} />
              <span>Olhos seguem o mouse</span></label>
            {av.olhos_seguem !== false && (
              <label className="dk-slider"><span>Velocidade</span>
                <input type="range" min="0.25" max="2" step="0.25" value={Number(av.olhos_vel) || 1}
                  onChange={(e) => save({ avatar: { olhos_vel: Number(e.target.value) } })} aria-label="Velocidade dos olhos" />
                <b>{(Number(av.olhos_vel) || 1).toFixed(2)}x</b></label>
            )}
          </div>
          <div className="dk-field dk-jeito"><span>Animações e desempenho</span>
            <label className="dk-toggle-row"><input type="checkbox" checked={av.piscar !== false} onChange={(e) => save({ avatar: { piscar: e.target.checked } })} />
              <span>Piscar sozinho</span></label>
            <label className="dk-toggle-row"><input type="checkbox" checked={av.brincadeiras !== false} onChange={(e) => save({ avatar: { brincadeiras: e.target.checked } })} />
              <span>Brincadeiras quando parado (olha em volta, boceja, cochila)</span></label>
            <label className="dk-slider"><span>Modo leve</span>
              <select value={cfg?.desempenho?.leve || "auto"} onChange={(e) => save({ desempenho: { leve: e.target.value } })} aria-label="Modo leve">
                <option value="auto">Automático (liga no notebook na bateria)</option>
                <option value="sim">Sempre ligado</option>
                <option value="nao">Desligado</option>
              </select></label>
            <small className="dk-muted">Modo leve: menos animações, avatar parado quando não fala e a ilha atualizando mais devagar.</small>
          </div>
          <div className="dk-field"><span>Cor do app</span><Swatches value={cfg?.cor || "#22d3ee"} colors={DESK_COLORS} onPick={(c) => save({ cor: c })} /></div>
          {msg && <p className="dk-err" role="alert">{msg}</p>}
        </div>
      </div>
    </Card>
  );
}

const PROVIDERS = [["groq", "Groq", "Muito rápida · grátis"], ["gemini", "Gemini", "Google · grátis"], ["openai", "ChatGPT", "OpenAI"], ["anthropic", "Claude", "Anthropic"]];
const PROVIDER_NAME = Object.fromEntries(PROVIDERS.map(([k, n]) => [k, n]));

// V8.2 (ideia 8): Cérebro (IA): "Automático grátis" (Groq principal, Gemini reserva, troca sozinho no limite) e
// conectar as IAs grátis colando a chave aqui (ela vai só para o .env deste PC e não aparece de novo).
function KeyCard({ api, p, onChange }) {
  const [key, setKey] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const connect = async (e) => {
    e.preventDefault();
    if (!key.trim()) return;
    setBusy(true);
    try {
      onChange(await api("/api/brain/key", { method: "POST", body: JSON.stringify({ provedor: p.id, chave: key.trim() }) }));
      setKey("");
      setMsg("");
    } catch (err) {
      setMsg(err.message);
    }
    setBusy(false);
  };
  const remove = async () => {
    if (!window.confirm(`Desconectar a ${p.nome}? A chave é apagada do PC.`)) return;
    try {
      onChange(await api(`/api/brain/key/${p.id}`, { method: "DELETE" }));
    } catch (err) {
      setMsg(err.message);
    }
  };
  if (p.conectada) {
    return (
      <div className="dk-keycard is-ok">
        <span className="dk-keyok">✓</span>
        <div><b>{p.nome} conectada</b><small>{p.papel}{p.descansando ? ` · no limite agora (volta em ${Math.ceil(p.descansando / 60)} min)` : ""}</small></div>
        <button type="button" className="dk-btn" onClick={remove}>Desconectar</button>
        {msg && <p className="dk-err" role="alert">{msg}</p>}
      </div>
    );
  }
  return (
    <div className="dk-keycard">
      <div className="dk-keyhead"><b>{p.nome}</b><span className="dk-pill is-free">Grátis</span></div>
      <small>{p.papel}</small>
      <ol className="dk-keysteps">
        <li>Entre com a sua conta em <a href={p.link} target="_blank" rel="noreferrer">{p.link.replace("https://", "")}</a> e clique em <b>Create API key</b> (Criar chave).</li>
        <li>Copie a chave e cole aqui (conecta sozinho):</li>
      </ol>
      <form className="dk-add" onSubmit={connect}>
        <input type="password" value={key} onChange={(e) => setKey(e.target.value)} placeholder="Cole a chave aqui" aria-label={`Chave da ${p.nome}`} autoComplete="off" spellCheck="false" />
        <button type="submit" className="dk-btn is-main" disabled={!key.trim() || busy}>{busy ? "…" : "CONECTAR"}</button>
      </form>
      <small className="dk-muted">🔒 A chave fica só no arquivo .env deste PC. Não vai para a nuvem e não aparece de novo aqui.</small>
      {msg && <p className="dk-err" role="alert">{msg}</p>}
    </div>
  );
}

function Brain({ api }) {
  const [st, load, setSt] = useLoad(api, "/api/brain");
  const [prefs, , setPrefs] = useLoad(api, "/api/prefs");
  const [test, setTest] = useState(null);
  const [busy, setBusy] = useState(false);
  const [pick, setPick] = useState(false);
  const cur = prefs?.llm_provider || st?.modo || "auto";
  const choose = async (p) => {
    try {
      setPrefs(await api("/api/prefs", { method: "PATCH", body: JSON.stringify({ llm_provider: p }) }));
      load();
    } catch (err) {
      setTest({ erro: err.message });
    }
  };
  const run = async () => {
    setBusy(true);
    setTest(null);
    try {
      setTest(await api("/api/desk/test-ai", { method: "POST", body: JSON.stringify({ provedor: cur }), timeout: 60_000 }));
      load();
    } catch (err) {
      setTest({ erro: err.message });
    }
    setBusy(false);
  };
  const provs = st?.provedores || [];
  const anyFree = provs.some((p) => p.conectada);
  const cd = prefs?.ai_cooldown;
  const banner = cur === "auto"
    ? (anyFree ? ["ok", "Funcionando no automático grátis", `${provs.filter((p) => p.conectada).map((p) => p.nome).join(" + ")}: quando uma chega no limite, a outra responde sozinha.`]
      : ["warn", "Conecte uma IA grátis", "Cole a chave da Groq (e a do Gemini, de reserva) logo abaixo."])
    : ["ok", `Funcionando com ${PROVIDER_NAME[cur] || cur}`, "Você escolheu a IA. O automático grátis troca sozinho no limite."];
  return (
    <Card title="Cérebro (IA)" icon="🧠">
      <div className={`dk-brainbanner is-${cd?.active ? "warn" : banner[0]}`}>
        <span className="dk-keyok">{cd?.active ? "⏳" : banner[0] === "ok" ? "✓" : "!"}</span>
        <div><b>{cd?.active ? "As IAs chegaram no limite" : banner[1]}</b><small>{cd?.active ? `Volta em ${Math.ceil((cd.remaining || 0) / 60)} min. Música, timers e abrir apps continuam funcionando.` : banner[2]}</small></div>
      </div>
      <small className="dk-label">1 · COMO O JARVIS PENSA</small>
      <div className="dk-grid2">
        <button type="button" className={`dk-tile${cur === "auto" ? " is-on" : ""}`} onClick={() => { choose("auto"); setPick(false); }} aria-pressed={cur === "auto"}>
          <b>⚡ Automático grátis <span className="dk-pill is-free">Recomendado</span></b>
          <small>Usa a Groq e o Gemini de graça e troca sozinho quando uma chega no limite.</small>{cur === "auto" && <i className="dk-tick">✓</i>}
        </button>
        <button type="button" className={`dk-tile${cur !== "auto" ? " is-on" : ""}`} onClick={() => setPick((v) => !v)} aria-expanded={pick}>
          <b>🎯 Eu escolho a IA</b><small>Groq, Gemini, ChatGPT ou Claude: fixa a que você quiser.</small>{cur !== "auto" && <i className="dk-tick">✓</i>}
        </button>
      </div>
      {(pick || cur !== "auto") && (
        <div className="dk-row is-wrap">
          {PROVIDERS.map(([k, label, sub]) => (
            <button type="button" key={k} className={`dk-chip${cur === k ? " is-on" : ""}`} onClick={() => choose(k)} title={sub}>{label}</button>
          ))}
        </div>
      )}
      <small className="dk-label">2 · CONECTAR AS IAS GRÁTIS</small>
      <div className="dk-keys">
        {provs.map((p) => <KeyCard key={p.id} api={api} p={p} onChange={setSt} />)}
        {!st && <p className="dk-muted">Carregando…</p>}
      </div>
      <small className="dk-label">TESTAR</small>
      <p className="dk-muted">Manda uma mensagem e mostra a resposta e o tempo.</p>
      <div className="dk-row"><button type="button" className="dk-btn is-main" onClick={run} disabled={busy}>{busy ? "Testando…" : "▶ TESTAR ESTA IA"}</button></div>
      {test && (test.erro ? <p className="dk-err" role="alert">{test.erro}</p>
        : <p className="dk-test"><b>{test.segundos}s</b> · {PROVIDER_NAME[test.provedor] || test.provedor} · {test.resposta}</p>)}
    </Card>
  );
}

function Functions({ api, send }) {
  const [q, setQ] = useState("");
  const list = FUNCTIONS.filter((f) => !q || `${f.titulo} ${f.exemplos.join(" ")}`.toLowerCase().includes(q.toLowerCase()));
  return (
    <Card title="Funções" icon="🧩" right={<input className="dk-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar função…" aria-label="Buscar função" />}>
      <p className="dk-muted">O que dá para falar com o JARVIS. Toque num exemplo para testar.</p>
      <div className="dk-grid2">
        {list.map((f) => (
          <div key={f.titulo} className="dk-func">
            <b>{f.icone} {f.titulo}</b>
            <div className="dk-row is-wrap">{f.exemplos.map((e) => <button type="button" key={e} className="dk-chip" onClick={() => send(e)}>"{e}"</button>)}</div>
          </div>
        ))}
      </div>
      <Shortcuts api={api} />
    </Card>
  );
}

function Shortcuts({ api }) {
  const [data, load] = useLoad(api, "/api/shortcuts");
  const [form, setForm] = useState({ name: "", app: "" });
  const add = async (e) => {
    e.preventDefault();
    if (!form.name.trim() || !form.app.trim()) return;
    const isUrl = /^https?:\/\//i.test(form.app.trim());
    await api("/api/shortcuts", { method: "POST", body: JSON.stringify({ name: form.name.trim(), apps: isUrl ? [] : [form.app.trim()], urls: isUrl ? [form.app.trim()] : [] }) }).catch(() => {});
    setForm({ name: "", app: "" });
    load();
  };
  const list = Object.entries(data?.shortcuts || {});
  return (
    <div className="dk-shortcuts">
      <small className="dk-label">MEUS ATALHOS ("abre o …")</small>
      <ul className="dk-list">
        {list.map(([name, s]) => (
          <li key={name}><b>"{name}"</b><span className="dk-muted">{[...(s.apps || []), ...(s.urls || [])].join(", ")}</span>
            <button type="button" className="dk-del" onClick={() => api(`/api/shortcuts/${encodeURIComponent(name)}`, { method: "DELETE" }).then(load).catch(() => {})} aria-label={`Apagar ${name}`}>✕</button></li>
        ))}
      </ul>
      <form className="dk-add is-two" onSubmit={add}>
        <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder='Nome (ex.: "meu trabalho")' aria-label="Nome do atalho" />
        <input value={form.app} onChange={(e) => setForm({ ...form, app: e.target.value })} placeholder="Programa (ex.: notepad) ou site (https://…)" aria-label="Programa ou site" />
        <button type="submit" className="dk-btn is-main">＋</button>
      </form>
    </div>
  );
}

function Island({ api, cfg, setCfg }) {
  const ilha = cfg?.ilha || {};
  const save = async (patch) => setCfg(await api("/api/desk", { method: "PATCH", body: JSON.stringify({ ilha: patch }) }).catch(() => cfg));
  return (
    <Card title="Ilha" icon="▭">
      <p className="dk-muted">A ilha é a barrinha no topo da tela do Windows (no app do JARVIS para Windows): mostra o JARVIS, a hora, a música tocando e as respostas.</p>
      <div className="dk-island-preview" data-size={ilha.tamanho || "media"}><RoboAvatar avatar={cfg?.avatar} size={22} /><i className="dk-dot" /><span>Highway to Hell · AC/DC</span></div>
      <label className="dk-toggle-row"><input type="checkbox" checked={ilha.ligada !== false} onChange={(e) => save({ ligada: e.target.checked })} /> Mostrar a ilha</label>
      <div className="dk-field"><span>Tamanho</span><div className="dk-row">{[["pequena", "Pequena"], ["media", "Média"], ["grande", "Grande"]].map(([k, l]) => <button type="button" key={k} className={`dk-chip${(ilha.tamanho || "media") === k ? " is-on" : ""}`} onClick={() => save({ tamanho: k })}>{l}</button>)}</div></div>
      <div className="dk-field"><span>Tamanho do painel aberto</span><div className="dk-row">{[["compacto", "Compacto"], ["medio", "Médio"], ["grande", "Grande"]].map(([k, l]) => <button type="button" key={k} className={`dk-chip${(ilha.painel || "medio") === k ? " is-on" : ""}`} onClick={() => save({ painel: k })}>{l}</button>)}</div></div>
      <label className="dk-slider"><span>Zoom do painel</span>
        <input type="range" min="0.7" max="1.4" step="0.05" value={Number(ilha.zoom) || 0.9} onChange={(e) => save({ zoom: Number(e.target.value) })} aria-label="Zoom do painel da ilha" />
        <b>{Math.round((Number(ilha.zoom) || 0.9) * 100)}%</b></label>
      <div className="dk-field"><span>Posição</span><div className="dk-row">
        <button type="button" className="dk-btn" onClick={() => save({ posicao: 0.5 })}>⟲ CENTRALIZAR</button>
        <small className="dk-muted">Ou arraste a ilha pelo topo para onde quiser.</small></div></div>
      <div className="dk-field"><span>Tecla para falar</span><div className="dk-row">{["PageDown", "F9", "Ctrl+Space"].map((k) => <button type="button" key={k} className={`dk-chip${ilha.atalho === k ? " is-on" : ""}`} onClick={() => save({ atalho: k })}>{k}</button>)}</div></div>
      <DownloadExe />
    </Card>
  );
}

export function DownloadExe({ compact = false }) {
  return (
    <a className={`dk-btn is-main dk-download${compact ? " is-compact" : ""}`} href="/api/desktop/app" onClick={(e) => { e.preventDefault(); window.dispatchEvent(new CustomEvent("jarvis-desktop-download")); }}>
      ⬇ APP PARA WINDOWS
    </a>
  );
}

function LinkCard({ title, icon, text, actions }) {
  return (
    <Card title={title} icon={icon}>
      <p className="dk-muted">{text}</p>
      <div className="dk-row is-wrap">{actions.map(([label, fn]) => <button type="button" key={label} className="dk-btn" onClick={fn}>{label}</button>)}</div>
    </Card>
  );
}

// ------------------------------------------------------------------ app
export default function DeskApp(props) {
  const { api, aiName = "JARVIS", userName = "", jarvisState = "idle", listening = false, interim = "", userText, response, responseCards, error,
    send, onToggleMic, onClassic, onLock, onOpenSettings, onOpenQr, onRename, updateInfo = null, onUpdate = null, embedded = false } = props;
  const [section, setSection] = useState(() => {
    try {
      return localStorage.getItem("jarvis.desk.section") || "inicio";
    } catch {
      return "inicio";
    }
  });
  const [cfg, setCfg] = useState(null);
  // V8.3.1: no app do Windows, a janela escondida pega a interface nova sozinha (sem fechar e abrir o app)
  useEffect(() => (IS_DESKTOP_APP ? watchNewBuild(() => document.hidden) : undefined), []);
  const [level, setLevel] = useState(null);
  const [missions, setMissions] = useState(null);
  const [toast, setToast] = useState("");
  const [menu, setMenu] = useState(false);
  const [search, setSearch] = useState("");
  const log = useConversationLog(userText, response, error, responseCards);
  // V8.4.0 (ideia 10): modo leve e, no app do Windows, o 🎙 pela Groq (o reconhecimento do navegador falha ali)
  useLiteMode(cfg?.desempenho?.leve || "auto");
  const [voiceMsg, setVoiceMsg] = useState("");
  const groqVoice = useGroqVoice({ onText: (t) => { setVoiceMsg(""); send(t); }, onError: setVoiceMsg });
  const mic = IS_DESKTOP_APP ? groqVoice.toggle : onToggleMic;
  const hearing = IS_DESKTOP_APP ? groqVoice.listening || listening : listening;
  const heard = IS_DESKTOP_APP && groqVoice.busy ? "Entendendo…" : interim;
  useEffect(() => {
    if (!voiceMsg) return undefined;
    const t = setTimeout(() => setVoiceMsg(""), 7000);
    return () => clearTimeout(t);
  }, [voiceMsg]);
  // V8.6.0: cutucou demais o avatar? No app do Windows ele sai correndo atrás do mouse (Pac-Man)
  const { mood, poke } = usePoke(() => {
    if (!startPacman()) setVoiceMsg("😤 Ele ficou bravo! No app do JARVIS para Windows, ele corre atrás do seu mouse.");
  });
  const voiceToggle = groqVoice.toggle;
  useEffect(() => { // tecla de atalho do app: já começa a gravar
    if (!IS_DESKTOP_APP) return undefined;
    window.addEventListener("jarvis-desktop-talk", voiceToggle);
    return () => window.removeEventListener("jarvis-desktop-talk", voiceToggle);
  }, [voiceToggle]);

  const loadCfg = useCallback(() => {
    api("/api/desk").then(setCfg).catch(() => setCfg({ avatar: DEFAULT_AVATAR, cor: "#22d3ee", ilha: {} }));
    api("/api/desk/xp").then(setLevel).catch(() => {});
    api("/api/desk/missions").then(setMissions).catch(() => {});
  }, [api]);
  useEffect(() => { loadCfg(); }, [loadCfg]);
  const refreshProgress = useCallback(() => {
    api("/api/desk/xp").then(setLevel).catch(() => {});
    api("/api/desk/missions").then(setMissions).catch(() => {});
  }, [api]);
  const onMissions = useCallback((m) => {
    if (m && m.itens) setMissions(m);
    api("/api/desk/xp").then(setLevel).catch(() => {});
  }, [api]);
  useEffect(() => { // V8.1: "Item novo liberado: capa de herói!"
    const novos = missions?.novos || [];
    if (!novos.length) return undefined;
    setToast(`Item novo liberado: ${novos.map((n) => n.nome).join(", ")}!`);
    api("/api/desk/missions/seen", { method: "POST" }).catch(() => {});
    api("/api/desk").then(setCfg).catch(() => {});
    const t = setTimeout(() => setToast(""), 6000);
    return () => clearTimeout(t);
  }, [missions?.novos, api]);
  useEffect(() => {
    const goTo = (e) => typeof e.detail === "string" && setSection(e.detail);
    window.addEventListener("jarvis-desk-go", goTo);
    return () => window.removeEventListener("jarvis-desk-go", goTo);
  }, []);
  useEffect(() => {
    const t = setInterval(refreshProgress, 30_000);
    return () => clearInterval(t);
  }, [refreshProgress]);
  useEffect(() => {
    if (response) refreshProgress();
  }, [response, refreshProgress]);
  useEffect(() => {
    try {
      localStorage.setItem("jarvis.desk.section", section);
    } catch {
      /* sem armazenamento */
    }
  }, [section]);

  const accent = cfg?.cor || "#22d3ee";
  const style = useMemo(() => ({ "--dk-accent": accent, "--dk-accent-rgb": hexToRgb(accent), "--dk-on-accent": isLight(accent) ? "#06121f" : "#fff" }), [accent]);
  const orbState = hearing ? "listening" : groqVoice.busy ? "processing" : jarvisState;
  const ctx = { log, send, onToggleMic: mic, listening: hearing, interim: heard, userName, aiName, orbState, level, missions, setMissions: onMissions, updateInfo };
  const go = (id) => {
    setSection(id);
    setMenu(false);
  };
  const allSettings = SETTINGS.flatMap(([, items]) => items);
  const found = search.trim() ? allSettings.filter(([, , l]) => l.toLowerCase().includes(search.trim().toLowerCase())) : null;

  let body;
  switch (section) {
    case "conversa": body = <Card title="Conversa" icon="💬" className="dk-full"><ChatBox log={log} send={send} onMic={mic} listening={hearing} interim={heard} /></Card>; break;
    case "memoria": body = <Suspense fallback={<Card title="Memória" icon="✳"><p className="dk-muted">Carregando…</p></Card>}><MemoryMap api={api} accent={accent} /></Suspense>; break;
    case "tarefas": body = <Tasks api={api} />; break;
    case "lembretes": body = <Reminders api={api} />; break;
    case "habitos": body = <Habits api={api} onChange={refreshProgress} />; break;
    case "missoes": body = <Missions api={api} data={missions} onChange={onMissions} />; break;
    case "timers": body = <Timers api={api} send={send} />; break;
    case "musica": body = <Music api={api} send={send} />; break;
    case "copiados": body = <Clips api={api} />; break;
    case "rotinas": body = <Routines api={api} />; break;
    case "meupc": body = <MyPc avatar={cfg?.avatar} />; break;
    case "personalizar": body = <Personalize api={api} cfg={cfg} setCfg={setCfg} aiName={aiName} onRename={onRename} />; break;
    case "cerebro": body = <Brain api={api} />; break;
    case "funcoes": case "atalhos": body = <Functions api={api} send={send} />; break;
    case "voz": body = <LinkCard title="Voz" icon="🎙" text="Voz do JARVIS, velocidade, microfone e palavra de ativação." actions={[["⚙ ABRIR CONFIGURAÇÕES DE VOZ", onOpenSettings], ["🎙 TESTAR MICROFONE", () => send("testar microfone")]]} />; break;
    case "ilha": body = <Island api={api} cfg={cfg} setCfg={setCfg} />; break;
    case "atualizar": body = <Updates api={api} info={updateInfo} onUpdate={onUpdate} cfg={cfg} setCfg={setCfg} />; break;
    case "celular": body = <LinkCard title="Celular e agendas" icon="📱" text="Pareie o celular pelo QR, conecte a agenda do Google e veja os aparelhos." actions={[["📱 QR DO CELULAR", onOpenQr], ["⚙ AGENDA E CONTAS", onOpenSettings]]} />; break;
    case "rosto": body = <LinkCard title="Proteção com rosto" icon="🙂" text="O bloqueio reconhece o seu rosto (e o PIN como alternativa)." actions={[["🔒 BLOQUEAR AGORA", onLock], ["⚙ SEGURANÇA", onOpenSettings]]} />; break;
    default: body = <Home api={api} ctx={ctx} avatar={cfg?.avatar} tema={cfg?.tema} setSection={go} />;
  }

  return (
    <div className={`dk-root${menu ? " is-menu" : ""}${embedded ? " is-embedded" : ""}`} style={style} role="application" aria-label="JARVIS, Modo Desk">
      <aside className="dk-side">
        <div className="dk-brand">
          <button type="button" className="dk-poke" onClick={poke} title="Não cutuque o JARVIS… 😈" aria-label="Cutucar o JARVIS">
            <RoboAvatar avatar={mood ? { ...(cfg?.avatar || {}), expressao: mood } : cfg?.avatar} tema={cfg?.tema} state={mood ? "idle" : orbState} size={44} still={Boolean(mood)} />
          </button>
          <div>
            <b>{aiName}</b>
            <small><i className={`dk-dot is-${orbState}`} />{stateText(orbState)}</small>
            {level && <div className="dk-mini-level"><span>Nv {level.nivel}</span><i><b style={{ width: `${level.pct}%` }} /></i></div>}
            {missions && (
              <button type="button" className={`dk-mini-streak${missions.ofensiva.feita_hoje ? " is-lit" : ""}`} onClick={() => go("missoes")}
                title={`Ofensiva: ${missions.ofensiva.atual} dias (recorde ${missions.ofensiva.recorde})`}>
                🔥 {missions.ofensiva.atual} <small>recorde {missions.ofensiva.recorde}</small>
              </button>
            )}
          </div>
          <button type="button" className="dk-menu-btn" onClick={() => setMenu((v) => !v)} aria-label="Menu" aria-expanded={menu}>☰</button>
        </div>
        <nav className="dk-nav" aria-label="Seções">
          {NAV.map(([id, ico, label]) => (
            <button type="button" key={id} className={section === id ? "is-on" : ""} onClick={() => go(id)} aria-current={section === id ? "page" : undefined}>
              <span>{ico}</span>{label}
            </button>
          ))}
          <input className="dk-search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar configuração" aria-label="Buscar configuração" />
          {(found ? [["Resultados", found]] : SETTINGS).map(([group, items]) => (
            <div key={group} className="dk-nav-group">
              <small>{group.toUpperCase()}</small>
              {items.map(([id, ico, label]) => (
                <button type="button" key={id} className={section === id ? "is-on" : ""} onClick={() => go(id)}><span>{ico}</span>{label}</button>
              ))}
            </div>
          ))}
        </nav>
        {updateInfo && (
          <button type="button" className="dk-btn is-main dk-update-btn" onClick={() => go("atualizar")} title="Tem versão nova do JARVIS">
            ⬆ ATUALIZAR{updateInfo.count ? <b>{updateInfo.count}</b> : null}
          </button>
        )}
        {embedded ? ( // V8.4.1: dentro da ilha (os outros botões ficam na barra de cima da ilha)
          <div className="dk-side-foot">
            <button type="button" className="dk-btn" onClick={onClassic} title="Abrir a janela grande do JARVIS">🖥 JANELA GRANDE</button>
            <button type="button" className="dk-btn" onClick={onLock} title="Bloquear">🔒</button>
          </div>
        ) : (
        <div className="dk-side-foot">
          <button type="button" className="dk-btn" onClick={onClassic} title="Voltar para a central clássica">◐ CENTRAL CLÁSSICA</button>
          <button type="button" className="dk-btn" onClick={() => window.dispatchEvent(new CustomEvent("jarvis-desktop-download"))} title="App do JARVIS para Windows">⬇</button>
          <button type="button" className="dk-btn" onClick={onLock}>🔒</button>
          {IS_DESKTOP_APP && <button type="button" className="dk-btn" onClick={() => window.pywebview?.api?.quit?.()} title="Sair do app (fecha a janela e a ilha; o JARVIS continua rodando no PC)">⏻</button>}
        </div>
        )}
      </aside>
      <main className="dk-main">{body}</main>
      {toast && <div className="dk-toast" role="status">🎁 {toast}</div>}
      {voiceMsg && <div className="dk-toast is-voice" role="alert">🎙 {voiceMsg}</div>}
    </div>
  );
}

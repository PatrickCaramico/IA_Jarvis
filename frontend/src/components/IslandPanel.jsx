import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../utils/api.js";

// V8.3.0 (ideia 9): os menus abrem DIRETO na ilha, sem abrir a janela do JARVIS (como no vídeo).
// A ilha cresce para baixo e mostra: Resumo do dia, Conversa, Tarefas, Lembretes, Música, Timers, Missões,
// Hábitos e Copiados. Usa as mesmas rotas do Modo Desk: o que é feito aqui aparece no app, na central e no celular.

export const ISLAND_TABS = [
  ["resumo", "⌂", "Resumo"], ["conversa", "💬", "Conversa"], ["tarefas", "☰", "Tarefas"], ["lembretes", "🔔", "Lembretes"],
  ["musica", "♫", "Música"], ["timers", "⏱", "Timers"], ["missoes", "🎯", "Missões"], ["habitos", "◆", "Hábitos"],
  ["copiados", "⧉", "Copiados"],
];

const pyApi = () => window.pywebview?.api || {};

/** Carrega uma rota e (opcionalmente) recarrega a cada `every` ms enquanto a aba estiver aberta. */
function useData(path, every = 0) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const load = useCallback(() => {
    api(path).then((d) => { setData(d); setErr(""); }).catch((e) => setErr(e.message || "Não consegui carregar."));
  }, [path]);
  useEffect(() => {
    load();
    if (!every) return undefined;
    const t = setInterval(load, every);
    return () => clearInterval(t);
  }, [load, every]);
  return [data, load, setData, err];
}

const post = (path, body, method = "POST") => api(path, { method, body: body === undefined ? undefined : JSON.stringify(body) });

/** "2026-11-16 09:00:00" -> "16/11 09:00" */
export function shortWhen(s) {
  const m = String(s || "").match(/^\d{4}-(\d{2})-(\d{2})[ T](\d{2}:\d{2})/);
  return m ? `${m[2]}/${m[1]} ${m[3]}` : String(s || "");
}

export function fmtSecs(s) {
  const n = Math.max(0, Math.round(Number(s) || 0));
  const m = Math.floor(n / 60);
  return m >= 60 ? `${Math.floor(m / 60)}h${String(m % 60).padStart(2, "0")}` : `${m}:${String(n % 60).padStart(2, "0")}`;
}

function Empty({ children }) {
  return <p className="ilp-empty">{children}</p>;
}

function Err({ text }) {
  return text ? <p className="ilp-err" role="alert">{text}</p> : null;
}

// ------------------------------------------------------------------ música (usada no Resumo e na aba Música)
function Player({ track, onControl, big = false }) {
  if (!track) return <Empty>Nada tocando agora.</Empty>;
  const playing = track.state === "playing";
  return (
    <div className={`il-player${big ? " is-big" : ""}`}>
      {track.image ? <img src={track.image} alt="" className="il-cover" /> : <span className="il-cover is-empty">♫</span>}
      <div className="il-track"><b>{track.title}</b><small>{track.artist}</small></div>
      <div className="il-ctrl">
        <button type="button" onClick={() => onControl("previous")} aria-label="Música anterior">⏮</button>
        <button type="button" className="is-main" onClick={() => onControl(playing ? "pause" : "play")} aria-label={playing ? "Pausar" : "Tocar"}>{playing ? "⏸" : "▶"}</button>
        <button type="button" onClick={() => onControl("next")} aria-label="Próxima música">⏭</button>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ abas
function Resumo({ st, track, onControl, go }) {
  const [tasks] = useData("/api/tasks", 15000);
  const [rems] = useData("/api/reminders?only_pending=true", 15000);
  const [mis] = useData("/api/desk/missions", 15000);
  const [hab] = useData("/api/desk/habits", 15000);
  const open = (tasks?.tasks || []).filter((t) => !t.concluida);
  const next = [...(rems?.reminders || [])].sort((a, b) => String(a.data_hora).localeCompare(String(b.data_hora)))[0];
  return (
    <div className="ilp-stack">
      <button type="button" className="ilp-row is-link" onClick={() => go("lembretes")}>
        <span className="ilp-ico">🔔</span>
        <span className="ilp-grow">{next ? <><b>{next.texto}</b><small>{shortWhen(next.data_hora)}</small></> : <small>Nenhum lembrete pendente.</small>}</span>
      </button>
      <button type="button" className="ilp-row is-link" onClick={() => go("tarefas")}>
        <span className="ilp-ico">☰</span>
        <span className="ilp-grow">
          <b>{open.length} {open.length === 1 ? "tarefa pendente" : "tarefas pendentes"}</b>
          {open.length > 0 && <small>{open.slice(0, 2).map((t) => t.texto).join(" · ")}</small>}
        </span>
      </button>
      <div className="ilp-tiles">
        <button type="button" className="ilp-tile" onClick={() => go("missoes")}>
          <b>{mis ? `${mis.feitas}/${mis.total}` : "—"}</b><small>missões · 🔥 {mis?.ofensiva?.atual ?? 0}</small>
        </button>
        <button type="button" className="ilp-tile" onClick={() => go("habitos")}>
          <b>{hab ? `${hab.feitos_hoje}/${hab.total}` : "—"}</b><small>hábitos hoje</small>
        </button>
      </div>
      {track && <Player track={track} onControl={onControl} />}
      {st?.resposta && <p className="il-last">{st.resposta}</p>}
    </div>
  );
}

function Conversa({ chat, busy, onSend, onTalk, listening }) {
  const [text, setText] = useState("");
  const endRef = useRef(null);
  useEffect(() => { endRef.current?.scrollIntoView({ block: "end" }); }, [chat.length, busy]);
  const submit = (e) => {
    e.preventDefault();
    const t = text.trim();
    if (!t) return;
    onSend(t);
    setText("");
  };
  return (
    <div className="ilp-chat">
      <div className="ilp-msgs" aria-live="polite">
        {chat.length === 0 && <Empty>Escreva abaixo ou toque em 🎙 para falar comigo.</Empty>}
        {chat.map((m) => <p key={m.id} className={`ilp-msg is-${m.role}`}>{m.text}</p>)}
        {listening && <p className="ilp-msg is-user is-live">Ouvindo…</p>}
        {busy && <p className="ilp-msg is-jarvis is-live">Pensando…</p>}
        <div ref={endRef} />
      </div>
      <form className="ilp-add" onSubmit={submit}>
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Escreva para o JARVIS…" aria-label="Mensagem para o JARVIS" />
        <button type="submit" disabled={!text.trim()} aria-label="Enviar">➤</button>
        <button type="button" className={listening ? "is-on" : ""} onClick={onTalk} aria-label="Falar">🎙</button>
      </form>
    </div>
  );
}

function Tarefas() {
  const [data, load, , err] = useData("/api/tasks");
  const [text, setText] = useState("");
  const [msg, setMsg] = useState("");
  const run = (p) => p.then(() => { setMsg(""); load(); }).catch((e) => setMsg(e.message));
  const add = (e) => {
    e.preventDefault();
    if (!text.trim()) return;
    run(post("/api/tasks", { texto: text.trim() }));
    setText("");
  };
  const open = (data?.tasks || []).filter((t) => !t.concluida);
  return (
    <div className="ilp-stack">
      <form className="ilp-add" onSubmit={add}>
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Nova tarefa e Enter" aria-label="Nova tarefa" />
        <button type="submit" disabled={!text.trim()} aria-label="Adicionar tarefa">＋</button>
      </form>
      <ul className="ilp-list">
        {open.map((t) => (
          <li key={t.id}>
            <button type="button" className="ilp-check" aria-label={`Concluir ${t.texto}`} onClick={() => run(post(`/api/tasks/${t.id}/complete`, undefined, "PATCH"))} />
            <span className="ilp-grow">{t.texto}</span>
          </li>
        ))}
      </ul>
      {data && open.length === 0 && <Empty>Nada pendente. 🎉</Empty>}
      <Err text={msg || err} />
    </div>
  );
}

function Lembretes({ onSend }) {
  const [data, load, , err] = useData("/api/reminders?only_pending=true", 20000);
  const [text, setText] = useState("");
  const [when, setWhen] = useState("");
  const [msg, setMsg] = useState("");
  const add = async (e) => {
    e.preventDefault();
    const t = text.trim();
    if (!t) return;
    try {
      // sem data escolhida, o JARVIS entende o texto ("amanhã 9h dentista")
      if (when) await post("/api/reminders", { texto: t, data_hora: when.replace("T", " ") });
      else await onSend(`me lembra ${t}`);
      setText("");
      setWhen("");
      setMsg("");
      setTimeout(load, when ? 0 : 2500);
    } catch (ex) {
      setMsg(ex.message);
    }
  };
  const list = [...(data?.reminders || [])].sort((a, b) => String(a.data_hora).localeCompare(String(b.data_hora)));
  return (
    <div className="ilp-stack">
      <form className="ilp-add is-two" onSubmit={add}>
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder='Ex.: "amanhã 9h dentista"' aria-label="Lembrete" />
        <input type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} aria-label="Quando (opcional)" />
        <button type="submit" disabled={!text.trim()} aria-label="Criar lembrete">＋</button>
      </form>
      <ul className="ilp-list">
        {list.map((r) => (
          <li key={r.id}>
            <span className="ilp-pill">{shortWhen(r.data_hora)}</span>
            <span className="ilp-grow">{r.texto}</span>
            <button type="button" className="ilp-del" aria-label={`Apagar ${r.texto}`} onClick={() => post(`/api/reminders/${r.id}`, undefined, "DELETE").then(load).catch((e) => setMsg(e.message))}>✕</button>
          </li>
        ))}
      </ul>
      {data && list.length === 0 && <Empty>Nenhum lembrete pendente.</Empty>}
      <Err text={msg || err} />
    </div>
  );
}

function Musica({ track, onControl, onSend }) {
  return (
    <div className="ilp-stack">
      <Player track={track} onControl={onControl} big />
      <div className="ilp-chips">
        {!track && <button type="button" onClick={() => onSend("toca minha playlist")}>▶ Tocar minha playlist</button>}
        <button type="button" onClick={() => onSend("abaixa o volume")}>🔉 Volume −</button>
        <button type="button" onClick={() => onSend("aumenta o volume")}>🔊 Volume +</button>
      </div>
    </div>
  );
}

function Timers({ onSend }) {
  const [data] = useData("/api/timers", 1000);
  const list = data?.timers || [];
  return (
    <div className="ilp-stack">
      <div className="ilp-chips">
        {[5, 10, 25].map((m) => <button type="button" key={m} onClick={() => onSend(`timer de ${m} minutos`)}>＋ {m} min</button>)}
      </div>
      <div className="ilp-timers">
        {list.map((t) => {
          const pct = t.total_seconds ? Math.round((t.seconds_left / t.total_seconds) * 100) : 0;
          return (
            <div key={t.id} className="ilp-timer">
              <b>{fmtSecs(t.seconds_left)}</b><small>{t.label || "timer"}</small>
              <i style={{ width: `${pct}%` }} />
            </div>
          );
        })}
      </div>
      {data && list.length === 0 && <Empty>Nenhum timer rodando.</Empty>}
    </div>
  );
}

const KIND = { uso: "⚡", sobre: "💭", bem: "🌿", semana: "🏆" };

function MissionItem({ m, onData }) {
  const [text, setText] = useState("");
  const [msg, setMsg] = useState("");
  const run = (path, body) => post(path, body).then((r) => { onData(r.missoes || r); setMsg(""); }).catch((e) => setMsg(e.message));
  return (
    <li className={m.feita ? "is-done" : ""}>
      <span className="ilp-ico">{m.feita ? "✓" : KIND[m.tipo] || "🎯"}</span>
      <span className="ilp-grow">
        <b>{m.texto}</b>
        <small>+{m.xp} XP{!m.feita && m.meta > 1 ? ` · ${m.progresso || 0}/${m.meta}` : ""}</small>
        {!m.feita && m.tipo === "sobre" && (
          <form className="ilp-add" onSubmit={(e) => { e.preventDefault(); if (text.trim()) run("/api/desk/missions/answer", { id: m.id, resposta: text.trim() }); }}>
            <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Sua resposta" aria-label={m.texto} maxLength={300} />
            <button type="submit" disabled={!text.trim()} aria-label="Responder">➤</button>
          </form>
        )}
        <Err text={msg} />
      </span>
      {!m.feita && m.tipo === "bem" && <button type="button" className="ilp-btn" onClick={() => run(`/api/desk/missions/${m.id}/done`)}>FEITO</button>}
    </li>
  );
}

function Missoes() {
  const [data, , setData, err] = useData("/api/desk/missions", 20000);
  const of = data?.ofensiva;
  return (
    <div className="ilp-stack">
      {of && (
        <div className="ilp-streak">
          <span className={of.feita_hoje ? "is-lit" : ""} aria-hidden="true">🔥</span>
          <b>{of.atual} {of.atual === 1 ? "dia" : "dias"} de ofensiva</b>
          <small>{of.feita_hoje ? "hoje já conta ✓" : "faça 1 missão hoje"}</small>
        </div>
      )}
      <ul className="ilp-list is-missions">
        {(data?.itens || []).map((m) => <MissionItem key={m.id} m={m} onData={setData} />)}
        {data?.semana && <MissionItem m={data.semana} onData={setData} />}
      </ul>
      <Err text={err} />
    </div>
  );
}

function Habitos() {
  const [data, , setData, err] = useData("/api/desk/habits");
  const [msg, setMsg] = useState("");
  const toggle = (h) => post(`/api/desk/habits/${h.id}/toggle`, { feito: !h.hoje }).then((d) => { setData(d); setMsg(""); }).catch((e) => setMsg(e.message));
  return (
    <div className="ilp-stack">
      <ul className="ilp-list">
        {(data?.itens || []).map((h) => (
          <li key={h.id} className={h.hoje ? "is-done" : ""}>
            <button type="button" className={`ilp-check${h.hoje ? " is-on" : ""}`} aria-pressed={h.hoje} aria-label={`${h.hoje ? "Desmarcar" : "Marcar"} ${h.nome}`} onClick={() => toggle(h)}>{h.hoje ? "✓" : ""}</button>
            <span className="ilp-grow"><b>{h.icone ? `${h.icone} ` : ""}{h.nome}</b><small>🔥 {h.sequencia} {h.sequencia === 1 ? "dia" : "dias"}</small></span>
          </li>
        ))}
      </ul>
      {data && data.itens.length === 0 && <Empty>Nenhum hábito ainda. Crie no app (◆ Hábitos).</Empty>}
      <Err text={msg || err} />
    </div>
  );
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    try {
      return Boolean(await pyApi().copy_text?.(text)); // a janela da ilha pode não ter o foco: o app copia pelo Windows
    } catch {
      return false;
    }
  }
}

function Copiados() {
  const [data, , , err] = useData("/api/desk/clips", 5000);
  const [copied, setCopied] = useState("");
  const copy = async (c) => {
    if (await copyText(c.texto)) {
      setCopied(c.id);
      setTimeout(() => setCopied(""), 1500);
    }
  };
  return (
    <div className="ilp-stack">
      <ul className="ilp-list">
        {(data?.itens || []).slice(0, 30).map((c) => (
          <li key={c.id}>
            <button type="button" className="ilp-clip" onClick={() => copy(c)} title="Copiar de novo">
              <span>{c.texto.length > 140 ? `${c.texto.slice(0, 140)}…` : c.texto}</span>
              <small>{copied === c.id ? "✓ copiado" : c.em}</small>
            </button>
          </li>
        ))}
      </ul>
      {data && data.itens.length === 0 && <Empty>{data.pausado ? "Copiados pausados." : "Nada copiado ainda."}</Empty>}
      <Err text={err} />
    </div>
  );
}

export default function IslandPanel({ tab, setTab, st, track, onControl, chat, busy, onSend, onTalk, listening }) {
  const tabs = {
    resumo: <Resumo st={st} track={track} onControl={onControl} go={setTab} />,
    conversa: <Conversa chat={chat} busy={busy} onSend={onSend} onTalk={onTalk} listening={listening} />,
    tarefas: <Tarefas />,
    lembretes: <Lembretes onSend={onSend} />,
    musica: <Musica track={track} onControl={onControl} onSend={onSend} />,
    timers: <Timers onSend={onSend} />,
    missoes: <Missoes />,
    habitos: <Habitos />,
    copiados: <Copiados />,
  };
  return (
    <>
      <nav className="ilp-tabs" aria-label="Menus da ilha">
        {ISLAND_TABS.map(([id, ico, label]) => (
          <button type="button" key={id} className={tab === id ? "is-on" : ""} onClick={() => setTab(id)} aria-label={label} aria-current={tab === id ? "page" : undefined} title={label}>{ico}</button>
        ))}
      </nav>
      <h4 className="ilp-title">{(ISLAND_TABS.find(([id]) => id === tab) || ISLAND_TABS[0])[2]}</h4>
      <div className="ilp-body">{tabs[tab] || tabs.resumo}</div>
    </>
  );
}

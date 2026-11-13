import { useCallback, useEffect, useRef, useState } from "react";
import PinPad from "./PinPad.jsx";
import useSpeechRecognition from "../hooks/useSpeechRecognition.js";
import { API_URL } from "../utils/api.js";
import { IS_JARVIS_APP } from "../utils/device.js";
import { change, cloud, cloudToken, setCloudToken } from "../utils/cloudApi.js";
import { applyAccessibility, applyBackground, applyTheme } from "../utils/theme.js";

// V6.6: MODO NUVEM. Com o notebook desligado (ou longe), a central roda pelas funções do Netlify:
// conversa com a IA, compras, tarefas, lembretes, alarmes, água, notícias e clima.
// Quando o PC volta a responder, sai sozinho e abre a central completa (onPcBack).

const TABS = [
  { id: "chat", label: "CONVERSA", icon: "◉" },
  { id: "listas", label: "LISTAS", icon: "☰" },
  { id: "agua", label: "ÁGUA", icon: "💧" },
  { id: "info", label: "NOTÍCIAS", icon: "☁" },
];
const OPEN_TAB = { noticias: "info", clima: "info", compras: "listas", tarefas: "listas", lembretes: "listas", agua: "agua" };
const DAYS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"];

function sayHere(text) {
  const clean = String(text || "").trim();
  if (!clean) return;
  try {
    if (window.JarvisApp?.say) {
      window.JarvisApp.say(clean); // app Android: voz do Android
      return;
    }
  } catch {
    /* segue para a voz do navegador */
  }
  try {
    const synth = window.speechSynthesis;
    if (!synth) return;
    synth.cancel();
    const u = new SpeechSynthesisUtterance(clean);
    u.lang = "pt-BR";
    const voice = synth.getVoices().find((v) => /pt[-_]BR/i.test(v.lang));
    if (voice) u.voice = voice;
    synth.speak(u);
  } catch {
    /* sem voz neste navegador */
  }
}

function beep() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    [0, 0.35, 0.7].forEach((t) => {
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.frequency.value = 880;
      g.gain.setValueAtTime(0.0001, ctx.currentTime + t);
      g.gain.exponentialRampToValueAtTime(0.3, ctx.currentTime + t + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + t + 0.25);
      o.connect(g).connect(ctx.destination);
      o.start(ctx.currentTime + t);
      o.stop(ctx.currentTime + t + 0.3);
    });
    setTimeout(() => ctx.close(), 1500);
  } catch {
    /* sem áudio */
  }
}

function whenText(stamp) {
  if (!stamp) return "";
  const [date, time] = stamp.split(" ");
  const [, m, d] = date.split("-");
  return `${d}/${m} às ${time}`;
}

// ------------------------------------------------------------------ entrada pelo PIN
function CloudLogin({ status, onLogged, onBack }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const submit = async (pin) => {
    setBusy(true);
    setMessage("");
    try {
      const { token } = await cloud("/login", { method: "POST", body: { pin } });
      setCloudToken(token);
      onLogged();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  };
  if (status && !status.configured) {
    return (
      <div className="cm-card cm-setup">
        <h2>O modo nuvem ainda não foi ligado</h2>
        <p>No painel do Netlify, em <b>Site configuration › Environment variables</b>, crie:</p>
        <ul>
          <li><code>JARVIS_NUVEM_PIN</code>: o PIN para entrar por aqui (4 a 8 números).</li>
          <li><code>JARVIS_NUVEM_CHAVE</code>: uma senha longa (a mesma vai no <code>.env</code> do PC, para sincronizar).</li>
          <li><code>GEMINI_API_KEY</code> (ou <code>OPENAI_API_KEY</code> / <code>ANTHROPIC_API_KEY</code>): a chave da IA.</li>
        </ul>
        <p>Depois, em Deploys, toque em <b>Trigger deploy</b>. O passo a passo está em <code>docs/MODO-NUVEM.md</code>.</p>
        {onBack && <button type="button" className="cm-chip" onClick={onBack}>VOLTAR</button>}
      </div>
    );
  }
  return (
    <div className="cm-login">
      <p className="cm-login-hint">O notebook não está respondendo. Entre com o PIN do modo nuvem para usar o JARVIS daqui.</p>
      <PinPad title="PIN DO MODO NUVEM" cancelLabel="" busy={busy} message={message} onSubmit={submit} onCancel={() => onBack?.()} />
      {onBack && <button type="button" className="cm-chip" onClick={onBack}>VOLTAR</button>}
    </div>
  );
}

// ------------------------------------------------------------------ abas
function ChatTab({ state, onSend, busy, listening, interim, onMic, micSupported }) {
  const [text, setText] = useState("");
  const endRef = useRef(null);
  const msgs = state?.conversa || [];
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [msgs.length, busy]);
  const send = (e) => {
    e?.preventDefault();
    const t = text.trim();
    if (!t || busy) return;
    setText("");
    onSend(t);
  };
  return (
    <div className="cm-chat">
      <div className="cm-msgs" aria-live="polite">
        {msgs.length === 0 && (
          <div className="cm-empty">
            Experimente: <i>"coloca leite e pão na lista"</i>, <i>"me lembra de pagar a luz amanhã às 9"</i>,
            {" "}<i>"bebi um copo d'água"</i>, <i>"como está o clima?"</i> ou <i>"quais as notícias?"</i>.
          </div>
        )}
        {msgs.map((m, i) => (
          <div key={`${m.at}-${i}`} className={`cm-msg ${m.role === "user" ? "is-user" : "is-jarvis"}`}>
            <span>{m.text}</span>
          </div>
        ))}
        {busy && <div className="cm-msg is-jarvis is-typing"><span>Pensando…</span></div>}
        <div ref={endRef} />
      </div>
      <form className="cm-input" onSubmit={send}>
        {micSupported && (
          <button type="button" className={`cm-mic ${listening ? "is-on" : ""}`} onClick={onMic} aria-label={listening ? "Parar de ouvir" : "Falar com o JARVIS"}>
            🎙
          </button>
        )}
        <input
          value={listening ? interim || "Ouvindo…" : text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Fale ou escreva para o JARVIS"
          disabled={listening}
          aria-label="Mensagem para o JARVIS"
        />
        <button type="submit" className="cm-send" disabled={busy || listening || !text.trim()}>ENVIAR</button>
      </form>
    </div>
  );
}

function ListsTab({ state, run }) {
  const [item, setItem] = useState("");
  const [task, setTask] = useState("");
  const [rem, setRem] = useState({ texto: "", data: "", hora: "" });
  const [alarm, setAlarm] = useState({ hora: "07:00", dias: [] });
  const compras = state?.compras || [];
  const tarefas = (state?.tarefas || []).filter((t) => !t.concluida);
  return (
    <div className="cm-grid">
      <section className="cm-card">
        <h3>🛒 COMPRAS</h3>
        <form className="cm-add" onSubmit={(e) => { e.preventDefault(); if (item.trim()) { run({ op: "shopping_add", itens: item.split(/,| e /).map((s) => s.trim()).filter(Boolean) }); setItem(""); } }}>
          <input value={item} onChange={(e) => setItem(e.target.value)} placeholder="leite, pão e ovos" aria-label="Item da lista de compras" />
          <button type="submit">+</button>
        </form>
        {compras.length === 0 ? <p className="cm-muted">Lista vazia.</p> : (
          <ul className="cm-list">
            {compras.map((i) => (
              <li key={i.id} className={i.comprado ? "is-done" : ""}>
                <label>
                  <input type="checkbox" checked={Boolean(i.comprado)} onChange={() => run({ op: "shopping_set", texto: i.texto, comprado: !i.comprado })} />
                  <span>{i.texto}</span>
                </label>
                <button type="button" aria-label={`Tirar ${i.texto}`} onClick={() => run({ op: "shopping_remove", texto: i.texto })}>✕</button>
              </li>
            ))}
          </ul>
        )}
        {compras.some((i) => i.comprado) && <button type="button" className="cm-chip" onClick={() => run({ op: "shopping_clear" })}>LIMPAR COMPRADOS</button>}
      </section>

      <section className="cm-card">
        <h3>✓ TAREFAS</h3>
        <form className="cm-add" onSubmit={(e) => { e.preventDefault(); if (task.trim()) { run({ op: "task_add", texto: task }); setTask(""); } }}>
          <input value={task} onChange={(e) => setTask(e.target.value)} placeholder="Nova tarefa" aria-label="Nova tarefa" />
          <button type="submit">+</button>
        </form>
        {tarefas.length === 0 ? <p className="cm-muted">Nenhuma tarefa aberta.</p> : (
          <ul className="cm-list">
            {tarefas.map((t) => (
              <li key={t.id}>
                <label>
                  <input type="checkbox" checked={false} onChange={() => run({ op: "task_done", texto: t.texto })} />
                  <span>{t.texto}</span>
                </label>
                <button type="button" aria-label={`Apagar ${t.texto}`} onClick={() => run({ op: "task_remove", texto: t.texto })}>✕</button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="cm-card">
        <h3>⏰ LEMBRETES</h3>
        <form className="cm-add cm-add-wrap" onSubmit={(e) => {
          e.preventDefault();
          if (rem.texto.trim() && rem.data && rem.hora) { run({ op: "reminder_add", texto: rem.texto, data_hora: `${rem.data} ${rem.hora}` }); setRem({ texto: "", data: "", hora: "" }); }
        }}>
          <input value={rem.texto} onChange={(e) => setRem({ ...rem, texto: e.target.value })} placeholder="Do que devo lembrar?" aria-label="Texto do lembrete" />
          <input type="date" value={rem.data} onChange={(e) => setRem({ ...rem, data: e.target.value })} aria-label="Dia do lembrete" />
          <input type="time" value={rem.hora} onChange={(e) => setRem({ ...rem, hora: e.target.value })} aria-label="Hora do lembrete" />
          <button type="submit">+</button>
        </form>
        {(state?.lembretes || []).length === 0 ? <p className="cm-muted">Nenhum lembrete.</p> : (
          <ul className="cm-list">
            {state.lembretes.map((r) => (
              <li key={r.id}>
                <span><b>{whenText(r.data_hora)}</b> · {r.texto}</span>
                <button type="button" aria-label={`Apagar lembrete ${r.texto}`} onClick={() => run({ op: "reminder_remove", texto: r.texto, data_hora: r.data_hora })}>✕</button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="cm-card">
        <h3>🔔 ALARMES</h3>
        <form className="cm-add cm-add-wrap" onSubmit={(e) => { e.preventDefault(); run({ op: "alarm_add", hora: alarm.hora, dias: alarm.dias, rotulo: "" }); }}>
          <input type="time" value={alarm.hora} onChange={(e) => setAlarm({ ...alarm, hora: e.target.value })} aria-label="Hora do alarme" />
          <div className="cm-days" role="group" aria-label="Dias da semana">
            {DAYS.map((d, i) => (
              <button key={d} type="button" className={alarm.dias.includes(i) ? "is-on" : ""} aria-pressed={alarm.dias.includes(i)}
                onClick={() => setAlarm({ ...alarm, dias: alarm.dias.includes(i) ? alarm.dias.filter((x) => x !== i) : [...alarm.dias, i] })}>{d}</button>
            ))}
          </div>
          <button type="submit">+</button>
        </form>
        {(state?.alarmes || []).length === 0 ? <p className="cm-muted">Nenhum alarme.</p> : (
          <ul className="cm-list">
            {state.alarmes.map((a) => (
              <li key={a.id}>
                <span><b>{a.hora}</b> · {a.dias?.length ? a.dias.map((d) => DAYS[d]).join(", ") : `uma vez (${whenText(a.proximo)})`}{a.rotulo ? ` · ${a.rotulo}` : ""}</span>
                <button type="button" aria-label={`Apagar alarme das ${a.hora}`} onClick={() => run({ op: "alarm_remove", hora: a.hora, rotulo: a.rotulo })}>✕</button>
              </li>
            ))}
          </ul>
        )}
        <p className="cm-muted">{IS_JARVIS_APP ? "Com o app fechado, o alarme chega como notificação do celular." : "O alarme toca com esta página aberta; com o PC ligado, ele toca no PC."}</p>
      </section>
    </div>
  );
}

function WaterTab({ state, run, quick }) {
  const w = state?.agua;
  const [goal, setGoal] = useState("");
  if (!w) return null;
  return (
    <div className="cm-grid">
      <section className="cm-card cm-water">
        <div className="cm-ring" style={{ "--pct": `${w.percentage}%` }} role="img" aria-label={`${w.percentage}% da meta de água`}>
          <div><b>{w.total_ml}</b><span>de {w.goal_ml} ml</span></div>
        </div>
        <div className="cm-water-btns">
          {(quick?.length ? quick : [200, 250, 500]).map((ml) => <button key={ml} type="button" onClick={() => run({ op: "water_add", ml })}>+{ml} ml</button>)}
        </div>
        {w.logs.length > 0 && <button type="button" className="cm-chip" onClick={() => run({ op: "water_undo" })}>DESFAZER O ÚLTIMO</button>}
        <form className="cm-add" onSubmit={(e) => { e.preventDefault(); if (goal) { run({ op: "water_goal", goal_ml: Number(goal) }); setGoal(""); } }}>
          <input type="number" min="500" max="10000" step="100" value={goal} onChange={(e) => setGoal(e.target.value)} placeholder={`Meta (${w.goal_ml} ml)`} aria-label="Meta diária de água em ml" />
          <button type="submit">OK</button>
        </form>
        {w.logs.length > 0 && <p className="cm-muted">Hoje: {w.logs.map((l) => `${l.time} ${l.ml} ml`).join(" · ")}</p>}
      </section>
    </div>
  );
}

function InfoTab({ themes = [] }) {
  const [weather, setWeather] = useState(null);
  const [news, setNews] = useState(null);
  const [topic, setTopic] = useState("");
  const [error, setError] = useState("");
  const loadNews = useCallback((q = "") => {
    setNews(null);
    cloud(`/news${q ? `?q=${encodeURIComponent(q)}` : ""}`).then(setNews).catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    cloud("/weather").then(setWeather).catch((e) => setError(e.message));
    loadNews();
  }, [loadNews]);
  return (
    <div className="cm-grid">
      <section className="cm-card">
        <h3>☁ CLIMA</h3>
        {!weather ? <p className="cm-muted">Carregando…</p> : (
          <>
            <div className="cm-weather-now">
              <span className="cm-weather-icon" aria-hidden="true">{weather.icon}</span>
              <div>
                <b>{weather.temperature}°C</b> · {weather.description}
                <div className="cm-muted">{weather.place} · sensação {weather.apparent_temperature}° · chuva {weather.rain_probability ?? "?"}%</div>
              </div>
            </div>
            <div className="cm-week">
              {weather.week.slice(1).map((d) => (
                <div key={d.date}><span>{d.weekday}</span><span aria-hidden="true">{d.icon}</span><span>{d.min}°/{d.max}°</span></div>
              ))}
            </div>
          </>
        )}
      </section>
      <section className="cm-card">
        <h3>📰 NOTÍCIAS</h3>
        <form className="cm-add" onSubmit={(e) => { e.preventDefault(); loadNews(topic.trim()); }}>
          <input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Tema (vazio = principais)" aria-label="Tema das notícias" />
          <button type="submit">🔎</button>
        </form>
        {themes.length > 0 && (
          <div className="cm-themes" role="group" aria-label="Seus temas de notícias">
            <button type="button" className={`cm-chip ${!news?.topic ? "is-on" : ""}`} onClick={() => { setTopic(""); loadNews(""); }}>Principais</button>
            {themes.map((t) => (
              <button key={t.title} type="button" className={`cm-chip ${news?.topic === t.q ? "is-on" : ""}`} onClick={() => { setTopic(""); loadNews(t.q); }}>{t.title}</button>
            ))}
          </div>
        )}
        {!news ? <p className="cm-muted">Carregando…</p> : news.items.length === 0 ? <p className="cm-muted">Nada encontrado.</p> : (
          <ul className="cm-news">
            {news.items.map((n) => (
              <li key={n.link}><a href={n.link} target="_blank" rel="noreferrer">{n.title}</a>{n.source && <span className="cm-muted"> · {n.source}</span>}</li>
            ))}
          </ul>
        )}
      </section>
      {error && <p className="cm-error" role="alert">{error}</p>}
    </div>
  );
}

// ------------------------------------------------------------------ tela principal
export default function CloudMode({ onPcBack, onBack }) {
  const [status, setStatus] = useState(null);
  const [logged, setLogged] = useState(Boolean(cloudToken()));
  const [state, setState] = useState(null);
  const [tab, setTab] = useState("chat");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [alert, setAlert] = useState(null);
  const [voiceOn, setVoiceOn] = useState(() => {
    try {
      return localStorage.getItem("jarvis.cloud.voice") !== "0";
    } catch {
      return true;
    }
  });
  const prefs = status?.prefs || {};
  const sinceRef = useRef(null);

  useEffect(() => {
    cloud("/status").then(setStatus).catch(() => setStatus({ configured: true }));
  }, []);

  // V6.6.2: as configurações da central (fundo, cor, acessibilidade, modo silencioso) valem aqui também.
  // O PC manda para a nuvem a cada minuto; vale a última que ele mandou.
  useEffect(() => {
    if (!status?.prefs) return;
    const p = status.prefs;
    if (p.background_style) applyBackground(p.background_style);
    applyAccessibility(p);
    if (p.theme_colors) applyTheme(p.theme_colors);
    try {
      if (localStorage.getItem("jarvis.cloud.voice") === null && p.silent_mode) setVoiceOn(false);
    } catch {
      /* sem armazenamento */
    }
  }, [status]);

  const refresh = useCallback(async () => {
    try {
      setState(await cloud("/state"));
      setError("");
    } catch (err) {
      if (err.status === 401) setLogged(false);
      else setError(err.message);
    }
  }, []);

  useEffect(() => {
    if (!logged) return undefined;
    setCloudToken(cloudToken()); // entrega a chave ao app Android (avisos com o app fechado)
    refresh();
    const t = setInterval(refresh, 30000);
    return () => clearInterval(t);
  }, [logged, refresh]);

  // Avisos (lembrete, alarme, água) com a tela aberta: bipe, cartão e voz
  useEffect(() => {
    if (!logged) return undefined;
    const check = async () => {
      try {
        const feed = await cloud(`/notifications?since=${sinceRef.current ?? -1}`);
        if (sinceRef.current !== null && feed.items.length) {
          const last = feed.items.at(-1);
          setAlert(last);
          beep();
          sayHere(`${last.title}. ${last.body}`);
          refresh();
        }
        sinceRef.current = feed.latest;
      } catch {
        /* tenta de novo no próximo ciclo */
      }
    };
    check();
    const t = setInterval(check, 20000);
    return () => clearInterval(t);
  }, [logged, refresh]);

  // O PC voltou? No navegador, confere o backend; no app, quem confere é o próprio app (e abre a central)
  useEffect(() => {
    if (IS_JARVIS_APP || !onPcBack) return undefined;
    let alive = true;
    const probe = async () => {
      try {
        const ctrl = new AbortController();
        const t = setTimeout(() => ctrl.abort(), 3000);
        const res = await fetch(`${API_URL}/api/health`, { cache: "no-store", signal: ctrl.signal });
        clearTimeout(t);
        if (res.ok && alive) onPcBack();
      } catch {
        /* PC ainda desligado */
      }
    };
    const t = setInterval(probe, 15000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [onPcBack]);

  const run = useCallback(async (op) => {
    try {
      await change(op);
      setError("");
    } catch (err) {
      setError(err.message);
    }
    refresh();
  }, [refresh]);

  const send = useCallback(async (message) => {
    setBusy(true);
    setState((s) => (s ? { ...s, conversa: [...(s.conversa || []), { role: "user", text: message, at: `local-${Date.now()}` }] } : s));
    try {
      const res = await cloud("/chat", { method: "POST", body: { message }, timeout: 45000 });
      if (voiceOn) sayHere(res.reply);
      const open = res.actions?.find((a) => a.tipo === "abrir" && OPEN_TAB[a.tela]);
      if (open) setTab(OPEN_TAB[open.tela]);
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
      refresh();
    }
  }, [refresh, voiceOn]);

  const speech = useSpeechRecognition({ onFinal: (t) => t?.trim() && send(t.trim()), onError: setError });

  const logout = () => {
    setCloudToken("");
    setLogged(false);
    setState(null);
  };

  const toggleVoice = () => {
    const next = !voiceOn;
    setVoiceOn(next);
    try {
      localStorage.setItem("jarvis.cloud.voice", next ? "1" : "0");
    } catch {
      /* vale só agora */
    }
    if (!next) window.speechSynthesis?.cancel?.();
  };

  return (
    <div className="cm-root">
      <header className="cm-header">
        <div>
          <div className="cm-brand">{(prefs.ai_name || status?.assistente || "JARVIS").toUpperCase()} <span>· MODO NUVEM</span></div>
          <div className="cm-sub">
            <span className="cm-dot" aria-hidden="true" />
            {status?.nome ? `${status.nome}, o` : "O"} notebook está desligado: usando a nuvem.
            {status?.sincronizado_em && <span className="cm-muted"> Último contato com o PC: {whenText(status.sincronizado_em)}.</span>}
          </div>
        </div>
        {logged && (
          <div className="cm-header-btns">
            <button type="button" className="cm-chip" onClick={toggleVoice} aria-pressed={voiceOn}>{voiceOn ? "🔊 VOZ" : "🔇 MUDO"}</button>
            <button type="button" className="cm-chip" onClick={logout}>SAIR</button>
          </div>
        )}
      </header>

      {alert && (
        <div className="cm-alert" role="alert">
          <b>{alert.title}</b> <span>{alert.body}</span>
          <button type="button" onClick={() => setAlert(null)} aria-label="Fechar aviso">OK</button>
        </div>
      )}

      {!logged ? (
        <CloudLogin status={status} onLogged={() => setLogged(true)} onBack={onBack} />
      ) : (
        <>
          <main className="cm-main">
            {tab === "chat" && (
              <ChatTab state={state} onSend={send} busy={busy} listening={speech.listening} interim={speech.interim}
                micSupported={speech.supported} onMic={() => (speech.listening ? speech.stop() : speech.start())} />
            )}
            {tab === "listas" && <ListsTab state={state} run={run} />}
            {tab === "agua" && <WaterTab state={state} run={run} quick={prefs.water_quick_ml} />}
            {tab === "info" && <InfoTab themes={prefs.briefing_news_themes} />}
            {error && <p className="cm-error" role="alert">{error}</p>}
          </main>
          <nav className="cm-tabs" aria-label="Seções do modo nuvem">
            {TABS.map((t) => (
              <button key={t.id} type="button" className={tab === t.id ? "is-on" : ""} aria-current={tab === t.id ? "page" : undefined} onClick={() => setTab(t.id)}>
                <span aria-hidden="true">{t.icon}</span>{t.label}
              </button>
            ))}
          </nav>
        </>
      )}
    </div>
  );
}

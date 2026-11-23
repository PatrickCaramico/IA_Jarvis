import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import useEscape from "../hooks/useEscape.js";
import { speechSeconds, stepTimerText } from "../utils/holoIntent.js";
import "../holo.css";
import HoloVisual from "./HoloVisual.jsx";
import { createAmbient, musicPreferred, rememberMusic } from "../utils/holoVisual.js";
import { holoFileName, holoText, mergePartial, newReqId, nextSpeed, readSpeed, saveSpeed, speedLabel } from "../utils/holoExport.js";
import { copyText } from "../utils/copyText.js";

// V7.1: HOLOGRAMA. A pesquisa vira uma tela viva:
// - APRESENTAÇÃO: cenas animadas (ícone, título, legenda palavra a palavra, tópicos, número que sobe) narradas
//   pela voz do JARVIS; cada cena avança quando ele termina de falar.
// - RECEITA VIVA: ingredientes para marcar e mandar à lista de compras, passo a passo grande, MODO COZINHA por voz
//   ("próximo passo", "repete") e timer do passo com um toque. A tela não apaga enquanto está aberta.
// Foto de fundo: a imagem do artigo da Wikipédia sobre o assunto (quando existe).

// V8.14: a apresentação pesquisa na internet antes; as falas dizem isso
const LOADING_LINES = ["Pesquisando na internet…", "Conferindo as fontes…", "Organizando as cenas…", "Calibrando o holograma…", "Sincronizando a voz…"];

// V7.5: frases faladas exatamente como vão para a voz (para gerar o áudio ANTES e trocar de cena sem pausa)
export const recipeIntro = (data) => `${data.fala || data.titulo}. Separe os ingredientes e diga "próximo passo" quando estiver pronto.`;
export const recipeStep = (data, i) => `Passo ${i + 1}. ${data.passos[i].texto}${i === data.passos.length - 1 && data.dica ? ` Dica de ouro: ${data.dica}` : ""}`;

const calmScreen = () => {
  try {
    return document.documentElement.dataset.perf === "lite" || document.documentElement.dataset.motion === "reduce"
      || window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return false;
  }
};

// o JARVIS está falando agora? (ondas de voz, partículas mais rápidas, anel pulsando)
function useSpeaking() {
  const [speaking, setSpeaking] = useState(false);
  useEffect(() => {
    const on = (e) => {
      const m = e.detail || {};
      if (m.type === "state") setSpeaking(m.state === "speaking");
    };
    window.addEventListener("jarvis_ws_event", on);
    return () => window.removeEventListener("jarvis_ws_event", on);
  }, []);
  return speaking;
}

// constelação de partículas no fundo (canvas leve; some no Modo leve e com "menos movimento")
function Particles({ speaking }) {
  const ref = useRef(null);
  const speakRef = useRef(speaking);
  speakRef.current = speaking;
  useEffect(() => {
    if (calmScreen()) return undefined;
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (!ctx) return undefined;
    let raf;
    let w = 0;
    let h = 0;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const resize = () => {
      w = canvas.clientWidth;
      h = canvas.clientHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener("resize", resize);
    const count = Math.round(Math.min(90, (w * h) / 16000));
    const pts = Array.from({ length: count }, () => ({
      x: Math.random() * w, y: Math.random() * h, vx: (Math.random() - 0.5) * 0.25, vy: -0.15 - Math.random() * 0.35, r: 0.6 + Math.random() * 1.8,
    }));
    const tick = () => {
      const boost = speakRef.current ? 2.4 : 1;
      ctx.clearRect(0, 0, w, h);
      for (const p of pts) {
        p.x += p.vx * boost;
        p.y += p.vy * boost;
        if (p.y < -10) { p.y = h + 10; p.x = Math.random() * w; }
        if (p.x < -10) p.x = w + 10;
        if (p.x > w + 10) p.x = -10;
      }
      ctx.lineWidth = 0.6;
      for (let i = 0; i < pts.length; i += 1) {
        for (let j = i + 1; j < pts.length; j += 1) {
          const dx = pts[i].x - pts[j].x;
          const dy = pts[i].y - pts[j].y;
          const d2 = dx * dx + dy * dy;
          if (d2 < 12000) {
            ctx.strokeStyle = `rgba(103, 232, 249, ${(1 - d2 / 12000) * (speakRef.current ? 0.35 : 0.18)})`;
            ctx.beginPath();
            ctx.moveTo(pts[i].x, pts[i].y);
            ctx.lineTo(pts[j].x, pts[j].y);
            ctx.stroke();
          }
        }
      }
      for (const p of pts) {
        ctx.fillStyle = speakRef.current ? "rgba(224, 251, 255, 0.95)" : "rgba(103, 232, 249, 0.75)";
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, []);
  return <canvas ref={ref} className="holo-particles" aria-hidden="true" />;
}

// título que se "decodifica" letra por letra
const GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#%&*+=<>/";
function Scramble({ text, duration = 900 }) {
  const [out, setOut] = useState(calmScreen() ? text : "");
  useEffect(() => {
    if (calmScreen()) {
      setOut(text);
      return undefined;
    }
    let raf;
    const start = performance.now();
    const step = (t) => {
      const p = Math.min(1, (t - start) / duration);
      const fixed = Math.floor(text.length * p);
      setOut(text.slice(0, fixed) + text.slice(fixed).replace(/\S/g, () => GLYPHS[Math.floor(Math.random() * GLYPHS.length)]));
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [text, duration]);
  return <>{out}</>;
}

// ondas de voz (só se mexem enquanto o JARVIS fala)
function VoiceWave({ active }) {
  return (
    <div className={`holo-wave${active ? " is-on" : ""}`} aria-hidden="true">
      {Array.from({ length: 28 }, (_, i) => (
        <i key={i} style={{ animationDelay: `${(i % 7) * -0.13}s`, animationDuration: `${0.55 + (i % 5) * 0.12}s` }} />
      ))}
    </div>
  );
}

// faíscas (ingrediente marcado, tudo separado, último passo)
function Burst({ id }) {
  if (!id || calmScreen()) return null;
  return (
    <span className="holo-burst" key={id} aria-hidden="true">
      {Array.from({ length: 14 }, (_, i) => <i key={i} style={{ "--a": `${(360 / 14) * i}deg`, "--d": `${40 + (i % 3) * 18}px` }} />)}
    </span>
  );
}

function useWikiImage(term) {
  const [img, setImg] = useState(null);
  useEffect(() => {
    if (!term) return undefined;
    let alive = true;
    fetch(`https://pt.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(term.replace(/ /g, "_"))}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        const src = d?.originalimage?.source || d?.thumbnail?.source;
        if (alive && src && !/\.svg/i.test(src)) setImg({ src, page: d?.content_urls?.desktop?.page || "" });
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [term]);
  return img;
}

// V7.13: a foto real da cena (Wikipédia), com o crédito embaixo
function ScenePhoto({ term }) {
  const img = useWikiImage(term);
  if (!img) return null;
  return (
    <figure className="holo-photo">
      <img src={img.src} alt={term} loading="lazy" />
      <figcaption>Foto: Wikipédia · {term}</figcaption>
    </figure>
  );
}

const isPhone = () => {
  try {
    return window.matchMedia("(max-width: 760px)").matches;
  } catch {
    return false;
  }
};

// V7.13: trilha ambiente baixinha (gerada no aparelho), abaixa quando o JARVIS fala
function useAmbient(active, speaking) {
  const [on, setOn] = useState(() => musicPreferred(isPhone()));
  const engine = useRef(null);
  useEffect(() => {
    if (!active || !on || calmScreen()) return undefined;
    const a = createAmbient();
    if (!a) return undefined;
    engine.current = a;
    a.start();
    return () => {
      a.stop();
      setTimeout(() => a.close(), 600);
      engine.current = null;
    };
  }, [active, on]);
  useEffect(() => {
    engine.current?.duck(speaking);
  }, [speaking]);
  const toggle = () => setOn((v) => {
    rememberMusic(!v);
    return !v;
  });
  return { on, toggle };
}

function useWakeLock() {
  useEffect(() => {
    let lock = null;
    navigator.wakeLock?.request("screen").then((l) => {
      lock = l;
    }).catch(() => {});
    return () => {
      lock?.release?.().catch(() => {});
    };
  }, []);
}

function CountUp({ value, duration = 1600 }) {
  const [shown, setShown] = useState(0);
  useEffect(() => {
    let raf;
    const start = performance.now();
    const step = (t) => {
      const p = Math.min(1, (t - start) / duration);
      setShown(value * (1 - (1 - p) ** 3));
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [value, duration]);
  const digits = Math.abs(value) < 10 && !Number.isInteger(value) ? 1 : 0;
  return <>{shown.toLocaleString("pt-BR", { maximumFractionDigits: digits, minimumFractionDigits: digits })}</>;
}

// legenda que aparece palavra a palavra no ritmo da fala
function Caption({ text, seconds, playing }) {
  const words = text.split(/\s+/);
  const per = (seconds / Math.max(words.length, 1)).toFixed(3);
  return (
    <p className={`holo-caption${playing ? "" : " is-paused"}`}>
      {words.map((w, i) => (
        <span key={i} style={{ animationDelay: `${(i * per).toFixed(2)}s` }}>{w} </span>
      ))}
    </p>
  );
}

// avança quando o JARVIS termina de falar (aviso "idle" depois de "speaking") ou, sem aviso, pelo tempo estimado
function useNarration({ speak, stop, enabled }) {
  const timer = useRef(null);
  const startTimer = useRef(null);
  const listener = useRef(null);
  const clear = useCallback(() => {
    clearTimeout(timer.current);
    clearTimeout(startTimer.current);
    if (listener.current) window.removeEventListener("jarvis_ws_event", listener.current);
    listener.current = null;
  }, []);
  const say = useCallback((text, onDone) => {
    clear();
    if (!enabled) return;
    let spoke = false;
    const finish = () => {
      clear();
      onDone?.();
    };
    listener.current = (e) => {
      const m = e.detail || {};
      if (m.type !== "state") return;
      if (m.state === "speaking") spoke = true;
      else if (m.state === "idle" && spoke) setTimeout(finish, 700);
    };
    window.addEventListener("jarvis_ws_event", listener.current);
    timer.current = setTimeout(finish, (speechSeconds(text) * 1.5 + 4) * 1000);
    startTimer.current = setTimeout(() => speak(text), 300); // dá tempo do "parar" da cena anterior chegar antes
  }, [clear, enabled, speak]);
  const halt = useCallback(() => {
    clear();
    stop();
  }, [clear, stop]);
  useEffect(() => clear, [clear]);
  return { say, halt, clear };
}

// V7.14: QUIZ no final: 3 perguntas de múltipla escolha (toque ou fale a letra), com placar e explicação
const LETTERS = ["A", "B", "C", "D"];
function Quiz({ api, data, say, onDone }) {
  const [qs, setQs] = useState(null);
  const [err, setErr] = useState("");
  const [i, setI] = useState(0);
  const [pick, setPick] = useState(null);
  const [score, setScore] = useState(0);
  useEffect(() => {
    let alive = true;
    api("/api/holo/quiz", { method: "POST", body: JSON.stringify({ titulo: data.titulo, falas: data.cenas.map((c) => c.fala) }), timeout: 45_000 })
      .then((d) => {
        if (!alive) return;
        setQs(d.perguntas);
        say(`Vamos lá, senhor. Pergunta 1. ${d.perguntas[0].pergunta}`);
      })
      .catch((e) => alive && setErr(e.message || "Não consegui montar o quiz."));
    return () => {
      alive = false;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const q = qs?.[i];
  const choose = useCallback((n) => {
    if (!q || pick !== null || n < 0 || n > 3) return;
    setPick(n);
    const right = n === q.certa;
    if (right) setScore((v) => v + 1);
    say(`${right ? "Certo!" : `Não, era a letra ${LETTERS[q.certa]}.`} ${q.explicacao || ""}`);
  }, [pick, q, say]);
  const next = () => {
    if (i + 1 >= qs.length) {
      setI(qs.length);
      const total = qs.length;
      say(score === total ? `Perfeito, senhor! ${score} de ${total}.` : `Você acertou ${score} de ${total}, senhor.`);
      return;
    }
    setI(i + 1);
    setPick(null);
    say(`Pergunta ${i + 2}. ${qs[i + 1].pergunta}`);
  };
  useHoloCommands((c) => {
    if (c && typeof c === "object" && c.type === "quiz") choose(c.letter);
    else if (c === "next" && pick !== null) next();
  });
  if (err) return <div className="holo-quiz"><p>{err}</p><button type="button" className="holo-cta" onClick={onDone}>VOLTAR</button></div>;
  if (!qs) return <div className="holo-quiz" role="status"><small>🧠 MONTANDO O QUIZ…</small><div className="holo-loadbar"><b /></div></div>;
  if (i >= qs.length) {
    return (
      <div className="holo-quiz is-end">
        <small>🧠 QUIZ · RESULTADO</small>
        <strong className="holo-quiz-score">{score}/{qs.length}</strong>
        <p>{score === qs.length ? "Perfeito! 🏆" : score >= qs.length / 2 ? "Muito bem!" : "Vale assistir de novo 😉"}</p>
        <button type="button" className="holo-cta" onClick={onDone}>VOLTAR</button>
      </div>
    );
  }
  return (
    <div className="holo-quiz" key={i}>
      <small>🧠 QUIZ · PERGUNTA {i + 1} DE {qs.length} · {score} {score === 1 ? "acerto" : "acertos"}</small>
      <h3>{q.pergunta}</h3>
      <div className="holo-quiz-opts">
        {q.opcoes.map((o, n) => (
          <button type="button" key={n} onClick={() => choose(n)} disabled={pick !== null}
            className={pick === null ? "" : n === q.certa ? "is-right" : n === pick ? "is-wrong" : "is-dim"}>
            <b>{LETTERS[n]}</b>{o}
          </button>
        ))}
      </div>
      {pick !== null && (
        <>
          <p className="holo-quiz-exp" role="status">{pick === q.certa ? "✓ Certo! " : `✗ Era a ${LETTERS[q.certa]}. `}{q.explicacao}</p>
          <button type="button" className="holo-cta" onClick={next}>{i + 1 >= qs.length ? "VER RESULTADO" : "PRÓXIMA ▶"}</button>
        </>
      )}
      {pick === null && <p className="holo-hint">Toque ou diga "letra A", "B", "C" ou "D".</p>}
    </div>
  );
}

// V7.14: ⭐ SALVAR (rever depois sem gastar IA)
function SaveButton({ api, data, query, savedId }) {
  const [state, setState] = useState(savedId ? "ok" : "");
  const save = async () => {
    setState("…");
    try {
      await api("/api/holo/saved", { method: "POST", body: JSON.stringify({ data, query }) });
      setState("ok");
    } catch (e) {
      setState(e.message || "erro");
    }
  };
  return (
    <button type="button" className="holo-save" onClick={save} disabled={state === "…" || state === "ok"} title={state && state !== "ok" && state !== "…" ? state : "Guardar para rever depois"}>
      {state === "ok" ? "★ SALVO" : state === "…" ? "…" : "☆ SALVAR"}
    </button>
  );
}

function Presentation({ data, image, speak, stop, onClose, speaking, api, speed = 1, onSpeed = null }) {
  const [idx, setIdx] = useState(0);
  const [prev, setPrev] = useState(null); // cena que está saindo (se dissolve enquanto a nova entra)
  const [playing, setPlaying] = useState(true);
  const [ended, setEnded] = useState(false);
  const [waitingMore, setWaitingMore] = useState(false); // V8.14: a próxima cena ainda está chegando
  const [note, setNote] = useState(""); // V8.14: "Copiado" / "Arquivo baixado"
  const scenes = data.cenas;
  const scene = scenes[idx];
  const seconds = speechSeconds(scene?.fala) / (speed || 1);
  // V8.14: as cenas crescem enquanto a IA escreve; o "go" lê sempre o estado mais novo
  const liveRef = useRef({ length: scenes.length, partial: Boolean(data.partial) });
  liveRef.current = { length: scenes.length, partial: Boolean(data.partial) };
  const { say, halt } = useNarration({ speak, stop, enabled: true });
  const [bubble, setBubble] = useState(null); // V7.14: pergunta no meio { q, a }
  const [askOpen, setAskOpen] = useState(false);
  const [askText, setAskText] = useState("");
  const [quiz, setQuiz] = useState(false);

  const ask = useCallback(async (pergunta) => {
    const q = String(pergunta || "").trim();
    if (!q) return;
    halt();
    setPlaying(false);
    setAskOpen(false);
    setAskText("");
    setBubble({ q, a: "" });
    try {
      const r = await api("/api/holo/ask", { method: "POST", body: JSON.stringify({ titulo: data.titulo, cena: scenes[idx]?.fala || "", pergunta: q }), timeout: 45_000 });
      setBubble({ q, a: r.resposta });
      say(r.resposta, () => {
        setBubble(null);
        setPlaying(true); // continua da mesma cena
      });
    } catch (e) {
      setBubble({ q, a: e.message || "Não consegui responder agora, senhor." });
    }
  }, [api, data.titulo, halt, idx, say, scenes]);

  const go = useCallback((next) => {
    if (next >= liveRef.current.length) {
      if (liveRef.current.partial) { // a próxima cena ainda não chegou: espera por ela (sem terminar)
        setWaitingMore(true);
        return;
      }
      setEnded(true);
      setPlaying(false);
      return;
    }
    setWaitingMore(false);
    setEnded(false);
    setIdx((cur) => {
      const n = Math.max(0, next);
      if (n !== cur) setPrev(cur);
      return n;
    });
  }, []);

  // V8.14: chegou a cena que faltava (ou a versão final sem mais cenas): segue a apresentação
  useEffect(() => {
    if (!waitingMore) return;
    if (scenes.length > idx + 1) go(idx + 1);
    else if (!data.partial) go(scenes.length);
  }, [waitingMore, scenes.length, data.partial, idx, go]);

  // V8.14: teclado: ← → trocam de cena, espaço pausa/continua
  const keyRef = useRef(null);
  useEffect(() => {
    const on = (e) => {
      // digitando uma pergunta NO holograma: as teclas são do campo (o chat da central fica por trás e não conta)
      const typing = ["INPUT", "TEXTAREA"].includes(e.target?.tagName) && e.target.closest?.(".holo-root");
      if (typing || e.ctrlKey || e.altKey || e.metaKey) return;
      if (e.key === "ArrowRight") { e.preventDefault(); keyRef.current?.("next"); }
      else if (e.key === "ArrowLeft") { e.preventDefault(); keyRef.current?.("prev"); }
      else if (e.key === " ") { e.preventDefault(); keyRef.current?.("toggle"); }
    };
    window.addEventListener("keydown", on);
    return () => window.removeEventListener("keydown", on);
  }, []);

  const flash = useCallback((text) => {
    setNote(text);
    setTimeout(() => setNote(""), 2200);
  }, []);
  const copyAll = async () => flash(await copyText(holoText(data)) ? "Copiado ✓" : "Não consegui copiar");
  const download = () => {
    try {
      const url = URL.createObjectURL(new Blob([holoText(data)], { type: "text/plain;charset=utf-8" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = holoFileName(data.titulo);
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      flash("Arquivo baixado ✓");
    } catch {
      flash("Não consegui baixar");
    }
  };
  const jump = (i) => { halt(); setEnded(false); setWaitingMore(false); go(i); setPlaying(true); };

  useEffect(() => {
    if (prev === null) return undefined;
    const t = setTimeout(() => setPrev(null), 650);
    return () => clearTimeout(t);
  }, [prev]);

  useEffect(() => {
    if (!playing || ended) return;
    say(scene.fala, () => go(idx + 1));
  }, [idx, playing, ended]); // eslint-disable-line react-hooks/exhaustive-deps

  const cmd = useCallback((c) => {
    if (c && typeof c === "object") {
      if (c.type === "ask" && !quiz) ask(c.text);
      return;
    }
    if (quiz) return; // no quiz, os comandos são dele
    if (c === "next") { halt(); go(idx + 1); setPlaying(true); }
    else if (c === "prev") { halt(); go(idx - 1); setPlaying(true); }
    else if (c === "repeat") { halt(); setPlaying(false); setTimeout(() => setPlaying(true), 50); }
    else if (c === "pause") { halt(); setPlaying(false); }
    else if (c === "play") setPlaying(true);
    else if (c === "close") { halt(); onClose(); }
    else if (c === "toggle") { if (playing) { halt(); setPlaying(false); } else setPlaying(true); }
  }, [ask, go, halt, idx, onClose, playing, quiz]);
  useHoloCommands(cmd);
  keyRef.current = cmd;

  if (quiz) return <Quiz api={api} data={data} say={(t) => say(t)} onDone={() => setQuiz(false)} />;

  if (ended) {
    return (
      <div className="holo-end">
        <div className="holo-end-badge" aria-hidden="true">✦</div>
        <small>FIM DA APRESENTAÇÃO</small>
        <h2><Scramble text={data.titulo} /></h2>
        <div className="holo-end-grid">
          {scenes.map((s, i) => (
            <button type="button" key={i} onClick={() => { setIdx(i); setEnded(false); setPlaying(true); }} style={{ animationDelay: `${i * 0.08}s` }}>
              <span>{s.icone}</span>{s.titulo}
            </button>
          ))}
        </div>
        {(data.fontes || []).length > 0 && (
          <div className="holo-sources">
            <small>🔎 FONTES DA PESQUISA</small>
            <ol>
              {data.fontes.map((f) => (
                <li key={f.url}><a href={f.url} target="_blank" rel="noopener noreferrer">{f.titulo}</a></li>
              ))}
            </ol>
          </div>
        )}
        <div className="holo-controls">
          <button type="button" className="is-main" onClick={() => { halt(); setQuiz(true); }}>🧠 QUIZ: TESTAR O QUE APRENDI</button>
          <button type="button" onClick={() => { setIdx(0); setEnded(false); setPlaying(true); }}>↻ ASSISTIR DE NOVO</button>
          <button type="button" onClick={copyAll} title="Copiar a apresentação em texto">📋 COPIAR</button>
          <button type="button" onClick={download} title="Baixar a apresentação em .txt">⬇ BAIXAR</button>
          <button type="button" onClick={() => cmd("close")}>✕ FECHAR</button>
        </div>
        {note && <p className="holo-note" role="status">{note}</p>}
      </div>
    );
  }

  const renderScene = (s, i, leaving) => (
    <article className={`holo-scene${leaving ? " is-leaving" : ""}`} key={`${i}-${leaving ? "out" : "in"}`} aria-live={leaving ? undefined : "polite"} aria-hidden={leaving || undefined}>
      {!s.visual && (
        <div className={`holo-icon${speaking && !leaving ? " is-talking" : ""}`}>
          <i className="holo-orbit" aria-hidden="true"><b /></i>
          <i className="holo-orbit is-2" aria-hidden="true"><b /></i>
          <span>{s.icone}</span>
        </div>
      )}
      <small className="holo-count">CENA {i + 1} DE {scenes.length}{data.partial ? "+" : ""}</small>
      {s.titulo && <h2 className="holo-title">{leaving ? s.titulo : <Scramble text={s.titulo} />}</h2>}
      {leaving ? <p className="holo-caption is-static">{s.fala}</p> : <Caption text={s.fala} seconds={seconds} playing={playing} />}
      {!leaving && <VoiceWave active={speaking && playing} />}
      {!leaving && (s.visual || s.foto) && (
        <div className={`holo-media${s.visual && s.foto ? " is-two" : ""}`}>
          {s.visual && <HoloVisual visual={s.visual} lite={isPhone()} />}
          {s.foto && <ScenePhoto term={s.foto} />}
        </div>
      )}
      {s.numero && (
        <div className="holo-number">
          <svg className="holo-gauge" viewBox="0 0 120 120" aria-hidden="true">
            <circle cx="60" cy="60" r="54" className="holo-gauge-track" />
            <circle cx="60" cy="60" r="54" className="holo-gauge-fill" />
          </svg>
          <strong>{leaving ? s.numero.valor.toLocaleString("pt-BR") : <CountUp value={s.numero.valor} />}</strong>
          <span>{s.numero.unidade}</span>
          {s.numero.rotulo && <small>{s.numero.rotulo}</small>}
        </div>
      )}
      {s.pontos.length > 0 && (
        <ul className="holo-points">
          {s.pontos.map((p, n) => <li key={p} style={{ animationDelay: `${0.9 + n * 0.45}s`, "--from": ["-60px, 0", "0, 40px", "60px, 0"][n % 3] }}>{p}</li>)}
        </ul>
      )}
    </article>
  );

  return (
    <>
      {/* V8.14: um toque num pedaço da barra pula para a cena; o último pisca enquanto as cenas ainda chegam */}
      <div className="holo-progress" role="group" aria-label="Cenas">
        {scenes.map((s, i) => (
          <button type="button" key={i} className={i < idx ? "is-done" : i === idx ? "is-now" : ""} onClick={() => jump(i)}
            aria-label={`Cena ${i + 1}: ${s.titulo || ""}`} aria-current={i === idx || undefined}>
            {i === idx && <b style={{ animationDuration: `${seconds}s`, animationPlayState: playing && !waitingMore ? "running" : "paused" }} />}
          </button>
        ))}
        {data.partial && <span className="is-coming" aria-hidden="true" />}
      </div>
      <div className="holo-stage-scenes">
        {prev !== null && scenes[prev] && renderScene(scenes[prev], prev, true)}
        {renderScene(scene, idx, false)}
      </div>
      {bubble && (
        <div className="holo-bubble" role="status" aria-live="polite">
          <small>❓ {bubble.q}</small>
          <p>{bubble.a || "Pensando…"}</p>
          {bubble.a && <button type="button" onClick={() => { halt(); setBubble(null); setPlaying(true); }}>CONTINUAR ▶</button>}
        </div>
      )}
      {askOpen && (
        <form className="holo-ask" onSubmit={(e) => { e.preventDefault(); ask(askText); }}>
          <input autoFocus value={askText} onChange={(e) => setAskText(e.target.value)} placeholder="Pergunte sobre esta cena…" aria-label="Pergunta sobre a cena" />
          <button type="submit" disabled={!askText.trim()}>PERGUNTAR</button>
        </form>
      )}
      {waitingMore && <p className="holo-note" role="status">⟳ Montando a próxima cena…</p>}
      <div className="holo-controls">
        <button type="button" onClick={() => { setAskOpen((v) => !v); if (playing) cmd("pause"); }} aria-label="Fazer uma pergunta" title='Ou diga "espera, o que é…?"'>❓</button>
        <button type="button" onClick={() => cmd("prev")} disabled={idx === 0} aria-label="Cena anterior" title="Cena anterior (←)">⟵</button>
        <button type="button" className="is-main" onClick={() => cmd(playing ? "pause" : "play")} aria-label={playing ? "Pausar" : "Continuar"} title="Pausar/continuar (espaço)">{playing ? "❚❚" : "▶"}</button>
        <button type="button" onClick={() => cmd("next")} aria-label="Próxima cena" title="Próxima cena (→)">⟶</button>
        {onSpeed && (
          <button type="button" className="holo-speed" onClick={() => onSpeed(nextSpeed(speed))} title="Velocidade da narração (vale a partir da próxima fala)"
            aria-label={`Velocidade da narração: ${speedLabel(speed)}`}>{speedLabel(speed)}</button>
        )}
      </div>
      {image && !image.own && <span className="holo-credit">Imagem: Wikipédia</span>}
    </>
  );
}

function Recipe({ data, image, api, speak, stop, onSend, onClose, speaking }) {
  useWakeLock();
  const [step, setStep] = useState(0);
  const [dir, setDir] = useState("next");
  const [burst, setBurst] = useState({ at: "", id: 0 });
  const [checked, setChecked] = useState({});
  const [shopping, setShopping] = useState("");
  const { say, halt } = useNarration({ speak, stop, enabled: true });
  const total = data.passos.length;
  const current = data.passos[step];

  const sayStep = useCallback((i) => say(recipeStep(data, i)), [data, say]);

  useEffect(() => {
    say(recipeIntro(data));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const goStep = useCallback((i) => {
    const n = Math.max(0, Math.min(total - 1, i));
    setDir(n >= step ? "next" : "prev");
    setStep(n);
    sayStep(n);
    if (n === total - 1 && n !== step) setBurst({ at: "step", id: Date.now() });
  }, [sayStep, total, step]);

  const cmd = useCallback((c) => {
    if (c === "next") goStep(step + 1);
    else if (c === "prev") goStep(step - 1);
    else if (c === "repeat" || c === "play") sayStep(step);
    else if (c === "pause") halt();
    else if (c === "close") { halt(); onClose(); }
  }, [goStep, halt, onClose, sayStep, step]);
  useHoloCommands(cmd);

  const toShopping = async () => {
    const missing = data.ingredientes.filter((_, i) => !checked[i]);
    if (!missing.length) return;
    try {
      await api("/api/shopping", { method: "POST", body: JSON.stringify({ texto: missing.join(", ") }) });
      setShopping(`✓ ${missing.length} ${missing.length === 1 ? "item foi" : "itens foram"} para a lista de compras`);
    } catch (err) {
      setShopping(err.message || "Não consegui mandar para a lista.");
    }
  };

  const done = Object.values(checked).filter(Boolean).length;
  const allDone = done === data.ingredientes.length;
  const toggle = (i) => {
    setChecked((c) => {
      const next = { ...c, [i]: !c[i] };
      const count = Object.values(next).filter(Boolean).length;
      if (next[i]) setBurst({ at: count === data.ingredientes.length ? "all" : `ing-${i}`, id: Date.now() });
      return next;
    });
  };
  const ring = 2 * Math.PI * 22;
  return (
    <div className="holo-recipe">
      <header className="holo-recipe-head">
        <div>
          <small>✦ RECEITA VIVA · MODO COZINHA</small>
          <h2>{data.titulo}</h2>
          <div className="holo-chips">
            {data.tempo && <span>⏱ {data.tempo}</span>}
            {data.rende && <span>🍽 {data.rende}</span>}
            {data.dificuldade && <span>★ {data.dificuldade}</span>}
          </div>
        </div>
      </header>
      <div className="holo-recipe-grid">
        <section className="holo-panel holo-ingredients">
          <h3>INGREDIENTES <small>{done}/{data.ingredientes.length} separados</small></h3>
          <ul>
            {data.ingredientes.map((ing, i) => (
              <li key={i} style={{ animationDelay: `${i * 0.06}s` }}>
                <button type="button" className={checked[i] ? "is-on" : ""} onClick={() => toggle(i)} aria-pressed={Boolean(checked[i])}>
                  <i aria-hidden="true">{checked[i] ? "✓" : ""}{burst.at === `ing-${i}` && <Burst id={burst.id} />}</i>{ing}
                </button>
              </li>
            ))}
          </ul>
          {allDone && (
            <p className="holo-celebrate" role="status">
              {burst.at === "all" && <Burst id={burst.id} />}✓ TUDO SEPARADO! Diga "próximo passo".
            </p>
          )}
          <button type="button" className="holo-cta" onClick={toShopping} disabled={allDone}>🛒 FALTANTES PARA A LISTA DE COMPRAS</button>
          {shopping && <p className="holo-ok" role="status">{shopping}</p>}
        </section>
        <section className="holo-panel holo-steps">
          <div className={`holo-step-now is-${dir}`} key={step}>
            <div className="holo-step-top">
              <svg className="holo-step-ring" viewBox="0 0 50 50" aria-hidden="true">
                <circle cx="25" cy="25" r="22" className="holo-gauge-track" />
                <circle cx="25" cy="25" r="22" className="holo-step-ring-fill" style={{ strokeDasharray: ring, strokeDashoffset: ring * (1 - (step + 1) / total) }} />
                <text x="25" y="29" textAnchor="middle">{step + 1}</text>
              </svg>
              <small>PASSO {step + 1} DE {total}</small>
              {step === total - 1 && <b className="holo-last">🍽 ÚLTIMO PASSO</b>}
              {burst.at === "step" && <Burst id={burst.id} />}
            </div>
            <p>{current.texto}</p>
            <VoiceWave active={speaking} />
            {current.minutos > 0 && (
              <button type="button" className="holo-cta" onClick={() => onSend(stepTimerText(current.minutos, data.titulo))}>
                ⏱ INICIAR TIMER DE {current.minutos >= 60 ? `${Math.floor(current.minutos / 60)}H${current.minutos % 60 ? ` ${current.minutos % 60}MIN` : ""}` : `${current.minutos} MIN`}
              </button>
            )}
          </div>
          <div className="holo-step-bar"><b style={{ width: `${((step + 1) / total) * 100}%` }} /></div>
          <ol className="holo-step-list">
            {data.passos.map((p, i) => (
              <li key={i} className={i === step ? "is-now" : i < step ? "is-done" : ""}>
                <button type="button" onClick={() => goStep(i)}>{p.texto}</button>
              </li>
            ))}
          </ol>
          {data.dica && <p className="holo-tip">💡 {data.dica}</p>}
          <div className="holo-controls">
            <button type="button" onClick={() => cmd("prev")} disabled={step === 0}>◀ ANTERIOR</button>
            <button type="button" onClick={() => cmd("repeat")}>🔊 REPETIR</button>
            <button type="button" className="is-main" onClick={() => cmd("next")} disabled={step === total - 1}>PRÓXIMO ▶</button>
          </div>
          <p className="holo-hint">Mãos ocupadas? Diga "Jarvis, próximo passo", "repete" ou "passo anterior".</p>
        </section>
      </div>
      {image && !image.own && <span className="holo-credit">Imagem: Wikipédia</span>}
    </div>
  );
}

function useHoloCommands(handler) {
  const ref = useRef(handler);
  ref.current = handler;
  useEffect(() => {
    const on = (e) => ref.current?.(e.detail);
    window.addEventListener("jarvis-holo-cmd", on);
    return () => window.removeEventListener("jarvis-holo-cmd", on);
  }, []);
}

export default function HoloStage({ api, request, onClose, onSend, onSpeak, onStop, onPrefetch = null }) {
  const [data, setData] = useState(null);
  // V8.14: velocidade da narração (1x, 1,25x, 1,5x), lembrada neste navegador
  const [speed, setSpeedState] = useState(readSpeed);
  const speedRef = useRef(speed);
  speedRef.current = speed;
  const setSpeed = useCallback((v) => { saveSpeed(v); setSpeedState(v); }, []);
  const speak = useCallback((t) => onSpeak(t, speedRef.current), [onSpeak]);
  const prefetched = useRef(new Set());
  const prefetch = useCallback((texts) => {
    const fresh = texts.filter((t) => t && !prefetched.current.has(`${speedRef.current}|${t}`));
    fresh.forEach((t) => prefetched.current.add(`${speedRef.current}|${t}`));
    if (fresh.length) onPrefetch?.(fresh.slice(0, 10), speedRef.current);
  }, [onPrefetch]);
  const reqIdRef = useRef("");
  // V8.14: as cenas chegam aos poucos (holo_partial): a apresentação começa na 1ª, sem esperar o resto
  useEffect(() => {
    const on = (e) => {
      const m = e.detail || {};
      if (m.type !== "holo_partial" || !reqIdRef.current || m.req_id !== reqIdRef.current) return;
      setData((cur) => mergePartial(cur, m, request.query));
      prefetch((m.cenas || []).map((c) => c.fala));
    };
    window.addEventListener("jarvis_ws_event", on);
    return () => window.removeEventListener("jarvis_ws_event", on);
  }, [prefetch, request.query]);
  const speaking = useSpeaking();
  const [error, setError] = useState("");
  const [line, setLine] = useState(0);
  const wikiImage = useWikiImage(request.photo ? "" : data?.wiki || "");
  const image = request.photo ? { src: request.photo, own: true } : wikiImage; // V7.8: a foto enviada vira o fundo

  const [library, setLibrary] = useState(request.library ? null : undefined); // V7.14: lista de salvos
  useEffect(() => { api?.("/api/desk/missions/track/holograma", { method: "POST" }).catch(() => {}); }, [api]); // V8.1: conta na missão
  const [savedId, setSavedId] = useState(request.savedId || "");

  const openSaved = useCallback(async (id) => {
    setError("");
    try {
      const item = await api(`/api/holo/saved/${encodeURIComponent(id)}`);
      setSavedId(id);
      setLibrary(undefined);
      setData(item.data);
    } catch (e) {
      setError(e.message || "Não consegui abrir a apresentação salva.");
    }
  }, [api]);

  useEffect(() => {
    if (!request.library) return;
    api("/api/holo/saved").then((d) => setLibrary(d.itens || [])).catch((e) => { setLibrary([]); setError(e.message); });
  }, [api, request.library]);

  useEffect(() => {
    if (request.library) return undefined;
    if (request.savedId) {
      openSaved(request.savedId);
      return undefined;
    }
    let alive = true;
    setData(null);
    setError("");
    const reqId = newReqId();
    reqIdRef.current = reqId;
    api("/api/holo", { method: "POST", body: JSON.stringify({ query: request.query, kind: request.kind, req_id: reqId }), timeout: 100_000 })
      .then((d) => {
        if (!alive) return;
        reqIdRef.current = ""; // chegou a versão final: ignora pedaços atrasados
        setData(d);
        // V7.5: gera as falas antes (troca de cena sem esperar a voz ficar pronta)
        const texts = d.tipo === "receita" ? [recipeIntro(d), ...d.passos.map((_, i) => recipeStep(d, i))] : (d.cenas || []).map((c) => c.fala);
        prefetch(texts);
      })
      .catch((err) => {
        if (!alive) return;
        reqIdRef.current = "";
        // V8.14: se a apresentação já começou pelas cenas parciais, continua com elas (só some o "montando")
        setData((cur) => (cur?.partial ? { ...cur, partial: false } : cur));
        setError((prev) => prev || err.message || "Não consegui montar o holograma.");
      });
    return () => {
      alive = false;
      reqIdRef.current = "";
    };
  }, [api, request]); // eslint-disable-line react-hooks/exhaustive-deps

  const removeSaved = async (item) => {
    if (!window.confirm(`Apagar "${item.titulo}" dos salvos?`)) return;
    try {
      const d = await api(`/api/holo/saved/${encodeURIComponent(item.id)}`, { method: "DELETE" });
      setLibrary(d.itens || []);
    } catch (e) {
      setError(e.message);
    }
  };

  useEffect(() => {
    if (data || error || library !== undefined) return undefined;
    const t = setInterval(() => setLine((n) => (n + 1) % LOADING_LINES.length), 1400);
    return () => clearInterval(t);
  }, [data, error, library]);

  const close = useCallback(() => {
    onStop();
    onClose();
  }, [onClose, onStop]);
  const music = useAmbient(data?.tipo === "apresentacao", speaking);

  useEscape(close);

  return createPortal(
    <div className={`holo-root${data ? ` is-${data.tipo}` : ""}${speaking ? " is-speaking" : ""}`} role="dialog" aria-modal="true" aria-label="Holograma do JARVIS">
      {image && <div className="holo-bg" style={{ backgroundImage: `url("${image.src}")` }} aria-hidden="true" />}
      <div className="holo-grid" aria-hidden="true" />
      <Particles speaking={speaking} />
      <div className="holo-beam" aria-hidden="true" />
      {data?.tipo !== "receita" && (
        <div className="holo-sphere" aria-hidden="true"><i /><i /><i /><i /></div>
      )}
      <div className="holo-scan" aria-hidden="true" />
      <button type="button" className="holo-close" onClick={close} aria-label="Fechar o holograma">✕</button>
      {data?.tipo === "apresentacao" && (data.partial || data.fontes) && (
        <div className={`holo-research${data.partial ? " is-building" : ""}`} role="status">
          {data.partial ? "⟳ MONTANDO AS PRÓXIMAS CENAS…" : data.pesquisado || data.fontes?.length
            ? `🔎 PESQUISADO NA INTERNET · ${data.fontes.length} ${data.fontes.length === 1 ? "FONTE" : "FONTES"}`
            : "⚠ SEM PESQUISA NA INTERNET: PODE ESTAR DESATUALIZADO"}
        </div>
      )}
      {data?.tipo === "apresentacao" && (
        <button type="button" className="holo-music" onClick={music.toggle} aria-pressed={music.on} title={music.on ? "Desligar a trilha" : "Ligar a trilha"}>
          {music.on ? "🔈 TRILHA" : "🔇 TRILHA"}
        </button>
      )}

      {data && !data.partial && (
        <SaveButton api={api} data={data} query={request.query || ""} savedId={savedId} key={`${data.titulo}-${savedId}`} />
      )}
      {library !== undefined && !data && (
        <div className="holo-library">
          <small>⭐ HOLOGRAMAS SALVOS</small>
          <h2>Rever sem gastar IA</h2>
          {library === null ? <p role="status">Carregando…</p> : library.length === 0 ? (
            <p>Nada salvo ainda. No fim (ou durante) uma apresentação ou receita, toque em ☆ SALVAR.</p>
          ) : (
            <ul>
              {library.map((it) => (
                <li key={it.id}>
                  <button type="button" className="holo-library-open" onClick={() => openSaved(it.id)}>
                    <span>{it.tipo === "receita" ? "🍳" : "✦"}</span>
                    <b>{it.titulo}</b>
                    <small>{it.salvo_em}</small>
                  </button>
                  <button type="button" className="holo-library-del" onClick={() => removeSaved(it)} aria-label={`Apagar ${it.titulo}`}>🗑</button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {!data && !error && library === undefined && (
        <div className="holo-loading" role="status">
          <div className="holo-rings" aria-hidden="true"><i /><i /><i /><b>✦</b></div>
          <small>MONTANDO O HOLOGRAMA</small>
          <h2><Scramble text={request.query || "Apresentação salva"} duration={1400} /></h2>
          <div className="holo-loadbar" aria-hidden="true"><b /></div>
          <p key={line}>{LOADING_LINES[line]}</p>
        </div>
      )}
      {error && !data && (
        <div className="holo-loading" role="alert">
          <small>HOLOGRAMA INDISPONÍVEL</small>
          <p>{error}</p>
          <button type="button" className="holo-cta" onClick={close}>FECHAR</button>
        </div>
      )}
      {data?.tipo === "apresentacao" && <Presentation data={data} image={image} speak={speak} stop={onStop} onClose={close} speaking={speaking} api={api} speed={speed} onSpeed={setSpeed} />}
      {data?.tipo === "receita" && <Recipe data={data} image={image} api={api} speak={speak} stop={onStop} onSend={onSend} onClose={close} speaking={speaking} />}
    </div>,
    document.body,
  );
}

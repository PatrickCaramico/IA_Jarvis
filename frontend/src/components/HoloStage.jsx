import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import useEscape from "../hooks/useEscape.js";
import { speechSeconds, stepTimerText } from "../utils/holoIntent.js";
import "../holo.css";

// V7.1: HOLOGRAMA. A pesquisa vira uma tela viva:
// - APRESENTAÇÃO: cenas animadas (ícone, título, legenda palavra a palavra, tópicos, número que sobe) narradas
//   pela voz do JARVIS; cada cena avança quando ele termina de falar.
// - RECEITA VIVA: ingredientes para marcar e mandar à lista de compras, passo a passo grande, MODO COZINHA por voz
//   ("próximo passo", "repete") e timer do passo com um toque. A tela não apaga enquanto está aberta.
// Foto de fundo: a imagem do artigo da Wikipédia sobre o assunto (quando existe).

const LOADING_LINES = ["Consultando a base de conhecimento…", "Organizando as cenas…", "Calibrando o holograma…", "Sincronizando a voz…"];

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

function Presentation({ data, image, speak, stop, onClose, speaking }) {
  const [idx, setIdx] = useState(0);
  const [prev, setPrev] = useState(null); // cena que está saindo (se dissolve enquanto a nova entra)
  const [playing, setPlaying] = useState(true);
  const [ended, setEnded] = useState(false);
  const scenes = data.cenas;
  const scene = scenes[idx];
  const seconds = speechSeconds(scene?.fala);
  const { say, halt } = useNarration({ speak, stop, enabled: true });

  const go = useCallback((next) => {
    if (next >= scenes.length) {
      setEnded(true);
      setPlaying(false);
      return;
    }
    setEnded(false);
    setIdx((cur) => {
      const n = Math.max(0, next);
      if (n !== cur) setPrev(cur);
      return n;
    });
  }, [scenes.length]);

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
    if (c === "next") { halt(); go(idx + 1); setPlaying(true); }
    else if (c === "prev") { halt(); go(idx - 1); setPlaying(true); }
    else if (c === "repeat") { halt(); setPlaying(false); setTimeout(() => setPlaying(true), 50); }
    else if (c === "pause") { halt(); setPlaying(false); }
    else if (c === "play") setPlaying(true);
    else if (c === "close") { halt(); onClose(); }
  }, [go, halt, idx, onClose]);
  useHoloCommands(cmd);

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
        <div className="holo-controls">
          <button type="button" onClick={() => { setIdx(0); setEnded(false); setPlaying(true); }}>↻ ASSISTIR DE NOVO</button>
          <button type="button" onClick={() => cmd("close")}>✕ FECHAR</button>
        </div>
      </div>
    );
  }

  const renderScene = (s, i, leaving) => (
    <article className={`holo-scene${leaving ? " is-leaving" : ""}`} key={`${i}-${leaving ? "out" : "in"}`} aria-live={leaving ? undefined : "polite"} aria-hidden={leaving || undefined}>
      <div className={`holo-icon${speaking && !leaving ? " is-talking" : ""}`}>
        <i className="holo-orbit" aria-hidden="true"><b /></i>
        <i className="holo-orbit is-2" aria-hidden="true"><b /></i>
        <span>{s.icone}</span>
      </div>
      <small className="holo-count">CENA {i + 1} DE {scenes.length}</small>
      {s.titulo && <h2 className="holo-title">{leaving ? s.titulo : <Scramble text={s.titulo} />}</h2>}
      {leaving ? <p className="holo-caption is-static">{s.fala}</p> : <Caption text={s.fala} seconds={seconds} playing={playing} />}
      {!leaving && <VoiceWave active={speaking && playing} />}
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
      <div className="holo-progress" aria-hidden="true">
        {scenes.map((_, i) => (
          <i key={i} className={i < idx ? "is-done" : i === idx ? "is-now" : ""}>
            {i === idx && <b style={{ animationDuration: `${seconds}s`, animationPlayState: playing ? "running" : "paused" }} />}
          </i>
        ))}
      </div>
      <div className="holo-stage-scenes">
        {prev !== null && scenes[prev] && renderScene(scenes[prev], prev, true)}
        {renderScene(scene, idx, false)}
      </div>
      <div className="holo-controls">
        <button type="button" onClick={() => cmd("prev")} disabled={idx === 0} aria-label="Cena anterior">⟵</button>
        <button type="button" className="is-main" onClick={() => cmd(playing ? "pause" : "play")} aria-label={playing ? "Pausar" : "Continuar"}>{playing ? "❚❚" : "▶"}</button>
        <button type="button" onClick={() => cmd("next")} aria-label="Próxima cena">⟶</button>
      </div>
      {image && <span className="holo-credit">Imagem: Wikipédia</span>}
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
      {image && <span className="holo-credit">Imagem: Wikipédia</span>}
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
  const speaking = useSpeaking();
  const [error, setError] = useState("");
  const [line, setLine] = useState(0);
  const image = useWikiImage(data?.wiki || "");

  useEffect(() => {
    let alive = true;
    setData(null);
    setError("");
    api("/api/holo", { method: "POST", body: JSON.stringify({ query: request.query, kind: request.kind }), timeout: 60_000 })
      .then((d) => {
        if (!alive) return;
        setData(d);
        // V7.5: gera as falas antes (troca de cena sem esperar a voz ficar pronta)
        const texts = d.tipo === "receita" ? [recipeIntro(d), ...d.passos.map((_, i) => recipeStep(d, i))] : (d.cenas || []).map((c) => c.fala);
        onPrefetch?.(texts.slice(0, 10));
      })
      .catch((err) => alive && setError(err.message || "Não consegui montar o holograma."));
    return () => {
      alive = false;
    };
  }, [api, request]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (data || error) return undefined;
    const t = setInterval(() => setLine((n) => (n + 1) % LOADING_LINES.length), 1400);
    return () => clearInterval(t);
  }, [data, error]);

  const close = useCallback(() => {
    onStop();
    onClose();
  }, [onClose, onStop]);

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

      {!data && !error && (
        <div className="holo-loading" role="status">
          <div className="holo-rings" aria-hidden="true"><i /><i /><i /><b>✦</b></div>
          <small>MONTANDO O HOLOGRAMA</small>
          <h2><Scramble text={request.query} duration={1400} /></h2>
          <div className="holo-loadbar" aria-hidden="true"><b /></div>
          <p key={line}>{LOADING_LINES[line]}</p>
        </div>
      )}
      {error && (
        <div className="holo-loading" role="alert">
          <small>HOLOGRAMA INDISPONÍVEL</small>
          <p>{error}</p>
          <button type="button" className="holo-cta" onClick={close}>FECHAR</button>
        </div>
      )}
      {data?.tipo === "apresentacao" && <Presentation data={data} image={image} speak={onSpeak} stop={onStop} onClose={close} speaking={speaking} />}
      {data?.tipo === "receita" && <Recipe data={data} image={image} api={api} speak={onSpeak} stop={onStop} onSend={onSend} onClose={close} speaking={speaking} />}
    </div>,
    document.body,
  );
}

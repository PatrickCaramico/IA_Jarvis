import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { speechSeconds, stepTimerText } from "../utils/holoIntent.js";
import "../holo.css";

// V7.1: HOLOGRAMA. A pesquisa vira uma tela viva:
// - APRESENTAÇÃO: cenas animadas (ícone, título, legenda palavra a palavra, tópicos, número que sobe) narradas
//   pela voz do JARVIS; cada cena avança quando ele termina de falar.
// - RECEITA VIVA: ingredientes para marcar e mandar à lista de compras, passo a passo grande, MODO COZINHA por voz
//   ("próximo passo", "repete") e timer do passo com um toque. A tela não apaga enquanto está aberta.
// Foto de fundo: a imagem do artigo da Wikipédia sobre o assunto (quando existe).

const LOADING_LINES = ["Consultando a base de conhecimento…", "Organizando as cenas…", "Calibrando o holograma…", "Sincronizando a voz…"];

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

function Presentation({ data, image, speak, stop, onClose }) {
  const [idx, setIdx] = useState(0);
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
    setIdx(Math.max(0, next));
  }, [scenes.length]);

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
        <small>FIM DA APRESENTAÇÃO</small>
        <h2>{data.titulo}</h2>
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

  return (
    <>
      <div className="holo-progress" aria-hidden="true">
        {scenes.map((_, i) => (
          <i key={i} className={i < idx ? "is-done" : i === idx ? "is-now" : ""}>
            {i === idx && <b style={{ animationDuration: `${seconds}s`, animationPlayState: playing ? "running" : "paused" }} />}
          </i>
        ))}
      </div>
      <article className="holo-scene" key={idx} aria-live="polite">
        <div className="holo-icon"><span>{scene.icone}</span></div>
        <small className="holo-count">CENA {idx + 1} DE {scenes.length}</small>
        {scene.titulo && <h2 className="holo-title" data-text={scene.titulo}>{scene.titulo}</h2>}
        <Caption text={scene.fala} seconds={seconds} playing={playing} />
        {scene.numero && (
          <div className="holo-number">
            <strong><CountUp value={scene.numero.valor} /></strong>
            <span>{scene.numero.unidade}</span>
            {scene.numero.rotulo && <small>{scene.numero.rotulo}</small>}
          </div>
        )}
        {scene.pontos.length > 0 && (
          <ul className="holo-points">
            {scene.pontos.map((p, i) => <li key={p} style={{ animationDelay: `${0.9 + i * 0.45}s` }}>{p}</li>)}
          </ul>
        )}
      </article>
      <div className="holo-controls">
        <button type="button" onClick={() => cmd("prev")} disabled={idx === 0} aria-label="Cena anterior">⟵</button>
        <button type="button" className="is-main" onClick={() => cmd(playing ? "pause" : "play")} aria-label={playing ? "Pausar" : "Continuar"}>{playing ? "❚❚" : "▶"}</button>
        <button type="button" onClick={() => cmd("next")} aria-label="Próxima cena">⟶</button>
      </div>
      {image && <span className="holo-credit">Imagem: Wikipédia</span>}
    </>
  );
}

function Recipe({ data, image, api, speak, stop, onSend, onClose }) {
  useWakeLock();
  const [step, setStep] = useState(0);
  const [checked, setChecked] = useState({});
  const [shopping, setShopping] = useState("");
  const { say, halt } = useNarration({ speak, stop, enabled: true });
  const total = data.passos.length;
  const current = data.passos[step];

  const sayStep = useCallback((i) => {
    const p = data.passos[i];
    say(`Passo ${i + 1}. ${p.texto}${i === total - 1 && data.dica ? ` Dica de ouro: ${data.dica}` : ""}`);
  }, [data, say, total]);

  useEffect(() => {
    say(`${data.fala || data.titulo}. Separe os ingredientes e diga "próximo passo" quando estiver pronto.`);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const goStep = useCallback((i) => {
    const n = Math.max(0, Math.min(total - 1, i));
    setStep(n);
    sayStep(n);
  }, [sayStep, total]);

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
                <button type="button" className={checked[i] ? "is-on" : ""} onClick={() => setChecked((c) => ({ ...c, [i]: !c[i] }))} aria-pressed={Boolean(checked[i])}>
                  <i aria-hidden="true">{checked[i] ? "✓" : ""}</i>{ing}
                </button>
              </li>
            ))}
          </ul>
          <button type="button" className="holo-cta" onClick={toShopping} disabled={done === data.ingredientes.length}>🛒 FALTANTES PARA A LISTA DE COMPRAS</button>
          {shopping && <p className="holo-ok" role="status">{shopping}</p>}
        </section>
        <section className="holo-panel holo-steps">
          <div className="holo-step-now" key={step}>
            <small>PASSO {step + 1} DE {total}</small>
            <p>{current.texto}</p>
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

export default function HoloStage({ api, request, onClose, onSend, onSpeak, onStop }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [line, setLine] = useState(0);
  const image = useWikiImage(data?.wiki || "");

  useEffect(() => {
    let alive = true;
    setData(null);
    setError("");
    api("/api/holo", { method: "POST", body: JSON.stringify({ query: request.query, kind: request.kind }), timeout: 60_000 })
      .then((d) => alive && setData(d))
      .catch((err) => alive && setError(err.message || "Não consegui montar o holograma."));
    return () => {
      alive = false;
    };
  }, [api, request]);

  useEffect(() => {
    if (data || error) return undefined;
    const t = setInterval(() => setLine((n) => (n + 1) % LOADING_LINES.length), 1400);
    return () => clearInterval(t);
  }, [data, error]);

  const close = useCallback(() => {
    onStop();
    onClose();
  }, [onClose, onStop]);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && close();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [close]);

  return createPortal(
    <div className={`holo-root${data ? ` is-${data.tipo}` : ""}`} role="dialog" aria-modal="true" aria-label="Holograma do JARVIS">
      {image && <div className="holo-bg" style={{ backgroundImage: `url("${image.src}")` }} aria-hidden="true" />}
      <div className="holo-grid" aria-hidden="true" />
      <div className="holo-scan" aria-hidden="true" />
      <button type="button" className="holo-close" onClick={close} aria-label="Fechar o holograma">✕</button>

      {!data && !error && (
        <div className="holo-loading" role="status">
          <div className="holo-rings" aria-hidden="true"><i /><i /><i /><b>✦</b></div>
          <small>MONTANDO O HOLOGRAMA</small>
          <h2>{request.query}</h2>
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
      {data?.tipo === "apresentacao" && <Presentation data={data} image={image} speak={onSpeak} stop={onStop} onClose={close} />}
      {data?.tipo === "receita" && <Recipe data={data} image={image} api={api} speak={onSpeak} stop={onStop} onSend={onSend} onClose={close} />}
    </div>,
    document.body,
  );
}

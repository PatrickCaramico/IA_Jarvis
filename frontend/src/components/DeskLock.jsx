import { useCallback, useEffect, useRef, useState } from "react";
import RoboAvatar from "./RoboAvatar.jsx";
import ProgressBar from "./ProgressBar.jsx";
import { FaceCircle } from "./LockOrbe.jsx";
import useNow from "../hooks/useNow.js";
import { hexToRgb } from "../utils/desk.js";
import { startPacman, usePoke } from "../utils/poke.js";
import { isLite } from "../utils/lite.js";
import DeskLockBg, { BG_EVENT, LOCK_BGS, readBg, saveBg } from "./DeskLockBg.jsx";
import "../desk.css";

// V8.8.0 (ideia 11): BLOQUEIO DO MODO DESK. Em vez da tela de bloqueio clássica, o robô JARVIS grande no centro,
// fazendo coisas: brincadeiras sozinho, olhos que seguem o mouse, reage quando você clica (e às cutucadas: na 5ª,
// o Pac-Man no app do Windows), um balão de fala que troca (hora, clima, contagens do dia e frases) e o mini-jogo
// "Pegue as estrelas". O DESBLOQUEIO é o mesmo de sempre (rosto ou PIN): esta tela só recebe os botões prontos.
// Com a tela bloqueada, ela só lê /api/desk/lockface (aparência e CONTAGENS, nada pessoal) e /api/weather.

export const GAME_SECONDS = 30;
export const STAR_LIFE_MS = 1700;
const RECORD_KEY = "jarvis.deskLock.record";
const PHRASES = [
  "Estou de olho em tudo por aqui, senhor. 👀",
  "Pode ir tranquilo: guardo o PC enquanto isso.",
  "Que tal uma pausa para um copo d'água? 💧",
  "Quando voltar, é só olhar para a câmera.",
  "Clique em mim… se tiver coragem. 😏",
  "Quer jogar enquanto espera? Toque em ⭐ JOGAR.",
];

/** As falas do balão, a partir do que a tela bloqueada pode mostrar (só contagens, nada pessoal). */
export function bubbleLines(face, weather, now = new Date()) {
  const lines = [];
  const hour = now.getHours();
  const hi = hour < 5 ? "Boa noite" : hour < 12 ? "Bom dia" : hour < 18 ? "Boa tarde" : "Boa noite";
  lines.push(`${hi}! Agora são ${String(hour).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}.`);
  if (weather && Number.isFinite(weather.temperature)) {
    lines.push(`Lá fora: ${weather.temperature}° e ${weather.description}${weather.rain_probability != null ? ` (chuva ${weather.rain_probability}%)` : ""}.`);
  }
  if (face) {
    if (face.proximo_lembrete) lines.push(`Você tem ${face.lembretes_hoje} ${face.lembretes_hoje === 1 ? "lembrete" : "lembretes"} hoje; o próximo é às ${face.proximo_lembrete}. ⏰`);
    if (face.tarefas > 0) lines.push(`${face.tarefas} ${face.tarefas === 1 ? "tarefa pendente" : "tarefas pendentes"} esperando você. ☰`);
    else lines.push("Nenhuma tarefa pendente. Missão cumprida! 🎉");
    if (face.ofensiva > 0) lines.push(`Ofensiva de ${face.ofensiva} ${face.ofensiva === 1 ? "dia" : "dias"}! Não deixe apagar. 🔥`);
  }
  return [...lines, ...PHRASES];
}

/** Uma estrela nova num ponto aleatório em volta do robô (porcentagens da área do jogo, longe do centro). */
export function randomStar(rnd = Math.random, id = 0) {
  const angle = rnd() * Math.PI * 2;
  const dist = 0.28 + rnd() * 0.18; // fora do robô, dentro da área
  return { id, x: 50 + Math.cos(angle) * dist * 100, y: 50 + Math.sin(angle) * dist * 100 * 0.8, born: Date.now() };
}

// V8.9.0 (ideia 12): AS ATIVIDADES do robô. Ele vai alternando sozinho, uma de cada vez, com um descanso no
// centro entre elas: andar de um lado pro outro, dormir de cobertinha (acorda quando você mexe), tomar café, ler,
// dançar (mais animado com música tocando), embaixadinha e bolhas. Qualquer interação o traz de volta ao centro.
export const ACTIVITIES = ["andar", "dormir", "cafe", "ler", "dancar", "bola", "bolhas"];
export const CALM_ACTIVITIES = ["cafe", "ler", "dormir"]; // no modo leve: só as calmas
export const WAKE_MOVE_PX = 40;
const ACT_SAY = {
  andar: "Vou dar uma voltinha… 🚶",
  dormir: "Zzz… 😴 (mexa o mouse ou toque para me acordar)",
  acordando: "Uaaah… acordei! 🥱",
  cafe: "Hora do cafezinho. ☕",
  ler: "Deixa eu ler um pouquinho… 📖",
  dancar: "Um, dois, um, dois… 💃",
  bola: "Olha a embaixadinha! ⚽",
  bolhas: "Bolhas de sabão! 🫧",
};
const ACT_FACE = { dormir: "dormindo", acordando: "bocejo", dancar: "feliz", bolhas: "feliz", cafe: "repouso" };

/** A próxima atividade: diferente da anterior; com música tocando, dançar fica bem mais provável. */
export function nextActivity(prev, { music = false, lite = false, rnd = Math.random } = {}) {
  let pool = lite ? CALM_ACTIVITIES : ACTIVITIES;
  if (music && !lite) pool = [...pool, "dancar", "dancar", "dancar"];
  const options = pool.filter((a) => a !== prev);
  return options[Math.floor(rnd() * options.length)] || pool[0];
}

/** Quanto tempo cada atividade dura (ms). Dormir dura mais; andar dá duas voltas inteiras. */
export function activityMs(act, rnd = Math.random) {
  if (act === "dormir") return 35000 + rnd() * 20000;
  if (act === "andar") return 24000;
  return 15000 + rnd() * 9000;
}

/** A fala do balão para a atividade (e para a música, quando está dançando com ela). */
export function activityLine(act, music = false) {
  if (act === "dancar" && music) return "Essa música está boa demais! 🎶";
  return ACT_SAY[act] || "";
}

function useActivity(enabled, musicRef) {
  const [act, setAct] = useState(null); // { id, at } ou null (parado no centro)
  const [cycle, setCycle] = useState(0);
  const prev = useRef(null);
  const waking = useRef(false);
  useEffect(() => {
    if (!enabled) return undefined;
    let t = 0;
    const rest = (ms) => {
      setAct(null);
      t = setTimeout(go, ms);
    };
    const go = () => {
      const id = nextActivity(prev.current, { music: musicRef.current, lite: isLite() });
      prev.current = id;
      setAct({ id, at: Date.now() });
      t = setTimeout(() => rest(9000 + Math.random() * 8000), activityMs(id));
    };
    if (waking.current) {
      waking.current = false;
      t = setTimeout(() => rest(9000 + Math.random() * 6000), 2000);
    } else {
      t = setTimeout(() => (act ? rest(9000) : go()), act ? 0 : 7000 + Math.random() * 5000);
    }
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- recomeça só ao ligar/desligar ou ao interromper
  }, [enabled, cycle]);
  /** Interação: acorda (se dormindo) ou volta para o centro e recomeça o ciclo. */
  const interrupt = useCallback(() => {
    setAct((a) => {
      if (a?.id === "dormir") {
        waking.current = true;
        return { id: "acordando", at: Date.now() };
      }
      return null;
    });
    setCycle((c) => c + 1);
  }, []);
  return [enabled ? act : null, interrupt];
}

function readRecord() {
  try {
    return Number(localStorage.getItem(RECORD_KEY)) || 0;
  } catch {
    return 0;
  }
}

function useStarsGame(onCatch) {
  const [playing, setPlaying] = useState(false);
  const [left, setLeft] = useState(0);
  const [score, setScore] = useState(0);
  const [stars, setStars] = useState([]);
  const [record, setRecord] = useState(readRecord);
  const [result, setResult] = useState(null);
  const idRef = useRef(0);
  const scoreRef = useRef(0);
  useEffect(() => {
    if (!playing) return undefined;
    const spawn = setInterval(() => setStars((s) => [...s.filter((x) => Date.now() - x.born < STAR_LIFE_MS), randomStar(Math.random, ++idRef.current)]), 650);
    const clean = setInterval(() => setStars((s) => s.filter((x) => Date.now() - x.born < STAR_LIFE_MS)), 250);
    const tick = setInterval(() => setLeft((t) => t - 1), 1000);
    return () => {
      clearInterval(spawn);
      clearInterval(clean);
      clearInterval(tick);
    };
  }, [playing]);
  useEffect(() => {
    if (!playing || left > 0) return;
    setPlaying(false);
    setStars([]);
    const final = scoreRef.current;
    const best = Math.max(final, readRecord());
    try {
      localStorage.setItem(RECORD_KEY, String(best));
    } catch {
      /* sem armazenamento */
    }
    setResult({ score: final, novo: final > record && final > 0 });
    setRecord(best);
  }, [left, playing, record]);
  const start = () => {
    scoreRef.current = 0;
    setScore(0);
    setResult(null);
    setLeft(GAME_SECONDS);
    setPlaying(true);
  };
  const stop = () => {
    setPlaying(false);
    setStars([]);
  };
  const catchStar = (id) => {
    setStars((s) => s.filter((x) => x.id !== id));
    scoreRef.current += 1;
    setScore(scoreRef.current);
    onCatch?.();
  };
  return { playing, left, score, stars, record, result, start, stop, catchStar };
}

export default function DeskLock({ api, phase, name, message, photoUrl, scan, pinBlock, mainLabel, onMain, mainVisible = true,
  failedActions = null, phoneButtons = null, jarvisState = "idle", onClassic = null, hint = "", phone = false,
  onUpdate = null, updateCount = 0, updateNote = "", updateProgress = null }) {
  const now = useNow(true);
  const [face, setFace] = useState(null);
  const [weather, setWeather] = useState(null);
  const [line, setLine] = useState(0);
  const [reaction, setReaction] = useState(null);
  const reactTimer = useRef(0);
  const react = useCallback((expr, ms = 1600) => {
    clearTimeout(reactTimer.current);
    setReaction(expr);
    reactTimer.current = setTimeout(() => setReaction(null), ms);
  }, []);
  useEffect(() => () => clearTimeout(reactTimer.current), []);
  const game = useStarsGame(() => react("conseguiu", 700));
  const { mood, poke } = usePoke(() => { if (!startPacman()) react("bravo", 2500); });
  const [hintShown, setHintShown] = useState(Boolean(hint)); // V8.8.1: no celular, a 1ª fala explica como entrar
  useEffect(() => {
    if (!hint) return undefined;
    setHintShown(true);
    const t = setTimeout(() => setHintShown(false), 9000);
    return () => clearTimeout(t);
  }, [hint]);

  useEffect(() => {
    if (!api) return undefined;
    let alive = true;
    const load = () => api("/api/desk/lockface").then((d) => alive && setFace(d)).catch(() => {});
    load();
    api("/api/weather").then((w) => alive && setWeather(w)).catch(() => {});
    const t = setInterval(load, 60000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [api]);
  const [waving, setWaving] = useState(false); // o "aceno" (o robô não tem braços: uma mãozinha acena ao lado)
  useEffect(() => {
    let off = 0;
    const t = setInterval(() => {
      setWaving(true);
      off = setTimeout(() => setWaving(false), 2200);
    }, 21000);
    return () => {
      clearInterval(t);
      clearTimeout(off);
    };
  }, []);
  const [bg, setBg] = useState(readBg);
  const [picking, setPicking] = useState(false);
  useEffect(() => {
    const on = (e) => setBg(e.detail || readBg());
    window.addEventListener(BG_EVENT, on);
    return () => window.removeEventListener(BG_EVENT, on);
  }, []);
  const musicRef = useRef(false);
  const [music, setMusic] = useState(false);
  useEffect(() => {
    if (!api) return undefined;
    let alive = true;
    const check = () => {
      if (isLite() || document.hidden) return;
      api("/api/integrations/spotify/track")
        .then((d) => { if (alive) { musicRef.current = d?.state === "playing"; setMusic(musicRef.current); } })
        .catch(() => { musicRef.current = false; });
    };
    check();
    const t = setInterval(check, 20000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [api]);
  const lines = bubbleLines(face, weather, now);
  useEffect(() => {
    const t = setInterval(() => setLine((n) => n + 1), 6500);
    return () => clearInterval(t);
  }, []);

  const scanning = phase === "scanning";
  const showFace = Boolean(scan) || scanning || (phase === "verified" && Boolean(photoUrl));
  const calm = !showFace && !pinBlock && !game.playing && phase !== "verified" && phase !== "failed" && !mood;
  const [act, interrupt] = useActivity(calm, musicRef);
  useEffect(() => { // dormindo: mexer o mouse (de verdade, não um tremidinho), tocar ou teclar acorda
    if (act?.id !== "dormir") return undefined;
    let start = null;
    const wake = () => interrupt();
    const move = (e) => {
      if (!start) start = { x: e.clientX, y: e.clientY };
      else if (Math.hypot(e.clientX - start.x, e.clientY - start.y) > WAKE_MOVE_PX) wake();
    };
    const t = setTimeout(() => { // um respiro: quem acabou de mexer não acorda ele na hora
      window.addEventListener("mousemove", move);
      window.addEventListener("pointerdown", wake);
      window.addEventListener("keydown", wake);
    }, 1500);
    return () => {
      clearTimeout(t);
      window.removeEventListener("mousemove", move);
      window.removeEventListener("pointerdown", wake);
      window.removeEventListener("keydown", wake);
    };
  }, [act?.id, interrupt]);
  const accent = face?.cor || "#22d3ee";
  const clickRobot = (e) => {
    e.stopPropagation();
    if (act?.id === "dormir") return interrupt(); // a 1ª cutucada só acorda
    if (act) interrupt();
    poke();
    if (!mood) react(Math.random() < 0.5 ? "feliz" : "rindo");
  };
  const expr = mood || reaction || ACT_FACE[act?.id] || null;
  const actSay = act && (act.id === "dormir" || act.id === "acordando" || now - act.at < 6000) ? activityLine(act.id, music) : "";
  const state = scanning ? "processing" : jarvisState === "speaking" ? "speaking" : "idle";
  const say = hint && (hintShown || phase === "failed") ? hint
    : phase === "failed" && message ? message
    : phase === "verified" ? `Bem-vindo de volta${name ? `, ${name}` : ""}! 💙`
      : scanning ? "Olhe para a câmera… estou te reconhecendo."
        : game.playing ? `⭐ ${game.score} · ${game.left}s`
          : game.result ? (game.result.novo ? `Recorde novo: ${game.result.score} estrelas! 🏆` : `Você pegou ${game.result.score} ${game.result.score === 1 ? "estrela" : "estrelas"}. Recorde: ${game.record}.`)
            : mood === "comendo" ? "Agora você me irritou! 😤" : mood ? "Ei! Pare de me cutucar! 😠"
              : actSay || lines[line % lines.length];

  return (
    <div className={`dkl${phone ? " is-phone" : ""}${bg !== "escuro" ? ` has-bg bg-${bg}` : ""}`} role="main" style={{ "--dk-accent": accent, "--dk-accent-rgb": hexToRgb(accent) }}>
      <DeskLockBg bg={bg} />
      <div className="dkl-glow" aria-hidden="true" />
      <header className="dkl-top">
        <div className="dkl-clock">{now.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</div>
        <div className="dkl-date">{now.toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" })}</div>
      </header>

      {pinBlock ? <div className="dkl-pin">{pinBlock}</div> : (
        <div className="dkl-stage">
          <div className="dkl-game" aria-hidden={!game.playing}>
            {game.stars.map((s) => (
              <button type="button" key={s.id} className="dkl-star" style={{ left: `${s.x}%`, top: `${s.y}%` }}
                onClick={(e) => { e.stopPropagation(); game.catchStar(s.id); }} aria-label="Pegar a estrela">⭐</button>
            ))}
          </div>
          {showFace ? (
            <div className="dkl-face"><FaceCircle scan={scan} phase={phase} photoUrl={photoUrl} /></div>
          ) : (
            <div className={`dkl-actor${act ? ` is-${act.id}` : ""}${music ? " is-music" : ""}`}>
              <button type="button" className={`dkl-robot${mood ? " is-poked" : ""}`} onClick={clickRobot} aria-label={`${face?.nome || "JARVIS"}: clique para interagir`}>
                <RoboAvatar avatar={expr ? { ...(face?.avatar || {}), expressao: expr } : face?.avatar} tema={face?.tema}
                  state={expr ? "idle" : state} size={260} still={Boolean(expr)} />
              </button>
              <ActivityProps act={act?.id} />
            </div>
          )}
          {waving && !act && !showFace && !game.playing && <span className="dkl-wave" aria-hidden="true">👋</span>}
          <p className="dkl-bubble" key={say} aria-live="polite">{say}</p>
        </div>
      )}

      <footer className="dkl-actions">
        {mainVisible && !pinBlock && (
          <button type="button" className="dkl-main" onClick={(e) => { e.stopPropagation(); onMain(); }}>
            {phase === "verified" ? "➜" : "🙂"} {mainLabel}
            {phase !== "verified" && <span className="dkl-key">ESPAÇO</span>}
          </button>
        )}
        {phoneButtons}
        {failedActions}
        {!pinBlock && !showFace && (
          <div className="dkl-row">
            {game.playing ? <button type="button" className="dkl-chip" onClick={(e) => { e.stopPropagation(); game.stop(); }}>⏹ PARAR O JOGO</button>
              : <button type="button" className="dkl-chip" onClick={(e) => { e.stopPropagation(); game.start(); }}>⭐ JOGAR{game.record ? ` · recorde ${game.record}` : ""}</button>}
            <button type="button" className={`dkl-chip${picking ? " is-on" : ""}`} aria-expanded={picking}
              onClick={(e) => { e.stopPropagation(); setPicking((v) => !v); }}>🖼 FUNDO</button>
            {/* V8.11: ATUALIZAR (com a bolinha de versões novas) e o Branding Book também no bloqueio do robô */}
            {onUpdate && (
              <button type="button" className="dkl-chip" onClick={(e) => { e.stopPropagation(); onUpdate(); }}
                title={phone ? "Procurar e instalar a versão nova do app" : "Baixar a versão mais nova do JARVIS e reiniciar"}>
                {phone ? "⟳ ATUALIZAR APP" : "⟳ ATUALIZAR"}
                {!phone && updateCount > 0 && (
                  <span className="upd-badge" aria-label={`${updateCount} ${updateCount === 1 ? "atualização disponível" : "atualizações disponíveis"}`}>{updateCount}</span>
                )}
              </button>
            )}
            {!phone && (
              <button type="button" className="dkl-chip" title="Identidade visual do JARVIS"
                onClick={(e) => { e.stopPropagation(); window.dispatchEvent(new CustomEvent("jarvis-open-branding")); }}>📘 BRANDING</button>
            )}
            {onClassic && !phone && <button type="button" className="dkl-chip is-ghost" onClick={(e) => { e.stopPropagation(); onClassic(); }}>◐ BLOQUEIO CLÁSSICO</button>}
          </div>
        )}
        {updateProgress != null && <div className="dkl-update"><ProgressBar pct={updateProgress} label="Atualizando o app" /></div>}
        {updateNote && <p className="dkl-update-note" role="status">{updateNote}</p>}
        {picking && !pinBlock && !showFace && (
          <div className="dkl-bgpick" role="radiogroup" aria-label="Papel de parede do bloqueio">
            {LOCK_BGS.map((b) => (
              <button type="button" key={b.id} role="radio" aria-checked={bg === b.id} className={`dkl-swatch sw-${b.id}${bg === b.id ? " is-on" : ""}`}
                onClick={(e) => { e.stopPropagation(); setBg(saveBg(b.id)); }}>
                <span aria-hidden="true">{b.emoji}</span>{b.label}
              </button>
            ))}
          </div>
        )}
      </footer>
    </div>
  );
}

/** Os objetos de cada atividade (cobertinha, xícara, livro, notas, bola, bolhas): só enfeite, sem clique. */
function ActivityProps({ act }) {
  if (!act) return null;
  if (act === "dormir" || act === "acordando") {
    return (
      <span className="dkl-props" aria-hidden="true">
        <i className="dkl-blanket" />
        {act === "dormir" && <span className="dkl-zzz"><i>z</i><i>z</i><i>Z</i></span>}
      </span>
    );
  }
  if (act === "cafe") return <span className="dkl-props" aria-hidden="true"><span className="dkl-cup">☕<i className="dkl-steam" /><i className="dkl-steam" /><i className="dkl-steam" /></span></span>;
  if (act === "ler") return <span className="dkl-props" aria-hidden="true"><span className="dkl-book"><i className="dkl-page" />📖</span></span>;
  if (act === "dancar") return <span className="dkl-props" aria-hidden="true"><span className="dkl-notes">{["♪", "♫", "♬", "♪", "♫"].map((n, i) => <i key={i}>{n}</i>)}</span></span>;
  if (act === "bola") return <span className="dkl-props" aria-hidden="true"><i className="dkl-ball">⚽</i></span>;
  if (act === "bolhas") return <span className="dkl-props" aria-hidden="true"><span className="dkl-soap">{[0, 1, 2, 3, 4, 5].map((i) => <i key={i} />)}</span></span>;
  return null;
}

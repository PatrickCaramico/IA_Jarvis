import { useCallback, useEffect, useRef, useState } from "react";
import RoboAvatar from "./RoboAvatar.jsx";
import { FaceCircle } from "./LockOrbe.jsx";
import useNow from "../hooks/useNow.js";
import { hexToRgb } from "../utils/desk.js";
import { startPacman, usePoke } from "../utils/poke.js";
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
  failedActions = null, phoneButtons = null, jarvisState = "idle", onClassic = null }) {
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
  const lines = bubbleLines(face, weather, now);
  useEffect(() => {
    const t = setInterval(() => setLine((n) => n + 1), 6500);
    return () => clearInterval(t);
  }, []);

  const scanning = phase === "scanning";
  const showFace = Boolean(scan) || scanning || (phase === "verified" && Boolean(photoUrl));
  const accent = face?.cor || "#22d3ee";
  const clickRobot = (e) => {
    e.stopPropagation();
    poke();
    if (!mood) react(Math.random() < 0.5 ? "feliz" : "rindo");
  };
  const expr = mood || reaction;
  const state = scanning ? "processing" : jarvisState === "speaking" ? "speaking" : "idle";
  const say = phase === "failed" && message ? message
    : phase === "verified" ? `Bem-vindo de volta${name ? `, ${name}` : ""}! 💙`
      : scanning ? "Olhe para a câmera… estou te reconhecendo."
        : game.playing ? `⭐ ${game.score} · ${game.left}s`
          : game.result ? (game.result.novo ? `Recorde novo: ${game.result.score} estrelas! 🏆` : `Você pegou ${game.result.score} ${game.result.score === 1 ? "estrela" : "estrelas"}. Recorde: ${game.record}.`)
            : mood === "comendo" ? "Agora você me irritou! 😤" : mood ? "Ei! Pare de me cutucar! 😠"
              : lines[line % lines.length];

  return (
    <div className="dkl" role="main" style={{ "--dk-accent": accent, "--dk-accent-rgb": hexToRgb(accent) }}>
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
            <button type="button" className={`dkl-robot${mood ? " is-poked" : ""}`} onClick={clickRobot} aria-label={`${face?.nome || "JARVIS"}: clique para interagir`}>
              <RoboAvatar avatar={expr ? { ...(face?.avatar || {}), expressao: expr } : face?.avatar} tema={face?.tema}
                state={expr ? "idle" : state} size={260} still={Boolean(expr)} />
            </button>
          )}
          {waving && !showFace && !game.playing && <span className="dkl-wave" aria-hidden="true">👋</span>}
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
            {onClassic && <button type="button" className="dkl-chip is-ghost" onClick={(e) => { e.stopPropagation(); onClassic(); }}>◐ BLOQUEIO CLÁSSICO</button>}
          </div>
        )}
      </footer>
    </div>
  );
}

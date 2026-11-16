import { useCallback, useEffect, useRef, useState } from "react";

// V8.6.0: IRRITAR O JARVIS. Cada clique rápido no avatar é uma "cutucada": ele fica surpreso, depois bravo e, na
// 5ª cutucada seguida, perde a paciência (no app do Windows ele sai correndo atrás do mouse, tipo Pac-Man).
export const POKES_TO_ANGRY = 5;
export const POKE_WINDOW_MS = 3000;

/** Humor depois de `count` cutucadas seguidas. */
export function pokeMood(count) {
  if (count >= POKES_TO_ANGRY) return "comendo";
  if (count >= 3) return "bravo";
  if (count >= 1) return "surpreso";
  return null;
}

export function usePoke(onAngry) {
  const [count, setCount] = useState(0);
  const timer = useRef(0);
  const cb = useRef(onAngry);
  useEffect(() => { cb.current = onAngry; }, [onAngry]);
  useEffect(() => () => clearTimeout(timer.current), []);
  const poke = useCallback(() => {
    clearTimeout(timer.current);
    setCount((c) => {
      const n = c + 1;
      if (n >= POKES_TO_ANGRY) setTimeout(() => cb.current?.(), 0);
      return n;
    });
    timer.current = setTimeout(() => setCount(0), POKE_WINDOW_MS);
  }, []);
  return { mood: pokeMood(count), poke };
}

/** Manda o app do Windows soltar o avatar atrás do mouse. Falso fora do app. */
export function startPacman() {
  const fn = window.pywebview?.api?.pacman_start;
  if (!fn) return false;
  fn();
  return true;
}

import { useMemo } from "react";

// V8.9.0 (ideia 12): PAPÉIS DE PAREDE ANIMADOS do bloqueio do Modo Desk. Feitos só com CSS (sem fotos pesadas):
// cada pedacinho anima apenas transform/opacity, que a placa de vídeo faz sozinha (não trava o PC).
// No modo leve e com "reduzir movimento", tudo fica parado.

export const LOCK_BGS = [
  { id: "escuro", label: "Escuro do app", emoji: "◼" },
  { id: "estrelas", label: "Céu estrelado", emoji: "✨" },
  { id: "aurora", label: "Aurora", emoji: "🌌" },
  { id: "cidade", label: "Cidade à noite", emoji: "🌃" },
  { id: "porsol", label: "Pôr do sol", emoji: "🌇" },
];
export const BG_KEY = "jarvis.deskLock.bg";
export const BG_EVENT = "jarvis-desklock-bg";

export function validBg(id) {
  return LOCK_BGS.some((b) => b.id === id) ? id : "escuro";
}

export function readBg() {
  try {
    return validBg(localStorage.getItem(BG_KEY));
  } catch {
    return "escuro";
  }
}

/** Guarda o fundo escolhido (só neste aparelho) e avisa as telas abertas. */
export function saveBg(id) {
  const bg = validBg(id);
  try {
    localStorage.setItem(BG_KEY, bg);
  } catch {
    /* sem armazenamento: vale só até fechar */
  }
  if (typeof window !== "undefined") window.dispatchEvent(new CustomEvent(BG_EVENT, { detail: bg }));
  return bg;
}

/** Sorteio com semente: o mesmo céu e a mesma cidade toda vez (nada pula ao redesenhar). */
export function seeded(seed = 1) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** As estrelinhas do céu: posição (%), tamanho (px) e o ritmo do pisca-pisca. */
export function starField(n = 70, seed = 7) {
  const rnd = seeded(seed);
  return Array.from({ length: n }, (_, i) => ({
    id: i,
    x: +(rnd() * 100).toFixed(2),
    y: +(rnd() * 78).toFixed(2),
    size: rnd() < 0.15 ? 3 : rnd() < 0.5 ? 2 : 1,
    dur: +(2 + rnd() * 4).toFixed(2),
    delay: +(-rnd() * 6).toFixed(2),
  }));
}

/** Os prédios da cidade: largura e altura (%) e as janelas que acendem e apagam em ritmos diferentes. */
export function cityBlocks(seed = 11) {
  const rnd = seeded(seed);
  const blocks = [];
  let x = 0;
  let id = 0;
  while (x < 100) {
    const w = 5 + rnd() * 7;
    const h = 18 + rnd() * 34;
    const windows = Array.from({ length: 3 + Math.floor(rnd() * 5) }, (_, k) => ({
      id: k,
      x: +(12 + rnd() * 70).toFixed(1),
      y: +(8 + rnd() * 80).toFixed(1),
      dur: +(5 + rnd() * 12).toFixed(1),
      delay: +(-rnd() * 15).toFixed(1),
    }));
    blocks.push({ id: id++, x: +x.toFixed(2), w: +w.toFixed(2), h: +h.toFixed(2), windows });
    x += w + rnd() * 1.2;
  }
  return blocks;
}

export default function DeskLockBg({ bg = "escuro" }) {
  const stars = useMemo(() => (bg === "estrelas" ? starField(70) : bg === "cidade" ? starField(28, 3) : []), [bg]);
  const city = useMemo(() => (bg === "cidade" ? cityBlocks() : []), [bg]);
  if (bg === "escuro") return null;
  return (
    <div className={`dkl-bg is-${bg}`} aria-hidden="true">
      {stars.map((s) => (
        <i key={s.id} className="dkl-twinkle" style={{ left: `${s.x}%`, top: `${s.y}%`, width: s.size, height: s.size,
          animationDuration: `${s.dur}s`, animationDelay: `${s.delay}s` }} />
      ))}
      {bg === "estrelas" && <i className="dkl-shoot" />}
      {bg === "aurora" && <>
        <i className="dkl-band is-1" /><i className="dkl-band is-2" /><i className="dkl-band is-3" />
        <i className="dkl-hills" />
      </>}
      {bg === "cidade" && <>
        <i className="dkl-moon" />
        <div className="dkl-city">
          {city.map((b) => (
            <div key={b.id} className="dkl-bld" style={{ left: `${b.x}%`, width: `${b.w}%`, height: `${b.h}%` }}>
              {b.windows.map((w) => (
                <i key={w.id} className="dkl-win" style={{ left: `${w.x}%`, top: `${w.y}%`, animationDuration: `${w.dur}s`, animationDelay: `${w.delay}s` }} />
              ))}
            </div>
          ))}
        </div>
      </>}
      {bg === "porsol" && <>
        <i className="dkl-sun" />
        <i className="dkl-cloud is-1" /><i className="dkl-cloud is-2" /><i className="dkl-cloud is-3" />
        <i className="dkl-sea" />
      </>}
    </div>
  );
}

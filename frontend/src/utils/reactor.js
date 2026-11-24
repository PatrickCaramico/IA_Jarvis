// V9.4.2: PERSONALIZAR O REATOR (só o orbe do centro da central): forma, cor, contraste, brilho, velocidade e fios.
// Fica salvo NESTE aparelho (o celular pode querer uma forma mais leve que o PC). Puro, testado em tests/reactor.test.js.

export const KEY = "jarvis.reactor";
export const EVENT = "jarvis-reactor-changed";

// peso: o quanto a forma custa para o aparelho redesenhar (a central mostra para ajudar a escolher)
export const SHAPES = [
  // pesos medidos na central (tempo de processador em 5 s): fios e minimal ~0,3 s, reator ~0,4 s, emaranhado ~4,7 s
  { id: "fios", label: "Fios", hint: "O anel de fios do JARVIS (padrão)", weight: "leve" },
  { id: "minimal", label: "Minimal", hint: "Três anéis e um núcleo, bem discreto", weight: "leve" },
  { id: "reator", label: "Reator", hint: "O Reator Arc clássico, com anéis", weight: "médio" },
  { id: "emaranhado", label: "Emaranhado", hint: "Linhas vivas que pulsam com a voz; pesa bem mais que as outras", weight: "pesado" },
];

export const COLORS = [
  ["#4fdcff", "Ciano JARVIS"], ["#3b82f6", "Azul"], ["#22c55e", "Verde"], ["#fbbf24", "Âmbar"],
  ["#ef4444", "Vermelho"], ["#a855f7", "Roxo"], ["#f472b6", "Rosa"], ["#f8fafc", "Branco"],
];

export const DEFAULTS = { shape: "fios", color: "#4fdcff", contrast: 100, glow: 100, speed: 100, wires: 18 };
const clamp = (v, lo, hi, d) => (Number.isFinite(Number(v)) ? Math.min(hi, Math.max(lo, Math.round(Number(v)))) : d);

/** Corrige qualquer valor estranho (de outra versão ou mexido à mão) para o que a central sabe desenhar. */
export function normalize(raw) {
  const r = raw && typeof raw === "object" ? raw : {};
  return {
    shape: SHAPES.some((s) => s.id === r.shape) ? r.shape : DEFAULTS.shape,
    color: /^#[0-9a-f]{6}$/i.test(r.color || "") ? r.color.toLowerCase() : DEFAULTS.color,
    contrast: clamp(r.contrast, 50, 160, DEFAULTS.contrast),
    glow: clamp(r.glow, 0, 200, DEFAULTS.glow),
    speed: clamp(r.speed, 25, 250, DEFAULTS.speed),
    wires: clamp(r.wires, 6, 30, DEFAULTS.wires),
  };
}

export function isDefault(cfg) {
  const n = normalize(cfg);
  return Object.keys(DEFAULTS).every((k) => n[k] === DEFAULTS[k]);
}

export function load(storage = globalThis.localStorage) {
  try {
    return normalize(JSON.parse(storage?.getItem(KEY) || "null"));
  } catch {
    return { ...DEFAULTS };
  }
}

export function save(cfg, storage = globalThis.localStorage) {
  const n = normalize(cfg);
  try {
    storage?.setItem(KEY, JSON.stringify(n));
  } catch {
    /* aba anônima: vale só nesta sessão */
  }
  try {
    globalThis.dispatchEvent?.(new CustomEvent(EVENT, { detail: n }));
  } catch {
    /* fora do navegador (testes) */
  }
  return n;
}

export function hexToRgb(hex) {
  const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex || "");
  return m ? [parseInt(m[1], 16), parseInt(m[2], 16), parseInt(m[3], 16)] : [79, 220, 255];
}

/** Matiz (0–359°) da cor. */
export function hue(hex) {
  const [r, g, b] = hexToRgb(hex).map((v) => v / 255);
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  if (max === min) return 0;
  const d = max - min;
  const h = max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return Math.round(((h * 60) + 360) % 360);
}

/** Variáveis CSS do orbe. Brilho 0 = sem a sombra luminosa (o que mais pesa para redesenhar a cada quadro). */
export function cssVars(cfg) {
  const n = normalize(cfg);
  return {
    "--rx-color": n.color,
    // o Reator clássico é desenhado em ciano (191°): gira o tom até a cor escolhida
    "--rx-hue": `${(hue(n.color) - 191 + 360) % 360}deg`,
    "--rx-contrast": (n.contrast / 100).toFixed(2),
    "--rx-glow": `${((n.glow / 100) * 5).toFixed(1)}px`,
    "--rx-slow": (100 / n.speed).toFixed(3),
  };
}

/** V9.4.4: saída de emergência. Abrir a central com ?reator=padrao no endereço volta o reator ao padrão (sem precisar
 *  clicar em nada, caso alguma forma atrapalhe a tela). Devolve true se resetou. */
export function resetFromUrl(search = globalThis.location?.search || "", storage = globalThis.localStorage) {
  try {
    if (new URLSearchParams(search).get("reator") !== "padrao") return false;
    storage?.removeItem(KEY);
    return true;
  } catch {
    return false;
  }
}

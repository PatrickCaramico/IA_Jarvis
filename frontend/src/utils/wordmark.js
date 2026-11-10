// Letras do nome "JARVIS" em traço (grade 56 x 72, traço 9). As mesmas de scripts/dev/gerar_kit_logo.py
// (conferido em tests/wordmark.test.js), para o nome sair igual na tela e no kit de logo.
export const LETTER_H = 72;
export const STROKE = 9;
export const GAP = 18;
export const LETTERS = {
  J: [56, ["M51.5 4.5 V58 L42 67.5 H14 L4.5 58 V50"]],
  A: [56, ["M4.5 67.5 V18 L18 4.5 H38 L51.5 18 V67.5", "M4.5 42 H51.5"]],
  R: [56, ["M4.5 67.5 V4.5 H40 L51.5 16 V30 L40 41.5 H4.5", "M32 41.5 L51.5 67.5"]],
  V: [56, ["M4.5 4.5 V40 L28 67.5 L51.5 40 V4.5"]],
  I: [9, ["M4.5 4.5 V67.5"]],
  S: [56, ["M51.5 4.5 H16 L4.5 16 V25 L15.5 36 H40.5 L51.5 47 V56 L40 67.5 H4.5"]],
};

// Lista de traços com a posição de cada letra: [{ d, x, letter }]
export function wordmarkStrokes(text = "JARVIS") {
  const out = [];
  let x = 0;
  for (const [i, ch] of [...text].entries()) {
    const [width, paths] = LETTERS[ch];
    paths.forEach((d) => out.push({ d, x, letter: i }));
    x += width + GAP;
  }
  return { strokes: out, width: x - GAP };
}

// O nome pode ser desenhado em traço? (só "JARVIS", com ou sem pontos)
export function isJarvisName(name) {
  return String(name || "").replace(/[^a-z]/gi, "").toUpperCase() === "JARVIS";
}
